import streamlit as st

st.set_page_config(
    page_title="チャットアプリ",
    page_icon="💬",
    layout="wide",
)

# https://www.webfx.com/tools/emoji-cheat-sheet/
st.title("チャットアプリ")
st.page_link("pages/openai_chat.py", label="OpenAI", icon=":material/face_2:")
st.page_link("pages/gemini_chat.py", label="Gemini Chat", icon=":material/robot_2:")
st.page_link("pages/gemini_image.py", label="Gemini Image", icon=":material/wand_stars:")