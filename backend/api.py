from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from backend.activity_planner import build_activity_plan
from backend.features import (
    CITY_CONFIG,
    CATEGORICAL_FEATURES,
    ENGINEERED_FEATURES,
    HISTORY_FEATURES,
    POLLUTANT_FEATURES,
    SPATIAL_FEATURES,
    WEATHER_FEATURES,
)
from backend.model_service import (
    AQIModelService,
    DATA_PATH,
    METADATA_PATH,
    MODEL_PATH,
    PROJECT_ROOT,
)


FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
RESULTS_DIR = PROJECT_ROOT / "models" / "results"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CRAWL_MANIFEST_PATH = RAW_DIR / "crawl_manifest.json"
MODEL_CARD_PATH = RESULTS_DIR / "model_card.json"
DATA_QUALITY_PATH = RESULTS_DIR / "data_quality_report.json"
DATA_QUALITY_CITY_PATH = RESULTS_DIR / "data_quality_by_city.csv"
ORIGINAL_SUITE_COMPARISON_PATH = RESULTS_DIR / "original_model_suite_comparison.csv"
ORIGINAL_SUITE_BY_CITY_PATH = RESULTS_DIR / "original_model_suite_by_city.csv"
ORIGINAL_SUITE_SELECTION_PATH = RESULTS_DIR / "original_model_suite_selection.json"

service = AQIModelService()


@asynccontextmanager
async def lifespan(_: FastAPI):
    service.load()
    yield


app = FastAPI(
    title="Vietnam PM2.5 Forecast API",
    description=(
        "Dự báo nồng độ PM2.5 sau 24 giờ cho ba điểm lưới đại diện gần trung tâm "
        "Hà Nội, TP.HCM và Đà Nẵng."
    ),
    version="2.2.0",
    lifespan=lifespan,
)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="assets")


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    city: str = Field(default="Hà Nội")
    observed_at: str | None = None
    profile: dict[str, Any] | None = None
    pm25: float | None = Field(default=None, ge=0)
    pm10: float | None = Field(default=None, ge=0)
    o3: float | None = Field(default=None, ge=0)
    no2: float | None = Field(default=None, ge=0)
    so2: float | None = Field(default=None, ge=0)
    co: float | None = Field(default=None, ge=0)
    temp: float | None = Field(default=None, ge=-10, le=55)
    humidity: float | None = Field(default=None, ge=0, le=100)
    wind_speed: float | None = Field(default=None, ge=0)
    wind_dir: float | None = Field(default=None, ge=0, le=360)
    precip: float | None = Field(default=None, ge=0)
    pressure: float | None = Field(default=None, ge=850, le=1100)
    cloud_cover: float | None = Field(default=None, ge=0, le=100)


class ActivityPlanRequest(BaseModel):
    city: str
    current_pm25: float = Field(ge=0)
    forecast_pm25: float = Field(ge=0)
    forecast_lower: float = Field(ge=0)
    forecast_upper: float = Field(ge=0)
    group: Literal["general", "sensitive"] = "general"
    activity: Literal["light", "moderate", "intense"] = "moderate"
    duration_minutes: int = Field(default=60, ge=15, le=240)


def read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv_records(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    frame = pd.read_csv(path, encoding="utf-8-sig")
    if "Unnamed: 0" in frame.columns:
        frame = frame.rename(columns={"Unnamed: 0": "label"})
    if limit is not None:
        frame = frame.head(limit)
    return frame.where(pd.notna(frame), None).to_dict(orient="records")


def crawl_summary() -> dict[str, Any]:
    manifest = read_json_file(CRAWL_MANIFEST_PATH)
    return {
        "schema_version": manifest.get("schema_version"),
        "run_id": manifest.get("run_id"),
        "created_at": manifest.get("created_at"),
        "start_date": manifest.get("start_date"),
        "end_date": manifest.get("end_date"),
        "coverage_statement": manifest.get("coverage_statement"),
        "sources": manifest.get("sources", {}),
        "cities": manifest.get("cities", {}),
        "all_cities": manifest.get("all_cities", {}),
        "quality": manifest.get("quality", {}),
    }


def data_profile() -> dict[str, Any]:
    quality = read_json_file(DATA_QUALITY_PATH)
    city_rows = read_csv_records(DATA_QUALITY_CITY_PATH)
    city_counts = {str(row["city"]): int(row["rows"]) for row in city_rows if row.get("city")}
    return {
        "rows": quality.get("rows"),
        "columns": quality.get("columns"),
        "cities": quality.get("cities", []),
        "city_counts": city_counts,
        "start_time": quality.get("start_time"),
        "end_time": quality.get("end_time"),
        "supervised_rows_24h": service.metrics.get("supervised_rows"),
        "missing_rate": quality.get("overall_missing_rate"),
        "quality_passed": quality.get("passed"),
        "source_sha256": quality.get("source_sha256"),
        "pollutant_features": [feature for feature in POLLUTANT_FEATURES if feature in service.numeric_features],
        "weather_features": [feature for feature in WEATHER_FEATURES if feature in service.numeric_features],
        "lag_features": [feature for feature in HISTORY_FEATURES if feature in service.numeric_features],
        "spatial_features": [feature for feature in SPATIAL_FEATURES if feature in service.numeric_features],
        "engineered_features": [feature for feature in ENGINEERED_FEATURES if feature in service.numeric_features],
        "source_limitations": quality.get("source_limitations", []),
        "source_summary": [
            "Open-Meteo / CAMS Global: PM2.5, PM10, O3, NO2, SO2, CO và chỉ số tham khảo",
            "Open-Meteo Historical/Forecast Weather: nhiệt độ, độ ẩm, gió, mưa, áp suất và mây",
            "OpenStreetMap / Overpass: ngữ cảnh công nghiệp tĩnh được dùng trong feature set cuối; không phải số liệu phát thải",
        ],
    }


def seasonal_naive_baseline() -> dict[str, Any]:
    rows = read_csv_records(RESULTS_DIR / "model_comparison.csv")
    return next((row for row in rows if row.get("model") == "Seasonal Naive"), {})


def original_model_suite() -> dict[str, Any]:
    selection = read_json_file(ORIGINAL_SUITE_SELECTION_PATH)
    selected_model = str(selection.get("selected_model", ""))
    slug_by_model = {"SARIMAX": "sarimax", "XGBoost": "xgboost", "LSTM": "lstm"}
    selected_slug = slug_by_model.get(selected_model)
    return {
        "protocol": {
            "target": "PM2.5 concentration at exactly t + 24 hours",
            "task": "time-series regression",
            "cities": list(CITY_CONFIG),
            "split": "global chronological 70/15/15 with 24-hour purge gaps",
            "selection_metric": "Validation RMSE",
            "test_used_for_selection": False,
        },
        "selection": selection,
        "comparison": read_csv_records(ORIGINAL_SUITE_COMPARISON_PATH),
        "comparison_by_city": read_csv_records(ORIGINAL_SUITE_BY_CITY_PATH),
        "selected_confusion_matrix": (
            read_csv_records(RESULTS_DIR / f"original_{selected_slug}_confusion_matrix.csv")
            if selected_slug
            else []
        ),
        "selected_classification_report": (
            read_csv_records(RESULTS_DIR / f"original_{selected_slug}_classification_report.csv")
            if selected_slug
            else []
        ),
        "selected_top_error_cases": (
            read_csv_records(RESULTS_DIR / f"original_{selected_slug}_top_error_cases.csv", limit=10)
            if selected_slug
            else []
        ),
        "xgboost_learning_curve": read_csv_records(
            RESULTS_DIR / "xgboost_canonical_learning_curve.csv"
        ),
        "lstm_training_history": read_csv_records(
            RESULTS_DIR / "lstm_canonical_training_history.csv"
        ),
        "sarimax_fit_summary": read_csv_records(
            RESULTS_DIR / "sarimax_canonical_fit_summary.csv"
        ),
    }


def raise_service_error(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    path = FRONTEND_DIST_DIR / "index.html" if FRONTEND_DIST_DIR.exists() else FRONTEND_DIR / "index.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(path)


@app.get("/api/health")
def health() -> dict[str, Any]:
    readiness = service.readiness()
    status = "ok" if readiness["status"] == "ready" and CRAWL_MANIFEST_PATH.exists() else "not_ready"
    return {
        "status": status,
        "api_version": app.version,
        "readiness": readiness,
        "assets": {
            "model": MODEL_PATH.exists(),
            "metadata": METADATA_PATH.exists(),
            "data": DATA_PATH.exists(),
            "crawl_manifest": CRAWL_MANIFEST_PATH.exists(),
            "frontend": (FRONTEND_DIST_DIR / "index.html").exists(),
        },
    }


@app.get("/api/model")
def model_info() -> dict[str, Any]:
    service.load()
    assert service.artifact is not None
    artifact = service.artifact
    return {
        "name": artifact.get("model_name", service.metrics.get("model")),
        "version": artifact.get("model_version"),
        "artifact": str(MODEL_PATH.relative_to(PROJECT_ROOT)),
        "target": artifact.get("target"),
        "model_details": artifact.get("model_details"),
        "metrics": service.metrics,
        "interval": artifact.get("interval"),
        "risk_standard": artifact.get("risk_standard"),
        "selection": artifact.get("selection"),
        "split": artifact.get("split"),
        "data_profile": data_profile(),
        "crawl_manifest": crawl_summary(),
        "comparison": read_csv_records(ORIGINAL_SUITE_COMPARISON_PATH),
        "comparison_by_city": read_csv_records(ORIGINAL_SUITE_BY_CITY_PATH),
        "baseline": seasonal_naive_baseline(),
        "required_model_suite": original_model_suite(),
        "feature_ablation": read_csv_records(RESULTS_DIR / "feature_ablation.csv"),
        "feature_importance": read_csv_records(RESULTS_DIR / "best_model_feature_importance.csv", limit=20),
        "learning_curve": read_csv_records(RESULTS_DIR / "best_model_learning_curve.csv"),
        "confusion_matrix": read_csv_records(RESULTS_DIR / "best_model_confusion_matrix.csv"),
        "classification_report": read_csv_records(RESULTS_DIR / "best_model_classification_report.csv"),
        "top_error_cases": read_csv_records(RESULTS_DIR / "best_model_top_error_cases.csv", limit=10),
        "bootstrap_ci": read_csv_records(RESULTS_DIR / "best_model_bootstrap_ci.csv"),
        "interval_coverage_by_city": read_csv_records(RESULTS_DIR / "prediction_interval_coverage_by_city.csv"),
        "cities": list(service.latest_profiles),
    }


@app.get("/api/model-card")
def model_card() -> dict[str, Any]:
    card = read_json_file(MODEL_CARD_PATH)
    if not card:
        raise HTTPException(status_code=404, detail="Model card not found")
    return card


@app.get("/api/cities")
def cities(refresh: bool = Query(default=False)) -> list[dict[str, Any]]:
    try:
        return service.cities(force_refresh=refresh)
    except Exception as exc:
        raise_service_error(exc)


@app.get("/api/history/{city}")
def history(
    city: str,
    limit: int = Query(default=168, ge=24, le=720),
    refresh: bool = Query(default=False),
) -> list[dict[str, Any]]:
    try:
        return service.history(city, limit=limit, force_refresh=refresh)
    except Exception as exc:
        raise_service_error(exc)


@app.post("/api/predict")
def predict(payload: PredictionRequest) -> dict[str, Any]:
    try:
        return service.predict(payload.model_dump(exclude_none=True))
    except Exception as exc:
        raise_service_error(exc)


@app.post("/api/explain")
def explain(
    payload: PredictionRequest,
    top_n: int = Query(default=10, ge=3, le=15),
) -> dict[str, Any]:
    try:
        return service.explain(payload.model_dump(exclude_none=True), top_n=top_n)
    except Exception as exc:
        raise_service_error(exc)


@app.get("/api/backtest/{city}")
def backtest(
    city: str,
    limit: int = Query(default=7, ge=3, le=14),
) -> dict[str, Any]:
    try:
        return service.backtest(city, limit=limit)
    except Exception as exc:
        raise_service_error(exc)


@app.post("/api/scenarios")
def scenarios(payload: PredictionRequest) -> list[dict[str, Any]]:
    try:
        return service.scenarios(payload.model_dump(exclude_none=True))
    except Exception as exc:
        raise_service_error(exc)


@app.post("/api/activity-plan")
def activity_plan(payload: ActivityPlanRequest) -> dict[str, Any]:
    try:
        return build_activity_plan(**payload.model_dump())
    except Exception as exc:
        raise_service_error(exc)
