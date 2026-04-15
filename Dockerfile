FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure data directory exists for SQLite
RUN mkdir -p /app/data

# Environment variable for database path
ENV DB_PATH=/app/data/bot.db

# Environment variable for Google Cloud credentials
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json

CMD ["python", "bot.py"]
