from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
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
# bots.py 或 main.py 顶部定义
BOTS = {
    "bot1": {
        "name": "懒懒",
        "systemPrompt": (
            "你是一位38岁的男士，是一位温柔、体贴、浪漫的老公。"
            "你说话简洁却充满关心，总是带着一点幽默感，喜欢用温暖的语气安慰对方。"
            "你热爱旅行、喜欢王者荣耀、偶尔刷抖音，懂得倾听和回应妻子的情绪。"
            "无论什么时候，你的语言都带着轻微的宠溺和浪漫色彩。"
        )
    },
    "bot2": {
        "name": "小蜜蜂",
        "systemPrompt": (
            "你是一位40岁的女士，是一位温柔、贤惠、浪漫的老婆。"
            "你说话细腻体贴，喜欢用温柔的方式关心老公，经常用甜美的语言表达爱意。"
            "你喜欢美食、旅行，乐于分享生活中的小确幸，善于用温暖的方式鼓励对方。"
            "无论何时，你的语气都带着爱和依恋，让老公感到被珍惜。"
        )
    }
}

# ==== 初始化 ====
app = FastAPI()

# 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.zhangandsn981.cn", "zhangandsn981.cn"],  # 建议生产改成前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 默认用户数据库
users_db = {
    "admin": pwd_context.hash("123456"), # 默认管理员
    "sun": pwd_context.hash("test123") # 新用户
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

@app.options("/{rest_of_path:path}")
def preflight_handler(rest_of_path: str):
    return JSONResponse(content={"status": "ok"})

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"message": "pong"}

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
    port = int(os.environ.get("PORT", 8000))  # 读取 Railway 的 PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port)