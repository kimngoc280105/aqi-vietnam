from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from backend.data_pipeline import clean_observations
from backend.features import CITY_CONFIG, enrich_frame, normalize_city_name


AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_VARIABLES = "pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,european_aqi,us_aqi"
WEATHER_VARIABLES = "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation,surface_pressure,cloud_cover"


@dataclass
class CacheEntry:
    frame: pd.DataFrame
    metadata: dict[str, Any]
    fetched_monotonic: float


class LiveDataProvider:
    def __init__(
        self,
        project_root: Path,
        ttl_seconds: int = 900,
        timeout_seconds: int | None = None,
        max_attempts: int | None = None,
        failure_backoff_seconds: int = 300,
    ) -> None:
        self.project_root = project_root
        self.ttl_seconds = ttl_seconds
        self.timeout_seconds = timeout_seconds or int(os.getenv("LIVE_DATA_TIMEOUT_SECONDS", "12"))
        self.max_attempts = max_attempts or int(os.getenv("LIVE_DATA_MAX_ATTEMPTS", "2"))
        self.failure_backoff_seconds = failure_backoff_seconds
        self._cache: dict[str, CacheEntry] = {}
        self._failures: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()
        self._spatial = self._load_spatial_counts()

    def _load_spatial_counts(self) -> dict[str, dict[str, float]]:
        path = self.project_root / "data" / "raw" / "factory_counts.csv"
        if not path.exists():
            return {city: {} for city in CITY_CONFIG}
        frame = pd.read_csv(path, encoding="utf-8-sig")
        output: dict[str, dict[str, float]] = {city: {} for city in CITY_CONFIG}
        for row in frame.itertuples():
            city = normalize_city_name(row.city)
            feature = f"factories_{int(row.radius_m) // 1000}km"
            output.setdefault(city, {})[feature] = float(row.factory_count)
        return output

    def _request(self, url: str, params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        headers = {"User-Agent": "Vietnam-AQI-Web/2.0 (student research)"}
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                return response.json(), {
                    "url": url,
                    "resolved_url": response.url,
                    "status_code": response.status_code,
                    "retry_count": attempt,
                }
            except Exception as exc:
                last_error = exc
                if attempt < self.max_attempts - 1:
                    time.sleep(1.0 + attempt)
        raise RuntimeError(f"Live source unavailable: {last_error}")

    def _fetch_city(self, city: str) -> CacheEntry:
        config = CITY_CONFIG[city]
        common = {
            "latitude": config["latitude"],
            "longitude": config["longitude"],
            "past_days": 8,
            "forecast_days": 1,
            "timezone": "Asia/Ho_Chi_Minh",
        }
        air_data, air_meta = self._request(
            AIR_URL,
            {
                **common,
                "hourly": AIR_VARIABLES,
                "domains": "cams_global",
                "cell_selection": "nearest",
            },
        )
        weather_data, weather_meta = self._request(
            WEATHER_URL,
            {**common, "hourly": WEATHER_VARIABLES},
        )

        air = air_data["hourly"]
        weather = weather_data["hourly"]
        air_frame = pd.DataFrame(
            {
                "datetime": pd.to_datetime(air["time"]),
                "pm25": air["pm2_5"],
                "pm10": air["pm10"],
                "o3": air["ozone"],
                "no2": air["nitrogen_dioxide"],
                "so2": air["sulphur_dioxide"],
                "co": air["carbon_monoxide"],
                "eu_aqi": air["european_aqi"],
                "aqi": air["us_aqi"],
                "city": city,
            }
        )
        weather_frame = pd.DataFrame(
            {
                "datetime": pd.to_datetime(weather["time"]),
                "temp": weather["temperature_2m"],
                "humidity": weather["relative_humidity_2m"],
                "wind_speed": weather["wind_speed_10m"],
                "wind_dir": weather["wind_direction_10m"],
                "precip": weather["precipitation"],
                "pressure": weather["surface_pressure"],
                "cloud_cover": weather["cloud_cover"],
            }
        )
        merged = air_frame.merge(weather_frame, on="datetime", how="inner", validate="one_to_one")
        for feature, value in self._spatial.get(city, {}).items():
            merged[feature] = value

        current_hour = pd.Timestamp.now(tz="Asia/Ho_Chi_Minh").tz_localize(None).floor("h")
        merged = merged[merged["datetime"] <= current_hour].copy()
        cleaned, cleaning = clean_observations(merged)
        enriched = enrich_frame(cleaned)
        if len(enriched) < 169:
            raise RuntimeError(f"Live source returned only {len(enriched)} usable rows for {city}.")
        metadata = {
            "status": "live",
            "provider": "Open-Meteo / CAMS Global",
            "city": city,
            "representative_point": {
                "latitude": config["latitude"],
                "longitude": config["longitude"],
                "coverage": config["coverage"],
            },
            "latest_observation": enriched["datetime"].max().isoformat(),
            "fetched_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "air_request": air_meta,
            "weather_request": weather_meta,
            "cleaning": cleaning,
        }
        return CacheEntry(enriched, metadata, time.monotonic())

    def get_city(self, city: str, force: bool = False) -> tuple[pd.DataFrame, dict[str, Any]]:
        normalized_city = normalize_city_name(city)
        if normalized_city not in CITY_CONFIG:
            raise ValueError(f"Unsupported city: {city}")
        with self._lock:
            now = time.monotonic()
            cached = self._cache.get(normalized_city)
            if cached and not force and now - cached.fetched_monotonic < self.ttl_seconds:
                metadata = dict(cached.metadata)
                metadata["status"] = "cache_fresh"
                return cached.frame.copy(), metadata
            failure = self._failures.get(normalized_city)
            if failure and not force and now - failure[0] < self.failure_backoff_seconds:
                if cached is not None:
                    metadata = dict(cached.metadata)
                    metadata.update({"status": "cache_stale", "refresh_error": failure[1]})
                    return cached.frame.copy(), metadata
                raise RuntimeError(f"Live source retry backoff: {failure[1]}")
        try:
            entry = self._fetch_city(normalized_city)
        except Exception as exc:
            with self._lock:
                cached = self._cache.get(normalized_city)
                self._failures[normalized_city] = (time.monotonic(), str(exc))
            if cached is None:
                raise
            metadata = dict(cached.metadata)
            metadata.update({"status": "cache_stale", "refresh_error": str(exc)})
            return cached.frame.copy(), metadata
        with self._lock:
            self._cache[normalized_city] = entry
            self._failures.pop(normalized_city, None)
        return entry.frame.copy(), dict(entry.metadata)

    def get_many(
        self,
        cities: list[str] | None = None,
        force: bool = False,
    ) -> dict[str, tuple[pd.DataFrame, dict[str, Any]] | Exception]:
        selected = cities or list(CITY_CONFIG)
        output: dict[str, tuple[pd.DataFrame, dict[str, Any]] | Exception] = {}
        with ThreadPoolExecutor(max_workers=min(3, len(selected))) as executor:
            futures = {executor.submit(self.get_city, city, force): city for city in selected}
            for future in as_completed(futures):
                city = futures[future]
                try:
                    output[city] = future.result()
                except Exception as exc:
                    output[city] = exc
        return output
