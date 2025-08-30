import streamlit as st
from groq import Groq

st.title("一問一答")
task_name = st.segmented_control("タスク", options=["翻訳", "要約"], default="翻訳", label_visibility="collapsed")

st.set_page_config(
    page_title=task_name,
    page_icon=":material/mark_chat_read:",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.header(task_name)

client = Groq()

with st.form("my_form"):
    system_prompt = f"ユーザーから与えられた文章を要約してください。\n要約した文章のみを出力してください。"
    icon = ":material/summarize:"
    if task_name == "翻訳":
        container = st.container(horizontal=True, vertical_alignment="center")
        container.text("翻訳先：")
        language = container.text_input(
            "翻訳先", value="日本語", placeholder="翻訳先", 
            autocomplete="language", label_visibility="collapsed"
        )
        system_prompt = f"ユーザーから与えられた文章を{language}に翻訳してください。\n翻訳した文章のみを出力してください。"
        icon = ":material/translate:"
    user_input = st.text_area(
        f'{task_name}したい文章', height="content", 
        placeholder=f"{task_name}したい文章を入力してください", label_visibility="collapsed"
    )
    st.form_submit_button(task_name)

message = st.chat_message("assistant", avatar=icon)
if user_input:
    response = client.chat.completions.create(
        model="moonshotai/kimi-k2-instruct",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_input
            },
        ],
        temperature=0,
        stream=True,
    )
    response_placeholder = message.empty()
    response_text = ""
    for chunk in response:
        if chunk.choices[0].finish_reason != 'stop':
            response_text += chunk.choices[0].delta.content
            response_placeholder.markdown(response_text)
else:
    message.write('文章が入力されていません。')