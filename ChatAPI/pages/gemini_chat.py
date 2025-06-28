import streamlit as st
from google import genai

st.set_page_config(
    page_title="Gemini",
    page_icon=":robot:",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title("Gemini")

client = genai.Client()

with st.sidebar:
    model_options = {
        "Gemini-2.5-Flash-Lite": "gemini-2.5-flash-lite-preview-06-17",
        "Gemini-2.5-Flash": "gemini-2.5-flash",
    }
    selected_label = st.selectbox(":gear: モデル選択", list(model_options.keys()))
    st.session_state["model_name"] = model_options[selected_label]

# --- セッションステートの初期化 ---
if "chat" not in st.session_state:
    # Gemini モデルの初期化
    st.session_state.chat = client.chats.create(model=st.session_state["model_name"])
    # Streamlitで表示するためのメッセージ履歴
    st.session_state.messages = []

# --- チャット履歴の表示 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- ユーザー入力と応答生成 ---
if prompt := st.chat_input("メッセージを入力してください..."):
    # ユーザーメッセージを履歴に追加して表示
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Geminiにメッセージを送信し、応答を取得
    with st.chat_message("assistant"):
        try:
            # Geminiのチャットセッションを通じてメッセージを送信
            # これにより、Geminiが会話履歴を自動的に考慮します
            response = st.session_state.chat.send_message_stream(prompt)

            # ストリーミング応答を処理
            full_response = ""
            message_placeholder = st.empty()
            for chunk in response:
                # chunk.text は安全にアクセスできることを確認
                if hasattr(chunk, 'text'):
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌") # タイピングエフェクト
            message_placeholder.markdown(full_response) # 最終的な応答を表示

            # AIの応答を履歴に追加
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"Gemini APIからの応答中にエラーが発生しました: {e}")
            # エラーが発生した場合も、ダミーの応答を履歴に追加（オプション）
            st.session_state.messages.append({"role": "assistant", "content": "エラーが発生しました。もう一度お試しください。"})

# --- チャット履歴のリセットボタン ---
if st.sidebar.button("チャットをリセット"):
    st.session_state.messages = []
    st.session_state.chat = client.chats.create(model=st.session_state["model_name"]) # 新しいチャットセッションを開始
    st.rerun() # ページを再読み込みしてチャットをクリア