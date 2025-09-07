import streamlit as st

pages = {
    "チャット": [
        st.Page("chat/free_chat.py", title="Free AI Chat", icon=":material/chat:"),
        st.Page("chat/gemini_image.py", title="Gemini 画像生成", icon=":material/image:"),
        st.Page("chat/openai_chat.py", title="OpenAI Chat", icon=":material/network_intelligence:"),
    ],
    "タスク": [
        st.Page("task/qa.py", title="一問一答", icon=":material/mark_chat_read:"),
    ],
    "音声": [
        st.Page("audio/text_to_speech.py", title="音声合成", icon=":material/text_to_speech:"),
        st.Page("audio/speech_to_text.py", title="音声認識", icon=":material/speech_to_text:"),
    ],
}

pg = st.navigation(pages)
pg.run()
