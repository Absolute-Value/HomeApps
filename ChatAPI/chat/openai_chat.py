import io
import base64
import sqlite3
import streamlit as st
from openai import OpenAI
from datetime import datetime
from PIL import Image

PAGE_TITLE = "OpenAI"
DATABASE_NAME = "/data/chat_history.db"
MODEL_OPTIONS = {
    "GPT-4.1-nano": "gpt-4.1-nano",
    "GPT-4.1-mini": "gpt-4.1-mini",
    "GPT-4.1": "gpt-4.1",
    "GPT-4o-mini-search": "gpt-4o-mini-search-preview",
    "GPT-4o-search": "gpt-4o-search-preview",
    "GPT-5-chat": "gpt-5-chat-latest",
}
model_name_list = list(MODEL_OPTIONS.values())

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=":material/network_intelligence:",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title(PAGE_TITLE)

client = OpenAI()

conn = sqlite3.connect(DATABASE_NAME)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT,
    last_model_id INTEGER,
    deleted INTEGER DEFAULT 0
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    role TEXT,
    content TEXT,
    image BLOB,
    model_id INTEGER,
    FOREIGN KEY(chat_id) REFERENCES chats(id)
)
""")
conn.commit()

session_var_list = ["current_chat_id", "editing_chat_id", "new_chat"]
for session_var in session_var_list:
    if session_var not in st.session_state:
        st.session_state[session_var] = None

if "model_id" not in st.session_state:
    st.session_state.model_id = 0

def load_chats():
    c.execute("SELECT id, title, last_model_id FROM chats WHERE deleted = 0 ORDER BY created_at DESC")
    return c.fetchall()

def load_messages(chat_id):
    c.execute("SELECT role, content, image, model_id FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))
    return [{"role": row[0], "content": row[1], "image": row[2], "model_id": row[3]} for row in c.fetchall()]

def create_new_chat_id():
    c.execute("SELECT seq FROM sqlite_sequence WHERE name='chats'")
    result = c.fetchone()
    if result is None:
        return 1
    else:
        return int(result[0]) + 1

def save_chat_and_message(chat_id, user_message, image=None, model_id=None):
    now = datetime.now().isoformat()
    c.execute("INSERT INTO chats (id, title, created_at, last_model_id) VALUES (?, ?, ?, ?)", (chat_id, "新しいチャット", now, model_id))
    c.execute("INSERT INTO messages (chat_id, role, content, image, model_id) VALUES (?, ?, ?, ?, ?)", (chat_id, "user", user_message, image, model_id))
    conn.commit()

def update_chat_title(chat_id, new_title):
    c.execute("UPDATE chats SET title = ? WHERE id = ?", (new_title, chat_id))
    conn.commit()

def delete_chat(chat_id):
    c.execute("UPDATE chats SET deleted = 1 WHERE id = ?", (chat_id,))
    conn.commit()

def add_message(chat_id, role, content, image=None, model_id=None):
    c.execute("UPDATE chats SET last_model_id = ? WHERE id = ?", (model_id, chat_id))
    c.execute("INSERT INTO messages (chat_id, role, content, image, model_id) VALUES (?, ?, ?, ?, ?)", (chat_id, role, content, image, model_id))
    conn.commit()

def generate_title(prompt):
    res = client.responses.create(
        model="gpt-5-nano",
        input=[
            {"role": "system", "content": "あなたはチャットタイトルを生成するアシスタントです。ユーザーの発言から、10〜20文字のタイトルを生成してください。回答はタイトルだけでお願いします。"},
            {"role": "user", "content": prompt}
        ]
    )
    return res.output_text.strip()

with st.sidebar:
    if st.button(":heavy_plus_sign: 新しいチャット"):
        st.session_state.current_chat_id = create_new_chat_id()
        st.session_state.new_chat = True
        st.rerun()

    st.header(":material/psychology: モデル選択")
    selected_label = st.selectbox("モデル選択", list(MODEL_OPTIONS.keys()), index=st.session_state.model_id, label_visibility="collapsed")
    st.session_state.model_id = list(MODEL_OPTIONS.keys()).index(selected_label)

    st.header(":material/chat: チャット一覧")
    for chat_id, title, last_model_id in load_chats():
        chat_container = st.container(horizontal=True, horizontal_alignment="right", gap="small", vertical_alignment="center")
        if st.session_state.editing_chat_id == chat_id:
            new_title = chat_container.text_input("タイトル編集", value=title, label_visibility="collapsed", key=f"edit_{chat_id}")
            icon = ":material/cancel:"
            if new_title != title:
                icon = ":material/save:"
            if chat_container.button(icon, key=f"save_{chat_id}", type="tertiary", width="content"):
                if new_title != title:
                    update_chat_title(chat_id, new_title)
                st.session_state.editing_chat_id = None
                st.rerun()
        else:
            col1, col2, col3 = chat_container.columns([6, 1, 1], vertical_alignment="center", gap=None)
            if col1.button(title, key=f"title_{chat_id}", type="tertiary", width="content"):
                st.session_state.current_chat_id = chat_id
                st.session_state.new_chat = False
                st.session_state.model_id = last_model_id - 1
                st.rerun()
            if col2.button(":material/edit:", key=f"edit_{chat_id}", type="tertiary", width="stretch"):
                st.session_state.editing_chat_id = chat_id
                st.rerun()
            if col3.button(":material/delete:", key=f"delete_{chat_id}", type="tertiary", width="stretch"):
                delete_chat(chat_id)
                if st.session_state.current_chat_id == chat_id:
                    st.session_state.current_chat_id = None
                st.rerun()

chat_id = st.session_state.current_chat_id
if chat_id:
    if st.session_state.new_chat:
        messages = []
    else:
        messages = load_messages(chat_id)

    for msg in messages:
        if msg["role"] == "assitant":
            avatar = ":material/face_2:"
        else:
            avatar = None
        with st.chat_message(msg["role"], avatar=avatar):
            st.text(msg["content"])
            if msg["image"]: # 画像がある場合は表示
                image = Image.open(io.BytesIO(msg["image"]))
                st.image(image)
            model_name = model_name_list[msg["model_id"]-1]
            if msg["role"] == "assistant":
                if  "-search" in model_name:
                    icon = ":material/search:"
                    color = "blue"
                else:
                    icon = None
                    color = "orange"
                st.badge(model_name, icon=icon, color=color)

    if prompt := st.chat_input("質問してみましょう", accept_file=True):
        image_bytes = None
        if prompt["files"]:
            image_file = prompt["files"][0]
            image = Image.open(image_file)
            if image.width > 1920 or image.height > 1920:
                image.thumbnail((1920, 1920))
            image_bytes = io.BytesIO()
            if image.mode == "RGBA":
                image = image.convert("RGB")
            image.save(image_bytes, format="JPEG")
            image_bytes = image_bytes.getvalue()

        # 新規チャットか既存チャットかで保存処理を分岐
        if st.session_state.new_chat:
            save_chat_and_message(chat_id, prompt.text, image_bytes, st.session_state.model_id + 1)
            st.session_state.new_chat = False
        else:
            add_message(chat_id, "user", prompt.text, image_bytes, st.session_state.model_id + 1)
        messages.append({
            "role": "user",
            "content": prompt.text,
            "image": image_bytes
        })

        # ユーザーメッセージ表示
        with st.chat_message("user"):
            st.text(prompt.text)
            if image_bytes:
                st.image(image_bytes)

        # アシスタント応答生成
        with st.chat_message("assistant",avatar=":material/face_2:"):
            processed_messages = []
            for m in messages:
                if m["image"]: # 画像付きメッセージの場合
                    processed_messages.append({
                        "role": m["role"],
                        "content": [
                            {"type": "text", "text": m["content"]},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(m['image']).decode('utf-8')}"}}
                        ]
                    })
                else: # テキストのみのメッセージの場合
                    processed_messages.append({
                        "role": m["role"],
                        "content": [
                            {"type": "text", "text": m["content"]}
                        ]
                    })
            if "-search-preview" in model_name_list[st.session_state.model_id]:
                stream = client.chat.completions.create(
                    model=model_name_list[st.session_state.model_id],
                    web_search_options={"search_context_size": "medium"},
                    messages=processed_messages,
                    stream=True,
                )
            else:
                stream = client.chat.completions.create(
                    model=model_name_list[st.session_state.model_id],
                    messages=processed_messages,
                    stream=True,
                )
            response = st.write_stream(stream)
        add_message(chat_id, "assistant", response, None, st.session_state.model_id + 1)

        # デフォルトタイトルなら要約して更新
        c.execute("SELECT title FROM chats WHERE id = ?", (chat_id,))
        current_title = c.fetchone()[0]
        if current_title == "新しいチャット":
            new_title = generate_title(prompt.text)
            update_chat_title(chat_id, new_title)

        st.rerun()
else:
    st.info("左のサイドバーからチャットを作成または選択してください。")
    st.info("画像入力に対応しました。")
                