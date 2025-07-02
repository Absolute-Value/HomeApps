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
    # 新しいチャットを作成し、そのIDを返す
    cursor.execute("INSERT INTO chats DEFAULT VALUES")
    chat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return chat_id

def get_all_chats():
    conn = get_db_connection()
    cursor = conn.cursor()
    # メッセージが存在するチャットのみを取得
    cursor.execute("""
        SELECT c.chat_id, c.created_at
        FROM chats c
        JOIN messages m ON c.chat_id = m.chat_id
        GROUP BY c.chat_id, c.created_at
        ORDER BY c.created_at DESC
    """)
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
    # 既にチャットが存在することを確認し、なければ作成する処理はinitialize_chat_sessionで行う
    # ここでは渡されたchat_idに対してメッセージを追加する
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
if 'chat_id' not in st.session_state or st.session_state.chat_id is None:
    # 最初のページロード時にはチャットIDをNoneにしておく
    st.session_state.chat_id = None
if 'chat_session' not in st.session_state:
    st.session_state.chat_session = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'model_name' not in st.session_state:
    st.session_state.model_name = MODEL_OPTIONS["Gemini-2.5-Flash"] # デフォルトモデルを設定

# --- チャットセッション初期化 ---
def initialize_chat_session(chat_id):
    if chat_id is None:
        st.session_state.chat_session = None
        st.session_state.messages = []
        return

    chat_history = load_chat_history(chat_id)
    client = genai.Client()
    formatted_history = []
    for chat_dict in chat_history:
        if chat_dict["role"]=="user":
            formatted_history.append(types.UserContent(parts=[types.Part.from_text(text=chat_dict["content"])]))
        else:
            # Gemini APIはrole='model'で応答を期待する
            formatted_history.append(types.Content(role="model", parts=[types.Part.from_text(text=chat_dict["content"])]))

    # createメソッドはモデル名と履歴を受け取ってチャットセッションを返す
    st.session_state.chat_session = client.chats.create(model=st.session_state["model_name"], history=formatted_history)
    st.session_state.messages = chat_history

# --- サイドバー：チャット管理 ---
with st.sidebar:
    # 「新しいチャット」ボタンは、メッセージ入力時または明示的に押されたときに新しいチャットを作成
    if st.button(":heavy_plus_sign: 新しいチャット", key="new_chat_button"):
        st.session_state.chat_id = create_new_chat()
        initialize_chat_session(st.session_state.chat_id)
        st.rerun()

    selected_label = st.selectbox(":gear: モデル選択", list(MODEL_OPTIONS.keys()), key="model_select")
    # モデル選択が変更されたら、現在のチャットセッションを新しいモデルで再初期化する
    if selected_label != list(MODEL_OPTIONS.keys())[list(MODEL_OPTIONS.values()).index(st.session_state.model_name)]:
        st.session_state["model_name"] = MODEL_OPTIONS[selected_label]
        initialize_chat_session(st.session_state.chat_id) # モデル変更に伴いセッションを再初期化
        st.rerun()

    st.subheader(":speech_balloon: チャット一覧")
    all_chats = get_all_chats()
    if not all_chats:
        st.info("まだチャットがありません。最初のメッセージを入力してください。")
    else:
        for c in all_chats:
            # 各チャットのボタンには一意のキーを付与
            col1, col2 = st.columns([4,1], vertical_alignment="center")
            with col1:
                # チャットの日付を表示するだけではなく、ボタンとして扱う
                # チャットの最初のメッセージの冒頭などをタイトルとして表示する方が親切かもしれない
                # ここではシンプルに日付のみ表示
                title = c['created_at']
                if st.button(title, key=f"chat_button_{c['chat_id']}", use_container_width=True):
                    st.session_state.chat_id = c['chat_id']
                    initialize_chat_session(st.session_state.chat_id) # 選択されたチャットのセッションを初期化
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"delete_button_{c['chat_id']}", use_container_width=True):
                    delete_chat(c['chat_id'])
                    # 現在表示しているチャットを削除した場合、新しいチャットを開始する
                    if st.session_state.chat_id == c['chat_id']:
                        st.session_state.chat_id = create_new_chat() # 新しいチャットを作成
                        st.session_state.messages = [] # メッセージ履歴もリセット
                    else:
                        # 削除したチャットが現在のチャットでない場合も、表示されているチャットのIDが有効か確認
                        # 有効でない場合は、新しいチャットを作成してリロードする
                        if st.session_state.chat_id not in [chat['chat_id'] for chat in get_all_chats() + [{'chat_id':-1}]] : # + [{'chat_id':-1}] は、全てのチャットが削除された場合を考慮
                            st.session_state.chat_id = create_new_chat()
                            st.session_state.messages = []
                    initialize_chat_session(st.session_state.chat_id) # 現在のチャットセッションを再初期化
                    st.rerun()

# 初期化処理:
# もしchat_idがまだNoneであれば、初回ロード時であることを示唆。
# ユーザーが入力するまで何もしない。
if st.session_state.chat_id is not None:
    initialize_chat_session(st.session_state.chat_id)

# --- メッセージ表示 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 入力処理 ---
user_input = st.chat_input("メッセージを入力してください...")

if user_input:
    # ここで最初のメッセージ入力があった場合に、まだchat_idがなければ新しいチャットを作成する
    if st.session_state.chat_id is None:
        st.session_state.chat_id = create_new_chat()
        initialize_chat_session(st.session_state.chat_id) # 新しいチャットのセッションを初期化

    # 表示・セッションに追加
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("model"):
        # send_message_stream はチャットセッションオブジェクトのメソッド
        response = st.session_state.chat_session.send_message_stream(user_input)
        response_text = ""
        message_placeholder = st.empty()
        for chunk in response:
            # chunkオブジェクトにtext属性があるか確認
            if hasattr(chunk, "text"):
                response_text += chunk.text
                message_placeholder.markdown(response_text)
        st.session_state.messages.append({"role": "model", "content": response_text})

    # DBに保存
    save_chat_history_items(
        st.session_state.chat_id,
        [{'role': 'user', 'content': user_input},
            {'role': 'model', 'content': response_text}]
    )

    # メッセージが追加されたので、UIを再描画
    st.rerun()