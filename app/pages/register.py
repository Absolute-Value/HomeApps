import os
import io
import pandas as pd
import streamlit as st
from PIL import Image
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

MAX_FILE_SIZE = 4 * 1024 * 1024

def initialize_document_intelligence_client():
    """Document Intelligence クライアントを初期化"""
    try:
        client = DocumentIntelligenceClient(
            endpoint=os.getenv("AZURE_ENDPOINT"),
            credential=AzureKeyCredential(os.getenv("AZURE_API_KEY"))
        )
        return client
    except Exception as e:
        st.error(f"Document Intelligence クライアントの初期化に失敗しました: {str(e)}")
        return None

def optimize_image(image_bytes, quality=85):
    """画像を最適化してファイルサイズを削減"""
    try:
        # PIL Imageとして開く
        image = Image.open(io.BytesIO(image_bytes))
        
        # RGBA を RGB に変換（必要に応じて）
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        
        # 画像サイズが大きすぎる場合はリサイズ
        if len(image_bytes) > MAX_FILE_SIZE:
            # 最適化された画像をバイト配列に変換
            optimized_bytes = io.BytesIO()
            image.save(optimized_bytes, format='JPEG', quality=quality, optimize=True)
            optimized_bytes.seek(0)
        else:
            # 画像サイズが適切な場合はそのまま使用
            optimized_bytes = io.BytesIO(image_bytes)
            optimized_bytes.seek(0)
        
        return optimized_bytes.getvalue()
    except Exception as e:
        st.warning(f"画像最適化に失敗: {str(e)}。元の画像を使用します。")
        return image_bytes

def main():
    st.title("レシート登録ページ")
    
    client = initialize_document_intelligence_client()
    if not client:
        return
    
    uploaded_file = st.file_uploader(
        "画像を選択してください",
        type=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'],
    )
    
    if uploaded_file is not None:
        image_bytes = uploaded_file.read()
        optimized_image_bytes = optimize_image(image_bytes)
        st.image(
            Image.open(io.BytesIO(optimized_image_bytes)),
            caption="アップロードされた画像",
            use_container_width=True
        )

        file_size_mb = len(optimized_image_bytes) / (1024 * 1024)
        st.info(f"アップロードされた画像のサイズ: {file_size_mb:.2f} MB")
        
        with st.spinner("OCRを実行中..."):
            poller = client.begin_analyze_document(
                "prebuilt-invoice",
                AnalyzeDocumentRequest(bytes_source=optimized_image_bytes)
            )
            result = poller.result()

        if not result.documents:
            st.error("OCRの結果を取得できませんでした。画像を確認してください。")
            return
        
        st.success("OCRの結果を取得しました")
        invoice = result.documents[0].fields
        for k, v in invoice.items():
            if k == "VendorName":
                st.text_input("店名", v.get("content", ""), key="VendorName")
            elif k == "VendorAddress":
                st.text_area("店の住所", v.get("content", ""), key="VendorAddress")
            elif k == "VendorAddressRecipient":
                st.text_input("店の受取人", v.get("content", ""), key="VendorAddressRecipient")
            elif k == "InvoiceDate":
                st.date_input("請求日", v.get("valueDate", ""), key="InvoiceDate")
            elif k == "InvoiceId":
                st.text_input("請求書番号", v.get("content", ""), key="InvoiceId")
            elif k == "Items":
                items = v.get("valueArray", [])
                rows = []
                for idx, item in enumerate(items):
                    # 各アイテムの内容を個別に表示
                    desc = item.get("valueObject", {}).get("Description", {}).get("content", "")
                    amount_data = item.get("valueObject", {}).get("Amount", {}).get("valueCurrency", {})
                    rows.append({
                        "品名": desc,
                        "金額": amount_data.get("amount", ""),
                        "単位": amount_data.get("currencyCode", "")
                    })
                df = pd.DataFrame(rows)
                edited_df = st.data_editor(df)
                st.write(f"品目の合計金額: {edited_df['金額'].apply(pd.to_numeric, errors='coerce').sum()}")
            elif k == "SubTotal":
                data = v.get("valueCurrency", {})
                st.number_input("小計", int(data.get("amount", "")), key="SubTotal")
                st.write(data.get("currencyCode", ""))
            elif k == "TotalTax":
                data = v.get("valueCurrency", {})
                st.number_input("税金", int(data.get("amount", "")), key="TotalTax")
                st.write(data.get("currencyCode", ""))
            elif k == "InvoiceTotal":
                data = v.get("valueCurrency")
                st.number_input("合計", int(data.get("amount", "")), key="InvoiceTotal")
                st.write(data.get("currencyCode", ""))
            else:
                st.write(f"{k}: {v}")

        st.write(invoice.get("VendorName"))
        
if __name__ == "__main__":
    main()