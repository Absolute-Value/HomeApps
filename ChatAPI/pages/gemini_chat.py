import sqlite3
import streamlit as st
from google import genai
from google.genai import types

# --- 設定 ---
DATABASE_NAME = "/data/gemini_history.db"
MODEL_OPTIONS = {
    "Gemini-2.5-Flash-Lite": "gemini-2.5-flash-lite-preview-06-17",
    "Gemini-2.5-Flash": "gemini-2.5-flash",
}

# --- DB接続 ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# --- テーブル作成 ---
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
        )
    ''')
    conn.commit()
    conn.close()

# --- チャット操作 ---
def create_new_chat():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chats DEFAULT VALUES")
    conn.commit()
    chat_id = cursor.lastrowid
    conn.close()
    return chat_id

def get_all_chats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, created_at FROM chats ORDER BY created_at DESC")
    chats = cursor.fetchall()
    conn.close()
    return chats

def delete_chat(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    cursor.execute("DELETE FROM chats WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

# --- メッセージ操作 ---
def load_chat_history(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY timestamp", (chat_id,))
    history = [{'role': row['role'], 'content': row['content']} for row in cursor.fetchall()]
    conn.close()
    return history

def save_chat_history_items(chat_id, history_items_to_save):
    conn = get_db_connection()
    cursor = conn.cursor()
    for item in history_items_to_save:
        role = item.get('role')
        content = item.get('content')
        if role and content:
            cursor.execute(
                "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
                (chat_id, role, content)
            )
    conn.commit()
    conn.close()

# --- Streamlit UI 初期化 ---
st.set_page_config(
    page_title="Gemini",
    page_icon=":robot:",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title("Gemini")

create_tables()

# --- セッション初期化 ---
if 'chat_id' not in st.session_state:
    st.session_state.chat_id = create_new_chat()
if 'chat_session' not in st.session_state:
    st.session_state.chat_session = None
if 'messages' not in st.session_state:
    st.session_state.messages = []

# --- チャットセッション初期化 ---
def initialize_chat_session(chat_id):
    chat_history = load_chat_history(chat_id)
    client = genai.Client()
    formatted_history = []
    for chat_dict in chat_history:
        if chat_dict["role"]=="user":
            formatted_history.append(types.UserContent(parts=[types.Part.from_text(text=chat_dict["content"])]))
        else:
            formatted_history.append(types.Content(role=chat_dict["role"], parts=[types.Part.from_text(text=chat_dict["content"])]))
    st.session_state.chat_session = client.chats.create(model=st.session_state["model_name"], history=formatted_history)
    st.session_state.messages = chat_history

# --- サイドバー：チャット管理 ---
with st.sidebar:
    selected_label = st.selectbox(":gear: モデル選択", list(MODEL_OPTIONS.keys()))
    st.session_state["model_name"] = MODEL_OPTIONS[selected_label]

    st.markdown("### チャット選択")
    all_chats = get_all_chats()
    chat_options = [f"Chat {c['chat_id']} - {c['created_at']}" for c in all_chats]
    chat_id_map = {f"Chat {c['chat_id']} - {c['created_at']}": c['chat_id'] for c in all_chats}

    selected_chat = st.selectbox("チャットを選択", chat_options)
    selected_chat_id = chat_id_map[selected_chat]

    if selected_chat_id != st.session_state.chat_id:
        st.session_state.chat_id = selected_chat_id
        initialize_chat_session(st.session_state.chat_id)
        st.rerun()

    if st.button("🆕 新しいチャットを開始"):
        st.session_state.chat_id = create_new_chat()
        initialize_chat_session(st.session_state.chat_id)
        st.rerun()

    if st.button("🗑️ このチャットを削除"):
        delete_chat(st.session_state.chat_id)
        st.session_state.chat_id = create_new_chat()
        initialize_chat_session(st.session_state.chat_id)
        st.rerun()
        
initialize_chat_session(st.session_state.chat_id)

# --- メッセージ表示 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 入力処理 ---
user_input = st.chat_input("メッセージを入力してください...")

if user_input:
    # 表示・セッションに追加
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    try:
        response = st.session_state.chat_session.send_message(user_input)
        response_text = response.text
        st.session_state.messages.append({"role": "model", "content": response_text})
        with st.chat_message("model"):
            st.markdown(response_text)

        # DBに保存
        save_chat_history_items(
            st.session_state.chat_id,
            [{'role': 'user', 'content': user_input},
             {'role': 'model', 'content': response_text}]
        )

    except Exception as e:
        st.error(f"エラー: {e}")
