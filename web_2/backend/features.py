from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd


HORIZON_HOURS = 24

CITY_CONFIG: dict[str, dict[str, Any]] = {
    "Hà Nội": {
        "slug": "hanoi",
        "latitude": 21.0245,
        "longitude": 105.8412,
        "coverage": "CAMS Global grid cell near the city centre",
    },
    "TP.HCM": {
        "slug": "hochiminh",
        "latitude": 10.7769,
        "longitude": 106.7009,
        "coverage": "CAMS Global grid cell near the city centre",
    },
    "Đà Nẵng": {
        "slug": "danang",
        "latitude": 16.0544,
        "longitude": 108.2022,
        "coverage": "CAMS Global grid cell near the city centre",
    },
}

CITY_ALIASES = {
    "ha noi": "Hà Nội",
    "hanoi": "Hà Nội",
    "hà nội": "Hà Nội",
    "ho chi minh": "TP.HCM",
    "hochiminh": "TP.HCM",
    "tp hcm": "TP.HCM",
    "tp.hcm": "TP.HCM",
    "da nang": "Đà Nẵng",
    "danang": "Đà Nẵng",
    "đà nẵng": "Đà Nẵng",
}

POLLUTANT_FEATURES = ["pm25", "pm10", "o3", "no2", "so2", "co"]
WEATHER_FEATURES = [
    "temp",
    "humidity",
    "wind_speed",
    "wind_dir",
    "precip",
    "pressure",
    "cloud_cover",
]
TEMPORAL_FEATURES = ["hour", "day_of_week", "month", "is_weekend", "day_of_year"]
HISTORY_FEATURES = [
    "pm25_lag_1h",
    "pm25_lag_3h",
    "pm25_lag_6h",
    "pm25_lag_12h",
    "pm25_lag_24h",
    "pm25_lag_48h",
    "pm25_lag_72h",
    "pm25_lag_96h",
    "pm25_lag_120h",
    "pm25_lag_144h",
    "pm25_lag_168h",
    "pm25_roll_6h",
    "pm25_roll_12h",
    "pm25_roll_24h",
    "pm25_roll_72h",
    "pm25_roll_168h",
    "pm25_std_6h",
    "pm25_std_12h",
    "pm25_std_24h",
    "pm25_std_72h",
    "pm25_std_168h",
    "pm25_min_24h",
    "pm25_max_24h",
    "pm25_delta_1h",
    "pm25_delta_3h",
    "pm25_delta_24h",
    "pm25_roll_ratio_6h_24h",
    "pm25_roll_ratio_24h_72h",
    "pm25_same_hour_mean_7d",
    "pm25_same_hour_median_7d",
    "pm25_same_hour_std_7d",
    "pm25_same_hour_min_7d",
    "pm25_same_hour_max_7d",
    "pm25_same_hour_ratio_7d",
    "pm25_weekly_delta",
]
ENGINEERED_FEATURES = [
    "ventilation_index",
    "humid_stagnation",
    "rain_flag",
    "calm_wind",
    "high_humidity",
    "wind_x",
    "wind_y",
    "hour_sin",
    "hour_cos",
    "day_sin",
    "day_cos",
    "month_sin",
    "month_cos",
    "pm25_pm10_ratio",
    "no2_co_ratio",
]
NUMERIC_FEATURES = (
    POLLUTANT_FEATURES
    + WEATHER_FEATURES
    + TEMPORAL_FEATURES
    + HISTORY_FEATURES
    + ENGINEERED_FEATURES
)
# Backwards-compatible aliases for older imports. Both now identify the same
# production feature set without static location context.
NUMERIC_FEATURES_NO_SPATIAL = NUMERIC_FEATURES
NUMERIC_FEATURES_FULL = NUMERIC_FEATURES
CATEGORICAL_FEATURES = ["city", "season"]

# Current U.S. EPA 2024 PM2.5 breakpoints. These are used as reference risk
# bands for an hourly forecast, not presented as an official 24-hour AQI.
PM25_BINS = [-np.inf, 9.0, 35.4, 55.4, 125.4, 225.4, np.inf]
PM25_LABELS = ["Good", "Moderate", "USG", "Unhealthy", "Very Unhealthy", "Hazardous"]
PM25_LABELS_VI = {
    "Good": "Tốt",
    "Moderate": "Trung bình",
    "USG": "Kém cho nhóm nhạy cảm",
    "Unhealthy": "Xấu",
    "Very Unhealthy": "Rất xấu",
    "Hazardous": "Nguy hại",
}
PM25_COLORS = {
    "Good": "#0f8f5f",
    "Moderate": "#c79700",
    "USG": "#e47b25",
    "Unhealthy": "#cf3030",
    "Very Unhealthy": "#7448a8",
    "Hazardous": "#7b1532",
}
HEALTH_NOTES = {
    "Good": "Chất lượng không khí nhìn chung ít gây rủi ro từ bụi mịn.",
    "Moderate": "Người đặc biệt nhạy cảm nên theo dõi triệu chứng khi hoạt động ngoài trời kéo dài.",
    "USG": "Trẻ em, người lớn tuổi và người có bệnh tim hoặc phổi nên giảm vận động ngoài trời kéo dài.",
    "Unhealthy": "Nhóm nhạy cảm nên tránh vận động ngoài trời nặng; những người khác nên giảm thời gian ở ngoài trời.",
    "Very Unhealthy": "Nên hạn chế ra ngoài và giảm các hoạt động làm tăng nhịp thở.",
    "Hazardous": "Nên tránh tiếp xúc ngoài trời nếu có thể và theo dõi khuyến cáo của cơ quan địa phương.",
}
RISK_STANDARD = {
    "name": "U.S. EPA 2024 PM2.5 reference bands",
    "scope": "Reference bands applied to an hourly PM2.5 forecast; not an official AQI value",
    "source": "https://aqs.epa.gov/aqsweb/documents/codetables/aqi_breakpoints.html",
    "breakpoints_ug_m3": [9.0, 35.4, 55.4, 125.4, 225.4],
}


def normalize_city_name(value: Any) -> str:
    city = str(value or "").strip()
    if city in CITY_CONFIG:
        return city
    return CITY_ALIASES.get(city.casefold(), city)


def season_for_month(month: int) -> str:
    if month in (12, 1, 2):
        return "Đông"
    if month in (3, 4, 5):
        return "Xuân"
    if month in (6, 7, 8):
        return "Hạ"
    return "Thu"


def safe_ratio(numerator: Any, denominator: Any, default: float = 0.0) -> Any:
    if isinstance(numerator, pd.Series) or isinstance(denominator, pd.Series):
        numerator_series = pd.Series(numerator, copy=False).astype(float)
        denominator_series = pd.Series(denominator, copy=False).astype(float).replace(0.0, np.nan)
        return (
            numerator_series.div(denominator_series)
            .replace([np.inf, -np.inf], np.nan)
            .fillna(default)
        )
    try:
        denominator_value = float(denominator)
        if abs(denominator_value) < 1e-9:
            return float(default)
        return float(numerator) / denominator_value
    except (TypeError, ValueError):
        return float(default)


def add_time_features(row: dict[str, Any], when: pd.Timestamp) -> dict[str, Any]:
    row["hour"] = int(when.hour)
    row["day_of_week"] = int(when.dayofweek)
    row["month"] = int(when.month)
    row["is_weekend"] = int(when.dayofweek in (5, 6))
    row["day_of_year"] = int(when.dayofyear)
    row["season"] = season_for_month(int(when.month))
    return row


def _enrich_city_history(city_df: pd.DataFrame) -> pd.DataFrame:
    city_df = city_df.sort_values("datetime").copy()
    for lag in (1, 3, 6, 12, 24, 48, 72, 96, 120, 144, 168):
        city_df[f"pm25_lag_{lag}h"] = city_df["pm25"].shift(lag)

    for window in (6, 12, 24, 72, 168):
        rolling = city_df["pm25"].rolling(window=window, min_periods=1)
        city_df[f"pm25_roll_{window}h"] = rolling.mean()
        city_df[f"pm25_std_{window}h"] = rolling.std().fillna(0.0)

    city_df["pm25_min_24h"] = city_df["pm25"].rolling(24, min_periods=1).min()
    city_df["pm25_max_24h"] = city_df["pm25"].rolling(24, min_periods=1).max()
    city_df["pm25_delta_1h"] = city_df["pm25"] - city_df["pm25_lag_1h"]
    city_df["pm25_delta_3h"] = city_df["pm25"] - city_df["pm25_lag_3h"]
    city_df["pm25_delta_24h"] = city_df["pm25"] - city_df["pm25_lag_24h"]
    city_df["pm25_roll_ratio_6h_24h"] = safe_ratio(
        city_df["pm25_roll_6h"], city_df["pm25_roll_24h"]
    )
    city_df["pm25_roll_ratio_24h_72h"] = safe_ratio(
        city_df["pm25_roll_24h"], city_df["pm25_roll_72h"]
    )
    same_hour_columns = ["pm25", *[f"pm25_lag_{lag}h" for lag in (24, 48, 72, 96, 120, 144)]]
    same_hour_values = city_df[same_hour_columns]
    city_df["pm25_same_hour_mean_7d"] = same_hour_values.mean(axis=1)
    city_df["pm25_same_hour_median_7d"] = same_hour_values.median(axis=1)
    city_df["pm25_same_hour_std_7d"] = same_hour_values.std(axis=1).fillna(0.0)
    city_df["pm25_same_hour_min_7d"] = same_hour_values.min(axis=1)
    city_df["pm25_same_hour_max_7d"] = same_hour_values.max(axis=1)
    city_df["pm25_same_hour_ratio_7d"] = safe_ratio(
        city_df["pm25"], city_df["pm25_same_hour_mean_7d"]
    )
    city_df["pm25_weekly_delta"] = city_df["pm25"] - city_df["pm25_lag_168h"]
    return city_df


def enrich_frame(df: pd.DataFrame) -> pd.DataFrame:
    required = {"datetime", "city", "pm25"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Cannot build features; missing columns: {sorted(missing)}")

    enriched = df.copy()
    enriched["datetime"] = pd.to_datetime(enriched["datetime"])
    enriched["city"] = enriched["city"].map(normalize_city_name)
    enriched = enriched.sort_values(["city", "datetime"]).reset_index(drop=True)
    if enriched.duplicated(["city", "datetime"]).any():
        raise ValueError("Duplicate city/datetime rows are not allowed.")

    enriched["year"] = enriched["datetime"].dt.year
    enriched["month"] = enriched["datetime"].dt.month
    enriched["day"] = enriched["datetime"].dt.day
    enriched["hour"] = enriched["datetime"].dt.hour
    enriched["day_of_week"] = enriched["datetime"].dt.dayofweek
    enriched["is_weekend"] = enriched["day_of_week"].isin([5, 6]).astype(int)
    enriched["day_of_year"] = enriched["datetime"].dt.dayofyear
    enriched["season"] = enriched["month"].map(season_for_month)

    enriched = pd.concat(
        [_enrich_city_history(city_df) for _, city_df in enriched.groupby("city", sort=False)],
        ignore_index=True,
    )
    wind_radians = np.deg2rad(enriched["wind_dir"].astype(float).fillna(0.0))
    enriched["wind_x"] = np.sin(wind_radians)
    enriched["wind_y"] = np.cos(wind_radians)
    enriched["ventilation_index"] = (
        enriched["wind_speed"].astype(float)
        * (100.0 - enriched["humidity"].astype(float))
        / 100.0
    )
    enriched["humid_stagnation"] = enriched["humidity"].astype(float) / (
        enriched["wind_speed"].astype(float) + 1.0
    )
    enriched["rain_flag"] = (enriched["precip"].astype(float) > 0.0).astype(int)
    enriched["calm_wind"] = (enriched["wind_speed"].astype(float) < 2.0).astype(int)
    enriched["high_humidity"] = (enriched["humidity"].astype(float) > 85.0).astype(int)
    enriched["hour_sin"] = np.sin(2.0 * np.pi * enriched["hour"].astype(float) / 24.0)
    enriched["hour_cos"] = np.cos(2.0 * np.pi * enriched["hour"].astype(float) / 24.0)
    enriched["day_sin"] = np.sin(2.0 * np.pi * enriched["day_of_year"].astype(float) / 365.25)
    enriched["day_cos"] = np.cos(2.0 * np.pi * enriched["day_of_year"].astype(float) / 365.25)
    enriched["month_sin"] = np.sin(2.0 * np.pi * enriched["month"].astype(float) / 12.0)
    enriched["month_cos"] = np.cos(2.0 * np.pi * enriched["month"].astype(float) / 12.0)
    enriched["pm25_pm10_ratio"] = safe_ratio(enriched["pm25"], enriched["pm10"])
    enriched["no2_co_ratio"] = safe_ratio(enriched["no2"], enriched["co"])
    return enriched.replace([np.inf, -np.inf], np.nan)


def enrich_row(row: dict[str, Any], when: pd.Timestamp | None = None) -> dict[str, Any]:
    enriched = dict(row)
    enriched["city"] = normalize_city_name(enriched.get("city"))
    timestamp = pd.Timestamp(when if when is not None else enriched.get("datetime", pd.Timestamp.now()))
    add_time_features(enriched, timestamp)

    pm25 = float(enriched.get("pm25", 0.0) or 0.0)
    for lag in (1, 3, 6, 12, 24, 48, 72, 96, 120, 144, 168):
        enriched[f"pm25_lag_{lag}h"] = float(enriched.get(f"pm25_lag_{lag}h", pm25) or pm25)
    for window in (6, 12, 24, 72, 168):
        enriched[f"pm25_roll_{window}h"] = float(enriched.get(f"pm25_roll_{window}h", pm25) or pm25)
        enriched[f"pm25_std_{window}h"] = float(enriched.get(f"pm25_std_{window}h", 0.0) or 0.0)

    enriched["pm25_min_24h"] = float(enriched.get("pm25_min_24h", pm25) or pm25)
    enriched["pm25_max_24h"] = float(enriched.get("pm25_max_24h", pm25) or pm25)
    enriched["pm25_delta_1h"] = pm25 - enriched["pm25_lag_1h"]
    enriched["pm25_delta_3h"] = pm25 - enriched["pm25_lag_3h"]
    enriched["pm25_delta_24h"] = pm25 - enriched["pm25_lag_24h"]
    enriched["pm25_roll_ratio_6h_24h"] = safe_ratio(
        enriched["pm25_roll_6h"], enriched["pm25_roll_24h"]
    )
    enriched["pm25_roll_ratio_24h_72h"] = safe_ratio(
        enriched["pm25_roll_24h"], enriched["pm25_roll_72h"]
    )
    same_hour_values = np.asarray(
        [pm25, *[enriched[f"pm25_lag_{lag}h"] for lag in (24, 48, 72, 96, 120, 144)]],
        dtype=float,
    )
    enriched["pm25_same_hour_mean_7d"] = float(np.mean(same_hour_values))
    enriched["pm25_same_hour_median_7d"] = float(np.median(same_hour_values))
    enriched["pm25_same_hour_std_7d"] = float(np.std(same_hour_values, ddof=1))
    enriched["pm25_same_hour_min_7d"] = float(np.min(same_hour_values))
    enriched["pm25_same_hour_max_7d"] = float(np.max(same_hour_values))
    enriched["pm25_same_hour_ratio_7d"] = safe_ratio(
        pm25, enriched["pm25_same_hour_mean_7d"]
    )
    enriched["pm25_weekly_delta"] = pm25 - enriched["pm25_lag_168h"]

    humidity = float(enriched.get("humidity", 0.0) or 0.0)
    wind_speed = float(enriched.get("wind_speed", 0.0) or 0.0)
    wind_dir = float(enriched.get("wind_dir", 0.0) or 0.0)
    precip = float(enriched.get("precip", 0.0) or 0.0)
    wind_radians = np.deg2rad(wind_dir)
    enriched["wind_x"] = float(np.sin(wind_radians))
    enriched["wind_y"] = float(np.cos(wind_radians))
    enriched["ventilation_index"] = wind_speed * (100.0 - humidity) / 100.0
    enriched["humid_stagnation"] = humidity / (wind_speed + 1.0)
    enriched["rain_flag"] = int(precip > 0.0)
    enriched["calm_wind"] = int(wind_speed < 2.0)
    enriched["high_humidity"] = int(humidity > 85.0)
    enriched["hour_sin"] = float(np.sin(2.0 * np.pi * enriched["hour"] / 24.0))
    enriched["hour_cos"] = float(np.cos(2.0 * np.pi * enriched["hour"] / 24.0))
    enriched["day_sin"] = float(np.sin(2.0 * np.pi * enriched["day_of_year"] / 365.25))
    enriched["day_cos"] = float(np.cos(2.0 * np.pi * enriched["day_of_year"] / 365.25))
    enriched["month_sin"] = float(np.sin(2.0 * np.pi * enriched["month"] / 12.0))
    enriched["month_cos"] = float(np.cos(2.0 * np.pi * enriched["month"] / 12.0))
    enriched["pm25_pm10_ratio"] = safe_ratio(pm25, enriched.get("pm10", 0.0))
    enriched["no2_co_ratio"] = safe_ratio(enriched.get("no2", 0.0), enriched.get("co", 0.0))
    enriched["datetime"] = timestamp.isoformat()
    return enriched


def build_feature_matrix(
    df: pd.DataFrame,
    feature_columns: Iterable[str] | None = None,
    numeric_features: list[str] | None = None,
    categorical_features: list[str] | None = None,
) -> pd.DataFrame:
    numeric = numeric_features or NUMERIC_FEATURES_NO_SPATIAL
    categorical = categorical_features or CATEGORICAL_FEATURES
    encoded = pd.get_dummies(
        df[numeric + categorical],
        columns=categorical,
        drop_first=False,
        dtype=float,
    )
    if feature_columns is None:
        return encoded.astype(float)
    ordered_columns = list(feature_columns)
    for column in ordered_columns:
        if column not in encoded.columns:
            encoded[column] = 0.0
    return encoded.reindex(columns=ordered_columns, fill_value=0.0).astype(float)


def pm25_category(values: Any) -> pd.Series:
    array = np.asarray(values, dtype=float)
    return pd.Series(pd.cut(array, bins=PM25_BINS, labels=PM25_LABELS, include_lowest=True))


def category_payload(value: float) -> dict[str, str]:
    category = str(pm25_category([value]).iloc[0])
    return {
        "category": category,
        "label_vi": PM25_LABELS_VI[category],
        "color": PM25_COLORS[category],
        "note": HEALTH_NOTES[category],
        "standard": RISK_STANDARD["name"],
    }
