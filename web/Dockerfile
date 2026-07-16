FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY web/frontend/package*.json ./
RUN npm ci

COPY web/frontend/index.html ./index.html
COPY web/frontend/vite.config.js ./vite.config.js
COPY web/frontend/src ./src
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY web/requirements-runtime.txt ./web/
RUN pip install --no-cache-dir -r web/requirements-runtime.txt

COPY web/backend ./web/backend
COPY --from=frontend-builder /frontend/dist ./web/frontend/dist
COPY data/raw/crawl_manifest.json ./data/raw/
COPY data/processed/inference_history.csv data/processed/inference_history_metadata.json ./data/processed/
COPY model/pm25_24h_best.joblib model/pm25_24h_best_metadata.json ./model/
COPY model/results ./model/results

RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app

USER appuser

WORKDIR /app/web

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT', '8000') + '/api/health', timeout=4)" || exit 1

CMD ["sh", "-c", "uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
