FROM python:3.12-slim

WORKDIR /app

COPY requirements-train.txt .

RUN pip install --no-cache-dir -r requirements-train.txt

COPY main-train.py .

CMD ["python", "main-train.py"]
