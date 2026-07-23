# Vietnam PM2.5 Forecast

Hệ thống dự báo trực tiếp nồng độ PM2.5 theo từng giờ từ `t+1` đến `t+24` cho ba điểm lưới đại diện gần trung tâm Hà Nội, TP.HCM và Đà Nẵng. Quy trình chính của dự án là:

`crawl dữ liệu -> EDA/tiền xử lý -> huấn luyện 3 mô hình -> chọn model -> local webapp -> cloud`

> Dữ liệu ô nhiễm là dữ liệu lưới CAMS Global lấy qua Open-Meteo, không phải số đo trạm mặt đất và không đại diện chi tiết theo quận/huyện.

## Kết quả hiện tại

| Hạng mục | Kết quả |
|---|---:|
| Mẫu supervised dùng để chia tập | 98.187 |
| Tỷ lệ chia theo thời gian | 70/15/15, purge gap 24 giờ |
| Mô hình so sánh | SARIMAX, XGBoost, LSTM |
| Mô hình được chọn | XGBoost Direct Multi-Horizon |
| Temporal-CV RMSE | 15,801 µg/m³ |
| Test mean-horizon RMSE | 14,013 µg/m³ |
| Test MAE | 8,911 µg/m³ |
| Test global R² | 0,665 |

Mô hình chỉ được chọn bằng Validation RMSE. Test không tham gia chọn mô hình hoặc siêu tham số.

## Pipeline dữ liệu và mô hình

Chạy EDA trước tại `code/notebook.ipynb`. Notebook này chỉ phân tích và trực quan hóa, không biến đổi dữ liệu cho model.

Sau đó chạy notebook đa chân trời theo đúng thứ tự:

1. `model/0_multihorizon_data_preparation.ipynb`: tạo 24 target đúng timestamp và temporal split.
2. `model/1_multihorizon_sarimax.ipynb`: huấn luyện SARIMAX đa chân trời.
3. `model/2_multihorizon_xgboost.ipynb`: huấn luyện 24 XGBoost trực tiếp.
4. `model/3_multihorizon_lstm.ipynb`: huấn luyện LSTM Sequence-to-Vector.
5. `model/4_multihorizon_model_selection.ipynb`: lựa chọn bằng năm khối Validation, phân tích model thắng và tạo figures cuối.

Thư mục `model_t24/` và `web_t24/` giữ phiên bản một chân trời để đối chiếu. Ứng dụng chính trong `web/` chỉ load saved artifact đa chân trời từ `model/` sau khi bước 5 hoàn tất; notebook model không phụ thuộc backend.

Để crawl lại snapshot cho ba thành phố trước bước tiền xử lý:

```powershell
python main.py
```

## Chạy webapp local

Yêu cầu Python 3.11+ và Node.js 20+.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r web/requirements-runtime.txt
cd web/frontend
npm ci
npm run build
cd ../..
cd web
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

Mở `http://localhost:8000`. API docs ở `http://localhost:8000/docs`.

Các endpoint chính:

- `GET /api/health`
- `GET /api/cities`
- `GET /api/history/{city}`
- `GET /api/model`
- `POST /api/forecast`
- `POST /api/predict`
- `POST /api/activity-plan`

## Kiểm tra frontend

    cd web/frontend
    npm run build

## Trải nghiệm web

- **Dự báo tự động:** web lấy snapshot gần nhất từ Open-Meteo/CAMS, cho chọn horizon 1--24 giờ, hiển thị dự báo điểm, khoảng conformal và so sánh ba thành phố.
- **Dự đoán nhập tay:** người dùng thay các chỉ số quan sát dễ hiểu; lag và rolling được backend lấy tự động từ profile lịch sử.
- **Activity Planner:** kết hợp dự báo điểm và khoảng conformal để so sánh thời điểm hoạt động; không phải khuyến cáo y khoa.

## Cloud

Repo có `web/Dockerfile` và `render.yaml` ở root. Render dùng repository root làm build context và Dockerfile trong thư mục `web`; một container phục vụ cả React build và FastAPI. Health check là `/api/health`.

Ứng dụng công khai: <https://aqi-vietnam-multihorizon.onrender.com>

```powershell
docker build -f web/Dockerfile -t aqi-vietnam .
docker run --rm -p 8000:8000 aqi-vietnam
```

## Cấu trúc

```text
code/             notebook EDA, phân tích PM2.5/AQI và utils
data/
  raw/            dữ liệu lấy từ API và manifest
  processed/      dữ liệu hợp nhất, làm sạch và runtime
figures/          hình đánh giá mô hình
model/            preprocessing đa target, 3 model, chọn model và saved artifact
web/
  backend/        FastAPI và inference service
  frontend/       React/Vite desktop webapp
  Dockerfile      image triển khai cloud
main.py           crawler Open-Meteo
requirements*.txt dependency local và phát triển
render.yaml       Render Blueprint dùng web/Dockerfile
```

## Giới hạn

- Mỗi thành phố chỉ có một điểm lưới CAMS độ phân giải khoảng 45 km.
- Hà Nội khó dự báo hơn đáng kể và có nhiều đỉnh PM2.5 đột ngột bị bỏ lỡ.
- Macro F1 theo dải tham chiếu còn thấp; đây vẫn là bài toán hồi quy PM2.5, không phải bộ phân loại AQI.
- Dải sức khỏe chỉ là ngưỡng tham chiếu PM2.5, không phải AQI 24 giờ chính thức.
