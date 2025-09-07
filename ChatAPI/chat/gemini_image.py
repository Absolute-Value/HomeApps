import sqlite3
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from datetime import datetime

PAGE_TITLE = "Gemini 画像生成"

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=":material/image:",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title(PAGE_TITLE)

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

    st.subheader(":speech_balloon: チャット一覧")
    for chat_id, title, ask in load_chat_asks():
        chat_container = st.container(horizontal=True, horizontal_alignment="right", gap="small", vertical_alignment="center")
        col1, col2 = chat_container.columns([6, 1], vertical_alignment="center", gap=None)
        if title is None:
            title = ask
        if col1.button(title, key=f"title_{chat_id}", type="tertiary", width="stretch"):
            st.session_state.chat_id = chat_id
            st.rerun()
        if col2.button(":material/delete:", key=f"delete_{chat_id}", type="tertiary", width="stretch"):
            delete_chat(chat_id)
            if st.session_state.chat_id == chat_id:
                st.session_state.chat_id = None
            st.rerun()

if prompt := st.chat_input("画像生成したいプロンプトを入力...", accept_file=True):
    with st.chat_message("user"):
        ask_text = prompt.text
        st.markdown(ask_text)
        if len(ask_text) > 20:
            title = generate_title(ask_text)
        else:
            title = None

        contents = [ask_text]
        if prompt["files"]:
            image = prompt["files"][0]
            image_bytes = image.read()
            st.image(image)
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type='image/jpeg',
                ),
                ask_text
            ]
        model_id = 0
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE']
        )

    with st.spinner("Wait for it...", show_time=True):
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=contents,
            config=config
        )
        answer = None
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                answer = part.text
            elif part.inline_data is not None:
                image_bytes = part.inline_data.data
                image = Image.open(BytesIO((image_bytes)))

    if image:
        with st.chat_message("assistant", avatar=':material/wand_stars:'):
            if answer is not None:
                st.write(answer)
            st.image(image)

        now = datetime.now().isoformat()
        c = conn.cursor()
        c.execute("INSERT INTO chats (ask, answer, image, created_at, model_id, title) VALUES (?, ?, ?, ?, ?, ?)", (ask_text, answer, image_bytes, now, model_id, title))
        conn.commit()
        st.session_state.chat_id = c.lastrowid
        conn.close()
        st.rerun()
    else:
        st.error(f"画像が生成されませんでした。{response}")
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
            st.image(image)