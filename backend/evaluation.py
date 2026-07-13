from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)

from backend.features import HORIZON_HOURS, PM25_LABELS, pm25_category


@dataclass(frozen=True)
class TemporalSplit:
    train_mask: pd.Series
    val_mask: pd.Series
    test_mask: pd.Series
    train_cut: pd.Timestamp
    val_cut: pd.Timestamp
    purge_hours: int

    def summary(self, frame: pd.DataFrame) -> dict[str, Any]:
        output: dict[str, Any] = {
            "strategy": "global chronological 70/15/15 split by target time with purge gaps",
            "train_cut": self.train_cut.isoformat(),
            "val_cut": self.val_cut.isoformat(),
            "purge_hours": self.purge_hours,
        }
        for name, mask in (
            ("train", self.train_mask),
            ("validation", self.val_mask),
            ("test", self.test_mask),
        ):
            part = frame.loc[mask]
            output[name] = {
                "rows": int(len(part)),
                "source_start": part["datetime"].min().isoformat(),
                "source_end": part["datetime"].max().isoformat(),
                "target_start": part["target_time"].min().isoformat(),
                "target_end": part["target_time"].max().isoformat(),
            }
        return output


def make_supervised_frame(df: pd.DataFrame, horizon_hours: int = HORIZON_HOURS) -> pd.DataFrame:
    frame = df.copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame = frame.sort_values(["city", "datetime"]).reset_index(drop=True)
    if frame.duplicated(["city", "datetime"]).any():
        raise ValueError("Duplicate city/datetime rows prevent exact target alignment.")

    frame["target_time"] = frame["datetime"] + pd.Timedelta(hours=horizon_hours)
    targets = frame[["city", "datetime", "pm25"]].rename(
        columns={"datetime": "target_time", "pm25": "target_pm25_24h"}
    )
    return frame.merge(targets, on=["city", "target_time"], how="left", validate="many_to_one")


def temporal_split(
    frame: pd.DataFrame,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
    purge_hours: int = HORIZON_HOURS,
) -> TemporalSplit:
    if train_fraction <= 0 or validation_fraction <= 0 or train_fraction + validation_fraction >= 1:
        raise ValueError("Temporal split fractions must leave non-empty train, validation and test sets.")
    unique_times = pd.Series(pd.to_datetime(frame["target_time"]).dropna().sort_values().unique())
    if len(unique_times) < 100:
        raise ValueError("Not enough target timestamps for a stable temporal split.")

    train_cut = pd.Timestamp(unique_times.iloc[int(len(unique_times) * train_fraction)])
    val_cut = pd.Timestamp(unique_times.iloc[int(len(unique_times) * (train_fraction + validation_fraction))])
    purge = pd.Timedelta(hours=purge_hours)
    target_time = pd.to_datetime(frame["target_time"])
    train_mask = target_time < train_cut
    val_mask = (target_time >= train_cut + purge) & (target_time < val_cut)
    test_mask = target_time >= val_cut + purge
    if not train_mask.any() or not val_mask.any() or not test_mask.any():
        raise ValueError("Temporal split produced an empty partition.")
    return TemporalSplit(train_mask, val_mask, test_mask, train_cut, val_cut, purge_hours)


def regression_metrics(y_true: Any, y_pred: Any) -> dict[str, float]:
    actual = np.asarray(y_true, dtype=float)
    predicted = np.clip(np.asarray(y_pred, dtype=float), 0.0, None)
    return {
        "rmse_ug_m3": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mae_ug_m3": float(mean_absolute_error(actual, predicted)),
        "r2": float(r2_score(actual, predicted)),
        "bias_ug_m3": float(np.mean(predicted - actual)),
    }


def risk_metrics(y_true: Any, y_pred: Any) -> dict[str, float]:
    actual_category = pm25_category(y_true)
    predicted_category = pm25_category(np.clip(np.asarray(y_pred, dtype=float), 0.0, None))
    actual_usg = actual_category.isin(PM25_LABELS[2:]).to_numpy()
    predicted_usg = predicted_category.isin(PM25_LABELS[2:]).to_numpy()
    actual_unhealthy = actual_category.isin(PM25_LABELS[3:]).to_numpy()
    predicted_unhealthy = predicted_category.isin(PM25_LABELS[3:]).to_numpy()
    return {
        "bucket_accuracy": float(accuracy_score(actual_category, predicted_category)),
        "bucket_f1_macro": float(
            f1_score(actual_category, predicted_category, labels=PM25_LABELS, average="macro", zero_division=0)
        ),
        "usg_plus_recall": float(recall_score(actual_usg, predicted_usg, zero_division=0)),
        "usg_plus_precision": float(precision_score(actual_usg, predicted_usg, zero_division=0)),
        "unhealthy_plus_recall": float(recall_score(actual_unhealthy, predicted_unhealthy, zero_division=0)),
        "unhealthy_plus_precision": float(precision_score(actual_unhealthy, predicted_unhealthy, zero_division=0)),
    }


def all_metrics(y_true: Any, y_pred: Any) -> dict[str, float]:
    return {**regression_metrics(y_true, y_pred), **risk_metrics(y_true, y_pred)}


def conformal_radius(y_true: Any, y_pred: Any, coverage: float = 0.90) -> float:
    if not 0.0 < coverage < 1.0:
        raise ValueError("Coverage must be between zero and one.")
    residuals = np.abs(np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float))
    n = residuals.size
    if n == 0:
        raise ValueError("Calibration residuals are empty.")
    quantile_level = min(1.0, np.ceil((n + 1) * coverage) / n)
    return float(np.quantile(residuals, quantile_level, method="higher"))


def interval_metrics(y_true: Any, y_pred: Any, radius: float) -> dict[str, float]:
    actual = np.asarray(y_true, dtype=float)
    prediction = np.asarray(y_pred, dtype=float)
    lower = np.maximum(0.0, prediction - radius)
    upper = prediction + radius
    return {
        "coverage": float(np.mean((actual >= lower) & (actual <= upper))),
        "mean_width_ug_m3": float(np.mean(upper - lower)),
    }


def metrics_by_city(frame: pd.DataFrame, predictions: Any) -> pd.DataFrame:
    scored = frame[["city", "target_pm25_24h"]].copy()
    scored["prediction_pm25"] = np.asarray(predictions, dtype=float)
    rows = []
    for city, city_frame in scored.groupby("city", sort=True):
        rows.append(
            {
                "city": city,
                "rows": int(len(city_frame)),
                **all_metrics(city_frame["target_pm25_24h"], city_frame["prediction_pm25"]),
            }
        )
    return pd.DataFrame(rows)
