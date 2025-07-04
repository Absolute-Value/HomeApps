# https://console.groq.com/docs/overview

import sqlite3
import streamlit as st
from groq import Groq
from google import genai
from google.genai import types
from datetime import datetime

DATABASE_NAME = "/data/free_chat_history.db"
MODEL_OPTIONS = {
    "LLaMA4-Marverick-17B": "meta-llama/llama-4-maverick-17b-128e-instruct",
    "LLaMA4-Scout-17B": "meta-llama/llama-4-scout-17b-16e-instruct",
    "Gemini-2.5-Flash-Lite": "gemini-2.5-flash-lite-preview-06-17",
    "Gemini-2.5-Flash": "gemini-2.5-flash",
    "Gemma-3-27B": "gemma-3-27b-it",
}
model_name_list = list(MODEL_OPTIONS.values())

st.set_page_config(
    page_title="Free AI Chat",
    page_icon="💬",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title("Free AI Chat")
groq_client = Groq()
gem_client = genai.Client()

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
    chat_id INTEGER,
    role TEXT,
    content TEXT,
    image_name TEXT,
    model TEXT,
    FOREIGN KEY(chat_id) REFERENCES chats(id)
)
""")
conn.commit()

if "cu_chat_id" not in st.session_state:
    st.session_state.cu_chat_id = None

if "ed_chat_id" not in st.session_state:
    st.session_state.ed_chat_id = None

if "ne_chat" not in st.session_state:
    st.session_state.ne_chat = False

if "model_name" not in st.session_state:
    st.session_state.model_name = model_name_list[0]

def load_chats():
    c.execute("""
        SELECT c.id, c.title, (SELECT m.model FROM messages m WHERE m.chat_id = c.id ORDER BY m.id DESC LIMIT 1) as model
        FROM chats c WHERE c.deleted = 0 ORDER BY c.created_at DESC
    """)
    return [list(row) for row in c.fetchall()]

def load_messages(chat_id):
    c.execute("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))
    return [{"role": row[0], "content": row[1]} for row in c.fetchall()]

def create_new_chat_id():
    c.execute("SELECT id FROM chats ORDER BY id DESC LIMIT 1")
    result = c.fetchone()
    if result is None:
        return 1
    else:
        return int(result[0]) + 1

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
    response = gem_client.models.generate_content(
        model="gemini-2.5-flash-lite-preview-06-17",
        contents=f"以下の文章に20文字以下のタイトルを生成してください。回答はタイトルだけでお願いします。\n\n文章「{prompt}」"
    )
    return response.text

with st.sidebar:
    if st.button(":heavy_plus_sign: 新しいチャット"):
        st.session_state.cu_chat_id = create_new_chat_id()
        st.session_state.ne_chat = True
        st.rerun()

    selected_label = st.selectbox(":gear: モデル選択", list(MODEL_OPTIONS.keys()), index=model_name_list.index(st.session_state.model_name))
    st.session_state.model_name = MODEL_OPTIONS[selected_label]
    if st.session_state.model_name.startswith("gem"):
        client = genai.Client()
    else:
        client = Groq()

    st.subheader(":speech_balloon: チャット一覧")
    for chat_id, title, model_name in load_chats():
        if st.session_state.ed_chat_id == chat_id:
            new_title = st.text_input("タイトル編集", value=title, key=f"edit_{chat_id}")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("保存", key=f"save_{chat_id}"):
                    update_chat_title(chat_id, new_title)
                    st.session_state.ed_chat_id = None
                    st.rerun()
            with col2:
                if st.button("キャンセル", key=f"cancel_{chat_id}"):
                    st.session_state.ed_chat_id = None
                    st.rerun()
        else:
            col1, col2, col3 = st.columns([4, 1, 1], vertical_alignment="center")
            with col1:
                if st.button(title, key=f"title_{chat_id}"):
                    st.session_state.cu_chat_id = chat_id
                    st.session_state.ne_chat = False
                    st.session_state.model_name = model_name
                    st.rerun()
            with col2:
                if st.button("✏️", key=f"edit_{chat_id}"):
                    st.session_state.ed_chat_id = chat_id
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"delete_{chat_id}"):
                    delete_chat(chat_id)
                    if st.session_state.cu_chat_id == chat_id:
                        st.session_state.cu_chat_id = None
                    st.rerun()

chat_id = st.session_state.cu_chat_id
if chat_id:
    if st.session_state.ne_chat:
        messages = []
    else:
        messages = load_messages(chat_id)

    chat_history = []
    for msg in messages:
        if msg["role"] == "assistant":
            chat_history.append(types.Content(role="model", parts=[types.Part.from_text(text=msg["content"])]))
            avatar = ":material/robot:"
        else:
            chat_history.append(types.UserContent(parts=[types.Part.from_text(text=msg["content"])]))
            avatar = None
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    if prompt := st.chat_input("質問してみましょう"):
        # 新規チャットか既存チャットかで保存処理を分岐
        if st.session_state.ne_chat:
            save_chat_and_message(chat_id, prompt, st.session_state.model_name)
            st.session_state.ne_chat = False
        else:
            add_message(chat_id, "user", prompt, st.session_state.model_name)
        messages.append({
            "role": "user",
            "content": prompt,
        })

        # ユーザーメッセージ表示
        with st.chat_message("user"):
            st.markdown(prompt)

        # アシスタント応答生成
        with st.chat_message("assistant",avatar=":material/robot:"):
            if st.session_state.model_name.startswith("gem"):
                chat = gem_client.chats.create(
                    model=st.session_state.model_name,
                    history=chat_history,
                )
                response = chat.send_message_stream(prompt)
            else:
                response = groq_client.chat.completions.create(
                    model=st.session_state.model_name,
                    messages=messages,
                    stream=True,
                )
            response_text = ""
            message_placeholder = st.empty()
            for chunk in response:
                if st.session_state.model_name.startswith("gem"):
                    if hasattr(chunk, "text"):
                        try:
                            response_text += chunk.text
                            message_placeholder.markdown(response_text)
                        except Exception as e:
                            st.warning(e)
                else:
                    try:
                        if chunk.choices[0].finish_reason != 'stop':
                            response_text += chunk.choices[0].delta.content
                            message_placeholder.markdown(response_text)
                    except Exception as e:
                        st.warning(e)
        add_message(chat_id, "assistant", response_text, model=st.session_state.model_name)

        # デフォルトタイトルなら要約して更新
        c.execute("SELECT title FROM chats WHERE id = ?", (chat_id,))
        current_title = c.fetchone()[0]
        if current_title == "新しいチャット":
            new_title = generate_title(prompt)
            update_chat_title(chat_id, new_title)

        st.rerun()
else:
    st.info("左のサイドバーからチャットを作成または選択してください。")
    st.info("画像入力に対応しました。")
                