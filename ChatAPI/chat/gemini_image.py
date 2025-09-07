import sqlite3
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from datetime import datetime

PAGE_TITLE = "Gemini 画像生成"
MODEL = "gemini-2.0-flash-preview-image-generation"

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
    title TEXT,
    used_at TEXT
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    role TEXT,
    content TEXT,
    image BLOB,
    FOREIGN KEY(chat_id) REFERENCES chats(id)
)
""")
conn.commit()

session_var_list = ["chat_id", "edit_id", "is_new"]
for session_var in session_var_list:
    if session_var not in st.session_state:
        st.session_state[session_var] = None

def load_chats():
    c.execute("SELECT id, title FROM chats ORDER BY used_at DESC")
    return [list(row) for row in c.fetchall()]

def load_messages(chat_id):
    c.execute("SELECT id, role, content, image FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))
    return [{"id": row[0], "role": row[1], "content": row[2], "image": row[3]} for row in c.fetchall()]

def create_new_chat_id():
    c.execute("SELECT seq FROM sqlite_sequence WHERE name='chats'")
    result = c.fetchone()
    if result is None:
        return 1
    else:
        return int(result[0]) + 1

def save_chat_and_message(chat_id, user_message, image=None, chat_title="新しいチャット"):
    now = datetime.now().isoformat()
    c.execute("INSERT INTO chats (title, used_at) VALUES (?, ?)", (chat_title, now))
    c.execute("INSERT INTO messages (chat_id, role, content, image) VALUES (?, ?, ?, ?)", (chat_id, "user", user_message, image))
    conn.commit()

def update_chat_title(chat_id, new_title):
    c.execute("UPDATE chats SET title = ? WHERE id = ?", (new_title, chat_id))
    conn.commit()

def delete_chat(chat_id):
    c.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    c.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    conn.commit()

def add_message(chat_id, role, content, image=None):
    now = datetime.now().isoformat()
    c.execute("UPDATE chats SET used_at = ? WHERE id = ?", (now, chat_id))
    c.execute("INSERT INTO messages (chat_id, role, content, image) VALUES (?, ?, ?, ?)", (chat_id, role, content, image))
    conn.commit()

def delete_message(message_id, now_chat_id):
    c.execute("DELETE FROM messages WHERE chat_id = ? AND id >= ?", (now_chat_id, message_id))
    conn.commit()

def generate_title(prompt):
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite-preview-06-17",
        contents=f"以下の文章に20文字以下のタイトルを生成してください。回答はタイトルだけでお願いします。\n\n文章「{prompt}」"
    )
    return response.text

with st.sidebar:
    if st.button(":heavy_plus_sign: 新しいチャット"):
        st.session_state.chat_id = create_new_chat_id()
        st.session_state.is_new = True
        st.rerun()

    st.subheader(":speech_balloon: チャット一覧")
    for chat_id, title in load_chats():
        chat_container = st.container(horizontal=True, horizontal_alignment="right", gap="small", vertical_alignment="center")
        if st.session_state.edit_id == chat_id:
            new_title = chat_container.text_input("タイトル編集", value=title, label_visibility="collapsed", key=f"edit_{chat_id}")
            icon = ":material/cancel:"
            if new_title != title:
                icon = ":material/save:"
            if chat_container.button(icon, key=f"save_{chat_id}", type="tertiary", width="content"):
                if new_title != title:
                    update_chat_title(chat_id, new_title)
                st.session_state.edit_id = None
                st.rerun()
        else:
            col1, col2, col3 = chat_container.columns([6, 1, 1], vertical_alignment="center", gap=None)
            if col1.button(title, key=f"title_{chat_id}", type="tertiary", width="stretch"):
                st.session_state.chat_id = chat_id
                st.session_state.is_new = False
                st.rerun()
            if col2.button(":material/edit:", key=f"edit_{chat_id}", type="tertiary", width="stretch"):
                st.session_state.edit_id = chat_id
                st.rerun()
            if col3.button(":material/delete:", key=f"delete_{chat_id}", type="tertiary", width="stretch"):
                delete_chat(chat_id)
                if st.session_state.chat_id == chat_id:
                    st.session_state.chat_id = None
                st.rerun()

chat_id = st.session_state.chat_id
if chat_id:
    contents = []
    if not st.session_state.is_new:
        messages = load_messages(chat_id)
        for i, msg in enumerate(messages):
            if msg["role"] == "assistant":
                with st.chat_message("assistant", avatar=":material/wand_stars:"):
                    st.markdown(msg["content"])
                    if msg["image"]:
                        image = Image.open(BytesIO(msg["image"]))
                        st.image(image)
            else:
                with st.chat_message("user"):
                    if msg["image"]:
                        image = Image.open(BytesIO(msg["image"]))
                        st.image(image)
                        contents.append(image)
                    st.text(msg["content"])
                    contents.append(msg["content"])
        
    if prompt := st.chat_input("画像生成したいプロンプトを入力...", accept_file=True):
        ask_text = prompt.text
        image_bytes = None
            
        with st.chat_message("user"):
            st.text(ask_text)

            if prompt["files"]:
                image = prompt["files"][0]
                image_bytes = image.read()
                st.image(image)
                contents.append(types.Part.from_bytes(
                    data=image_bytes,
                    mime_type='image/jpeg',
                ))
        contents.append(ask_text)
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE']
        )
        if st.session_state.is_new:
            if len(ask_text) > 20:
                chat_title = generate_title(ask_text)
            else:
                chat_title = ask_text
            save_chat_and_message(chat_id, ask_text, image_bytes, chat_title)
            st.session_state.is_new = False
        else:
            add_message(chat_id, "user", ask_text, image_bytes)

        with st.spinner("Wait for it...", show_time=True):
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=config
            )
            answer = None
            image = None
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

            add_message(chat_id, "assistant", answer, image_bytes)
            st.rerun()
        else:
            st.error(f"画像が生成されませんでした。{response}")
else:
    st.info("左のサイドバーからチャットを作成または選択してください。")