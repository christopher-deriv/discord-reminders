# Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/client
COPY client/package*.json ./
RUN npm ci
COPY client/ ./
# We accept an arg for the Vite env var so it can be passed at build time
ARG VITE_DISCORD_CLIENT_ID
ENV VITE_DISCORD_CLIENT_ID=$VITE_DISCORD_CLIENT_ID
RUN npm run build

# Build backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies if any (none required for basic discord.py)
# RUN apt-get update && apt-get install -y --no-install-recommends ...

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy built frontend assets
COPY --from=frontend-build /app/client/dist /app/client/dist

# Ensure data directory exists for SQLite
RUN mkdir -p /app/data

# Environment variable for database path
ENV DB_PATH=/app/data/bot.db

# Environment variable for Google Cloud credentials
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json

CMD ["python", "bot.py"]
