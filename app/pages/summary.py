import os
import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "/data/expenses.db"

st.set_page_config(
    page_title="集計ページ",
    page_icon="📊",
    layout="wide",
)

def main():
    st.title("集計ページ")

    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        invoice_df = pd.read_sql_query("SELECT * FROM invoices", conn)
        conn.close()

        # 店名ごとに合計金額を集計
        if '店名' in invoice_df.columns and '合計' in invoice_df.columns:
            store_summary = invoice_df.groupby('店名')['合計'].sum().reset_index()
            store_summary = store_summary.sort_values('合計', ascending=False)
            st.subheader("店名ごとの合計金額")
            st.dataframe(store_summary, hide_index=True)
        
        # 年ごとの合計金額を集計し、年を選択して棒グラフを表示
        if '請求日' in invoice_df.columns and '合計' in invoice_df.columns:
            invoice_df['年'] = pd.to_datetime(invoice_df['請求日']).dt.year
            year_summary = invoice_df.groupby('年')['合計'].sum().reset_index()
            year_summary = year_summary.sort_values('合計', ascending=False)

            # 年を選択
            years = sorted(invoice_df['年'].unique())
            selected_year = st.selectbox("年を選択してください", years)

            # 選択した年の月ごとの合計金額を集計
            df_selected = invoice_df[invoice_df['年'] == selected_year].copy()
            df_selected['月'] = pd.to_datetime(df_selected['請求日']).dt.month
            month_summary = df_selected.groupby('月')['合計'].sum().reset_index()
            month_summary = month_summary.sort_values('月')

            st.subheader(f"{selected_year}年の月ごとの合計金額（棒グラフ）")
            st.bar_chart(month_summary.set_index('月'))

if __name__ == "__main__":
    main()