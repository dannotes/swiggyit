FROM python:3.12-slim

LABEL org.opencontainers.image.source=https://github.com/dannotes/swiggyit
LABEL org.opencontainers.image.description="Swiggy order data parser and analytics loader"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY sql/ sql/

ENTRYPOINT ["python3", "src/main.py"]
CMD ["--input", "/data/input", "--tmp", "/data/.tmp"]
