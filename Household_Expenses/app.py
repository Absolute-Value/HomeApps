import streamlit as st

st.set_page_config(
    page_title="家計簿アプリ",
    page_icon=":money_with_wings:",
    layout="wide",
)

st.title("家計簿アプリ")
st.page_link("pages/upload.py", label="登録ページ", icon="📝")
st.page_link("pages/summary.py", label="集計ページ", icon="📊")
st.page_link("pages/list.py", label="一覧ページ", icon="📃")