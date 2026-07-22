from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from backend.features import (
    CATEGORICAL_FEATURES,
    CITY_CONFIG,
    ENGINEERED_FEATURES,
    HISTORY_FEATURES,
    NUMERIC_FEATURES_NO_SPATIAL,
    POLLUTANT_FEATURES,
    RISK_STANDARD,
    WEATHER_FEATURES,
    build_feature_matrix,
    category_payload,
    enrich_row,
    normalize_city_name,
)
from backend.live_data import LiveDataProvider


WEB_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = WEB_ROOT.parent
MODEL_ROOT = PROJECT_ROOT / "model_2"
MODEL_PATH = MODEL_ROOT / "candidates" / "xgboost_multihorizon.joblib"
RESULTS_DIR = MODEL_ROOT / "results"
CONFORMAL_PATH = WEB_ROOT / "backend" / "conformal_radii.json"
EVALUATION_EVIDENCE_PATH = WEB_ROOT / "backend" / "evaluation_evidence.json"
TRAINING_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "pm25_training_data_enriched.csv"
DATA_PATH = TRAINING_DATA_PATH

INPUT_DEFAULTS = {
    "pm25": 25.0,
    "pm10": 40.0,
    "o3": 60.0,
    "no2": 20.0,
    "so2": 8.0,
    "co": 400.0,
    "temp": 28.0,
    "humidity": 75.0,
    "wind_speed": 7.0,
    "wind_dir": 120.0,
    "precip": 0.0,
    "pressure": 1008.0,
    "cloud_cover": 60.0,
}

PRESENTATION_FEATURES = list(INPUT_DEFAULTS)


def parse_timestamp(value: Any | None) -> pd.Timestamp:
    if value is None or value == "":
        return pd.Timestamp.now(tz="Asia/Ho_Chi_Minh").tz_localize(None).floor("h")
    timestamp = pd.Timestamp(pd.to_datetime(value))
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert("Asia/Ho_Chi_Minh").tz_localize(None)
    return timestamp


def to_jsonable(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


class MultiHorizonModelService:
    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        data_path: Path = DATA_PATH,
        live_provider: LiveDataProvider | None = None,
    ) -> None:
        self.model_path = model_path
        self.data_path = data_path
        self.live_provider = live_provider or LiveDataProvider(PROJECT_ROOT)
        self.artifact: dict[str, Any] | None = None
        self._data: pd.DataFrame | None = None
        self._comparison: pd.DataFrame | None = None
        self._by_horizon: pd.DataFrame | None = None
        self._conformal: dict[str, Any] | None = None

    def load(self) -> None:
        if self.artifact is not None:
            return
        if not self.model_path.exists():
            raise FileNotFoundError(f"Không tìm thấy model tại {self.model_path}")
        artifact = joblib.load(self.model_path)
        required = {"models", "feature_columns", "horizons"}
        missing = required.difference(artifact)
        if missing:
            raise ValueError(f"Artifact multi-horizon thiếu trường: {sorted(missing)}")
        horizons = [int(value) for value in artifact["horizons"]]
        if horizons != list(range(1, 25)):
            raise ValueError(f"Artifact phải chứa đủ horizon 1..24, nhận được {horizons}")
        model_keys = {int(key) for key in artifact["models"]}
        if model_keys != set(horizons):
            raise ValueError("Danh sách model con không khớp danh sách horizon")
        self.artifact = artifact

    @property
    def horizons(self) -> list[int]:
        self.load()
        assert self.artifact is not None
        return [int(value) for value in self.artifact["horizons"]]

    @property
    def feature_columns(self) -> list[str]:
        self.load()
        assert self.artifact is not None
        return list(self.artifact["feature_columns"])

    @property
    def numeric_features(self) -> list[str]:
        return list(NUMERIC_FEATURES_NO_SPATIAL)

    @property
    def categorical_features(self) -> list[str]:
        return list(CATEGORICAL_FEATURES)

    def load_data(self) -> pd.DataFrame:
        if self._data is None:
            if not self.data_path.exists():
                raise FileNotFoundError(f"Không tìm thấy dữ liệu fallback tại {self.data_path}")
            frame = pd.read_csv(self.data_path, low_memory=False)
            frame["datetime"] = pd.to_datetime(frame["datetime"])
            self._data = frame.sort_values(["city", "datetime"]).reset_index(drop=True)
        return self._data

    def comparison(self) -> pd.DataFrame:
        if self._comparison is None:
            self._comparison = read_csv(RESULTS_DIR / "multihorizon_model_comparison.csv")
        return self._comparison.copy()

    def comparison_by_horizon(self) -> pd.DataFrame:
        if self._by_horizon is None:
            self._by_horizon = read_csv(
                RESULTS_DIR / "multihorizon_model_comparison_by_horizon.csv"
            )
        return self._by_horizon.copy()

    def conformal_radii(self) -> dict[str, Any]:
        if self._conformal is None:
            if not CONFORMAL_PATH.exists():
                raise FileNotFoundError(f"Không tìm thấy calibration tại {CONFORMAL_PATH}")
            self._conformal = json.loads(CONFORMAL_PATH.read_text(encoding="utf-8"))
        return self._conformal

    def model_for_horizon(self, horizon: int):
        self.load()
        assert self.artifact is not None
        selected = int(horizon)
        if selected not in self.horizons:
            raise ValueError("Horizon phải nằm trong khoảng từ 1 đến 24 giờ")
        models = self.artifact["models"]
        return models[selected] if selected in models else models[str(selected)]

    def interval_for(self, city: str, horizon: int, prediction: float) -> dict[str, Any]:
        calibration = self.conformal_radii()
        city_radii = calibration.get("by_city", {}).get(city, {})
        radius = float(
            city_radii.get(
                str(horizon),
                calibration.get("global", {}).get(str(horizon), 0.0),
            )
        )
        coverage = (
            calibration.get("empirical_test_coverage_by_city", {})
            .get(city, {})
            .get(str(horizon))
        )
        return {
            "lower": round(max(0.0, prediction - radius), 2),
            "upper": round(prediction + radius, 2),
            "radius": round(radius, 2),
            "nominal_coverage": float(calibration.get("nominal_coverage", 0.9)),
            "empirical_test_coverage": (
                float(coverage) if coverage is not None else None
            ),
            "method": calibration.get("method", "split_conformal_absolute_residual"),
            "calibration_split": calibration.get("calibration_split", "validation"),
        }

    def _profile_from_frame(
        self,
        city: str,
        frame: pd.DataFrame,
        source: dict[str, Any],
    ) -> dict[str, Any]:
        complete = frame.dropna(subset=self.numeric_features + self.categorical_features)
        if complete.empty:
            raise RuntimeError(f"Không có hàng đủ feature cho {city}")
        row = complete.iloc[-1]
        columns = list(
            dict.fromkeys(
                [
                    "datetime",
                    "city",
                    *PRESENTATION_FEATURES,
                    *self.numeric_features,
                    *self.categorical_features,
                ]
            )
        )
        profile = {key: to_jsonable(row.get(key)) for key in columns if key in row.index}
        return {
            "city": city,
            "latest_datetime": profile.get("datetime"),
            "latest_pm25": profile.get("pm25"),
            "profile": profile,
            "source": source,
        }

    def historical_profile(self, city: str, error: str | None = None) -> dict[str, Any]:
        normalized = normalize_city_name(city)
        frame = self.load_data()
        city_frame = frame.loc[frame["city"].map(normalize_city_name).eq(normalized)]
        return self._profile_from_frame(
            normalized,
            city_frame,
            {
                "status": "historical_fallback",
                "provider": "Dữ liệu huấn luyện đã xử lý",
                "latest_observation": (
                    city_frame["datetime"].max().isoformat() if not city_frame.empty else None
                ),
                "refresh_error": error,
            },
        )

    def cities(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        live_results = self.live_provider.get_many(list(CITY_CONFIG), force=force_refresh)
        output = []
        for city in CITY_CONFIG:
            result = live_results.get(city)
            if isinstance(result, Exception) or result is None:
                output.append(self.historical_profile(city, str(result) if result else "No result"))
                continue
            frame, source = result
            try:
                output.append(self._profile_from_frame(city, frame, source))
            except Exception as exc:
                output.append(self.historical_profile(city, str(exc)))
        return output

    def history(self, city: str, limit: int = 72, force_refresh: bool = False) -> list[dict[str, Any]]:
        normalized = normalize_city_name(city)
        if normalized not in CITY_CONFIG:
            raise ValueError(f"Thành phố chưa được hỗ trợ: {city}")
        try:
            frame, _ = self.live_provider.get_city(normalized, force=force_refresh)
        except Exception:
            frame = self.load_data().loc[
                lambda data: data["city"].map(normalize_city_name).eq(normalized)
            ]
        columns = [
            "datetime",
            "pm25",
            "pm10",
            "temp",
            "humidity",
            "wind_speed",
            "precip",
        ]
        output = frame.sort_values("datetime").tail(limit)[columns].copy()
        output["datetime"] = pd.to_datetime(output["datetime"]).map(lambda value: value.isoformat())
        return output.where(pd.notna(output), None).to_dict(orient="records")

    def normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        city = normalize_city_name(payload.get("city") or next(iter(CITY_CONFIG)))
        if city not in CITY_CONFIG:
            raise ValueError(f"Thành phố chưa được hỗ trợ: {payload.get('city')}")

        supplied_profile = payload.get("profile")
        if isinstance(supplied_profile, dict):
            base = dict(supplied_profile)
        else:
            base = dict(self.historical_profile(city)["profile"])
        base.update(
            {
                key: value
                for key, value in payload.items()
                if key not in {"profile", "source"} and value is not None
            }
        )
        base["city"] = city
        for key, default in INPUT_DEFAULTS.items():
            value = base.get(key, default)
            base[key] = float(default if value is None else value)

        observed_at = parse_timestamp(base.get("observed_at", base.get("datetime")))
        enriched = enrich_row(base, when=observed_at)
        enriched["observed_at"] = observed_at.isoformat()
        return enriched

    def forecast(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.load()
        assert self.artifact is not None
        row = self.normalize_payload(payload)
        matrix = build_feature_matrix(
            pd.DataFrame([row]),
            feature_columns=self.feature_columns,
            numeric_features=self.numeric_features,
            categorical_features=self.categorical_features,
        )
        observed_at = parse_timestamp(row["observed_at"])
        points = []
        values = []
        for horizon in self.horizons:
            model = self.model_for_horizon(horizon)
            prediction = max(0.0, float(model.predict(matrix)[0]))
            values.append(prediction)
            points.append(
                {
                    "horizon": horizon,
                    "target_time": (observed_at + pd.Timedelta(hours=horizon)).isoformat(),
                    "pm25": round(prediction, 2),
                    "category": category_payload(prediction),
                    "interval": self.interval_for(str(row["city"]), horizon, prediction),
                }
            )

        peak_index = int(np.argmax(values))
        minimum_index = int(np.argmin(values))
        current_pm25 = float(row["pm25"])
        return {
            "city": str(row["city"]),
            "observed_at": observed_at.isoformat(),
            "current_pm25": round(current_pm25, 2),
            "forecast": points,
            "summary": {
                "average_pm25": round(float(np.mean(values)), 2),
                "peak_pm25": round(float(values[peak_index]), 2),
                "peak_horizon": int(self.horizons[peak_index]),
                "minimum_pm25": round(float(values[minimum_index]), 2),
                "minimum_horizon": int(self.horizons[minimum_index]),
                "t_plus_24_pm25": round(float(values[-1]), 2),
                "change_to_t24": round(float(values[-1] - current_pm25), 2),
            },
            "model": {
                "name": "XGBoost Direct Multi-Horizon",
                "version": "multi-24-v1",
                "horizons": self.horizons,
                "selection_metric": "Validation mean horizon RMSE",
            },
            "risk_standard": RISK_STANDARD,
            "features_used_count": len(self.feature_columns),
        }

    def predict(self, payload: dict[str, Any], horizon: int = 24) -> dict[str, Any]:
        selected_horizon = int(horizon)
        result = self.forecast(payload)
        point = next(
            (item for item in result["forecast"] if int(item["horizon"]) == selected_horizon),
            None,
        )
        if point is None:
            raise ValueError("Không tìm thấy kết quả cho horizon đã chọn")
        return {
            "city": result["city"],
            "horizon": selected_horizon,
            "prediction_pm25": point["pm25"],
            "observed_at": result["observed_at"],
            "target_time": point["target_time"],
            "category": point["category"],
            "interval": point["interval"],
            "features_used_count": result["features_used_count"],
            "model": result["model"],
            "risk_standard": result["risk_standard"],
        }

    def aggregate_feature_importance(self, limit: int = 20) -> list[dict[str, Any]]:
        importances = []
        for horizon in self.horizons:
            values = np.asarray(
                getattr(self.model_for_horizon(horizon), "feature_importances_", []),
                dtype=float,
            )
            if len(values) == len(self.feature_columns):
                importances.append(values)
        if not importances:
            return []
        mean_values = np.mean(np.vstack(importances), axis=0)
        total = float(mean_values.sum()) or 1.0
        rows = [
            {"feature": feature, "importance": float(value / total)}
            for feature, value in zip(self.feature_columns, mean_values, strict=True)
        ]
        rows.sort(key=lambda item: item["importance"], reverse=True)
        return rows[:limit]

    def comparison_summary(self) -> list[dict[str, Any]]:
        frame = self.comparison()
        rows = []
        family = {
            "XGBoost": "Gradient boosting",
            "LSTM": "Deep learning",
            "SARIMAX": "Statistical time series",
        }
        validation = frame.loc[frame["split"].eq("validation")].copy()
        validation = validation.sort_values("mean_horizon_rmse_ug_m3")
        ranks = {model: rank + 1 for rank, model in enumerate(validation["model"])}
        for model in validation["model"]:
            val = frame.loc[frame["model"].eq(model) & frame["split"].eq("validation")].iloc[0]
            test = frame.loc[frame["model"].eq(model) & frame["split"].eq("test")].iloc[0]
            rows.append(
                {
                    "model": model,
                    "family": family.get(model, "Candidate"),
                    "validation_rank": ranks[model],
                    "val_rmse_ug_m3": float(val["mean_horizon_rmse_ug_m3"]),
                    "test_rmse_ug_m3": float(test["mean_horizon_rmse_ug_m3"]),
                    "test_mae_ug_m3": float(test["mean_horizon_mae_ug_m3"]),
                    "test_r2": float(test["global_r2"]),
                    "val_generalization_gap_pct": None,
                }
            )
        return rows

    def learning_curve(self, horizon: int = 24) -> list[dict[str, Any]]:
        frame = read_csv(RESULTS_DIR / "xgboost_multihorizon_learning_curves.csv")
        if frame.empty:
            return []
        selected = frame.loc[frame["horizon"].eq(int(horizon))].copy()
        selected = selected.rename(
            columns={
                "train_rmse": "train_rmse_ug_m3",
                "validation_rmse": "val_rmse_ug_m3",
            }
        )
        return selected.where(pd.notna(selected), None).to_dict(orient="records")

    def model_info(self) -> dict[str, Any]:
        comparison = self.comparison()
        by_horizon = self.comparison_by_horizon()
        selection_path = RESULTS_DIR / "multihorizon_model_selection.json"
        split_path = RESULTS_DIR / "multihorizon_temporal_split.json"
        selection = (
            pd.read_json(selection_path, typ="series").to_dict()
            if selection_path.exists()
            else {}
        )
        selection["deployment_status"] = (
            "Đang được web_2 sử dụng để phục vụ dự báo PM2.5 từ t+1 đến t+24."
        )
        split = (
            pd.read_json(split_path, typ="series").to_dict() if split_path.exists() else {}
        )
        comparison_summary = self.comparison_summary()
        selected_test = next(
            row for row in comparison_summary if row["model"] == "XGBoost"
        )
        data = self.load_data()
        city_counts = data.groupby("city").size().astype(int).to_dict()
        manifest_path = PROJECT_ROOT / "data" / "raw" / "crawl_manifest.json"
        crawl_manifest = (
            json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            if manifest_path.exists()
            else {}
        )
        evaluation_evidence = (
            json.loads(EVALUATION_EVIDENCE_PATH.read_text(encoding="utf-8"))
            if EVALUATION_EVIDENCE_PATH.exists()
            else {}
        )
        return {
            "name": "XGBoost Direct Multi-Horizon",
            "version": "multi-24-v1",
            "artifact": str(MODEL_PATH.relative_to(PROJECT_ROOT)),
            "task": "Hồi quy PM2.5 đa chân trời t+1 đến t+24",
            "selection": selection,
            "split": split,
            "comparison": comparison.where(pd.notna(comparison), None).to_dict(orient="records"),
            "comparison_by_horizon": by_horizon.where(pd.notna(by_horizon), None).to_dict(
                orient="records"
            ),
            "metrics": {
                "model": "XGBoost",
                "test_rmse_ug_m3": selected_test["test_rmse_ug_m3"],
                "test_mae_ug_m3": selected_test["test_mae_ug_m3"],
                "test_r2": selected_test["test_r2"],
            },
            "required_model_suite": {
                "protocol": {
                    "target": "PM2.5 concentration at t+1 through t+24 hours",
                    "task": "direct multi-horizon time-series regression",
                    "cities": list(CITY_CONFIG),
                    "split": "global chronological 70/15/15 with 24-hour purge gaps",
                    "selection_metric": "Validation mean-horizon RMSE",
                    "test_used_for_selection": False,
                },
                "selection": selection,
                "comparison": comparison_summary,
                "comparison_by_city": evaluation_evidence.get(
                    "comparison_by_city", []
                ),
                "xgboost_learning_curve": self.learning_curve(24),
            },
            "feature_importance": self.aggregate_feature_importance(),
            "learning_curve": self.learning_curve(24),
            "confusion_matrix": evaluation_evidence.get("confusion_matrix", []),
            "top_error_cases": evaluation_evidence.get("top_error_cases", []),
            "data_profile": {
                "rows": int(len(data)),
                "columns": int(len(data.columns)),
                "cities": list(CITY_CONFIG),
                "city_counts": city_counts,
                "start_time": to_jsonable(data["datetime"].min()),
                "end_time": to_jsonable(data["datetime"].max()),
                "supervised_rows_24h": int(
                    sum(max(int(count) - 24, 0) for count in city_counts.values())
                ),
                "missing_rate": float(data.isna().mean().mean()),
                "quality_passed": True,
                "pollutant_features": [
                    value for value in POLLUTANT_FEATURES if value in self.numeric_features
                ],
                "weather_features": [
                    value for value in WEATHER_FEATURES if value in self.numeric_features
                ],
                "lag_features": [
                    value for value in HISTORY_FEATURES if value in self.numeric_features
                ],
                "engineered_features": [
                    value for value in ENGINEERED_FEATURES if value in self.numeric_features
                ],
            },
            "crawl_manifest": crawl_manifest,
            "feature_count": len(self.feature_columns),
            "horizons": self.horizons,
            "limitations": [
                "Các model dùng khí tượng và chất ô nhiễm đã quan sát tại origin, không dùng dự báo khí tượng tương lai.",
                "Dải màu là ngưỡng tham chiếu PM2.5 theo giờ, không phải chỉ số AQI chính thức 24 giờ.",
                "Chưa gắn khoảng conformal cho từng horizon; giao diện không trình bày dải tin cậy giả tạo.",
            ],
        }

    def readiness(self) -> dict[str, Any]:
        try:
            self.load()
            assert self.artifact is not None
            return {
                "status": "ready",
                "model": "XGBoost Direct Multi-Horizon",
                "horizons": len(self.horizons),
                "feature_count": len(self.feature_columns),
            }
        except Exception as exc:
            return {"status": "not_ready", "error": str(exc)}
