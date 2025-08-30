import streamlit as st
from groq import Groq

PAGE_TITLE = "翻訳"
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=":material/translate:",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title(PAGE_TITLE)

client = Groq()

with st.form("my_form"):
    container = st.container(horizontal=True, vertical_alignment="center")
    container.text("翻訳先：")
    language = container.text_input(
        "翻訳先", value="日本語", placeholder="翻訳先", 
        autocomplete="language", label_visibility="collapsed"
    )
    user_input = st.text_area(
        '翻訳したい文章', height="content", 
        placeholder="翻訳したい文章を入力してください", label_visibility="collapsed"
    )
    st.form_submit_button('翻訳')

if user_input:
    response = client.chat.completions.create(
        model="moonshotai/kimi-k2-instruct",
        messages=[
            {
                "role": "system",
                "content": f"ユーザーから与えられた文章を{language}に翻訳してください。\n翻訳した文章のみを出力してください。"
            },
            {
                "role": "user",
                "content": user_input
            },
        ],
        temperature=0,
        stream=True,
    )
    message = st.chat_message("assistant", avatar=":material/translate:")
    response_placeholder = message.empty()
    response_text = ""
    for chunk in response:
        if chunk.choices[0].finish_reason != 'stop':
            response_text += chunk.choices[0].delta.content
            response_placeholder.markdown(response_text)
else:
    st.write('文章が入力されていません。')