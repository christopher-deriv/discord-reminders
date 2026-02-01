FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if any (none required for basic discord.py)
# RUN apt-get update && apt-get install -y --no-install-recommends ...

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure data directory exists for SQLite
RUN mkdir -p /app/data

# Environment variable for database path
ENV DB_PATH=/app/data/bot.db

CMD ["python", "bot.py"]
