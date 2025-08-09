FROM python:3.10

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

# ✅ 用 shell 模式解析环境变量 $PORT
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port $PORT"