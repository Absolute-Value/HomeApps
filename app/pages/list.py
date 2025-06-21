import os
import sqlite3
import pandas as pd
import streamlit as st

IMAGES_DIR = "/data/done"
DB_PATH = "/data/expenses.db"

st.set_page_config(
    page_title="一覧ページ",
    page_icon="📃",
    layout="wide",
)

def main():
    st.title("一覧ページ")
    
    st.write("ここでは、登録されたレシートの集計結果を表示します。")
    if st.button("更新"):
        st.rerun()

    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        invoice_df = pd.read_sql_query("SELECT * FROM invoices", conn)
        st.dataframe(invoice_df, hide_index=True)
        conn.close()

        selected_id = st.selectbox("IDを選択してください", invoice_df["id"])
            
        conn = sqlite3.connect(DB_PATH)
        item_df = pd.read_sql_query(f"SELECT 品名, 金額, 単位 FROM items WHERE invoice_id = {selected_id}", conn)
        st.dataframe(item_df, hide_index=True)
        conn.close()

        image_name = invoice_df.loc[invoice_df["id"] == selected_id, "画像名"].values[0]
        image_path = os.path.join(IMAGES_DIR, image_name)
        if os.path.exists(image_path):
            st.image(image_path)
        else:
            st.warning(f"画像は削除されています: {image_name}")

if __name__ == "__main__":
    main()