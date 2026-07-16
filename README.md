# Vietnam PM2.5 Forecast

Hệ thống dự báo trực tiếp nồng độ PM2.5 tại đúng `t + 24 giờ` cho ba điểm lưới đại diện gần trung tâm Hà Nội, TP.HCM và Đà Nẵng. Quy trình chính của dự án là:

`crawl dữ liệu -> EDA/tiền xử lý -> huấn luyện 3 mô hình -> chọn model -> local webapp -> cloud`

> Dữ liệu ô nhiễm là dữ liệu lưới CAMS Global lấy qua Open-Meteo, không phải số đo trạm mặt đất và không đại diện chi tiết theo quận/huyện.

## Kết quả hiện tại

| Hạng mục | Kết quả |
|---|---:|
| Mẫu supervised hợp lệ | 98.331 |
| Tỷ lệ chia theo thời gian | 70/15/15, purge gap 24 giờ |
| Mô hình so sánh | SARIMAX, XGBoost, LSTM |
| Mô hình được chọn | XGBoost 3.0.0 |
| Validation RMSE | 18,095 µg/m³ |
| Test RMSE | 15,957 µg/m³ |
| Test MAE | 10,232 µg/m³ |
| Test R² | 0,586 |
| Độ phủ conformal 90% trên Test | 92,7% |

Mô hình chỉ được chọn bằng Validation RMSE. Test không tham gia chọn mô hình hoặc siêu tham số.

## Pipeline dữ liệu và mô hình

Chạy EDA trước tại `code/notebook.ipynb`. Notebook này chỉ phân tích và trực quan hóa, không biến đổi dữ liệu cho model.

Sau đó chạy notebook model theo đúng thứ tự:

1. `model/0_data_preprocessing.ipynb`: làm sạch dữ liệu, nội suy theo từng thành phố, tạo lag/rolling/feature và lưu dữ liệu huấn luyện.
2. `model/1_baseline_sarimax.ipynb`: huấn luyện SARIMAX cho cả ba thành phố.
3. `model/2_xgboost_tuning.ipynb`: tinh chỉnh và huấn luyện XGBoost.
4. `model/3_lstm_deeplearning.ipynb`: huấn luyện LSTM với cửa sổ 48 giờ.
5. `model/4_original_model_selection.ipynb`: so sánh bằng Validation RMSE, phân tích lỗi và tạo `model/pm25_24h_best.joblib`.

Mỗi notebook model tự tạo target t+24, tự chia Train/Validation/Test và tự tính metric. Notebook model không import `web/backend`. Backend chỉ load saved model sau khi bước 5 hoàn tất.

Để crawl lại snapshot cho ba thành phố trước bước tiền xử lý:

```powershell
python main.py
```

## Chạy webapp local

Yêu cầu Python 3.11+ và Node.js 20+.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd web/frontend
npm ci
npm run build
cd ../..
cd web
uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

Mở `http://localhost:8000`. API docs ở `http://localhost:8000/docs`.

Các endpoint chính:

- `GET /api/health`
- `GET /api/cities`
- `GET /api/history/{city}`
- `GET /api/model`
- `GET /api/model-card`
- `POST /api/predict`
- `POST /api/scenarios`
- `POST /api/activity-plan`

## Kiểm tra frontend

    cd web/frontend
    npm run build

## Trải nghiệm web

- **Dự báo tự động:** web lấy snapshot gần nhất từ Open-Meteo/CAMS và trình bày PM2.5 hiện tại, dự báo t+24, khoảng 90% và so sánh ba thành phố như một bản tin thời tiết.
- **Dự đoán nhập tay:** người dùng thay các chỉ số ô nhiễm, thời tiết và lịch sử PM2.5 rồi chạy cùng model XGBoost để tạo kịch bản riêng.
- **Preset kịch bản:** có thể nạp dữ liệu hiện tại, mô phỏng ô nhiễm tăng hoặc gió thông thoáng; kết quả nhập tay được so trực tiếp với dự báo tự động.
- **Activity Planner:** kết hợp dự báo điểm và khoảng conformal để so sánh thời điểm hoạt động; không phải khuyến cáo y khoa.

## Cloud

Repo có `web/Dockerfile` và `render.yaml` ở root. Render dùng repository root làm build context và Dockerfile trong thư mục `web`; một container phục vụ cả React build và FastAPI. Health check là `/api/health`.

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
model/            preprocessing, 3 model, chọn model và saved artifact
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
