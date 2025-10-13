from groq import Groq
from ulid import ULID
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import models

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

groq_client = Groq()

def sse_event(data: str) -> bytes:
    return f"data: {data}\n\n".encode("utf-8")

def generate_title(user_input: str) -> str:
    if len(user_input) < 20:
        return user_input
    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": "あなたはチャットタイトルを生成するアシスタントです。ユーザーの発言から、20文字以下のタイトルを生成してください。回答はタイトルだけでお願いします。"},
            {"role": "user", "content": user_input}
        ]
    )
    if response.choices:
        return response.choices[0].message.content
    return user_input[:20]

async def stream_groq_response(chat_id: str, user_input: str):
    yield sse_event(f"{{\"event\": \"meta\", \"chat_id\": \"{chat_id}\"}}")
    messages = models.load_messages(chat_id)
    groq_messages = []
    for message in messages:
        groq_messages.append({
            "role": message.role,
            "content": message.content
        })

    stream = groq_client.chat.completions.create(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        messages=groq_messages,
        stream=True
    )

    response_text = ""
    for chunk in stream:
        text = chunk.choices[0].delta.content or ""
        response_text += text
        yield sse_event(text)

    if response_text:
        models.save_chat_and_message(chat_id, "", "assistant", response_text)

@app.on_event("startup")
def init_db():
    models.create_db_and_tables()

@app.get("/")
async def read_root(request: Request):
    chats = models.load_chats()
    return templates.TemplateResponse("index.html", {"request": request, "page": "Free Chat", "chats": chats})

@app.post("/")
async def chat_endpoint(request: Request):
    form_data = await request.form()
    chat_id = str(ULID())
    user_input = form_data['user_input']
    title = generate_title(user_input)
    models.save_chat_and_message(chat_id, title, "user", user_input)

    generator = stream_groq_response(chat_id, user_input)
    return StreamingResponse(generator, media_type='text/event-stream')

@app.get("/c/{chat_id}")
async def get_chat(request: Request, chat_id: str):
    if not models.chat_exists(chat_id):
        return RedirectResponse(url="/", status_code=303)
    messages = models.load_messages(chat_id)
    chats = models.load_chats()
    title = models.get_chat_title(chat_id)
    return templates.TemplateResponse("index.html", {"request": request, "page": title, "chats": chats, "messages": messages})

@app.post("/c/{chat_id}")
async def post_chat(request: Request, chat_id: str):
    form_data = await request.form()
    user_input = form_data['user_input']
    models.save_chat_and_message(chat_id, "", "user", user_input)

    generator = stream_groq_response(chat_id, user_input)
    return StreamingResponse(generator, media_type='text/event-stream')

@app.get("/delete/{chat_id}")
async def delete_chat(chat_id: str):
    models.delete_chat(chat_id)
    return RedirectResponse(url="/", status_code=303)