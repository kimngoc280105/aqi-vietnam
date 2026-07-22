from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from backend.activity_planner import build_activity_plan
from backend.model_service import DATA_PATH, MODEL_PATH, MultiHorizonModelService


WEB_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = WEB_ROOT / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"

service = MultiHorizonModelService()


@asynccontextmanager
async def lifespan(_: FastAPI):
    service.load()
    yield


app = FastAPI(
    title="Vietnam PM2.5 Multi-Horizon Forecast API",
    description="Dự báo PM2.5 theo từng giờ từ t+1 đến t+24 cho Hà Nội, TP.HCM và Đà Nẵng.",
    version="3.0.0",
    lifespan=lifespan,
)

cors_origins = [
    value.strip()
    for value in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8001,http://127.0.0.1:8001",
    ).split(",")
    if value.strip()
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


class ForecastRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    city: str = "Hà Nội"
    horizon: int = Field(default=24, ge=1, le=24)
    observed_at: str | None = None
    profile: dict[str, Any] | None = None
    pm25: float | None = Field(default=None, ge=0, le=500)
    pm10: float | None = Field(default=None, ge=0, le=800)
    o3: float | None = Field(default=None, ge=0, le=500)
    no2: float | None = Field(default=None, ge=0, le=500)
    so2: float | None = Field(default=None, ge=0, le=500)
    co: float | None = Field(default=None, ge=0, le=50000)
    temp: float | None = Field(default=None, ge=-10, le=55)
    humidity: float | None = Field(default=None, ge=0, le=100)
    wind_speed: float | None = Field(default=None, ge=0, le=150)
    wind_dir: float | None = Field(default=None, ge=0, le=360)
    precip: float | None = Field(default=None, ge=0)
    pressure: float | None = Field(default=None, ge=850, le=1100)
    cloud_cover: float | None = Field(default=None, ge=0, le=100)


class ActivityPlanRequest(BaseModel):
    city: str
    horizon_hours: int = Field(default=24, ge=1, le=24)
    current_pm25: float = Field(ge=0)
    forecast_pm25: float = Field(ge=0)
    forecast_lower: float = Field(ge=0)
    forecast_upper: float = Field(ge=0)
    group: Literal["general", "sensitive"] = "general"
    activity: Literal["light", "moderate", "intense"] = "moderate"
    duration_minutes: int = Field(default=60, ge=15, le=240)


def raise_service_error(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    path = FRONTEND_DIST_DIR / "index.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Frontend chưa được build")
    return FileResponse(path)


@app.get("/api/health")
def health() -> dict[str, Any]:
    readiness = service.readiness()
    return {
        "status": "ok" if readiness.get("status") == "ready" else "not_ready",
        "api_version": app.version,
        "readiness": readiness,
        "assets": {
            "model": MODEL_PATH.exists(),
            "data": DATA_PATH.exists(),
            "frontend": (FRONTEND_DIST_DIR / "index.html").exists(),
        },
    }


@app.get("/api/cities")
def cities(refresh: bool = Query(default=False)) -> list[dict[str, Any]]:
    try:
        return service.cities(force_refresh=refresh)
    except Exception as exc:
        raise_service_error(exc)


@app.get("/api/history/{city}")
def history(
    city: str,
    limit: int = Query(default=72, ge=24, le=336),
    refresh: bool = Query(default=False),
) -> list[dict[str, Any]]:
    try:
        return service.history(city, limit=limit, force_refresh=refresh)
    except Exception as exc:
        raise_service_error(exc)


@app.post("/api/forecast")
def forecast(payload: ForecastRequest) -> dict[str, Any]:
    try:
        return service.forecast(payload.model_dump(exclude_none=True))
    except Exception as exc:
        raise_service_error(exc)


@app.post("/api/predict")
def predict(payload: ForecastRequest) -> dict[str, Any]:
    try:
        values = payload.model_dump(exclude_none=True)
        horizon = int(values.pop("horizon", 24))
        return service.predict(values, horizon=horizon)
    except Exception as exc:
        raise_service_error(exc)


@app.post("/api/activity-plan")
def activity_plan(payload: ActivityPlanRequest) -> dict[str, Any]:
    try:
        return build_activity_plan(**payload.model_dump())
    except Exception as exc:
        raise_service_error(exc)


@app.get("/api/model")
def model_info() -> dict[str, Any]:
    try:
        return service.model_info()
    except Exception as exc:
        raise_service_error(exc)


@app.get("/{path:path}", include_in_schema=False)
def frontend_fallback(path: str) -> FileResponse:
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint không tồn tại")
    index_path = FRONTEND_DIST_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend chưa được build")
    return FileResponse(index_path)
