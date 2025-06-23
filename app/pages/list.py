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
        st.dataframe(
            invoice_df,
            hide_index=True,
            column_config={
                "品目の合計金額": st.column_config.NumberColumn(),
                "小計": st.column_config.NumberColumn(),
                "税金": st.column_config.NumberColumn(),
                "合計": st.column_config.NumberColumn(),
                "請求日": st.column_config.DateColumn(
                    format="YYYY/MM/DD",
                    help="請求日を選択してください"
                ),
            }
        )
        conn.close()

        selected_id = st.selectbox("IDを選択してください", invoice_df["id"], index=None, placeholder="IDを選択")
        
        if selected_id:
            invoice_selected = invoice_df[invoice_df["id"] == selected_id].copy()
            if "請求日" in invoice_selected.columns:
                invoice_selected["請求日"] = pd.to_datetime(invoice_selected["請求日"], errors="coerce")
            edited_invoice = st.data_editor(
                invoice_selected,
                hide_index=True,
                disabled=["id", "品目の合計金額", "画像名"],
                use_container_width=True,
                key="invoice_editor",
                column_config={
                    "品目の合計金額": st.column_config.NumberColumn(min_value=0),
                    "小計": st.column_config.NumberColumn(min_value=0),
                    "税金": st.column_config.NumberColumn(min_value=0),
                    "合計": st.column_config.NumberColumn(min_value=0),
                    "請求日": st.column_config.DateColumn(
                        format="YYYY/MM/DD",
                        help="請求日を選択してください"
                    )
                }
            )
            
            conn = sqlite3.connect(DB_PATH)
            item_df = pd.read_sql_query(f"SELECT id, 品名, 金額, 単位 FROM items WHERE invoice_id = {selected_id}", conn)
            conn.close()

            image_name = invoice_df.loc[invoice_df["id"] == selected_id, "画像名"].values[0]
            image_path = os.path.join(IMAGES_DIR, image_name)
            if os.path.exists(image_path):
                col1, col2 = st.columns(2)
                with col2:
                    st.image(image_path, use_container_width=True)
            else:
                col1 = st.columns(1)

            with col1:
                edited_item = st.data_editor(
                    item_df,
                    hide_index=True,
                    disabled=["id"],
                    num_rows="dynamic",
                    use_container_width=True,
                    key="item_editor",
                    column_config={
                        "品名": st.column_config.TextColumn(required=True),
                        "金額": st.column_config.NumberColumn(step=1,format="%d",required=True),
                        "単位": st.column_config.SelectboxColumn(options=["JPY"],default="JPY",required=True)
                    },
                    column_order=["品名", "金額", "単位"]
                )
                total = edited_item["金額"].sum()
                st.write(f"品目の合計金額: {total} 円")

                if st.button("変更を保存"):
                    conn = sqlite3.connect(DB_PATH)
                    for idx, row in edited_item.iterrows():
                        if pd.isnull(row["id"]):
                            # 新規行の追加
                            conn.execute(
                                "INSERT INTO items (invoice_id, 品名, 金額, 単位) VALUES (?, ?, ?, ?)",
                                (selected_id, row["品名"], row["金額"], row["単位"])
                            )
                        else:
                            # 既存行の更新
                            conn.execute(
                                "UPDATE items SET 品名 = ?, 金額 = ?, 単位 = ? WHERE id = ?",
                                (row["品名"], row["金額"], row["単位"], row["id"])
                            )

                    original_ids = set(item_df["id"])
                    edited_ids = set(edited_item["id"])
                    deleted_ids = original_ids - edited_ids
                    for del_id in deleted_ids:
                        conn.execute("DELETE FROM items WHERE id = ?", (del_id,))
                    row = edited_invoice.iloc[0]
                    conn.execute(
                        "UPDATE invoices SET 店名 = ?, 店の受取人 = ?, 店の住所 = ?, 請求日 = ?, 小計 = ?, 税金 = ?, 合計 = ?, 品目の合計金額 = ? WHERE id = ?",
                        (
                            row["店名"],
                            row["店の受取人"],
                            row["店の住所"],
                            row["請求日"].strftime("%Y-%m-%d") if pd.notnull(row["請求日"]) else None,
                            row["小計"],
                            row["税金"],
                            row["合計"],
                            total,
                            selected_id
                        )
                    )
                    conn.commit()
                    conn.close()
                    st.rerun()

if __name__ == "__main__":
    main()