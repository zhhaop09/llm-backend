from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import uvicorn

API_KEY = "a911b9ce204a417c93f953c556550a82.ZRj8cH4BQYuE0wQe"
MODEL_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 放开所有跨域以调试
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"message": "pong"}

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "glm-4",
            "messages": [m.dict() for m in request.messages]
        }
        resp = requests.post(MODEL_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        reply_text = resp.json()["choices"][0]["message"]["content"]
        return {"reply": reply_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = 8000
    uvicorn.run("main:app", host="0.0.0.0", port=port)