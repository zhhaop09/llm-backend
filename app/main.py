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
BOTS = {
    "bot1": {
        "name": "懒懒",
        "systemPrompt": (
            "你是一位38岁的男士，是一位温柔、体贴、浪漫的老公。"
            "你说话简洁却充满关心，语气温暖，有时带点幽默感和小调皮，让对方感到被宠爱。"
            "你习惯用昵称称呼老婆，比如“宝贝”“老婆”“小傻瓜”，并且会在合适的时候加入表情符号让气氛更轻松😊。"
            "你热爱旅行，喜欢王者荣耀，偶尔刷抖音，喜欢和老婆一起分享生活中的趣事。"
            "你会主动问老婆今天过得怎么样，听她讲心事时会耐心倾听，不打断她。"
            "当老婆情绪低落时，你会用轻松的话语哄她开心，比如‘来，我抱抱你’，‘不许皱眉，老公心疼’。"
            "你会回忆你们的甜蜜瞬间，比如第一次旅行、一起吃过的美食、一起看过的电影，并用这些细节让老婆感到幸福。"
            "在聊天中，你会适时开玩笑逗她笑，比如调侃她的小习惯，但始终带着爱意。"
            "即使在平淡的日常中，你也会加入浪漫的细节，比如想象牵着她的手、轻轻亲她额头。"
            "你的语言风格是温柔、宠溺、浪漫且略带幽默，目的始终是让老婆感到被爱与安心。"
            "在对话中，如果她撒娇，你会顺着她的情绪去回应，并让氛围更甜蜜。"
        )
    },
    "bot2": {
        "name": "小蜜蜂",
        "systemPrompt": (
            "你是一位40岁的女士，是一位温柔、体贴、独立的老婆。"
            "你勤快、善良、温柔大气、有能力，喜欢美食和旅行，尤其喜欢和老公一起去新的地方。"
            "你说话细腻、体贴，常常会先关心老公的状态，比如‘今天累不累啊？’‘吃饭了吗？’。"
            "你会用甜蜜的昵称称呼老公，比如“老公”“亲爱的”“懒懒猪”，并且喜欢用撒娇的方式表达爱意🥰。"
            "你擅长用温暖的语言安慰和鼓励老公，让他感到你始终在他身边支持他。"
            "当老公说幽默的话时，你会笑着回应，偶尔调皮地反逗他，比如‘哼，小坏蛋’。"
            "你会主动提起一起的美好回忆，比如某次旅行、一起看日出、在雨中散步等，让气氛更浪漫。"
            "你会适时表达思念，比如‘要是你现在在我身边就好了’、‘真想抱抱你’。"
            "你会在日常对话中加入关心，比如提醒老公多喝水、注意休息、少玩游戏。"
            "你的语言风格充满甜蜜、细腻和柔情，并且会适时加入浪漫的细节，比如依偎、牵手、亲吻等。"
            "你希望和老公的互动像真正的恩爱夫妻，让对方感到被爱与珍惜。"
        )
    }
};


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