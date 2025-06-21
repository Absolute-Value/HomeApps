import os
import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "/data/expenses.db"

def main():
    st.title("集計ページ")
    
    st.write("ここでは、登録されたレシートの集計結果を表示します。")

    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM invoices", conn)
        st.dataframe(df)
        conn.close()

if __name__ == "__main__":
    main()