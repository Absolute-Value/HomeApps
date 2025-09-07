# https://console.groq.com/docs/overview

import io
import wave
import base64
import sqlite3
import streamlit as st
from PIL import Image
from groq import Groq
from google import genai
from google.genai import types
from datetime import datetime

PAGE_TITLE = "Free AI Chat"
DATABASE_NAME = "/data/free_chat_history.db"

def load_chats(c):
    c.execute("SELECT id, title, last_model_id FROM chats ORDER BY used_at DESC")
    return [list(row) for row in c.fetchall()]

def load_messages(c, chat_id):
    c.execute("SELECT id, role, content, image, model_id FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))
    return [{"id": row[0], "role": row[1], "content": row[2], "image": row[3], "model_id": row[4]} for row in c.fetchall()]

def create_new_chat_id(c):
    c.execute("SELECT seq FROM sqlite_sequence WHERE name='chats'")
    result = c.fetchone()
    if result is None:
        return 1
    else:
        return int(result[0]) + 1

def save_chat_and_message(c, conn, chat_id, user_message, image=None, model_id=None):
    now = datetime.now().isoformat()
    c.execute("INSERT INTO chats (title, used_at, last_model_id) VALUES (?, ?, ?)", ("新しいチャット", now, model_id))
    c.execute("INSERT INTO messages (chat_id, role, content, image, model_id) VALUES (?, ?, ?, ?, ?)", (chat_id, "user", user_message, image, model_id))
    conn.commit()

def update_chat_title(c, conn, chat_id, new_title):
    c.execute("UPDATE chats SET title = ? WHERE id = ?", (new_title, chat_id))
    conn.commit()

def delete_chat(c, conn, chat_id):
    c.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    c.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    conn.commit()

def add_message(c, conn, chat_id, role, content, image=None, model_id=None):
    now = datetime.now().isoformat()
    c.execute("UPDATE chats SET used_at = ?, last_model_id = ? WHERE id = ?", (now, model_id, chat_id))
    c.execute("INSERT INTO messages (chat_id, role, content, image, model_id) VALUES (?, ?, ?, ?, ?)", (chat_id, role, content, image, model_id))
    conn.commit()

def delete_message(c, conn, message_id, now_chat_id):
    c.execute("DELETE FROM messages WHERE chat_id = ? AND id >= ?", (now_chat_id, message_id))
    conn.commit()

def generate_title(gen_client, prompt):
    response = gen_client.models.generate_content(
        model="gemini-2.5-flash-lite-preview-06-17",
        contents=f"以下の文章に20文字以下のタイトルを生成してください。回答はタイトルだけでお願いします。\n\n文章「{prompt}」"
    )
    return response.text

def wave_file_bytes(pcm, channels=1, rate=24000, sample_width=2):
    """PCMデータをWAVバイト列に変換"""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()

def generate_audio(gen_client, text):
    content = f'Japanese Female: {text}'
    response = gen_client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=content,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Leda",
                    )
                )
            ),
        )
    )
    blob = response.candidates[0].content.parts[0].inline_data.data
    return wave_file_bytes(blob)

def main():
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=":material/chat:",
        initial_sidebar_state="expanded",
        layout="wide",
    )
    st.title(PAGE_TITLE)
    groq_client = Groq()
    gen_client = genai.Client()

    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        used_at TEXT,
        last_model_id INTEGER
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
        FOREIGN KEY(chat_id) REFERENCES chats(id),
        FOREIGN KEY(model_id) REFERENCES models(id)
    )
    """)
    conn.commit()

    session_var_list = ["now_chat_id", "edit_chat_id", "is_new_chat"]
    for session_var in session_var_list:
        if session_var not in st.session_state:
            st.session_state[session_var] = None

    if "free_model_id" not in st.session_state:
        st.session_state.free_model_id = 1

    c.execute("SELECT name, display FROM models ORDER BY id")
    model_rows = c.fetchall()
    model_names = [row[0] for row in model_rows]
    model_displays = [row[1] for row in model_rows]

    c.execute("SELECT id FROM models WHERE image = 1")
    image_model_ids = [row[0] for row in c.fetchall()]

    with st.sidebar:
        if st.button(":heavy_plus_sign: 新しいチャット"):
            st.session_state.now_chat_id = create_new_chat_id(c)
            st.session_state.is_new_chat = True
            st.rerun()

        st.header(":material/psychology: モデル選択")
        selected_display = st.selectbox("モデル選択", model_displays, index=st.session_state.free_model_id-1, label_visibility="collapsed")
        st.session_state.free_model_id = model_displays.index(selected_display) + 1

        st.header(":material/chat: チャット一覧")
        for chat_id, title, last_model_id in load_chats(c):
            chat_container = st.container(horizontal=True, horizontal_alignment="right", gap="small", vertical_alignment="center")
            if st.session_state.edit_chat_id == chat_id:
                new_title = chat_container.text_input("タイトル編集", value=title, label_visibility="collapsed", key=f"edit_{chat_id}")
                icon = ":material/cancel:"
                if new_title != title:
                    icon = ":material/save:"
                if chat_container.button(icon, key=f"save_{chat_id}", type="tertiary", width="content"):
                    if new_title != title:
                        update_chat_title(c, conn, chat_id, new_title)
                    st.session_state.edit_chat_id = None
                    st.rerun()
            else:
                col1, col2, col3 = chat_container.columns([6, 1, 1], vertical_alignment="center", gap=None)
                if col1.button(title, key=f"title_{chat_id}", type="tertiary", width="content"):
                    st.session_state.now_chat_id = chat_id
                    st.session_state.is_new_chat = False
                    st.session_state.free_model_id = last_model_id
                    st.rerun()
                if col2.button(":material/edit:", key=f"edit_{chat_id}", type="tertiary", width="stretch"):
                    st.session_state.edit_chat_id = chat_id
                    st.rerun()
                if col3.button(":material/delete:", key=f"delete_{chat_id}", type="tertiary", width="stretch"):
                    delete_chat(c, conn, chat_id)
                    if st.session_state.now_chat_id == chat_id:
                        st.session_state.now_chat_id = None
                    st.rerun()

    if "now_message_id" in st.session_state:
        delete_message(c, conn, st.session_state.now_message_id, st.session_state.now_chat_id)
    st.session_state.now_message_id = None

    chat_id = st.session_state.now_chat_id
    if chat_id:
        if st.session_state.is_new_chat:
            messages = []
        else:
            messages = load_messages(c, chat_id)

        chat_history = []
        for i, msg in enumerate(messages):
            if msg["role"] == "assistant":
                chat_history.append(types.Content(role="model", parts=[types.Part.from_text(text=msg["content"])]))
                model_name = model_names[msg["model_id"]-1]
                with st.chat_message(model_name.split('-')[1]):
                    st.markdown(msg["content"])
                    st.badge(model_name)
                    if st.button("音声として再生", icon=":material/play_circle:", key=i):
                        with st.spinner("音声に変換中..."):
                            audio_bytes = generate_audio(gen_client, msg["content"])
                        st.audio(audio_bytes, format="audio/wav", autoplay=True)

            elif msg["role"] == "reasoning":
                model_name = model_names[messages[i+1]["model_id"]-1]
                with st.chat_message(model_name.split('-')[1]):
                    with st.expander("Reasoning"):
                        st.caption(msg["content"])
            else:
                chat_history.append(types.UserContent(parts=[types.Part.from_text(text=msg["content"])]))
                with st.chat_message("user"):
                    col1, col2 = st.columns([0.99, 0.01], vertical_alignment="center")
                    with col1:
                        st.text(msg["content"])
                        if msg["image"]: # 画像がある場合は表示
                            if st.session_state.free_model_id in image_model_ids:
                                image = Image.open(io.BytesIO(msg["image"]))
                                chat_history.append(types.UserContent(parts=[types.Part.from_bytes(data=msg["image"], mime_type="image/jpeg")]))
                                st.image(image)
                            else:
                                st.error("選択中のモデルは画像に対応していません。")
                    with col2:
                        if st.button(":material/delete:", key=f"user_{msg['id']}"):
                            st.session_state.now_message_id = msg["id"]
                            st.rerun()
            msg.pop("model_id", None)
            msg.pop("id", None)

        if prompt := st.chat_input("質問してみましょう", accept_file=True):
            image_bytes = None
            if prompt["files"]:
                if st.session_state.free_model_id in image_model_ids:
                    image_file = prompt["files"][0]
                    image = Image.open(image_file)
                    if image.width > 1920 or image.height > 1920:
                        image.thumbnail((1920, 1920))
                    image_bytes = io.BytesIO()
                    if image.mode == "RGBA":
                        image = image.convert("RGB")
                    image.save(image_bytes, format="JPEG")
                    image_bytes = image_bytes.getvalue()
                    chat_history.append(types.UserContent(parts=[types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")]))
                else:
                    st.error("選択中のモデルは画像に対応していません。")
            # 新規チャットか既存チャットかで保存処理を分岐
            if st.session_state.is_new_chat:
                save_chat_and_message(c, conn, chat_id, prompt.text, image_bytes, st.session_state.free_model_id)
                st.session_state.is_new_chat = False
            else:
                add_message(c, conn, chat_id, "user", prompt.text, image_bytes, st.session_state.free_model_id)
            messages.append({
                "role": "user",
                "content": prompt.text,
                "image": image_bytes
            })

            # ユーザーメッセージ表示
            with st.chat_message("user"):
                col1, col2 = st.columns([0.99, 0.01], vertical_alignment="center")
                with col1:
                    st.text(prompt.text)
                    if image_bytes:
                        st.image(image_bytes)
                with col2:
                    if st.button(":material/delete:", key=f"user_{len(messages)}"):
                        st.session_state.now_message_id = len(messages)
                        st.rerun()

            # アシスタント応答生成
            model_name = model_names[st.session_state.free_model_id-1]
            with st.chat_message(model_name.split('-')[1]):
                reasoning_placeholder = st.empty()
                message_placeholder = st.empty()
            if model_name.startswith("gem"):
                chat = gen_client.chats.create(
                    model=model_name,
                    history=chat_history,
                )
                response = chat.send_message_stream(prompt.text)
            else:
                processed_messages = []
                for m in messages:
                    if m["image"] and st.session_state.free_model_id in image_model_ids: # 画像付きメッセージの場合
                        processed_messages.append({
                            "role": m["role"],
                            "content": [
                                {"type": "text", "text": m["content"]},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(m['image']).decode('utf-8')}"}}
                            ]
                        })
                    elif m["role"] != "reasoning": # テキストのみのメッセージの場合
                        processed_messages.append({
                            "role": m["role"],
                            "content": [
                                {"type": "text", "text": m["content"]}
                            ]
                        })
                response = groq_client.chat.completions.create(
                    model=model_name,
                    messages=processed_messages,
                    stream=True,
                )
            resoning_text = ""
            response_text = ""
            for chunk in response:
                if model_name.startswith("gem"):
                    if hasattr(chunk, "text"):
                        try:
                            response_text += chunk.text
                            message_placeholder.markdown(response_text)
                        except Exception as e:
                            st.warning(e)
                else:
                    if chunk.choices[0].finish_reason != 'stop':
                        content = chunk.choices[0].delta.content
                        reasoning = chunk.choices[0].delta.reasoning
                        if content:
                            response_text += content
                            message_placeholder.markdown(response_text)
                        elif reasoning:
                            resoning_text += chunk.choices[0].delta.reasoning
                            reasoning_placeholder.caption(resoning_text)
                    
            if resoning_text:
                add_message(c, conn, chat_id, "reasoning", resoning_text, None, st.session_state.free_model_id)
            add_message(c, conn, chat_id, "assistant", response_text, None, st.session_state.free_model_id)

            # デフォルトタイトルなら要約して更新
            c.execute("SELECT title FROM chats WHERE id = ?", (chat_id,))
            current_title = c.fetchone()[0]
            if current_title == "新しいチャット":
                new_title = generate_title(gen_client, prompt)
                update_chat_title(c, conn, chat_id, new_title)

            st.rerun()
    else:
        st.info("左のサイドバーからチャットを作成または選択してください。")
        st.warning("Geminiの入力は学習に使用されます。")
        all_model = sorted([m.id for m in groq_client.models.list().data])
        st.html("<br>".join(all_model))

if __name__ == "__main__" or True:  # Streamlitでは直接実行されるため
    main()