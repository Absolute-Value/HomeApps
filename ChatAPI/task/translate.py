import streamlit as st
from groq import Groq

PAGE_TITLE = "翻訳"
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=":material/chat:",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title(PAGE_TITLE)

client = Groq()

LANGUAGE_OPTIONS = ('日本語', '英語')
if "before_lang" not in st.session_state:
    st.session_state.before_lang = LANGUAGE_OPTIONS[1]
if "after_lang" not in st.session_state:
    st.session_state.after_lang = LANGUAGE_OPTIONS[0]

@st.fragment
def language_fragment():
    language_container = st.container(horizontal=True, vertical_alignment="center")
    st.session_state.before_lang = language_container.text_input(
        "before", value=st.session_state.before_lang, placeholder="翻訳前", 
        autocomplete="language", width=150, label_visibility="collapsed"
    )
    language_container.text('から')
    st.session_state.after_lang = language_container.text_input(
        "after", value=st.session_state.after_lang, placeholder="翻訳後", 
        autocomplete="language", width=150, label_visibility="collapsed"
    )
    if language_container.button("<->"):
        tmp = st.session_state.before_lang
        st.session_state.before_lang = st.session_state.after_lang
        st.session_state.after_lang = tmp
        st.rerun(scope="fragment")

language_fragment()
user_input = st.text_area('翻訳したい文章', height="content", placeholder="翻訳したい文章を入力してください", label_visibility="collapsed")

if st.button('翻訳'):
    response = client.chat.completions.create(
        model="moonshotai/kimi-k2-instruct",
        messages=[
            {
                "role": "system",
                "content": f"ユーザーから与えられた文章を{st.session_state.before_lang}から{st.session_state.after_lang}に翻訳してください。\n翻訳した文章のみを出力してください。"
            },
            {
                "role": "user",
                "content": user_input
            },
        ],
        temperature=0,
        stream=True,
    )
    response_placeholder = st.empty()
    response_text = ""
    for chunk in response:
        if chunk.choices[0].finish_reason != 'stop':
            response_text += chunk.choices[0].delta.content
            response_placeholder.markdown(response_text)