# Stage 1: build frontend assets
FROM node:20 AS frontend-builder
WORKDIR /app

COPY package.json package-lock.json ./
COPY client ./client
COPY shared ./shared

RUN npm install --legacy-peer-deps
RUN npm run client:build

# Stage 2: produce final runtime image
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-builder /app/client/dist ./client/dist

EXPOSE 8080

ENV PORT=8080
ENV PYTHONPATH=/app

CMD ["python", "main.py"]