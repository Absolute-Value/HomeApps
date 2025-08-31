import os
import sqlite3
import pandas as pd
import streamlit as st

PAGE_TITLE = "集計ページ"
DB_PATH = "/data/expenses.db"

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=":material/bar_chart_4_bars:",
    layout="wide",
)

def main():
    st.title(PAGE_TITLE)

    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        invoice_df = pd.read_sql_query("SELECT * FROM invoices", conn)
        conn.close()
        
        # 店名ごとの合計金額を集計し、上位20個の項目について棒グラフを表示
        if '店名' in invoice_df.columns and '合計' in invoice_df.columns:
            shop_summary = invoice_df.groupby('店名')['合計'].sum().reset_index()
            shop_summary = shop_summary.sort_values('合計', ascending=False)
            top20 = shop_summary.head(20)
            
            st.subheader("店名ごとの合計金額（上位20件）")
            st.bar_chart(top20.set_index('店名'), horizontal=True, height=600)
        # 年月（YY/MM）ごとの合計金額を集計し、折れ線グラフを表示
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
                    d = st.dataframe(
                        shop_summary, 
                        hide_index=True, 
                        selection_mode="single-row", 
                        on_select="rerun"
                    )

                    if d.selection.rows:
                        filtered_selected = filtered_df[filtered_df["店名"] == shop_summary.iloc[d.selection.rows[0]]['店名']].copy().sort_values('合計', ascending=False)
                        st.dataframe(
                            filtered_selected,
                            column_order=("id", "店の受取人", "請求日", "品目の合計金額", "小計", "税金", "合計"),
                            hide_index=True, 
                        )

if __name__ == "__main__":
    main()