import sqlite3
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from datetime import datetime

st.set_page_config(
    page_title="Gemini 画像生成",
    page_icon="🌈",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title("Gemini 画像生成")

client = genai.Client()

conn = sqlite3.connect("/data/image_gen.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ask TEXT,
    answer TEXT,
    image BLOB,
    created_at TEXT,
    deleted INTEGER DEFAULT 0
)
""")
conn.commit()

if "chat_id" not in st.session_state:
    st.session_state.chat_id = None

def load_chat_asks():
    c.execute("SELECT id, ask FROM chats ORDER BY created_at DESC")
    return c.fetchall()

def load_chat(chat_id):
    c.execute("SELECT ask, answer, image FROM chats WHERE id = ?", (chat_id,))
    return c.fetchone()

def delete_chat(chat_id):
    c.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()

with st.sidebar:
    st.subheader(":speech_balloon: チャット一覧")
    for chat_id, ask in load_chat_asks():
        col1, col2 = st.columns([5, 1], vertical_alignment="center")
        with col1:
            if st.button(ask, key=f"title_{chat_id}"):
                st.session_state.chat_id = chat_id
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"delete_{chat_id}"):
                delete_chat(chat_id)
                if st.session_state.chat_id == chat_id:
                    st.session_state.chat_id = None
                st.rerun()
        
if prompt := st.chat_input("画像生成のプロンプトを入力してください..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Wait for it...", show_time=True):
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=(prompt),
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                answer = part.text
            elif part.inline_data is not None:
                image_bytes = part.inline_data.data
                image = Image.open(BytesIO((image_bytes)))

    with st.chat_message("assistant", avatar=':material/wand_stars:'):
        st.write(answer)
        st.image(image)
    now = datetime.now().isoformat()
    c = conn.cursor()
    c.execute("INSERT INTO chats (ask, answer, image, created_at) VALUES (?, ?, ?, ?)", (prompt, answer, image_bytes, now))
    conn.commit()
    st.session_state.chat_id = c.lastrowid
    conn.close()
    st.rerun()
else:
    chat_id = st.session_state.chat_id
    if chat_id:
        ask, answer, image_bytes = load_chat(chat_id)
        with st.chat_message("user"):
            st.markdown(ask)
        with st.chat_message("assistant", avatar=':material/wand_stars:'):
            st.write(answer)
            image = Image.open(BytesIO((image_bytes)))
            st.image(image)