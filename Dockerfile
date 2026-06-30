FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV JARVIS_APP_MODE=1
ENV NEURALPAL_BIND=0.0.0.0
ENV NEURALPAL_BACKEND_PORT=8766

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /frontend/dist ./dist

EXPOSE 8766
CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8766"]
