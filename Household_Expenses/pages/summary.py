import os
import sqlite3
import pandas as pd
import altair as alt
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
        
        with st.expander("店名ごとの回数ランキング（上位20件）", icon=":material/store:", expanded=True):
            shop_count = invoice_df['店名'].value_counts().reset_index()
            shop_count.columns = ['店名', '回数']
            shop_count = shop_count.sort_values('回数', ascending=False)
            top20 = shop_count.head(20)

            chart = (
                alt.Chart(top20)
                .mark_bar()
                .encode(
                    x=alt.X('回数:Q'),
                    y=alt.Y('店名:N', sort=top20['店名'].tolist())  # ← 並び順を固定
                )
                .properties(height=600)
            )
            st.altair_chart(chart, use_container_width=True)

        # 店名ごとの合計金額を集計し、上位20個の項目について棒グラフを表示
        with st.expander("店名ごとの合計金額（上位20件）", icon=":material/point_of_sale:"):
            shop_summary = invoice_df.groupby('店名')['合計'].sum().reset_index()
            shop_summary = shop_summary.sort_values('合計', ascending=False)
            top20 = shop_summary.head(20)
            
            chart = (
                alt.Chart(top20)
                .mark_bar()
                .encode(
                    x=alt.X('合計:Q'),
                    y=alt.Y('店名:N', sort=top20['店名'].tolist())  # ← 並び順を固定
                )
                .properties(height=600)
            )
            st.altair_chart(chart, use_container_width=True)

        with st.expander("年月（YY/MM）ごとの合計金額（棒グラフ）", icon=":material/calendar_month:", expanded=True):
            invoice_df['年月'] = pd.to_datetime(invoice_df['請求日']).dt.strftime('%y/%m')
            ym_summary = invoice_df.groupby('年月')['合計'].sum().reset_index()
            ym_summary = ym_summary.sort_values('年月')

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