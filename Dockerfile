# Multi-stage: önce frontend, sonra backend + frontend build'i
FROM node:20-alpine AS frontend-builder
WORKDIR /build
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

# Sistem bağımlılıkları (psycopg2 ve bcrypt için)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY apps/api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend kodu
COPY apps/api/ ./

# Frontend build çıktısını static klasörüne kopyala
COPY --from=frontend-builder /build/dist ./static

# Railway PORT env variable kullanır
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
