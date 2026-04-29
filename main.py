"""
Crawl dữ liệu AQI Việt Nam - 3 thành phố: Hà Nội, TP.HCM, Đà Nẵng
=======================================================================
Nguồn data:
  - OpenAQ API v3  : Dữ liệu lịch sử PM2.5, PM10, NO2, SO2, O3, CO (theo giờ)
  - AQICN API      : AQI real-time hiện tại (kiểm tra / validate)
  - Open-Meteo     : Khí tượng lịch sử miễn phí (nhiệt độ, độ ẩm, gió, mưa)

Cài thư viện:
    pip install requests pandas openmeteo-requests requests-cache retry-requests tqdm

Output:
    data/raw/openaq_<city>.csv
    data/raw/weather_<city>.csv
    data/processed/merged_<city>.csv
    data/processed/all_cities.csv   <-- dùng để train model
"""

import requests
import pandas as pd
import time
import os
from datetime import datetime
from tqdm import tqdm

try:
    import openmeteo_requests
    import requests_cache
    from retry_requests import retry
    OPENMETEO_OK = True
except ImportError:
    OPENMETEO_OK = False
    print("⚠️  Chưa có openmeteo. Chạy: pip install openmeteo-requests requests-cache retry-requests")

# ============================================================
# CẤU HÌNH
# ============================================================
AQICN_TOKEN = "373f6f468b8915a84a9a85ff5d0d81debefd0cfa"
START_DATE  = "2020-01-01"
END_DATE    = datetime.today().strftime("%Y-%m-%d")

# OpenAQ location IDs — chạy find_openaq_vietnam_locations() để xem đầy đủ
CITIES = {
    "hanoi": {
        "label"      : "Hà Nội",
        "aqicn_feed" : "hanoi",
        "openaq_ids" : [240480, 240481, 228771],
        "lat"        : 21.0245,
        "lon"        : 105.8412,
    },
    "hochiminh": {
        "label"      : "TP.HCM",
        "aqicn_feed" : "ho-chi-minh-city",
        "openaq_ids" : [228779, 476182, 240483],
        "lat"        : 10.7769,
        "lon"        : 106.7009,
    },
    "danang": {
        "label"      : "Đà Nẵng",
        "aqicn_feed" : "da-nang",
        "openaq_ids" : [228775, 240482],
        "lat"        : 16.0544,
        "lon"        : 108.2022,
    },
}

os.makedirs("data/raw",       exist_ok=True)
os.makedirs("data/processed", exist_ok=True)


# ============================================================
# BƯỚC 0: TÌM LOCATION IDs VIỆT NAM TRÊN OPENAQ
# Chạy hàm này 1 lần để xem tất cả trạm, rồi cập nhật CITIES ở trên
# ============================================================
def find_openaq_vietnam_locations():
    print("\n🔍 Tìm trạm đo Việt Nam trên OpenAQ...")
    url     = "https://api.openaq.org/v3/locations"
    params  = {"country": "VN", "limit": 100}
    headers = {"accept": "application/json"}

    r    = requests.get(url, params=params, headers=headers, timeout=15)
    data = r.json()

    if "results" not in data:
        print("  ❌", data)
        return

    print(f"  Tìm thấy {len(data['results'])} trạm:\n")
    for loc in data["results"]:
        lid    = loc.get("id")
        name   = loc.get("name", "")
        city   = loc.get("locality", "")
        params = [p["parameter"] for p in loc.get("parameters", [])]
        print(f"  ID={lid:8} | {city:20} | {name[:40]:40} | {params}")


# ============================================================
# BƯỚC 1: CRAWL LỊCH SỬ TỪ OPENAQ
# ============================================================
def crawl_openaq_location(location_id: int) -> pd.DataFrame:
    url     = f"https://api.openaq.org/v3/locations/{location_id}/measurements"
    headers = {"accept": "application/json"}
    records = []
    page    = 1

    while True:
        params = {
            "date_from": START_DATE + "T00:00:00Z",
            "date_to"  : END_DATE   + "T23:59:59Z",
            "limit"    : 1000,
            "page"     : page,
        }
        try:
            r = requests.get(url, params=params, headers=headers, timeout=20)
            if r.status_code != 200:
                break
            data    = r.json()
            results = data.get("results", [])
            if not results:
                break
            for item in results:
                records.append({
                    "datetime" : item["period"]["datetimeFrom"]["utc"],
                    "parameter": item["parameter"]["name"].lower(),
                    "value"    : item["value"],
                })
            if len(results) < 1000:
                break
            page += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"    ⚠️  trang {page}: {e}")
            break

    if not records:
        return pd.DataFrame()

    df             = pd.DataFrame(records)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def crawl_openaq_city(city_key: str, cfg: dict) -> pd.DataFrame:
    print(f"\n📡 OpenAQ — {cfg['label']}")
    frames = []

    for loc_id in cfg["openaq_ids"]:
        print(f"  → Location {loc_id} ...", end=" ", flush=True)
        df = crawl_openaq_location(loc_id)
        if df.empty:
            print("không có data")
        else:
            print(f"{len(df):,} records")
            frames.append(df)
        time.sleep(0.5)

    if not frames:
        print(f"  ❌ Không lấy được data cho {cfg['label']}")
        return pd.DataFrame()

    df_all         = pd.concat(frames, ignore_index=True)
    df_all["hour"] = df_all["datetime"].dt.floor("h")

    # Pivot: mỗi pollutant thành 1 cột
    df_pivot = (df_all
                .groupby(["hour", "parameter"])["value"]
                .mean()
                .unstack("parameter")
                .reset_index()
                .rename(columns={"hour": "datetime"}))
    df_pivot.columns.name = None
    df_pivot["city"]      = cfg["label"]

    # Đổi tên cột chuẩn
    rename = {"pm2.5": "pm25", "pm 25": "pm25"}
    df_pivot = df_pivot.rename(columns={c: rename.get(c, c) for c in df_pivot.columns})

    path = f"data/raw/openaq_{city_key}.csv"
    df_pivot.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  💾 {path} | {len(df_pivot):,} giờ | cột: {list(df_pivot.columns)}")
    return df_pivot


# ============================================================
# BƯỚC 1B: AQICN – kiểm tra kết nối & AQI hiện tại
# ============================================================
def check_aqicn(cfg: dict):
    url = f"https://api.waqi.info/feed/{cfg['aqicn_feed']}/?token={AQICN_TOKEN}"
    try:
        d = requests.get(url, timeout=10).json()
        if d.get("status") == "ok":
            info = d["data"]
            iaqi = info.get("iaqi", {})
            print(f"  ✅ {cfg['label']:8} | AQI={info['aqi']} | "
                  f"PM2.5={iaqi.get('pm25',{}).get('v','n/a')} | "
                  f"Trạm: {info['city']['name']}")
        else:
            print(f"  ❌ {cfg['label']}: {d.get('data')}")
    except Exception as e:
        print(f"  ❌ {cfg['label']}: {e}")


# ============================================================
# BƯỚC 2: CRAWL KHÍ TƯỢNG TỪ OPEN-METEO
# ============================================================
def crawl_weather(city_key: str, cfg: dict) -> pd.DataFrame:
    if not OPENMETEO_OK:
        return pd.DataFrame()

    print(f"\n🌤  Open-Meteo — {cfg['label']}")

    cache   = requests_cache.CachedSession(".weather_cache", expire_after=-1)
    session = retry(cache, retries=5, backoff_factor=0.3)
    om      = openmeteo_requests.Client(session=session)

    params = {
        "latitude"  : cfg["lat"],
        "longitude" : cfg["lon"],
        "start_date": START_DATE,
        "end_date"  : END_DATE,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "wind_direction_10m",
            "precipitation",
            "surface_pressure",
            "cloud_cover",
        ],
        "timezone": "Asia/Ho_Chi_Minh"
    }

    try:
        resp = om.weather_api("https://archive-api.open-meteo.com/v1/archive", params=params)[0]
        hr   = resp.Hourly()
        n    = hr.Variables(0).ValuesAsNumpy().shape[0]

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

    except Exception as e:
        print(f"  ❌ Lỗi Open-Meteo: {e}")
        return pd.DataFrame()


# ============================================================
# BƯỚC 3: MERGE + FEATURE ENGINEERING
# ============================================================
def merge_and_fe(city_key: str, df_aqi: pd.DataFrame, df_w: pd.DataFrame) -> pd.DataFrame:
    label              = CITIES[city_key]["label"]
    df_aqi["datetime"] = pd.to_datetime(df_aqi["datetime"])

    if not df_w.empty:
        df_w["datetime"] = pd.to_datetime(df_w["datetime"])
        df = pd.merge(df_aqi,
                      df_w.drop(columns=["city"], errors="ignore"),
                      on="datetime", how="left")
    else:
        df = df_aqi.copy()

    df["city"] = label
    df = df.sort_values("datetime").reset_index(drop=True)

    # Thời gian
    df["year"]        = df["datetime"].dt.year
    df["month"]       = df["datetime"].dt.month
    df["day"]         = df["datetime"].dt.day
    df["hour"]        = df["datetime"].dt.hour
    df["day_of_week"] = df["datetime"].dt.dayofweek
    df["is_weekend"]  = df["day_of_week"].isin([5, 6]).astype(int)

    # Mùa
    def season(month, city):
        if city == "Hà Nội":
            if month in [12, 1, 2]:     return "Đông"
            elif month in [3, 4]:       return "Xuân"
            elif month in [5, 6, 7, 8]: return "Hạ"
            else:                       return "Thu"
        return "Khô" if month in [11, 12, 1, 2, 3, 4] else "Mưa"

    df["season"] = df.apply(lambda r: season(r["month"], r["city"]), axis=1)

    # Lag + Rolling cho PM2.5
    if "pm25" in df.columns:
        for lag in [1, 3, 6, 12, 24]:
            df[f"pm25_lag_{lag}h"] = df["pm25"].shift(lag)
        df["pm25_roll_6h"]  = df["pm25"].rolling(6,  min_periods=1).mean()
        df["pm25_roll_24h"] = df["pm25"].rolling(24, min_periods=1).mean()
        df["pm25_roll_72h"] = df["pm25"].rolling(72, min_periods=1).mean()

        def aqi_cat(v):
            if pd.isna(v): return None
            v = float(v)
            if v <= 50:    return "Tốt"
            elif v <= 100: return "Trung bình"
            elif v <= 150: return "Kém (nhạy cảm)"
            elif v <= 200: return "Xấu"
            elif v <= 300: return "Rất xấu"
            else:          return "Nguy hại"
        df["aqi_category"] = df["pm25"].apply(aqi_cat)

    return df


def merge_all(aqi_dfs: dict, weather_dfs: dict) -> pd.DataFrame:
    print("\n── BƯỚC 3: Merge & Feature Engineering ──")
    merged = []
    for ck in CITIES:
        if ck not in aqi_dfs or aqi_dfs[ck].empty:
            continue
        df   = merge_and_fe(ck, aqi_dfs[ck], weather_dfs.get(ck, pd.DataFrame()))
        path = f"data/processed/merged_{ck}.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  💾 {path} | {len(df):,} dòng | {len(df.columns)} cột")
        merged.append(df)

    if not merged:
        return pd.DataFrame()

    df_all = pd.concat(merged, ignore_index=True)
    df_all.to_csv("data/processed/all_cities.csv", index=False, encoding="utf-8-sig")
    print(f"\n🎉 all_cities.csv: {len(df_all):,} dòng")
    print(f"   Phân bố: {df_all['city'].value_counts().to_dict()}")
    print(f"   Cột: {list(df_all.columns)}")
    return df_all


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🇻🇳 CRAWL DỮ LIỆU AQI VIỆT NAM")
    print(f"   Thành phố : Hà Nội, TP.HCM, Đà Nẵng")
    print(f"   Giai đoạn : {START_DATE} → {END_DATE}")
    print("=" * 60)

    # ── Tuỳ chọn: xem danh sách trạm VN để cập nhật openaq_ids ──
    find_openaq_vietnam_locations()

    # ── Kiểm tra AQICN ──
    print("\n── Kiểm tra AQICN real-time ──")
    for cfg in CITIES.values():
        check_aqicn(cfg)

    # ── Crawl OpenAQ ──
    print("\n── BƯỚC 1: Crawl lịch sử OpenAQ ──")
    aqi_dfs = {}
    for ck, cfg in CITIES.items():
        df = crawl_openaq_city(ck, cfg)
        if not df.empty:
            aqi_dfs[ck] = df
        time.sleep(1)

    # ── Crawl Open-Meteo ──
    print("\n── BƯỚC 2: Crawl khí tượng Open-Meteo ──")
    weather_dfs = {}
    for ck, cfg in CITIES.items():
        df = crawl_weather(ck, cfg)
        if not df.empty:
            weather_dfs[ck] = df

    # ── Merge ──
    df_final = merge_all(aqi_dfs, weather_dfs)

    print("\n" + "=" * 60)
    if not df_final.empty:
        print("✅ XONG! Dùng: data/processed/all_cities.csv để train model")
    else:
        print("⚠️  Chưa lấy được data từ OpenAQ.")
        print("   Gợi ý: bỏ comment dòng find_openaq_vietnam_locations()")
        print("   để xem đúng location IDs rồi cập nhật lại biến CITIES")