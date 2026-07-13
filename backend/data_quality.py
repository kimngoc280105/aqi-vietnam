from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backend.evaluation import make_supervised_frame
from backend.features import CITY_CONFIG, HORIZON_HOURS, pm25_category


RANGE_RULES: dict[str, tuple[float | None, float | None]] = {
    "pm25": (0.0, None),
    "pm10": (0.0, None),
    "o3": (0.0, None),
    "no2": (0.0, None),
    "so2": (0.0, None),
    "co": (0.0, None),
    "temp": (-10.0, 55.0),
    "humidity": (0.0, 100.0),
    "wind_speed": (0.0, None),
    "wind_dir": (0.0, 360.0),
    "precip": (0.0, None),
    "pressure": (850.0, 1100.0),
    "cloud_cover": (0.0, 100.0),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def audit_frame(df: pd.DataFrame, source_path: Path | None = None) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    frame = df.copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="coerce")
    duplicate_rows = int(frame.duplicated(["city", "datetime"]).sum())
    invalid_datetimes = int(frame["datetime"].isna().sum())
    unknown_cities = sorted(set(frame["city"].dropna().astype(str)).difference(CITY_CONFIG))

    range_violations: dict[str, int] = {}
    for column, (lower, upper) in RANGE_RULES.items():
        if column not in frame.columns:
            range_violations[column] = -1
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        invalid = pd.Series(False, index=frame.index)
        if lower is not None:
            invalid |= values < lower
        if upper is not None:
            invalid |= values > upper
        range_violations[column] = int(invalid.sum())

    continuity_rows = []
    city_rows = []
    for city, city_frame in frame.sort_values("datetime").groupby("city", sort=True):
        deltas = city_frame["datetime"].diff().dropna().dt.total_seconds().div(3600.0)
        non_hourly = deltas[deltas != 1.0]
        continuity_rows.extend(
            {
                "city": city,
                "previous_time": city_frame.loc[index - 1, "datetime"] if index - 1 in city_frame.index else None,
                "current_time": city_frame.loc[index, "datetime"],
                "gap_hours": float(delta),
            }
            for index, delta in non_hourly.items()
        )
        categories = pm25_category(city_frame["pm25"].to_numpy())
        category_counts = categories.value_counts().to_dict()
        city_rows.append(
            {
                "city": city,
                "rows": int(len(city_frame)),
                "start_time": city_frame["datetime"].min(),
                "end_time": city_frame["datetime"].max(),
                "missing_rate": float(city_frame.isna().mean().mean()),
                "non_hourly_gaps": int(len(non_hourly)),
                "pm25_mean": float(city_frame["pm25"].mean()),
                "pm25_median": float(city_frame["pm25"].median()),
                "pm25_p95": float(city_frame["pm25"].quantile(0.95)),
                "pm25_max": float(city_frame["pm25"].max()),
                **{f"risk_{key}": int(value) for key, value in category_counts.items()},
            }
        )

    supervised = make_supervised_frame(frame, horizon_hours=HORIZON_HOURS)
    exact_target_rows = int(supervised["target_pm25_24h"].notna().sum())
    missing = frame.isna().mean().sort_values(ascending=False)
    required_source_missing = {
        column: int(frame[column].isna().sum()) if column in frame.columns else -1
        for column in RANGE_RULES
    }
    missing_table = missing.rename_axis("column").reset_index(name="missing_rate")
    continuity_table = pd.DataFrame(
        continuity_rows,
        columns=["city", "previous_time", "current_time", "gap_hours"],
    )
    city_table = pd.DataFrame(city_rows)

    report = {
        "schema_version": 1,
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "cities": sorted(frame["city"].dropna().astype(str).unique().tolist()),
        "start_time": _jsonable(frame["datetime"].min()),
        "end_time": _jsonable(frame["datetime"].max()),
        "duplicate_city_time_rows": duplicate_rows,
        "invalid_datetimes": invalid_datetimes,
        "unknown_cities": unknown_cities,
        "non_hourly_gaps": int(len(continuity_table)),
        "overall_missing_rate": float(frame.isna().mean().mean()),
        "exact_target_rows_24h": exact_target_rows,
        "target_coverage": float(exact_target_rows / len(frame)) if len(frame) else 0.0,
        "range_violations": range_violations,
        "required_source_missing": required_source_missing,
        "source_path": str(source_path) if source_path else None,
        "source_sha256": sha256_file(source_path) if source_path and source_path.exists() else None,
        "source_limitations": [
            "Open-Meteo air quality values for Vietnam are CAMS Global gridded model data, not ground-station measurements.",
            "Each city is represented by one grid point near its centre; results must not be interpreted at district level.",
            "OSM industrial-object counts are static context and do not establish a causal emissions relationship.",
        ],
        "passed": bool(
            duplicate_rows == 0
            and invalid_datetimes == 0
            and not unknown_cities
            and len(continuity_table) == 0
            and all(count == 0 for count in range_violations.values())
            and all(count == 0 for count in required_source_missing.values())
        ),
    }
    return report, city_table, pd.concat(
        {
            "missing": missing_table,
            "continuity": continuity_table,
        },
        names=["section", "row"],
    )


def write_audit(
    data_path: Path,
    results_dir: Path,
) -> dict[str, Any]:
    frame = pd.read_csv(data_path, low_memory=False)
    report, city_table, issue_table = audit_frame(frame, source_path=data_path)
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "data_quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    city_table.to_csv(results_dir / "data_quality_by_city.csv", index=False, encoding="utf-8-sig")
    issue_table.to_csv(results_dir / "data_quality_details.csv", encoding="utf-8-sig")
    return report
