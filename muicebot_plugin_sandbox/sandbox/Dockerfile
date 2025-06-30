# 第 1 阶段：构建环境
FROM python:3.11-slim AS builder

WORKDIR /tmp

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --wheel-dir=/wheels -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple

# 第 2 阶段：运行环境
FROM python:3.11-slim

LABEL author="MuikaAI" description="Python sandbox for Muicebot"

COPY run_wrapper.py /usr/local/bin/run_wrapper.py
RUN chmod +x /usr/local/bin/run_wrapper.py

WORKDIR /workspace

COPY --from=builder /wheels /wheels
COPY --from=builder /tmp/requirements.txt .

RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt

ENTRYPOINT ["python", "/usr/local/bin/run_wrapper.py"]
