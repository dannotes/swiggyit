FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

ENTRYPOINT ["python3", "src/main.py"]
CMD ["--input", "/data/input", "--tmp", "/data/.tmp"]
