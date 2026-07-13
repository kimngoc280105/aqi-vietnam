# ✅ CHECKLIST TIẾN ĐỘ ĐỒ ÁN
> Cập nhật: 2026-07-13 — Đối chiếu yêu cầu `ml-project.pdf` với thực tế bài làm

---

## 📋 QUY TRÌNH 7 BƯỚC

### ✅ Bước 1: Xác định và Phân tích Vấn đề
| Tiêu chí | Trạng thái | Bằng chứng |
|----------|-----------|------------|
| Mô tả bài toán rõ ràng | ✅ Hoàn thành | `main (2).tex` §1: Giới thiệu bài toán PM2.5, tính cấp thiết với người bệnh hô hấp |
| Bối cảnh Việt Nam | ✅ Hoàn thành | 3 thành phố: Hà Nội, TP.HCM, Đà Nẵng; phân tích đốt rơm rạ, gió mùa |
| Lý giải lựa chọn Target (PM2.5 thay vì AQI) | ✅ Xuất sắc | Có phần "Target Pivot" với 3 lý do kỹ thuật rõ ràng |

---

### ✅ Bước 2: Thu thập và Chuẩn bị Dữ liệu
| Tiêu chí | Trạng thái | Bằng chứng |
|----------|-----------|------------|
| Nguồn dữ liệu rõ ràng | ✅ Hoàn thành | Open-Meteo/CAMS, Open-Meteo Weather, OpenStreetMap/Overpass |
| Phương pháp thu thập | ✅ Hoàn thành | `main.py` crawl API; `crawl_manifest.json` ghi lại metadata |
| Dữ liệu đã thu thập | ✅ Hoàn thành | `data/raw/`: 6 file CSV ~2.5MB/file cho 3 thành phố (AQI + Weather) |
| Quy trình gán nhãn | ✅ Có mô tả | Ánh xạ PM2.5 → 6 nhóm rủi ro sau xử lý (hậu xử lý, không phải gán nhãn thủ công) |

---

### ✅ Bước 3: Tiền xử lý và EDA
| Tiêu chí | Trạng thái | Bằng chứng |
|----------|-----------|------------|
| Làm sạch dữ liệu | ✅ Hoàn thành | `models/0_data_preprocessing.ipynb`; nội suy tuyến tính, xử lý O3 âm, loại multicollinearity |
| Xử lý missing values | ✅ Hoàn thành | `<0.08%` missing, về 0% sau xử lý |
| Xử lý outliers | ✅ Hoàn thành | Giữ lại có lý do (Tukey's Fence, 3×IQR) |
| Feature Engineering | ✅ Hoàn thành | Lag 1h/3h/6h/12h/24h, rolling 6h/24h/72h, One-Hot encoding |
| EDA / Trực quan hóa | ✅ Hoàn thành | `figures/`: 14 biểu đồ (phân phối AQI, heatmap, boxplot, feature distributions, v.v.) |
| Báo cáo EDA trong notebook | ✅ Hoàn thành | `models/0_data_preprocessing.ipynb` (42KB) |

---

### ✅ Bước 4: Lựa chọn và Huấn luyện Mô hình
| Tiêu chí | Trạng thái | Bằng chứng |
|----------|-----------|------------|
| **≥ 3 mô hình** | ✅ Hoàn thành | SARIMAX + XGBoost + LSTM (đúng yêu cầu tối thiểu) |
| SARIMAX (Baseline) | ✅ Hoàn thành | `models/1_baseline_sarimax.ipynb` (250KB) |
| XGBoost | ✅ Hoàn thành | `models/2_xgboost_tuning.ipynb` (86KB) + Random Search + Early Stopping |
| LSTM (Deep Learning) | ✅ Hoàn thành | `models/3_lstm_deeplearning.ipynb` (148KB) + 2 LSTM layers + Dropout |
| Lý giải lựa chọn mô hình | ✅ Hoàn thành | `models/4_original_model_selection.ipynb`; chọn bằng Validation RMSE |
| Trình bày siêu tham số | ✅ Xuất sắc | Bảng chi tiết trong báo cáo (Section 4) |

---

### ✅ Bước 5: Đánh giá và Tinh chỉnh Mô hình
| Tiêu chí | Trạng thái | Bằng chứng |
|----------|-----------|------------|
| Độ đo phù hợp (RMSE, MAE) | ✅ Hoàn thành | RMSE và MAE cho cả 3 mô hình trên tập Test |
| **Confusion Matrix** | ✅ Hoàn thành | `models/results/best_model_confusion_matrix.csv` + hình `figures/best_model_confusion_matrix.png` |
| Phân tích kết quả sâu | ✅ Xuất sắc | Phân tích overfitting/underfitting, top error cases, error by band, feature importance |
| Tinh chỉnh tham số | ✅ Hoàn thành | Randomized Search + Early Stopping + ReduceLROnPlateau |
| So sánh 3 mô hình | ✅ Hoàn thành | `models/results/model_comparison.csv`, bảng báo cáo Section 5 |
| Learning Curves | ✅ Hoàn thành | LSTM (epoch) + XGBoost (boosting round); SARIMAX không áp dụng (có giải thích) |
| Confidence Intervals | ✅ Bonus | `bootstrap_ci.csv` + conformal prediction interval 90% |

---

### ✅ Bước 6: Xây dựng Giao diện Ứng dụng Web
| Tiêu chí | Trạng thái | Bằng chứng |
|----------|-----------|------------|
| Đóng gói mô hình | ✅ Hoàn thành | `models/pm25_24h_best.joblib` (306KB) + metadata JSON |
| Ứng dụng web | ✅ Hoàn thành | React/Vite frontend (`frontend/src/App.jsx` ~83KB) |
| Backend API | ✅ Hoàn thành | FastAPI (`backend/api.py`) với 8+ endpoints |
| Người dùng tương tác được | ✅ Hoàn thành | Dự báo tự động, nhập tay, preset kịch bản, Activity Planner |
| Tích hợp API ngoài | ✅ Xuất sắc | Open-Meteo + CAMS live data trong `backend/live_data.py` |

---

### ⚠️ Bước 7: Triển khai lên Cloud
| Tiêu chí | Trạng thái | Bằng chứng |
|----------|-----------|------------|
| Dockerfile | ✅ Hoàn thành | `Dockerfile` (47 dòng, multi-stage build, Node + Python) |
| render.yaml | ✅ Hoàn thành | `render.yaml` với health check `/api/health` |
| **URL công khai** | ⚠️ **CHƯA XÁC NHẬN** | Có config Render nhưng chưa thấy URL deploy thực tế |

> **⚠️ CẦN KIỂM TRA:** Ứng dụng đã được deploy lên Render hay chưa? Cần URL công khai để nộp.

---

## 📦 MINH CHỨNG NỘP (5 hạng mục)

| # | Hạng mục | Trạng thái | Ghi chú |
|---|----------|-----------|---------|
| 1 | **Báo cáo PDF** | ✅ Có | `main (2).pdf` (1.7MB, 531 dòng LaTeX đầy đủ) |
| 2 | **Mã nguồn ZIP** | ⚠️ Chưa đóng gói | Có đầy đủ code nhưng chưa nén thành file `.zip` để nộp |
| 3 | **Saved Model** | ✅ Có | `models/pm25_24h_best.joblib` (306KB) |
| 4 | **Slide bảo vệ** | ❌ **CHƯA CÓ** | Không tìm thấy file `.pptx` hoặc slide PDF nào trong project |
| 5 | **URL deploy** | ⚠️ Chưa xác nhận | Config đã có (`render.yaml`), nhưng cần xác nhận URL thực |

---

## 📊 TÓM TẮT ĐÁNH GIÁ THEO TIÊU CHÍ CHẤM

| Tiêu chí | Trọng số | Ước tính | Nhận xét |
|----------|---------|---------|---------|
| **Báo cáo Khoa học** | 30% | ~26–28/30 | Rất tốt: 7 bước đầy đủ, phân tích sâu, bảng công thức toán học |
| **Code & Model** | 30% | ~26–28/30 | Rất tốt: code sạch, 3 mô hình, feature engineering chi tiết, conformal CI |
| **Ứng dụng Web** | 30% | ~27–29/30 | Rất tốt: React + FastAPI + live API; Activity Planner là điểm cộng |
| **Điểm Sáng tạo** | 10% | ~8–10/10 | Xuất sắc: conformal prediction, live data, multi-city, Activity Planner |

---

## 🚨 VIỆC CẦN LÀM NGAY

| Ưu tiên | Việc cần làm |
|---------|-------------|
| 🔴 **Cao nhất** | **Làm Slide bảo vệ** (chưa có — thiếu minh chứng bắt buộc) |
| 🔴 **Cao nhất** | **Deploy lên Render** và lấy URL công khai (hoặc xác nhận đã deploy) |
| 🟡 **Trung bình** | Đóng gói mã nguồn thành file `.zip` để nộp |
| 🟢 **Thấp** | Kiểm tra lại báo cáo PDF có đủ figures (một số hình dẫn như `xgboost_feature_importance.png` chưa thấy trong `figures/`) |

---

> **Kết luận:** Bài làm **rất chắc chắn về kỹ thuật** (7/7 bước pipeline hoàn chỉnh, code chất lượng cao). Điểm yếu duy nhất là **thiếu Slide bảo vệ** và cần xác nhận deploy cloud. Hoàn thiện 2 việc đó là đủ điều kiện nộp đồ án.
