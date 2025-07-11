import sqlite3
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from datetime import datetime

MODEL_OPTIONS = {
    "Gemini-2.5-Flash-Lite": "gemini-2.5-flash-lite-preview-06-17",
    "Gemini-2.5-Flash": "gemini-2.5-flash",
    "Gemini-2.5-Pro": "gemini-2.5-pro",
}
model_name_list = list(MODEL_OPTIONS.values())

st.set_page_config(
    page_title="Gemini 画像(生成/認識)",
    page_icon="🌈",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title("Gemini 画像")

client = genai.Client()

conn = sqlite3.connect("/data/with_image.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ask TEXT,
    answer TEXT,
    image BLOB,
    created_at TEXT,
    model_id INTEGER DEFAULT 0
)
""")
conn.commit()

if "chat_id" not in st.session_state:
    st.session_state.chat_id = None

def load_chat_asks():
    c.execute("SELECT id, title, ask FROM chats ORDER BY created_at DESC")
    return c.fetchall()

def load_chat(chat_id):
    c.execute("SELECT ask, answer, image, model_id FROM chats WHERE id = ?", (chat_id,))
    return c.fetchone()

def delete_chat(chat_id):
    c.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()

def generate_title(prompt):
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite-preview-06-17",
        contents=f"以下の文章に20文字以下のタイトルを生成してください。回答はタイトルだけでお願いします。\n\n文章「{prompt}」"
    )
    return response.text

with st.sidebar:
    if st.button(":heavy_plus_sign: 新しいチャット"):
        st.session_state.chat_id = None
        st.rerun()

    selected_label = st.selectbox(":gear: モデル選択", list(MODEL_OPTIONS.keys()))
    model_id = list(MODEL_OPTIONS.keys()).index(selected_label) + 1

    st.subheader(":speech_balloon: チャット一覧")
    for chat_id, title, ask in load_chat_asks():
        col1, col2 = st.columns([5, 1], vertical_alignment="center")
        with col1:
            if title is None:
                title = ask
            if st.button(title, key=f"title_{chat_id}"):
                st.session_state.chat_id = chat_id
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"delete_{chat_id}"):
                delete_chat(chat_id)
                if st.session_state.chat_id == chat_id:
                    st.session_state.chat_id = None
                st.rerun()

if prompt := st.chat_input("画像ありで画像認識、画像なしで画像生成を行います。", accept_file=True):
    with st.chat_message("user"):
        ask_text = prompt.text
        st.markdown(ask_text)
        if len(ask_text) > 20:
            title = generate_title(ask_text)
        else:
            title = None

        if prompt["files"]:
            image = prompt["files"][0]
            image_bytes = image.read()
            st.image(image)
            model = model_name_list[model_id - 1]
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type='image/jpeg',
                ),
                ask_text
            ]
            config = None
        else:
            model_id = 0
            model = "gemini-2.0-flash-preview-image-generation"
            contents = (ask_text)
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )

    with st.spinner("Wait for it...", show_time=True):
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                answer = part.text
            elif part.inline_data is not None:
                image_bytes = part.inline_data.data
                image = Image.open(BytesIO((image_bytes)))

    with st.chat_message("assistant", avatar=':material/wand_stars:'):
        if answer:
            st.write(answer)
        if model_id == 0:
            st.image(image)
        else:
            st.badge(model_name_list[model_id - 1])

    now = datetime.now().isoformat()
    c = conn.cursor()
    c.execute("INSERT INTO chats (ask, answer, image, created_at, model_id, title) VALUES (?, ?, ?, ?, ?, ?)", (ask_text, answer, image_bytes, now, model_id, title))
    conn.commit()
    st.session_state.chat_id = c.lastrowid
    conn.close()
    st.rerun()
else:
    if st.session_state.chat_id:
        ask, answer, image_bytes, mode = load_chat(st.session_state.chat_id)
        image = Image.open(BytesIO((image_bytes)))
        with st.chat_message("user"):
            st.markdown(ask)
            if mode > 0:
                st.image(image)
        with st.chat_message("assistant", avatar=':material/wand_stars:'):
            st.write(answer)
            if mode == 0:
                st.image(image)
            else:
                st.badge(model_name_list[model_id - 1])