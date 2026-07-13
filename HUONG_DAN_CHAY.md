# 🚀 HƯỚNG DẪN CHẠY WEB LOCAL

## Yêu cầu
- Python 3.10+
- Node.js 20+

---

## ⚡ Lần đầu tiên (setup)

Mở PowerShell tại thư mục project, chạy lần lượt:

```powershell
# Bước 1: Tạo môi trường ảo Python
python -m venv .venv

# Bước 2: Cài Python packages
.venv\Scripts\pip install -r requirements.txt

# Bước 3: Build giao diện React
cd frontend
npm ci
npm run build
cd ..
```

> ✅ Bước 1–3 chỉ cần làm **một lần duy nhất**.

---

### ▶️ Bước 4 — Chạy server *(mỗi lần muốn dùng web)*

```powershell
.\run.ps1
```

> Script tự động mở trình duyệt và hiện link `http://localhost:8000` click được.

Hoặc chạy thủ công:
```powershell
.venv\Scripts\uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

---

### 🌐 Bước 5 — Mở trình duyệt

Truy cập: **`http://localhost:8000`**

API docs: **`http://localhost:8000/docs`**

---

### ⏹️ Tắt server

Nhấn **`Ctrl + C`** trong terminal.

---

## ❗ Lưu ý

- Warning `XGBoost older version` khi khởi động là **bình thường**, bỏ qua.
- Nếu port 8000 bị chiếm, đổi port: thêm `--port 8001` vào lệnh uvicorn.

# Tìm process đang dùng port 8000
netstat -ano | findstr :8000

# Kill theo PID (số cuối cùng trong kết quả trên)
taskkill /PID <số_pid> /F

