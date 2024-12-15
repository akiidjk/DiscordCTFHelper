FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

RUN useradd -m -s /bin/bash botuser && \
    chown -R botuser:botuser /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

VOLUME ["/app/database"]

RUN chown -R botuser:botuser /app/database

USER botuser

CMD ["python3", "bot.py", "INFO"]
