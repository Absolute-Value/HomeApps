import streamlit as st

pages = [
    st.Page("pages/upload.py", title="登録", icon=":material/add_a_photo:"),
    st.Page("pages/list.py", title="一覧", icon=":material/list_alt:"),
    st.Page("pages/summary.py", title="集計", icon=":material/bar_chart_4_bars:"),
]

pg = st.navigation(pages)
pg.run()