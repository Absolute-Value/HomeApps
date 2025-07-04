# https://github.com/googleapis/python-genai

import uuid
import sqlite3
import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime

DATABASE_NAME = "/data/gemini_history.db"
MODEL_OPTIONS = {
    "Gemini-2.5-Flash-Lite": "gemini-2.5-flash-lite-preview-06-17",
    "Gemini-2.5-Flash": "gemini-2.5-flash",
}

st.set_page_config(
    page_title="Gemini",
    page_icon="💬",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title("Gemini")

client = genai.Client()

conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT,
    deleted INTEGER DEFAULT 0
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT,
    role TEXT,
    content TEXT,
    model TEXT,
    FOREIGN KEY(chat_id) REFERENCES chats(id)
)
""")
conn.commit()

if "cur_chat_id" not in st.session_state:
    st.session_state.cur_chat_id = None

if "edit_chat_id" not in st.session_state:
    st.session_state.edit_chat_id = None

if "is_new_chat" not in st.session_state:
    st.session_state.is_new_chat = False  # TrueならまだDB未保存の新規チャット

def load_chats():
    c.execute("SELECT id, title FROM chats WHERE deleted = 0 ORDER BY created_at DESC")
    return c.fetchall()

def load_messages(chat_id):
    c.execute("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))
    return [{"role": row[0], "content": row[1]} for row in c.fetchall()]

def create_new_chat_id():
    return str(uuid.uuid4())

def save_chat_and_message(chat_id, user_message, model=None):
    now = datetime.now().isoformat()
    c.execute("INSERT INTO chats (id, title, created_at, deleted) VALUES (?, ?, ?, 0)", (chat_id, "新しいチャット", now))
    c.execute("INSERT INTO messages (chat_id, role, content, model) VALUES (?, ?, ?, ?)", (chat_id, "user", user_message, model))
    conn.commit()

def update_chat_title(chat_id, new_title):
    c.execute("UPDATE chats SET title = ? WHERE id = ?", (new_title, chat_id))
    conn.commit()

def delete_chat(chat_id):
    c.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    c.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    conn.commit()

def add_message(chat_id, role, content, model=None):
    c.execute("INSERT INTO messages (chat_id, role, content, model) VALUES (?, ?, ?, ?)", (chat_id, role, content, model))
    conn.commit()

def generate_title(prompt):
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite-preview-06-17",
        contents=f"以下の発言から、10〜20文字のタイトルを生成してください。回答はタイトルだけでお願いします。\n\n{prompt}"
    )
    return response.text

with st.sidebar:
    if st.button(":heavy_plus_sign: 新しいチャット"):
        st.session_state.cur_chat_id = create_new_chat_id()
        st.session_state.is_new_chat = True
        st.rerun()

    selected_label = st.selectbox(":gear: モデル選択", list(MODEL_OPTIONS.keys()))
    st.session_state["openai_model"] = MODEL_OPTIONS[selected_label]

    st.subheader(":speech_balloon: チャット一覧")
    for chat_id, title in load_chats():
        if st.session_state.edit_chat_id == chat_id:
            new_title = st.text_input("タイトル編集", value=title, key=f"edit_{chat_id}")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("保存", key=f"save_{chat_id}"):
                    update_chat_title(chat_id, new_title)
                    st.session_state.edit_chat_id = None
                    st.rerun()
            with col2:
                if st.button("キャンセル", key=f"cancel_{chat_id}"):
                    st.session_state.edit_chat_id = None
                    st.rerun()
        else:
            col1, col2, col3 = st.columns([4, 1, 1], vertical_alignment="center")
            with col1:
                if st.button(title, key=f"title_{chat_id}"):
                    st.session_state.cur_chat_id = chat_id
                    st.session_state.is_new_chat = False
                    st.rerun()
            with col2:
                if st.button("✏️", key=f"edit_{chat_id}"):
                    st.session_state.edit_chat_id = chat_id
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"delete_{chat_id}"):
                    delete_chat(chat_id)
                    if st.session_state.cur_chat_id == chat_id:
                        st.session_state.cur_chat_id = None
                    st.rerun()

chat_id = st.session_state.cur_chat_id

if chat_id:
    if st.session_state.is_new_chat:
        messages = []
    else:
        messages = load_messages(chat_id)

    chat_history = []
    for msg in messages:
        if msg["role"] == "user":
            chat_history.append(types.UserContent(parts=[types.Part.from_text(text=msg["content"])]))
            avatar = None
        else:
            chat_history.append(types.Content(role="model", parts=[types.Part.from_text(text=msg["content"])]))
            avatar = ":material/robot_2:"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    chat = client.chats.create(
        model=st.session_state["openai_model"],
        history=chat_history,
    )
    if prompt := st.chat_input("質問してみましょう"):
        # 新規チャットか既存チャットかで保存処理を分岐
        if st.session_state.is_new_chat:
            save_chat_and_message(chat_id, prompt, st.session_state["openai_model"])
            st.session_state.is_new_chat = False
        else:
            add_message(chat_id, "user", prompt, st.session_state["openai_model"])

        # ユーザーメッセージ表示
        with st.chat_message("user"):
            st.markdown(prompt)

        # アシスタント応答生成
        with st.chat_message("assistant", avatar=":material/robot_2:"):
            response = chat.send_message_stream(prompt)
            response_text = ""
            message_placeholder = st.empty()
            for chunk in response:
                # chunkオブジェクトにtext属性があるか確認
                if hasattr(chunk, "text"):
                    try:
                        response_text += chunk.text
                        message_placeholder.markdown(response_text)
                    except Exception as e:
                        st.warning(e)
        add_message(chat_id, "assistant", response_text, model=st.session_state["openai_model"])

        # デフォルトタイトルなら要約して更新
        c.execute("SELECT title FROM chats WHERE id = ?", (chat_id,))
        current_title = c.fetchone()[0]
        if current_title == "新しいチャット":
            new_title = generate_title(prompt)
            update_chat_title(chat_id, new_title)

        st.rerun()
else:
    st.info("左のサイドバーからチャットを作成または選択してください。")
    st.warning("Geminiとの会話は学習に使用されます")