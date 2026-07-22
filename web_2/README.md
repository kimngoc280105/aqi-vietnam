# Vietnam PM2.5 24-hour Forecast Web

Webapp giữ nguyên giao diện và các luồng chức năng của bản dự báo `t+24`, sử dụng mô hình XGBoost Direct Multi-Horizon và bổ sung bộ chọn mốc dự báo từ `t+1` đến `t+24` tại Hà Nội, TP.HCM và Đà Nẵng.

## Chạy local

Từ thư mục gốc dự án:

```powershell
cd web_2\frontend
npm ci
npm run build
cd ..
python -m pip install -r requirements-runtime.txt
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8001
```

Mở `http://127.0.0.1:8001`.

## API chính

- `GET /api/health`: trạng thái API, model và frontend.
- `GET /api/cities`: quan trắc gần nhất của ba thành phố.
- `GET /api/history/{city}`: chuỗi PM2.5 lịch sử để hiển thị.
- `POST /api/forecast`: trả toàn bộ 24 mốc dự báo.
- `POST /api/predict`: trả mốc dự báo được chọn qua trường `horizon` từ 1 đến 24.
- `POST /api/activity-plan`: lập kế hoạch hoạt động theo horizon và khoảng conformal tương ứng.
- `GET /api/model`: kết quả so sánh XGBoost, LSTM và SARIMAX.

## Docker

Build từ thư mục gốc dự án để Docker nhận đủ model và dữ liệu:

```powershell
docker build -f web_2/Dockerfile -t aqi-vietnam-web .
docker run --rm -p 8000:8000 aqi-vietnam-web
```

Mở `http://127.0.0.1:8000`. Cùng Dockerfile này có thể dùng trên Render với root directory là thư mục gốc dự án.
