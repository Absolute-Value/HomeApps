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
    st.title("📊 集計ページ")

    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        invoice_df = pd.read_sql_query("SELECT * FROM invoices", conn)
        conn.close()
        
        # 年月（YY/MM）ごとの合計金額を集計し、棒グラフを表示
        if '請求日' in invoice_df.columns and '合計' in invoice_df.columns:
            invoice_df['年月'] = pd.to_datetime(invoice_df['請求日']).dt.strftime('%y/%m')
            ym_summary = invoice_df.groupby('年月')['合計'].sum().reset_index()
            ym_summary = ym_summary.sort_values('年月')

            st.subheader("年月（YY/MM）ごとの合計金額（棒グラフ）")
            st.line_chart(ym_summary.set_index('年月'))
            selected_ym = st.selectbox("年月を選択してください", ym_summary['年月'][::-1])

            if selected_ym:
                filtered_df = invoice_df[invoice_df['年月'] == selected_ym]
                if '店名' in filtered_df.columns and '合計' in filtered_df.columns:
                    shop_summary = filtered_df.groupby('店名')['合計'].sum().reset_index()
                    shop_summary = shop_summary.sort_values('合計', ascending=False)
                    st.dataframe(shop_summary, hide_index=True)

if __name__ == "__main__":
    main()