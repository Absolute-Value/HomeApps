import asyncio
import os
import shutil
import aiosqlite
import pandas as pd
import altair as alt
import base64
import re
from uuid import uuid4
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from groq import Groq

app = FastAPI()
templates = Jinja2Templates(directory="templates")

client = Groq()

def _log_background_exception(task: asyncio.Task) -> None:
    try:
        task.result()
    except Exception as exc:
        print(f"バックグラウンドタスクエラー: {exc}")

# テンプレートコンテキストにroot_pathを追加するためのカスタム関数
def get_root_path(request: Request = None):
    if request and "x-forwarded-prefix" in request.headers:
        return request.headers["x-forwarded-prefix"]
    return ""

DB_PATH = "../data/expenses.db"
IMAGES_DIR = "../data/done"
WAIT_DIR = "../data/wait"
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(WAIT_DIR, exist_ok=True)

app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

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


def _analyze_document_sync(client: DocumentIntelligenceClient, image_path: str):
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    poller = client.begin_analyze_document(
        "prebuilt-invoice",
        AnalyzeDocumentRequest(bytes_source=image_bytes)
    )
    return poller.result()

async def process_image_ocr(image_path: str, image_name: str):
    """画像をOCR処理してDBに保存するバックグラウンドタスク"""
    try:
        client = initialize_document_intelligence_client()
        if not client:
            print(f"クライアント初期化失敗: {image_name}")
            return
        
        result = await asyncio.to_thread(_analyze_document_sync, client, image_path)

        if not result.documents:
            print(f"OCRの結果を取得できませんでした: {image_name}")
            return

        invoice = result.documents[0].fields

        database_keys = [
            "店名", "店の受取人", "店の住所", "請求日", "請求書番号", "品目の合計金額", "小計", "税金", "合計"
        ]
        database = {key: "" for key in database_keys}
        items_rows = []
        
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
                for item in items:
                    desc = item.get("valueObject", {}).get("Description", {}).get("content", "")
                    amount_data = item.get("valueObject", {}).get("Amount", {}).get("valueCurrency", {})
                    items_rows.append({
                        "品名": desc,
                        "金額": amount_data.get("amount", ""),
                        "単位": amount_data.get("currencyCode", "")
                    })
                df = pd.DataFrame(items_rows)
                if not df.empty and "金額" in df.columns:
                    database["品目の合計金額"] = df['金額'].apply(pd.to_numeric, errors='coerce').sum()
                else:
                    database["品目の合計金額"] = 0
            elif k == "SubTotal":
                data = v.get("valueCurrency", {})
                database["小計"] = int(data.get("amount", ""))
            elif k == "TotalTax":
                data = v.get("valueCurrency", {})
                database["税金"] = int(data.get("amount", ""))
            elif k == "InvoiceTotal":
                data = v.get("valueCurrency")
                database["合計"] = int(data.get("amount", ""))

        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.execute("""
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
            invoice_id = cursor.lastrowid
            for row in items_rows:
                await conn.execute("""
                    INSERT INTO items (invoice_id, 品名, 金額, 単位)
                    VALUES (?, ?, ?, ?)
                """, (
                    invoice_id,
                    row.get("品名", ""),
                    row.get("金額", ""),
                    row.get("単位", "")
                ))
            await conn.commit()

        # 画像をdoneフォルダに移動
        done_path = os.path.join(IMAGES_DIR, image_name)
        os.rename(image_path, done_path)
        print(f"処理完了: {image_name}")
        
    except Exception as e:
        print(f"画像処理エラー ({image_name}): {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    invoices = []
    if os.path.exists(DB_PATH):
        async with aiosqlite.connect(DB_PATH) as conn:
            async with conn.execute("SELECT * FROM invoices ORDER BY id DESC") as cursor:
                rows = await cursor.fetchall()
                columns = [col[0] for col in cursor.description]
                invoices = [dict(zip(columns, row)) for row in rows]
    waiting_count = len(os.listdir(WAIT_DIR))
    return templates.TemplateResponse("index.html", {
        "request": request,
        "page_title": "家計レシート一覧",
        "invoices": invoices,
        "root_path": get_root_path(request),
        "waiting_count": waiting_count
    })

@app.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    # ファイルが選択されているか確認
    if not file or not file.filename:
        return RedirectResponse(url=f"{get_root_path(request)}/?error=ファイルが選択されていません", status_code=303)
    
    # 画像保存
    filename = f"{uuid4()}.jpg"
    save_path = os.path.join(WAIT_DIR, filename)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    task = asyncio.create_task(process_image_ocr(save_path, filename))
    task.add_done_callback(_log_background_exception)
    return RedirectResponse(url=f"{get_root_path(request)}/", status_code=303)

@app.get("/images/{image_name}")
async def get_image(image_name: str):
    image_path = os.path.join(IMAGES_DIR, image_name)
    if os.path.exists(image_path):
        return FileResponse(image_path)
    return HTMLResponse("画像が見つかりません", status_code=404)

@app.get("/edit/{invoice_id}", response_class=HTMLResponse)
async def edit_invoice(request: Request, invoice_id: int):
    invoice = None
    items = []
    items_total = 0
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                columns = [col[0] for col in cursor.description]
                invoice = dict(zip(columns, row))
        async with conn.execute("SELECT * FROM items WHERE invoice_id = ?", (invoice_id,)) as cursor:
            rows = await cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            items = [dict(zip(columns, r)) for r in rows]
            # 品目の合計金額を計算
            for row in rows:
                amount = row[3] if len(row) > 3 else 0  # 金額は4番目のカラム
                items_total += float(amount) if amount else 0
    if not invoice:
        return HTMLResponse("データが見つかりません", status_code=404)
    return templates.TemplateResponse("edit.html", {
        "request": request,
        "invoice": invoice,
        "items": items,
        "items_total": items_total,
        "root_path": get_root_path(request)
    })

@app.post("/edit/{invoice_id}")
async def save_invoice(request: Request, invoice_id: int):
    form = await request.form()
    # 品目の更新・追加
    await update_items(form, invoice_id)
    # 請求書本体の更新（品目の合計金額を含む）
    await update_invoice(form, invoice_id)
    return RedirectResponse(url=f"{get_root_path(request)}/", status_code=303)

# 請求書本体の更新
async def update_invoice(form, invoice_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("""
            UPDATE invoices SET 店名=?, 店の受取人=?, 店の住所=?, 請求日=?, 請求書番号=?, 品目の合計金額=?, 小計=?, 税金=?, 合計=? WHERE id=?
        """, (
            form.get("店名", ""),
            form.get("店の受取人", ""),
            form.get("店の住所", ""),
            form.get("請求日", ""),
            form.get("請求書番号", ""),
            form.get("品目の合計金額", ""),
            form.get("小計", ""),
            form.get("税金", ""),
            form.get("合計", ""),
            invoice_id
        ))
        await conn.commit()

# 品目の更新・追加
async def update_items(form, invoice_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        # 既存品目の更新
        for key in form.keys():
            if key.startswith("item_") and key.endswith("_品名"):
                item_id = key.split("_")[1]
                品名 = form.get(f"item_{item_id}_品名", "")
                金額 = form.get(f"item_{item_id}_金額", 0)
                単位 = form.get(f"item_{item_id}_単位", "JPY")
                await conn.execute("""
                    UPDATE items SET 品名=?, 金額=?, 単位=? WHERE id=?
                """, (品名, 金額, 単位, item_id))
        # 新規品目の追加
        new_品名 = form.get("new_品名", "")
        new_金額 = form.get("new_金額", "")
        new_単位 = form.get("new_単位", "JPY")
        if new_品名 and new_金額:
            await conn.execute("""
                INSERT INTO items (invoice_id, 品名, 金額, 単位) VALUES (?, ?, ?, ?)
            """, (invoice_id, new_品名, new_金額, new_単位))
        await conn.commit()

# 品目削除API
@app.get("/delete_item/{item_id}")
async def delete_item(request: Request, item_id: int, invoice_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        await conn.commit()
    return RedirectResponse(url=f"{get_root_path(request)}/edit/{invoice_id}", status_code=303)

@app.get("/delete/{invoice_id}")
async def delete_invoice(request: Request, invoice_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        # 画像名を取得
        async with conn.execute("SELECT 画像名 FROM invoices WHERE id=?", (invoice_id,)) as cursor:
            row = await cursor.fetchone()
            image_name = row[0] if row else None
        # DBから削除
        await conn.execute("DELETE FROM invoices WHERE id=?", (invoice_id,))
        await conn.execute("DELETE FROM items WHERE invoice_id=?", (invoice_id,))
        await conn.commit()
    # 画像ファイルも削除
    if image_name:
        image_path = os.path.join(IMAGES_DIR, image_name)
        if os.path.exists(image_path):
            os.remove(image_path)
    return RedirectResponse(url=f"{get_root_path(request)}/", status_code=303)

# 集計ページ（/summary）
@app.get("/summary", response_class=HTMLResponse)
async def summary(request: Request, ym: str = None):
    PAGE_TITLE = "集計ページ"
    shop_count = []
    shop_summary = []
    ym_summary = []
    selected_ym = None
    shop_summary_selected = []
    filtered_selected = []
    # DBからデータ取得
    if os.path.exists(DB_PATH):
        async with aiosqlite.connect(DB_PATH) as conn:
            invoice_df = pd.DataFrame()
            async with conn.execute("SELECT * FROM invoices") as cursor:
                rows = await cursor.fetchall()
                columns = [col[0] for col in cursor.description]
                invoice_df = pd.DataFrame(rows, columns=columns)
            # 店名ごとの回数ランキング
            if not invoice_df.empty:
                # 数値カラムを数値型に変換
                numeric_columns = ['品目の合計金額', '小計', '税金', '合計']
                for col in numeric_columns:
                    if col in invoice_df.columns:
                        invoice_df[col] = pd.to_numeric(invoice_df[col], errors='coerce').fillna(0)
                
                shop_count_df = invoice_df['店名'].value_counts().reset_index()
                shop_count_df.columns = ['店名', '回数']
                shop_count_df = shop_count_df.sort_values('回数', ascending=False)
                shop_count = shop_count_df.head(20).to_dict(orient='records')
                # 店名ごとの合計金額
                shop_summary_df = invoice_df.groupby('店名')['合計'].sum().reset_index()
                shop_summary_df = shop_summary_df.sort_values('合計', ascending=False)
                shop_summary = shop_summary_df.head(20).to_dict(orient='records')
                # 年月ごとの合計金額
                invoice_df['年月'] = pd.to_datetime(invoice_df['請求日']).dt.strftime('%y/%m')
                ym_summary_df = invoice_df.groupby('年月')['合計'].sum().reset_index()
                ym_summary_df = ym_summary_df.sort_values('年月')
                ym_summary = ym_summary_df.to_dict(orient='records')
                # 選択年月のデータ（クエリパラメータがあればそれを、なければ最新年月を使用）
                if not ym_summary_df.empty:
                    if ym and ym in ym_summary_df['年月'].values:
                        selected_ym = ym
                    else:
                        selected_ym = ym_summary_df['年月'].iloc[-1]
                    filtered_df = invoice_df[invoice_df['年月'] == selected_ym]
                    if '店名' in filtered_df.columns and '合計' in filtered_df.columns:
                        shop_summary_selected_df = filtered_df.groupby('店名')['合計'].sum().reset_index()
                        shop_summary_selected_df = shop_summary_selected_df.sort_values('合計', ascending=False)
                        shop_summary_selected = shop_summary_selected_df.to_dict(orient='records')
                        filtered_selected = filtered_df.sort_values('合計', ascending=False).to_dict(orient='records')
    return templates.TemplateResponse(
        "summary.html",
        {
            "request": request,
            "page_title": PAGE_TITLE,
            "shop_count": shop_count,
            "shop_summary": shop_summary,
            "ym_summary": ym_summary,
            "selected_ym": selected_ym,
            "shop_summary_selected": shop_summary_selected,
            "filtered_selected": filtered_selected,
            "root_path": get_root_path(request)
        }
    )

TYPES = {
    'subtotal': '小計',
    'tax': '消費税',
    'total': '合計'
}
@app.get('/ask/{ask_type}')
async def ask_ai(request: Request, ask_type: str):
    # フロントエンドからは image_name を送る想定。
    # 互換性のため image_path も許容し、basename を使って画像名を決定する。
    image_name = request.query_params.get('image_name', '')
    image_path = request.query_params.get('image_path', '')
    if not image_name and image_path:
        image_name = os.path.basename(image_path)
    if not image_name:
        return {"error": "image_name が指定されていません"}
    if ask_type not in TYPES:
        return {"error": "不明なタイプです"}
    field_name = TYPES[ask_type]

    ask_text = f"このレシートの画像から、{field_name}を抜き出してください。回答は数字のみで、記号やカンマは含めないでください。"
    # サニタイズして IMAGES_DIR 内のファイルを直接開く
    image_name = os.path.basename(image_name)
    image_file = os.path.join(IMAGES_DIR, image_name)
    if not os.path.exists(image_file):
        return {"error": "画像ファイルが見つかりません"}
    with open(image_file, "rb") as f:
        image_bytes = f.read()
    
    # 3つのモデルを順番に試行
    models = [
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "moonshotai/kimi-k2-instruct-0905"
    ]
    
    completion = None
    last_error = None
    
    for model in models:
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": ask_text},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('ascii')}"}}
                        ]
                    },
                ],
                stream=False,
                stop=None,
            )
            # 成功したらループを抜ける
            break
        except Exception as e:
            last_error = e
            print(f"モデル {model} が失敗しました: {str(e)}")
            continue
    
    # すべてのモデルが失敗した場合
    if completion is None:
        return {"error": f"すべてのモデルが失敗しました。最後のエラー: {str(last_error)}"}
    
    answer = float(completion.choices[0].message.content.strip())
    return {"answer": answer}