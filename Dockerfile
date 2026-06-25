FROM python:3.11-slim

# 设置时区为上海
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制程序文件
COPY monitor.py .
COPY config.yaml .

# 创建日志目录
RUN mkdir -p /app/logs

CMD ["python", "-u", "monitor.py"]