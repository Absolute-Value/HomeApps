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

        selected_id = st.selectbox("IDを選択してください", invoice_df["id"], index=None, placeholder="IDを選択")
        
        if selected_id:
            conn = sqlite3.connect(DB_PATH)
            item_df = pd.read_sql_query(f"SELECT id, 品名, 金額, 単位 FROM items WHERE invoice_id = {selected_id}", conn)
            conn.close()

            edited_df = st.data_editor(
                item_df,
                hide_index=True,
                disabled=["id"],
                num_rows="dynamic",
                use_container_width=True,
                key="item_editor"
            )
            total = edited_df["金額"].sum()
            st.write(f'小計: {invoice_df.loc[invoice_df["id"] == selected_id, "小計"].values[0]} 円')
            st.write(f"品目の合計金額: {total} 円")

            if st.button("変更を保存"):
                conn = sqlite3.connect(DB_PATH)
                for idx, row in edited_df.iterrows():
                    conn.execute(
                        "UPDATE items SET 品名 = ?, 金額 = ?, 単位 = ? WHERE id = ?",
                        (row["品名"], row["金額"], row["単位"], row["id"])
                    )
                # 削除された行をDBから削除
                original_ids = set(item_df["id"])
                edited_ids = set(edited_df["id"])
                deleted_ids = original_ids - edited_ids
                for del_id in deleted_ids:
                    conn.execute("DELETE FROM items WHERE id = ?", (del_id,))
                conn.execute(
                    "UPDATE invoices SET 品目の合計金額 = ? WHERE id = ?",
                    (total, selected_id)
                )
                conn.commit()
                conn.close()
                st.success("変更を保存しました。")
                st.rerun()

            image_name = invoice_df.loc[invoice_df["id"] == selected_id, "画像名"].values[0]
            image_path = os.path.join(IMAGES_DIR, image_name)
            if os.path.exists(image_path):
                st.image(image_path)
            else:
                st.warning(f"画像は削除されています: {image_name}")

if __name__ == "__main__":
    main()