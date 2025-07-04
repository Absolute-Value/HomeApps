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

conn = sqlite3.connect(DATABASE_NAME)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    created_at TEXT,
    last_model_id INTEGER
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
)
""")
c.execute("SELECT COUNT(*) FROM models")
count = c.fetchone()[0]
if count == 0:
    c.executemany("INSERT INTO models (name) VALUES (?)", [(m,) for m in model_name_list])
c.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    role TEXT,
    content TEXT,
    model_id INTEGER,
    FOREIGN KEY(chat_id) REFERENCES chats(id),
    FOREIGN KEY(model_id) REFERENCES models(id)
)
""")
conn.commit()

if "now_chat_id" not in st.session_state:
    st.session_state.now_chat_id = None

if "edit_chat_id" not in st.session_state:
    st.session_state.edit_chat_id = None

if "is_new_chat" not in st.session_state:
    st.session_state.is_new_chat = False

if "model_id" not in st.session_state:
    st.session_state.model_id = 0

def load_chats():
    c.execute("SELECT id, title, last_model_id FROM chats ORDER BY created_at DESC")
    return [list(row) for row in c.fetchall()]

def load_messages(chat_id):
    c.execute("SELECT role, content, model_id FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))
    return [{"role": row[0], "content": row[1], "model_id": row[2]} for row in c.fetchall()]

def create_new_chat_id():
    c.execute("SELECT seq FROM sqlite_sequence WHERE name='chats'")
    result = c.fetchone()
    if result is None:
        return 1
    else:
        return int(result[0]) + 1

def save_chat_and_message(chat_id, user_message, model_id=None):
    now = datetime.now().isoformat()
    c.execute("INSERT INTO chats (title, created_at, last_model_id) VALUES (?, ?, ?)", ("新しいチャット", now, model_id))
    c.execute("INSERT INTO messages (chat_id, role, content, model_id) VALUES (?, ?, ?, ?)", (chat_id, "user", user_message, model_id))
    conn.commit()

def update_chat_title(chat_id, new_title):
    c.execute("UPDATE chats SET title = ? WHERE id = ?", (new_title, chat_id))
    conn.commit()

def delete_chat(chat_id):
    c.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    c.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    conn.commit()

def add_message(chat_id, role, content, model_id=None):
    c.execute("UPDATE chats SET last_model_id = ? WHERE id = ?", (model_id, chat_id))
    c.execute("INSERT INTO messages (chat_id, role, content, model_id) VALUES (?, ?, ?, ?)", (chat_id, role, content, model_id))
    conn.commit()

def generate_title(prompt):
    response = gem_client.models.generate_content(
        model="gemini-2.5-flash-lite-preview-06-17",
        contents=f"以下の文章に20文字以下のタイトルを生成してください。回答はタイトルだけでお願いします。\n\n文章「{prompt}」"
    )
    return response.text

with st.sidebar:
    if st.button(":heavy_plus_sign: 新しいチャット"):
        st.session_state.now_chat_id = create_new_chat_id()
        st.session_state.is_new_chat = True
        st.rerun()

    selected_label = st.selectbox(":gear: モデル選択", list(MODEL_OPTIONS.keys()), index=st.session_state.model_id)
    st.session_state.model_id = list(MODEL_OPTIONS.keys()).index(selected_label)

    st.subheader(":speech_balloon: チャット一覧")
    for chat_id, title, last_model_id in load_chats():
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
                    st.session_state.now_chat_id = chat_id
                    st.session_state.is_new_chat = False
                    st.session_state.model_id = last_model_id - 1
                    st.rerun()
            with col2:
                if st.button("✏️", key=f"edit_{chat_id}"):
                    st.session_state.edit_chat_id = chat_id
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"delete_{chat_id}"):
                    delete_chat(chat_id)
                    if st.session_state.now_chat_id == chat_id:
                        st.session_state.now_chat_id = None
                    st.rerun()

chat_id = st.session_state.now_chat_id
if chat_id:
    if st.session_state.is_new_chat:
        messages = []
    else:
        messages = load_messages(chat_id)

    chat_history = []
    for msg in messages:
        if msg["role"] == "assistant":
            chat_history.append(types.Content(role="model", parts=[types.Part.from_text(text=msg["content"])]))
            model_name = model_name_list[msg["model_id"]-1]
            with st.chat_message(model_name.split('-')[1]):
                st.markdown(msg["content"])
                st.badge(model_name)
        else:
            chat_history.append(types.UserContent(parts=[types.Part.from_text(text=msg["content"])]))
            with st.chat_message("user"):
                st.text(msg["content"])
        msg.pop("model_id", None) 

    if prompt := st.chat_input("質問してみましょう"):
        # 新規チャットか既存チャットかで保存処理を分岐
        if st.session_state.is_new_chat:
            save_chat_and_message(chat_id, prompt, st.session_state.model_id + 1)
            st.session_state.is_new_chat = False
        else:
            add_message(chat_id, "user", prompt, st.session_state.model_id + 1)
        messages.append({
            "role": "user",
            "content": prompt,
        })

        # ユーザーメッセージ表示
        with st.chat_message("user"):
            st.text(prompt)

        # アシスタント応答生成
        model_name = model_name_list[st.session_state.model_id]
        with st.chat_message(model_name.split('-')[1]):
            if model_name.startswith("gem"):
                chat = gem_client.chats.create(
                    model=model_name,
                    history=chat_history,
                )
                response = chat.send_message_stream(prompt)
            else:
                response = groq_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    stream=True,
                )
            response_text = ""
            message_placeholder = st.empty()
            for chunk in response:
                if model_name.startswith("gem"):
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
        add_message(chat_id, "assistant", response_text, st.session_state.model_id + 1)

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
                