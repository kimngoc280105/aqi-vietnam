from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from backend.features import (
    CATEGORICAL_FEATURES,
    CITY_CONFIG,
    HORIZON_HOURS,
    NUMERIC_FEATURES_NO_SPATIAL,
    RISK_STANDARD,
    build_feature_matrix,
    category_payload,
    enrich_row,
    normalize_city_name,
)
from backend.live_data import LiveDataProvider


WEB_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = WEB_ROOT.parent
TRAINING_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "pm25_training_data_enriched.csv"
RUNTIME_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "inference_history.csv"
DATA_PATH = RUNTIME_DATA_PATH if RUNTIME_DATA_PATH.exists() else TRAINING_DATA_PATH
MODEL_PATH = PROJECT_ROOT / "model" / "pm25_24h_best.joblib"
METADATA_PATH = PROJECT_ROOT / "model" / "pm25_24h_best_metadata.json"

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

# These fields are useful to people browsing the app and for manual scenarios.
PRESENTATION_FEATURES = [
    "pm25",
    "pm10",
    "o3",
    "no2",
    "so2",
    "co",
    "temp",
    "humidity",
    "wind_speed",
    "wind_dir",
    "precip",
    "pressure",
    "cloud_cover",
]


def parse_timestamp(value: Any | None) -> pd.Timestamp:
    if value is None or value == "":
        return pd.Timestamp.now(tz="Asia/Ho_Chi_Minh").tz_localize(None).floor("h")
    timestamp = pd.to_datetime(value)
    if isinstance(timestamp, pd.Timestamp) and timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert("Asia/Ho_Chi_Minh").tz_localize(None)
    return pd.Timestamp(timestamp)


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


class AQIModelService:
    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        data_path: Path = DATA_PATH,
        live_provider: LiveDataProvider | None = None,
    ) -> None:
        self.model_path = model_path
        self.data_path = data_path
        self.artifact: dict[str, Any] | None = None
        self._data: pd.DataFrame | None = None
        self.live_provider = live_provider or LiveDataProvider(PROJECT_ROOT)

    def load(self) -> None:
        if self.artifact is not None:
            return
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model artifact not found at {self.model_path}.")
        artifact = joblib.load(self.model_path)
        required = {"model", "feature_columns", "numeric_features", "categorical_features", "metrics"}
        missing = required.difference(artifact)
        if missing:
            raise ValueError(f"Model artifact schema is incomplete: {sorted(missing)}")
        self.artifact = artifact

    @property
    def feature_columns(self) -> list[str]:
        self.load()
        assert self.artifact is not None
        return list(self.artifact["feature_columns"])

    @property
    def numeric_features(self) -> list[str]:
        self.load()
        assert self.artifact is not None
        return list(self.artifact.get("numeric_features", NUMERIC_FEATURES_NO_SPATIAL))

    @property
    def categorical_features(self) -> list[str]:
        self.load()
        assert self.artifact is not None
        return list(self.artifact.get("categorical_features", CATEGORICAL_FEATURES))

    @property
    def metrics(self) -> dict[str, Any]:
        self.load()
        assert self.artifact is not None
        return dict(self.artifact.get("metrics", {}))

    @property
    def latest_profiles(self) -> dict[str, dict[str, Any]]:
        self.load()
        assert self.artifact is not None
        return dict(self.artifact.get("latest_profiles", {}))

    def load_data(self) -> pd.DataFrame:
        if self._data is None:
            frame = pd.read_csv(self.data_path, low_memory=False)
            frame["datetime"] = pd.to_datetime(frame["datetime"])
            self._data = frame.sort_values(["city", "datetime"]).reset_index(drop=True)
        return self._data

    def _profile_from_live_frame(
        self,
        city: str,
        frame: pd.DataFrame,
        source: dict[str, Any],
    ) -> dict[str, Any]:
        complete = frame.dropna(subset=self.numeric_features + self.categorical_features)
        if complete.empty:
            raise RuntimeError(f"Live frame has no model-ready row for {city}.")
        row = complete.iloc[-1]
        profile_columns = list(
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
        profile = {key: to_jsonable(row.get(key)) for key in profile_columns if key in row.index}
        return {
            "city": city,
            "latest_datetime": profile["datetime"],
            "latest_pm25": profile.get("pm25"),
            "profile": profile,
            "source": source,
        }

    def _historical_fallback(self, city: str, error: str | None = None) -> dict[str, Any]:
        profile = dict(self.latest_profiles.get(city, {}))
        try:
            city_data = self.load_data().loc[lambda frame: frame["city"].map(normalize_city_name) == city]
            complete = city_data.dropna(subset=self.numeric_features + self.categorical_features)
            if not complete.empty:
                row = complete.iloc[-1]
                profile_columns = list(
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
                profile.update(
                    {key: to_jsonable(row.get(key)) for key in profile_columns if key in row.index}
                )
        except Exception:
            # The saved model profile remains a valid last-resort fallback.
            pass
        if not profile:
            raise ValueError(f"No profile is available for {city}.")
        return {
            "city": city,
            "latest_datetime": profile.get("datetime"),
            "latest_pm25": profile.get("pm25"),
            "profile": profile,
            "source": {
                "status": "historical_fallback",
                "provider": "Saved training snapshot",
                "latest_observation": profile.get("datetime"),
                "refresh_error": error,
            },
        }

    def cities(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        self.load()
        live_results = self.live_provider.get_many(list(CITY_CONFIG), force=force_refresh)
        output = []
        for city in CITY_CONFIG:
            result = live_results.get(city)
            if isinstance(result, Exception) or result is None:
                output.append(self._historical_fallback(city, str(result) if result else "No result"))
                continue
            frame, source = result
            try:
                output.append(self._profile_from_live_frame(city, frame, source))
            except Exception as exc:
                output.append(self._historical_fallback(city, str(exc)))
        return output

    def normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        city = normalize_city_name(payload.get("city") or next(iter(CITY_CONFIG)))
        if city not in CITY_CONFIG:
            raise ValueError(f"Unsupported city: {payload.get('city')}")

        base = dict(self.latest_profiles.get(city, {}))
        supplied_profile = payload.get("profile")
        if isinstance(supplied_profile, dict):
            base.update(supplied_profile)
        else:
            # Direct API clients commonly send only a city. Keep that path in
            # sync with the web app instead of silently predicting from the
            # profile embedded in the training artifact.
            try:
                current = next(item for item in self.cities() if item["city"] == city)
                current_profile = current.get("profile")
                if isinstance(current_profile, dict):
                    base.update(current_profile)
            except Exception:
                # The saved artifact remains the documented offline fallback.
                pass
        base.update({key: value for key, value in payload.items() if key not in {"profile"} and value is not None})
        base["city"] = city
        for key, default in INPUT_DEFAULTS.items():
            value = base.get(key, default)
            base[key] = float(default if value is None else value)

        when = parse_timestamp(base.get("observed_at", base.get("datetime")))
        enriched = enrich_row(base, when=when)
        enriched["observed_at"] = when.isoformat()
        return enriched

    def _interval_for(self, city: str, prediction: float, level: str = "90") -> dict[str, Any]:
        self.load()
        assert self.artifact is not None
        interval = self.artifact.get("interval", {})
        level_details = interval.get("levels", {}).get(level, {})
        city_details = level_details.get("by_city", {}).get(city, {})
        radius = float(
            city_details.get(
                "radius_ug_m3",
                level_details.get("fallback_global_radius_ug_m3", self.metrics.get("test_mae_ug_m3", 0.0)),
            )
        )
        return {
            "lower": round(max(0.0, prediction - radius), 2),
            "upper": round(prediction + radius, 2),
            "radius": round(radius, 2),
            "nominal_coverage": int(level) / 100.0,
            "empirical_test_coverage": city_details.get("coverage"),
            "method": interval.get("method", "fallback_error_band"),
        }

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.load()
        assert self.artifact is not None
        row = self.normalize_payload(payload)
        matrix = build_feature_matrix(
            pd.DataFrame([row]),
            feature_columns=self.feature_columns,
            numeric_features=self.numeric_features,
            categorical_features=self.categorical_features,
        )
        prediction = max(0.0, float(self.artifact["model"].predict(matrix)[0]))
        city = str(row["city"])
        return {
            "city": city,
            "prediction_pm25": round(prediction, 2),
            "observed_at": row["observed_at"],
            "target_time": (parse_timestamp(row["observed_at"]) + pd.Timedelta(hours=HORIZON_HOURS)).isoformat(),
            "category": category_payload(prediction),
            "interval": self._interval_for(city, prediction, level="90"),
            "features_used": {
                key: to_jsonable(row.get(key)) for key in self.numeric_features + self.categorical_features
            },
            "model": {
                "name": self.artifact.get("model_name", self.metrics.get("model")),
                "version": self.artifact.get("model_version"),
                "metrics": self.metrics,
            },
            "risk_standard": self.artifact.get("risk_standard", RISK_STANDARD),
        }

    def explain(self, payload: dict[str, Any], top_n: int = 10) -> dict[str, Any]:
        """Return local TreeSHAP contributions for the exact row being predicted."""
        self.load()
        assert self.artifact is not None
        row = self.normalize_payload(payload)
        matrix = build_feature_matrix(
            pd.DataFrame([row]),
            feature_columns=self.feature_columns,
            numeric_features=self.numeric_features,
            categorical_features=self.categorical_features,
        )
        model = self.artifact["model"]
        if not hasattr(model, "get_booster"):
            raise ValueError("The deployed model does not expose TreeSHAP contributions.")

        booster = model.get_booster()
        best_iteration = getattr(model, "best_iteration", None)
        iteration_range = (
            (0, int(best_iteration) + 1)
            if best_iteration is not None and int(best_iteration) >= 0
            else (0, 0)
        )
        contribution_matrix = booster.predict(
            xgb.DMatrix(matrix, feature_names=self.feature_columns),
            pred_contribs=True,
            iteration_range=iteration_range,
        )
        values = np.asarray(contribution_matrix[0], dtype=float)
        baseline = float(values[-1])
        contributions = values[:-1]
        prediction = max(0.0, float(model.predict(matrix)[0]))
        rows = [
            {
                "feature": feature,
                "feature_value": float(matrix.iloc[0][feature]),
                "contribution_ug_m3": float(contribution),
                "direction": "increase" if contribution >= 0 else "decrease",
            }
            for feature, contribution in zip(self.feature_columns, contributions, strict=True)
        ]
        rows.sort(key=lambda item: abs(item["contribution_ug_m3"]), reverse=True)
        selected = rows[: max(1, min(int(top_n), len(rows)))]
        explained_prediction = baseline + float(np.sum(contributions))
        return {
            "city": str(row["city"]),
            "observed_at": row["observed_at"],
            "target_time": (
                parse_timestamp(row["observed_at"]) + pd.Timedelta(hours=HORIZON_HOURS)
            ).isoformat(),
            "prediction_pm25": round(prediction, 2),
            "baseline_pm25": round(baseline, 2),
            "explained_prediction_pm25": round(explained_prediction, 2),
            "reconstruction_error": round(abs(prediction - explained_prediction), 8),
            "contributions": selected,
            "method": {
                "name": "TreeSHAP",
                "scope": "local explanation for this prediction",
                "interpretation": (
                    "Positive values push the forecast above the model baseline; "
                    "negative values push it below the baseline."
                ),
                "causal": False,
            },
        }

    def backtest(self, city: str, limit: int = 7) -> dict[str, Any]:
        """Replay recent historical forecasts with exact t+24 observations."""
        self.load()
        assert self.artifact is not None
        normalized_city = normalize_city_name(city)
        if normalized_city not in CITY_CONFIG:
            raise ValueError(f"Unsupported city: {city}")

        city_frame = self.load_data()
        city_frame = city_frame.loc[
            city_frame["city"].map(normalize_city_name) == normalized_city
        ].copy()
        city_frame = city_frame.sort_values("datetime").reset_index(drop=True)
        city_frame["target_time"] = city_frame["datetime"] + pd.Timedelta(hours=HORIZON_HOURS)
        target_lookup = city_frame.set_index("datetime")["pm25"]
        city_frame["actual_pm25_24h"] = city_frame["target_time"].map(target_lookup)
        ready = city_frame.dropna(
            subset=self.numeric_features + self.categorical_features + ["actual_pm25_24h"]
        ).copy()
        if ready.empty:
            raise ValueError(f"No replay-ready rows are available for {normalized_city}.")

        anchor_hour = int(ready["datetime"].max().hour)
        daily = ready.loc[ready["datetime"].dt.hour == anchor_hour]
        sample = daily.tail(max(1, min(int(limit), 14))).copy()
        matrix = build_feature_matrix(
            sample,
            feature_columns=self.feature_columns,
            numeric_features=self.numeric_features,
            categorical_features=self.categorical_features,
        )
        sample["predicted_pm25"] = np.clip(
            self.artifact["model"].predict(matrix), 0.0, None
        )
        sample["abs_error_ug_m3"] = np.abs(
            sample["actual_pm25_24h"] - sample["predicted_pm25"]
        )
        rows = []
        for _, replay in sample.iterrows():
            prediction = float(replay["predicted_pm25"])
            actual = float(replay["actual_pm25_24h"])
            rows.append(
                {
                    "observed_at": to_jsonable(replay["datetime"]),
                    "target_time": to_jsonable(replay["target_time"]),
                    "current_pm25": round(float(replay["pm25"]), 2),
                    "predicted_pm25": round(prediction, 2),
                    "actual_pm25": round(actual, 2),
                    "abs_error_ug_m3": round(abs(actual - prediction), 2),
                    "prediction_category": category_payload(prediction),
                    "actual_category": category_payload(actual),
                }
            )
        actual = sample["actual_pm25_24h"].to_numpy(dtype=float)
        predicted = sample["predicted_pm25"].to_numpy(dtype=float)
        return {
            "city": normalized_city,
            "horizon_hours": HORIZON_HOURS,
            "source": "bundled historical CAMS snapshot",
            "rows": rows,
            "summary": {
                "samples": int(len(sample)),
                "rmse_ug_m3": round(float(np.sqrt(np.mean((actual - predicted) ** 2))), 2),
                "mae_ug_m3": round(float(np.mean(np.abs(actual - predicted))), 2),
            },
        }

    def scenarios(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        base = self.normalize_payload(payload)
        cases = [
            ("Hiện tại", {}),
            ("PM2.5 hiện tại tăng 20%", {"pm25": base["pm25"] * 1.2}),
            (
                "Nền 24 giờ gần đây cao hơn 20%",
                {
                    "pm25_roll_6h": base["pm25_roll_6h"] * 1.2,
                    "pm25_roll_24h": base["pm25_roll_24h"] * 1.2,
                },
            ),
            (
                "Cùng giờ tuần trước thấp hơn 20%",
                {
                    "pm25_lag_168h": base["pm25_lag_168h"] * 0.8,
                },
            ),
        ]
        output = []
        for name, updates in cases:
            scenario_payload = dict(base)
            scenario_payload.update(updates)
            result = self.predict(scenario_payload)
            output.append(
                {
                    "name": name,
                    "kind": "input_sensitivity_not_causal",
                    **result,
                }
            )
        return output

    def history(self, city: str, limit: int = 168, force_refresh: bool = False) -> list[dict[str, Any]]:
        normalized_city = normalize_city_name(city)
        if normalized_city not in CITY_CONFIG:
            raise ValueError(f"Unsupported city: {city}")
        try:
            frame, source = self.live_provider.get_city(normalized_city, force=force_refresh)
            history_frame = frame.tail(max(1, min(limit, 720))).copy()
            source_status = source.get("status", "live")
        except Exception:
            frame = self.load_data()
            history_frame = frame[frame["city"] == normalized_city].tail(max(1, min(limit, 720))).copy()
            source_status = "historical_fallback"
        columns = ["datetime", "pm25", "pm10", "temp", "humidity", "wind_speed", "precip"]
        return [
            {
                **{key: to_jsonable(value) for key, value in row.items()},
                "source_status": source_status,
            }
            for row in history_frame[columns].to_dict(orient="records")
        ]

    def readiness(self) -> dict[str, Any]:
        try:
            self.load()
            profile = next(iter(self.latest_profiles.values()))
            city = normalize_city_name(profile.get("city"))
            result = self.predict({"city": city, "profile": profile})
            return {
                "status": "ready",
                "model_name": self.artifact.get("model_name") if self.artifact else None,
                "model_version": self.artifact.get("model_version") if self.artifact else None,
                "feature_count": len(self.feature_columns),
                "smoke_prediction_pm25": result["prediction_pm25"],
            }
        except Exception as exc:
            return {"status": "not_ready", "error": str(exc)}
