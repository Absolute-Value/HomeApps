import os
import time
import sqlite3
import pandas as pd
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

IMAGE_FOLDER = "/data/images"
DONE_FOLDER = "/data/done"
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(DONE_FOLDER, exist_ok=True)

DB_PATH = "/data/expenses.db"

def initialize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            店名 TEXT,
            店の受取人 TEXT,
            店の住所 TEXT,
            請求日 TEXT,
            請求書番号 TEXT,
            品目の合計金額 REAL,
            小計 REAL,
            税金 REAL,
            合計 REAL,
            画像名 TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            品名 TEXT,
            金額 REAL,
            単位 TEXT,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id)
        )
    """)
    conn.commit()
    conn.close()

initialize_database()

def initialize_document_intelligence_client():
    """Document Intelligence クライアントを初期化"""
    try:
        client = DocumentIntelligenceClient(
            endpoint=os.getenv("AZURE_ENDPOINT"),
            credential=AzureKeyCredential(os.getenv("AZURE_API_KEY"))
        )
        return client
    except Exception as e:
        print(f"Document Intelligence クライアントの初期化に失敗しました: {str(e)}")
        return None

def main():
    client = initialize_document_intelligence_client()
    
    while True:
        image_names = os.listdir(IMAGE_FOLDER)
        if len(image_names) > 0:
            print(len(image_names))
            for idx, image_name in enumerate(image_names):
                print(f"{idx + 1}: {image_name}")
                image_path = os.path.join(IMAGE_FOLDER, image_name)
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
                poller = client.begin_analyze_document(
                    "prebuilt-invoice",
                    AnalyzeDocumentRequest(bytes_source=image_bytes)
                )
                result = poller.result()

                if not result.documents:
                    print("OCRの結果を取得できませんでした。画像を確認してください。")
                    continue
        
                invoice = result.documents[0].fields

                database_keys = [
                    "店名", "店の受取人", "店の住所", "請求日", "請求書番号", "品目の合計金額", "小計", "税金", "合計"
                ]
                database = {key: "" for key in database_keys}
                for k, v in invoice.items():
                    if k == "VendorName":
                        database["店名"] = v.get("content", "")
                    elif k == "VendorAddress":
                        database["店の住所"] = v.get("content", "")
                    elif k == "VendorAddressRecipient":
                        database["店の受取人"] = v.get("content", "")
                    elif k == "InvoiceDate":
                        database["請求日"] = v.get("valueDate", "")
                    elif k == "InvoiceId":
                        database["請求書番号"] = v.get("content", "")
                    elif k == "Items":
                        items = v.get("valueArray", [])
                        items_rows = []
                        for idx, item in enumerate(items):
                            # 各アイテムの内容を個別に表示
                            desc = item.get("valueObject", {}).get("Description", {}).get("content", "")
                            amount_data = item.get("valueObject", {}).get("Amount", {}).get("valueCurrency", {})
                            items_rows.append({
                                "品名": desc,
                                "金額": amount_data.get("amount", ""),
                                "単位": amount_data.get("currencyCode", "")
                            })
                        df = pd.DataFrame(items_rows)
                        database["品目の合計金額"] = df['金額'].apply(pd.to_numeric, errors='coerce').sum()
                    elif k == "SubTotal":
                        data = v.get("valueCurrency", {})
                        database["小計"] = int(data.get("amount", ""))
                    elif k == "TotalTax":
                        data = v.get("valueCurrency", {})
                        database["税金"] = int(data.get("amount", ""))
                    elif k == "InvoiceTotal":
                        data = v.get("valueCurrency")
                        database["合計"] = int(data.get("amount", ""))
                    else:
                        print(f"{k}: {v}")
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO invoices (店名, 店の受取人, 店の住所, 請求日, 請求書番号, 品目の合計金額, 小計, 税金, 合計, 画像名)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    database["店名"],
                    database["店の受取人"],
                    database["店の住所"],
                    database["請求日"],
                    database["請求書番号"],
                    database["品目の合計金額"],
                    database["小計"],
                    database["税金"],
                    database["合計"],
                    image_name
                ))
                invoice_id = cursor.lastrowid  # 追加した請求書のIDを取得

                # itemsテーブルに品目を挿入
                for row in items_rows:
                    cursor.execute("""
                        INSERT INTO items (invoice_id, 品名, 金額, 単位)
                        VALUES (?, ?, ?, ?)
                    """, (
                        invoice_id,
                        row.get("品名", ""),
                        row.get("金額", ""),
                        row.get("単位", "")
                    ))

                conn.commit()
                conn.close()

                # 画像をdoneフォルダに移動
                done_path = os.path.join(DONE_FOLDER, image_name)
                os.rename(image_path, done_path)

        time.sleep(5)  # 5秒待機してから再度チェック

if __name__ == "__main__":
    main()