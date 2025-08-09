# filename: main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import uvicorn  # 添加这一行22

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
    allow_origins=["*"],
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

# ✅ Railway 需要的入口
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # 必须用 PORT 环境变量！
    uvicorn.run("main:app", host="0.0.0.0", port=port)
