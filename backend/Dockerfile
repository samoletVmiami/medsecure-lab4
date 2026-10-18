FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir email-validator "bcrypt<4.1.0"

COPY . .

CMD sh -c "python -m app.init_db && uvicorn app.main:app --host 0.0.0.0 --port 8000"