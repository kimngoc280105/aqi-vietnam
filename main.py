"""
Crawl dữ liệu AQI Việt Nam - Hà Nội, TP.HCM, Đà Nẵng
Tích hợp: Khí tượng (Open-Meteo) & Dữ liệu không gian Nhà máy (OpenStreetMap)
=======================================================
"""

import pandas as pd
import os
from datetime import datetime, timedelta
import time
import requests

import openmeteo_requests
from retry_requests import retry

# ============================================================
# CẤU HÌNH
# ============================================================
START_DATE = "2022-08-01"
END_DATE   = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

CITIES = {
    "hanoi"     : {"label": "Hà Nội",  "lat": 21.0245, "lon": 105.8412},
    "hochiminh" : {"label": "TP.HCM",  "lat": 10.7769, "lon": 106.7009},
    "danang"    : {"label": "Đà Nẵng", "lat": 16.0544, "lon": 108.2022},
}

# Các mốc bán kính (mét) để quét số lượng nhà máy xung quanh tọa độ
FACTORY_RADII = [2000, 5000, 10000] 

os.makedirs("data/raw",       exist_ok=True)
os.makedirs("data/processed", exist_ok=True)


# [ĐÃ SỬA LỖI 1]: Dùng requests.Session() bình thường, bỏ cache để tránh lỗi database
def get_om_client():
    session = retry(requests.Session(), retries=5, backoff_factor=0.3)
    return openmeteo_requests.Client(session=session)


# ============================================================
# CRAWL CHẤT LƯỢNG KHÔNG KHÍ
# ============================================================
def crawl_air_quality(city_key: str, cfg: dict) -> pd.DataFrame:
    print(f"\n🌫  Air Quality — {cfg['label']}")
    om = get_om_client()

    resp = om.weather_api(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        params={
            "latitude"  : cfg["lat"],
            "longitude" : cfg["lon"],
            "start_date": START_DATE,
            "end_date"  : END_DATE,
            "hourly"    : ["pm2_5", "pm10", "ozone", "nitrogen_dioxide",
                           "sulphur_dioxide", "carbon_monoxide",
                           "european_aqi", "us_aqi"],
            "timezone"  : "Asia/Ho_Chi_Minh",
        }
    )[0]

    hr = resp.Hourly()
    n  = hr.Variables(0).ValuesAsNumpy().shape[0]

    df = pd.DataFrame({
        "datetime": pd.date_range(
            start   = pd.to_datetime(hr.Time(), unit="s", utc=True)
                        .tz_convert("Asia/Ho_Chi_Minh").tz_localize(None),
            periods = n, freq="h"),
        "pm25"    : hr.Variables(0).ValuesAsNumpy(),
        "pm10"    : hr.Variables(1).ValuesAsNumpy(),
        "o3"      : hr.Variables(2).ValuesAsNumpy(),
        "no2"     : hr.Variables(3).ValuesAsNumpy(),
        "so2"     : hr.Variables(4).ValuesAsNumpy(),
        "co"      : hr.Variables(5).ValuesAsNumpy(),
        "eu_aqi"  : hr.Variables(6).ValuesAsNumpy(),
        "aqi"     : hr.Variables(7).ValuesAsNumpy(),
    })

    df = df.dropna(subset=["pm25", "aqi"])
    df["city"] = cfg["label"]

    path = f"data/raw/airquality_{city_key}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  ✅ {len(df):,} giờ | 💾 {path}")
    return df


# ============================================================
# CRAWL KHÍ TƯỢNG
# ============================================================
def crawl_weather(city_key: str, cfg: dict) -> pd.DataFrame:
    print(f"\n🌤  Weather — {cfg['label']}")
    om = get_om_client()

    resp = om.weather_api(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude"  : cfg["lat"],
            "longitude" : cfg["lon"],
            "start_date": START_DATE,
            "end_date"  : END_DATE,
            "hourly"    : ["temperature_2m", "relative_humidity_2m",
                           "wind_speed_10m", "wind_direction_10m",
                           "precipitation", "surface_pressure", "cloud_cover"],
            "timezone"  : "Asia/Ho_Chi_Minh",
        }
    )[0]

    hr = resp.Hourly()
    n  = hr.Variables(0).ValuesAsNumpy().shape[0]

    df = pd.DataFrame({
        "datetime"   : pd.date_range(
            start   = pd.to_datetime(hr.Time(), unit="s", utc=True)
                        .tz_convert("Asia/Ho_Chi_Minh").tz_localize(None),
            periods = n, freq="h"),
        "temp"       : hr.Variables(0).ValuesAsNumpy(),
        "humidity"   : hr.Variables(1).ValuesAsNumpy(),
        "wind_speed" : hr.Variables(2).ValuesAsNumpy(),
        "wind_dir"   : hr.Variables(3).ValuesAsNumpy(),
        "precip"     : hr.Variables(4).ValuesAsNumpy(),
        "pressure"   : hr.Variables(5).ValuesAsNumpy(),
        "cloud_cover": hr.Variables(6).ValuesAsNumpy(),
    })
    df["city"] = cfg["label"]

    path = f"data/raw/weather_{city_key}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  ✅ {len(df):,} giờ | 💾 {path}")
    return df

# ============================================================
# CRAWL DỮ LIỆU KHÔNG GIAN (NHÀ MÁY) - OVERPASS API
# ============================================================
# ============================================================
# CRAWL DỮ LIỆU KHÔNG GIAN (NHÀ MÁY) - OVERPASS API (ĐÃ NÂNG CẤP)
# ============================================================
def get_factories_count(lat: float, lon: float, radius: int) -> int:
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # [NÂNG CẤP 1]: Thêm [timeout:50] vào Overpass QL để xin thêm thời gian xử lý
    query = f"""
    [out:json][timeout:50];
    (
      node["landuse"="industrial"](around:{radius},{lat},{lon});
      way["landuse"="industrial"](around:{radius},{lat},{lon});
      relation["landuse"="industrial"](around:{radius},{lat},{lon});
      
      node["man_made"="works"](around:{radius},{lat},{lon});
      way["man_made"="works"](around:{radius},{lat},{lon});
      relation["man_made"="works"](around:{radius},{lat},{lon});
    );
    out count;
    """
    
    headers = {
        'User-Agent': 'Vietnam-AQI-ML-Project/1.0 (Student Research)'
    }
    
    # [NÂNG CẤP 2]: Thử gọi lại API tối đa 3 lần nếu bị Timeout
    for attempt in range(3):
        try:
            # Thêm timeout=60 ở thư viện requests để tránh Python bỏ cuộc sớm
            resp = requests.post(overpass_url, data={'data': query}, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            return int(data['elements'][0]['tags']['total'])
        except Exception as e:
            print(f"    ⚠️ Lỗi API (Lần thử {attempt + 1}/3): {e}")
            time.sleep(3) # Nghỉ 3 giây trước khi thử lại
            
    return 0 # Nếu thử 3 lần vẫn thất bại thì đành trả về 0

# ============================================================
# MERGE + FEATURE ENGINEERING
# ============================================================
def merge_and_fe(city_key: str, df_aq: pd.DataFrame, df_weather: pd.DataFrame, spatial_features: dict) -> pd.DataFrame:
    label = CITIES[city_key]["label"]

    df = pd.merge(df_aq, df_weather.drop(columns=["city"]), on="datetime", how="inner")
    df["city"] = label
    df = df.sort_values("datetime").reset_index(drop=True)

    for feature_name, value in spatial_features.items():
        df[feature_name] = value

    df["year"]        = df["datetime"].dt.year
    df["month"]       = df["datetime"].dt.month
    df["day"]         = df["datetime"].dt.day
    df["hour"]        = df["datetime"].dt.hour
    df["day_of_week"] = df["datetime"].dt.dayofweek
    df["is_weekend"]  = df["day_of_week"].isin([5, 6]).astype(int)
    df["day_of_year"] = df["datetime"].dt.dayofyear

    def get_season(month, city):
        if city == "Hà Nội":
            if month in [12, 1, 2]: return "Đông"
            if month in [3, 4]:     return "Xuân"
            if month in [5, 6, 7, 8]: return "Hạ"
            return "Thu"
        return "Khô" if month in [11, 12, 1, 2, 3, 4] else "Mưa"
    df["season"] = df.apply(lambda r: get_season(r["month"], r["city"]), axis=1)

    for lag in [1, 3, 6, 12, 24]:
        df[f"pm25_lag_{lag}h"] = df["pm25"].shift(lag)
    df["pm25_roll_6h"]  = df["pm25"].rolling(6,  min_periods=1).mean()
    df["pm25_roll_24h"] = df["pm25"].rolling(24, min_periods=1).mean()
    df["pm25_roll_72h"] = df["pm25"].rolling(72, min_periods=1).mean()

    def aqi_category(v):
        if pd.isna(v):  return None
        v = float(v)
        if v <= 50:     return "Tốt"
        if v <= 100:    return "Trung bình"
        if v <= 150:    return "Kém"
        if v <= 200:    return "Xấu"
        if v <= 300:    return "Rất xấu"
        return "Nguy hại"
    df["aqi_category"] = df["aqi"].apply(aqi_category)

    return df


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🇻🇳 CRAWL DỮ LIỆU AQI VIỆT NAM (KÈM DỮ LIỆU NHÀ MÁY)")
    print(f"   Giai đoạn: {START_DATE} → {END_DATE}")
    print("=" * 60)

    aq_dfs, weather_dfs = {}, {}

    print("\n── BƯỚC 1: Air Quality ──")
    for ck, cfg in CITIES.items():
        try:
            aq_dfs[ck] = crawl_air_quality(ck, cfg)
        except Exception as e:
            print(f"  ❌ {e}")

    print("\n── BƯỚC 2: Khí tượng ──")
    for ck, cfg in CITIES.items():
        try:
            weather_dfs[ck] = crawl_weather(ck, cfg)
        except Exception as e:
            print(f"  ❌ {e}")

    print("\n── BƯỚC 3: Dữ liệu Không gian (Nhà máy) ──")
    city_spatial_features = {}
    for ck, cfg in CITIES.items():
        print(f"🏭 Đang đếm nhà máy xung quanh {cfg['label']}...")
        city_spatial_features[ck] = {}
        for r in FACTORY_RADII:
            count = get_factories_count(cfg['lat'], cfg['lon'], r)
            city_spatial_features[ck][f"factories_{r//1000}km"] = count
            time.sleep(1.5)
        print(f"  ✅ {city_spatial_features[ck]}")

    print("\n── BƯỚC 4: Merge & Feature Engineering ──")
    merged = []
    for ck in CITIES:
        if ck not in aq_dfs or ck not in weather_dfs:
            print(f"  ⚠️  Thiếu data cho {ck}, bỏ qua")
            continue
        
        df = merge_and_fe(ck, aq_dfs[ck], weather_dfs[ck], city_spatial_features[ck])
        
        path = f"data/processed/merged_{ck}.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  💾 {path} | {len(df):,} dòng | {len(df.columns)} cột")
        merged.append(df)

    if merged:
        df_all = pd.concat(merged, ignore_index=True)
        df_all.to_csv("data/processed/all_cities.csv", index=False, encoding="utf-8-sig")
        print(f"\n🎉 all_cities.csv: {len(df_all):,} dòng")
        print(f"   Phân bố: {df_all['city'].value_counts().to_dict()}")
        print(f"   Cột mới được thêm: {[c for c in df_all.columns if 'factories' in c]}")
        print("\n✅ XONG! Dùng data/processed/all_cities.csv để train model")