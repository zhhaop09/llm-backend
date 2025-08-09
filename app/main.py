from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import requests
import uvicorn
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
import os

# ==== 配置 ====
API_KEY = os.getenv("API_KEY", "a911b9ce204a417c93f953c556550a82.ZRj8cH4BQYuE0wQe")
MODEL_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret")
ALGORITHM = "HS256"

# Bot 列表
BOTS = {
    "bot1": {"name": "知识型助手", "systemPrompt": "你是一个严谨的知识问答专家"},
    "bot2": {"name": "幽默聊天伙伴", "systemPrompt": "你是一个幽默有趣的聊天伙伴"}
}

# ==== 初始化 ====
app = FastAPI()

# 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.zhangandsn981.cn/", "zhangandsn981.cn/"],  # 建议生产改成前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 默认用户数据库
users_db = {
    "admin": pwd_context.hash("123456")  # 默认管理员
}

# ==== 工具函数 ====
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)

def create_access_token(data: dict, expires_minutes=60):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username not in users_db:
            raise HTTPException(status_code=401, detail="用户不存在")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="无效Token")

# ==== 数据模型 ====
class User(BaseModel):
    username: str
    password: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    botId: str
    messages: list[ChatMessage]

# ==== 基础路由 ====
@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"message": "pong"}

# ==== 用户系统 ====
@app.post("/register")
def register(user: User):
    if user.username in users_db:
        raise HTTPException(status_code=400, detail="用户已存在")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="禁止注册管理员账号")
    users_db[user.username] = hash_password(user.password)
    return {"message": "注册成功"}

@app.post("/login")
def login(user: User):
    if user.username not in users_db or not verify_password(user.password, users_db[user.username]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

# 方便开发调试：直接获取 admin token
@app.get("/dev/admin-token")
def dev_admin_token():
    return {"access_token": create_access_token({"sub": "admin"}), "token_type": "bearer"}

# ==== Bot 列表 ====
@app.get("/bots")
def get_bots(current_user: str = Depends(get_current_user)):
    return BOTS

# ==== 聊天接口 ====
@app.post("/chat")
def chat(request: ChatRequest, current_user: str = Depends(get_current_user)):
    if request.botId not in BOTS:
        raise HTTPException(status_code=400, detail="无效的Bot ID")

    bot_config = BOTS[request.botId]

    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "glm-4",
            "messages": [
                {"role": "system", "content": bot_config["systemPrompt"]}
            ] + [m.dict() for m in request.messages]
        }
        resp = requests.post(MODEL_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        reply_text = resp.json()["choices"][0]["message"]["content"]
        return {"reply": reply_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模型调用失败: {str(e)}")

# ==== 启动 ====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
