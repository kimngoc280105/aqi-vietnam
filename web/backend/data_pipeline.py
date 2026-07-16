from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backend.features import CITY_CONFIG, normalize_city_name


VALID_RANGES: dict[str, tuple[float | None, float | None]] = {
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


def clean_observations(df: pd.DataFrame, interpolation_limit: int = 6) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = df.copy()
    required = {"datetime", "city", *VALID_RANGES}
    missing_columns = sorted(required.difference(frame.columns))
    if missing_columns:
        raise ValueError(f"Raw dataset is missing required columns: {missing_columns}")

    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="raise")
    frame["city"] = frame["city"].map(normalize_city_name)
    unknown_cities = sorted(set(frame["city"].dropna()).difference(CITY_CONFIG))
    if unknown_cities:
        raise ValueError(f"Unknown cities in raw data: {unknown_cities}")
    frame = frame.sort_values(["city", "datetime"]).reset_index(drop=True)
    if frame.duplicated(["city", "datetime"]).any():
        raise ValueError("Duplicate city/datetime rows must be resolved before cleaning.")

    invalid_counts: dict[str, int] = {}
    missing_before: dict[str, int] = {}
    for column, (lower, upper) in VALID_RANGES.items():
        values = pd.to_numeric(frame[column], errors="coerce")
        missing_before[column] = int(values.isna().sum())
        invalid = pd.Series(False, index=frame.index)
        if lower is not None:
            invalid |= values < lower
        if upper is not None:
            invalid |= values > upper
        invalid_counts[column] = int(invalid.sum())
        frame[column] = values.mask(invalid)

    numeric_columns = list(VALID_RANGES)
    boundary_rows_trimmed: dict[str, int] = {}
    trimmed_parts = []
    for city, city_frame in frame.groupby("city", sort=False):
        complete_source = city_frame[numeric_columns].notna().all(axis=1)
        if not complete_source.any():
            raise ValueError(f"City {city} has no complete source row after range validation.")
        first_valid = complete_source[complete_source].index[0]
        last_valid = complete_source[complete_source].index[-1]
        trimmed = city_frame.loc[first_valid:last_valid].copy()
        boundary_rows_trimmed[str(city)] = int(len(city_frame) - len(trimmed))
        trimmed_parts.append(trimmed)
    frame = pd.concat(trimmed_parts, ignore_index=True).sort_values(["city", "datetime"]).reset_index(drop=True)

    before_interpolation = frame[numeric_columns].isna().sum()
    frame[numeric_columns] = frame.groupby("city", sort=False)[numeric_columns].transform(
        lambda group: group.interpolate(
            method="linear",
            limit=interpolation_limit,
            limit_direction="both",
            limit_area="inside",
        )
    )
    after_interpolation = frame[numeric_columns].isna().sum()

    report = {
        "schema_version": 1,
        "rows": int(len(frame)),
        "interpolation_limit_hours": interpolation_limit,
        "boundary_rows_trimmed": boundary_rows_trimmed,
        "invalid_values_replaced": invalid_counts,
        "missing_before_cleaning": missing_before,
        "values_interpolated": {
            column: int(before_interpolation[column] - after_interpolation[column])
            for column in numeric_columns
        },
        "missing_after_cleaning": {
            column: int(after_interpolation[column]) for column in numeric_columns
        },
        "policy": (
            "Incomplete leading/trailing boundaries are trimmed. Physically invalid values become missing. "
            "Only interior gaps of at most six hourly rows are linearly interpolated within each city; "
            "longer gaps remain missing and fail the data audit."
        ),
    }
    return frame.replace([np.inf, -np.inf], np.nan), report
