import os
import uuid
import base64
import sqlite3
import streamlit as st
from openai import OpenAI
from datetime import datetime
from PIL import Image

IMAGE_FOLDER = "/data/images"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

st.set_page_config(
    page_title="Chat API",
    page_icon=":robot:",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title("Chat API")

client = OpenAI()

conn = sqlite3.connect("/data/chat_history.db", check_same_thread=False)
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
    image_name TEXT,
    model TEXT,
    FOREIGN KEY(chat_id) REFERENCES chats(id)
)
""")
conn.commit()

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

if "editing_chat_id" not in st.session_state:
    st.session_state.editing_chat_id = None

if "new_chat" not in st.session_state:
    st.session_state.new_chat = False  # TrueならまだDB未保存の新規チャット

def load_chats():
    # deleted = 0 のチャットのみ表示
    c.execute("SELECT id, title FROM chats WHERE deleted = 0 ORDER BY created_at DESC")
    return c.fetchall()

def load_messages(chat_id):
    c.execute("SELECT role, content, image_name FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))
    return [{"role": row[0], "content": row[1], "image_name": row[2]} for row in c.fetchall()]

def create_new_chat_id():
    return str(uuid.uuid4())

def save_chat_and_message(chat_id, user_message, image_name=None, model=None):
    now = datetime.now().isoformat()
    c.execute("INSERT INTO chats (id, title, created_at, deleted) VALUES (?, ?, ?, 0)", (chat_id, "新しいチャット", now))
    c.execute("INSERT INTO messages (chat_id, role, content, image_name, model) VALUES (?, ?, ?, ?, ?)", (chat_id, "user", user_message, image_name, model))
    conn.commit()

def update_chat_title(chat_id, new_title):
    c.execute("UPDATE chats SET title = ? WHERE id = ?", (new_title, chat_id))
    conn.commit()

def delete_chat(chat_id):
    # 論理削除: deletedフラグを1に更新
    c.execute("UPDATE chats SET deleted = 1 WHERE id = ?", (chat_id,))
    conn.commit()

def add_message(chat_id, role, content, image_name=None, model=None):
    c.execute("INSERT INTO messages (chat_id, role, content, image_name, model) VALUES (?, ?, ?, ?, ?)", (chat_id, role, content, image_name, model))
    conn.commit()

def generate_title(prompt):
    summary_prompt = f"以下の発言から、10〜20文字のタイトルを生成してください:\n\n{prompt}"
    res = client.responses.create(
        model="gpt-4.1-nano",
        input=[
            {"role": "system", "content": "あなたはチャットタイトルを生成するアシスタントです。"},
            {"role": "user", "content": summary_prompt}
        ]
    )
    return res.output_text.strip()

with st.sidebar:
    st.header('Ver 1.0.3')
    if st.button(":heavy_plus_sign: 新しいチャット"):
        st.session_state.current_chat_id = create_new_chat_id()
        st.session_state.new_chat = True
        st.rerun()

    st.subheader(":gear: モデル選択")
    model_options = {
        "GPT-4.1-nano": "gpt-4.1-nano",
        "GPT-4.1-mini": "gpt-4.1-mini",
        "GPT-4.1": "gpt-4.1",
        "GPT-4o-mini-search": "gpt-4o-mini-search-preview",
        "GPT-4o-search": "gpt-4o-search-preview"
    }
    selected_label = st.selectbox("使用モデル", list(model_options.keys()))
    st.session_state["openai_model"] = model_options[selected_label]

    st.subheader(":speech_balloon: チャット一覧")
    for chat_id, title in load_chats():
        if st.session_state.editing_chat_id == chat_id:
            new_title = st.text_input("タイトル編集", value=title, key=f"edit_{chat_id}")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("保存", key=f"save_{chat_id}"):
                    update_chat_title(chat_id, new_title)
                    st.session_state.editing_chat_id = None
                    st.rerun()
            with col2:
                if st.button("キャンセル", key=f"cancel_{chat_id}"):
                    st.session_state.editing_chat_id = None
                    st.rerun()
        else:
            col1, col2, col3 = st.columns([4, 1, 1], vertical_alignment="center")
            with col1:
                if st.button(title, key=f"title_{chat_id}"):
                    st.session_state.current_chat_id = chat_id
                    st.session_state.new_chat = False
                    st.rerun()
            with col2:
                if st.button("✏️", key=f"edit_{chat_id}"):
                    st.session_state.editing_chat_id = chat_id
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"delete_{chat_id}"):
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
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["image_name"]:
                # 画像がある場合は表示
                image = Image.open(os.path.join(IMAGE_FOLDER, msg["image_name"]))
                st.image(image)

    if prompt := st.chat_input("質問してみましょう", accept_file=True):
        image_name = None
        image_path = None
        base64_image = None

        # 画像がアップロードされた場合の処理
        if prompt["files"]:
            image_name = f"{uuid.uuid4()}.jpg"
            image_path = os.path.join(IMAGE_FOLDER, image_name)
            image_file = prompt["files"][0]
            image = Image.open(image_file)
            if image.width > 1920 or image.height > 1920:
                image.thumbnail((1920, 1920))
            image.save(image_path, format="JPEG")
            base64_image = base64.b64encode(open(image_path, "rb").read()).decode("utf-8")

        # 新規チャットか既存チャットかで保存処理を分岐
        if st.session_state.new_chat:
            save_chat_and_message(chat_id, prompt.text, image_name, st.session_state["openai_model"])
            st.session_state.new_chat = False
        else:
            add_message(chat_id, "user", prompt.text, image_name, st.session_state["openai_model"])
        messages.append({
            "role": "user",
            "content": prompt.text,
            "image_name": image_name
        })

        # ユーザーメッセージ表示
        with st.chat_message("user"):
            st.markdown(prompt.text)
            if image_path:
                st.image(image_path)

        # アシスタント応答生成
        with st.chat_message("assistant"):
            for i, m in enumerate(messages):
                if m["image_name"]:
                    image_path = os.path.join(IMAGE_FOLDER, m["image_name"])
                    with open(image_path, "rb") as img_file:
                        base64_image = base64.b64encode(img_file.read()).decode("utf-8")
                    messages[i]["content"] = [
                        {"type": "text", "text": m["content"]},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
            if "-search-preview" in st.session_state["openai_model"]:
                web_search_options = {
                    "search_context_size": "medium",
                }
            else:
                web_search_options = None
            stream = client.chat.completions.create(
                model=st.session_state["openai_model"],
                web_search_options=web_search_options,
                messages=messages,
                stream=True,
            )
            response = st.write_stream(stream)
        add_message(chat_id, "assistant", response, model=st.session_state["openai_model"])

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
                