import streamlit as st

st.set_page_config(
    page_title="チャットアプリ",
    page_icon="💬",
    layout="wide",
)

# https://fonts.google.com/icons
st.title("チャットアプリ")
st.page_link("pages/openai_chat.py", label="OpenAI Chat", icon=":material/face_2:")
st.page_link("pages/gemini_chat.py", label="Gemini Chat", icon=":material/robot_2:")
st.page_link("pages/gemini_image.py", label="Gemini Image", icon=":material/wand_stars:")
st.page_link("pages/groq_chat.py", label="Groq Chat", icon=":material/robot:")