FROM node:20-alpine AS frontend-build

WORKDIR /build/frontend
COPY web/frontend/package*.json ./
RUN npm ci
COPY web/frontend/ ./
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY web/requirements-runtime.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY data/processed/pm25_training_data_enriched.csv data/processed/pm25_training_data_enriched.csv
COPY data/raw/crawl_manifest.json data/raw/crawl_manifest.json
COPY model/candidates/xgboost_multihorizon.joblib model/candidates/xgboost_multihorizon.joblib
COPY model/results/multihorizon_model_comparison.csv model/results/multihorizon_model_comparison.csv
COPY model/results/multihorizon_model_comparison_by_horizon.csv model/results/multihorizon_model_comparison_by_horizon.csv
COPY model/results/xgboost_multihorizon_learning_curves.csv model/results/xgboost_multihorizon_learning_curves.csv
COPY model/results/multihorizon_model_selection.json model/results/multihorizon_model_selection.json
COPY model/results/multihorizon_temporal_split.json model/results/multihorizon_temporal_split.json
COPY web/backend web/backend
COPY --from=frontend-build /build/frontend/dist web/frontend/dist

WORKDIR /app/web

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.api:app --host 0.0.0.0 --port ${PORT}"]
