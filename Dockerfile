FROM python:3.11-slim
WORKDIR /app
# 安装构建所需的系统依赖（如需额外依赖可扩展）
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 确保 gunicorn 可用
RUN pip install --no-cache-dir gunicorn
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 5000
# 生产使用 gunicorn 启动，app.py 中定义了顶层 app
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "2"]
