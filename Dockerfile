FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 创建目录结构
COPY app.py .
COPY templates ./templates
COPY static ./static

# 创建数据目录
RUN mkdir -p /app/data

EXPOSE 5000

# 使用gunicorn运行应用
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]