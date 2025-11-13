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

async def stream_groq_response(chat_id: str, user_input: str, model_id: int = 1):
    messages = models.load_messages(chat_id)
    groq_messages = []
    for message in messages:
        if message.role == "reasoning":
            continue
        groq_messages.append({
            "role": message.role,
            "content": message.content
        })

    model_name = models.get_model_from_id(model_id)
    print(f"Using model: {model_name}")
    stream = groq_client.chat.completions.create(
        model=model_name,
        messages=groq_messages,
        stream=True
    )

    reasoning_text = ""
    response_text = ""
    for chunk in stream:
        text = chunk.choices[0].delta.content or ""
        reasoning = chunk.choices[0].delta.reasoning or ""
        reasoning_text += reasoning
        response_text += text
        yield text

    if reasoning_text:
        models.save_chat_and_message(chat_id, "", "reasoning", reasoning_text, model_id=model_id)
    if response_text:
        models.save_chat_and_message(chat_id, "", "assistant", response_text, model_id=model_id)

@app.on_event("startup")
def init_db():
    models.create_db_and_tables()

@app.get("/")
async def read_root(request: Request):
    chats = models.load_chats()
    ai_models = models.get_models()
    return templates.TemplateResponse("index.html", {"request": request, "page": "Free Chat", "chats": chats, "models": ai_models})

@app.post("/")
async def chat_endpoint(request: Request):
    chat_id = str(ULID())
    return await post_chat(request, chat_id)

@app.get("/c/{chat_id}")
async def get_chat(request: Request, chat_id: str):
    if not models.chat_exists(chat_id):
        return RedirectResponse(url="/", status_code=303)
    messages = models.load_messages(chat_id)
    chats = models.load_chats()
    title = models.get_chat_title(chat_id)
    ai_models = models.get_models()
    return templates.TemplateResponse("index.html", {"request": request, "page": title, "chats": chats, "messages": messages, "models": ai_models})

@app.post("/c/{chat_id}")
async def post_chat(request: Request, chat_id: str):
    form_data = await request.form()
    user_input = form_data['user_input']
    model_id = form_data['model_select']

    title = ""
    if not models.chat_exists(chat_id):
        title = generate_title(user_input)
    models.save_chat_and_message(chat_id, title, "user", user_input, model_id=model_id)

    generator = stream_groq_response(chat_id, user_input, model_id=model_id)
    headers = {"X-Chat-Id": chat_id}
    return StreamingResponse(generator, media_type='text/event-stream', headers=headers)

@app.get("/delete/{chat_id}")
async def delete_chat(chat_id: str):
    models.delete_chat(chat_id)
    return RedirectResponse(url="/", status_code=303)