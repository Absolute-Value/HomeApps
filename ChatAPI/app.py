import streamlit as st

st.set_page_config(
    page_title="チャットアプリ",
    page_icon="💬",
    layout="wide",
)

# https://fonts.google.com/icons
st.title("チャットアプリ")
st.page_link("pages/openai_chat.py", label="OpenAI Chat", icon=":material/face_2:")
st.page_link("pages/free_chat.py", label="Free AI Chat", icon=":material/robot_2:")
st.page_link("pages/gemini_image.py", label="Gemini Image", icon=":material/wand_stars:")