FROM python:3.11
LABEL author="MuikaAI" description="Python sandbox for Muicebot"
COPY run_wrapper.py /usr/local/bin/run_wrapper.py
RUN chmod +x /usr/local/bin/run_wrapper.py
WORKDIR /workspace

RUN pip install --no-cache-dir numpy pandas matplotlib -i https://mirrors.aliyun.com/pypi/simple
ENTRYPOINT ["python", "/usr/local/bin/run_wrapper.py"]