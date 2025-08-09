from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum  # 云函数适配器
import requests
import os

# 从环境变量读取 API_KEY（云函数可配置），也可以直接写死
API_KEY = os.getenv("API_KEY", "a911b9ce204a417c93f953c556550a82.ZRj8cH4BQYuE0wQe")
MODEL_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

app = FastAPI()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产建议改成具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
def chat(request: ChatRequest):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "glm-4",
        "messages": [m.dict() for m in request.messages]
    }
    try:
        resp = requests.post(MODEL_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        reply_text = data["choices"][0]["message"]["content"]
        return {"reply": reply_text}

    except requests.exceptions.HTTPError:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 云函数入口
handler = Mangum(app)
