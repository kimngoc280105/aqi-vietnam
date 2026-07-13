# ĐỒ ÁN MÔN HỌC MÁY
> Nguồn gốc: `ml-project.pdf` — đọc và tổng hợp lại để tham khảo nhanh

---

## 📌 TỔNG QUAN

**Tên đồ án:** Xây dựng và Triển khai Hệ thống Học máy Ứng dụng

**Triết lý:** Thu hẹp khoảng cách giữa lý thuyết học thuật và nhu cầu thực tiễn tại Việt Nam.

Mỗi nhóm sinh viên thực hiện hành trình đầy đủ:
- Xác định vấn đề cuộc sống có ý nghĩa
- Thu thập & xử lý dữ liệu với ngữ cảnh Việt Nam
- Xây dựng mô hình thông minh
- Triển khai thành sản phẩm phần mềm có ứng dụng thực tiễn

**Lĩnh vực:** Không giới hạn nội dung nhưng **bắt buộc phải có ngữ cảnh Việt Nam**.

---

## 🎯 MỤC TIÊU ĐỒ ÁN

Sau khi hoàn thành, sinh viên có khả năng:

| # | Kỹ năng | Mô tả |
|---|---------|-------|
| 1 | **End-to-End Pipeline** | Thành thạo từ ý tưởng → triển khai sản phẩm |
| 2 | **Bài toán thực tiễn VN** | Xử lý vấn đề đặc thù: ngôn ngữ, kinh tế, văn hóa, xã hội Việt Nam |
| 3 | **Dữ liệu đa phương tiện** | Kinh nghiệm với văn bản, hình ảnh, âm thanh (phi cấu trúc) |
| 4 | **Tư duy hệ thống** | Tích hợp API, hiểu mô hình là một phần trong hệ thống lớn hơn |
| 5 | **Kỹ năng mềm** | Làm việc nhóm, quản lý dự án, trình bày & bảo vệ sản phẩm |

---

## 🔄 QUY TRÌNH THỰC HIỆN (7 Bước)

> **Bắt buộc** ghi lại rõ ràng tất cả các bước trong báo cáo.

### Bước 1: Xác định và Phân tích Vấn đề (Problem Definition)
- Mô tả bài toán, tính cấp thiết và ý nghĩa trong bối cảnh Việt Nam

### Bước 2: Thu thập và Chuẩn bị Dữ liệu (Data Acquisition & Preparation)
- Trình bày chi tiết nguồn và phương pháp thu thập dữ liệu (scraping, API, tự tạo)
- Mô tả quy trình gán nhãn (nếu có)

### Bước 3: Tiền xử lý và Phân tích Khám phá (Preprocessing & EDA)
- Làm sạch, xử lý dữ liệu đặc thù
- Trực quan hóa để tìm ra các thông tin và đặc điểm nổi bật của dữ liệu

### Bước 4: Lựa chọn và Huấn luyện Mô hình (Model Selection & Training)
- Thử nghiệm và so sánh **ít nhất 3 mô hình** phù hợp
- Lý giải sự lựa chọn
- Trình bày quá trình huấn luyện và các thông số

### Bước 5: Đánh giá và Tinh chỉnh Mô hình (Evaluation & Tuning)
- Sử dụng các độ đo phù hợp để đánh giá
- Phân tích kết quả, **ma trận nhầm lẫn (confusion matrix)**
- Tinh chỉnh tham số để tối ưu hiệu năng

### Bước 6: Xây dựng Giao diện Ứng dụng (Application Development)
- Đóng gói mô hình tối ưu
- Xây dựng **ứng dụng web** để người dùng tương tác với mô hình

### Bước 7: Triển khai và Demo Sản phẩm (Deployment & Demonstration)
- Triển khai ứng dụng lên **nền tảng cloud công khai** để demo sản phẩm

---

## 📦 MINH CHỨNG NỘP (5 hạng mục)

| # | Hạng mục | Mô tả |
|---|----------|-------|
| 1 | **Báo cáo Đồ án** (PDF) | Trình bày chi tiết, khoa học theo 7 bước trên |
| 2 | **Mã nguồn** (ZIP) | Tiền xử lý + huấn luyện mô hình + ứng dụng web |
| 3 | **Mô hình đã huấn luyện** (Saved Model) | File trọng số của mô hình tốt nhất (`.h5`, `.pt`, `.pkl`) |
| 4 | **Slide Bảo vệ** (PDF/PPTX) | Slide trình bày cho buổi bảo vệ cuối kỳ |
| 5 | **Đường dẫn Ứng dụng Web** (URL) | Link công khai đến ứng dụng đã triển khai |

---

## 📅 CÁC MỐC THỜI GIAN

| Tuần | Nội dung |
|------|----------|
| **Tuần 3** | Nộp đề cương sơ bộ (1–2 trang) |
| **Tuần 6** | Báo cáo tiến độ lần 1: Hoàn thành thu thập & tiền xử lý dữ liệu, trình bày kết quả EDA |
| **Tuần 10** | Báo cáo tiến độ lần 2: Kết quả huấn luyện & đánh giá các mô hình, đã chọn được mô hình tốt nhất |
| **Tuần báo cáo** | Hoàn thiện ứng dụng web, triển khai, viết báo cáo cuối kỳ và chuẩn bị slide. **Nộp toàn bộ sản phẩm.** |

---

## 📊 TIÊU CHÍ ĐÁNH GIÁ

| Mục | Trọng số | Tiêu chí đánh giá |
|-----|----------|-------------------|
| **Báo cáo Khoa học & Chiều sâu Lý thuyết** | **30%** | Phân tích vấn đề sắc bén. Trình bày cơ sở lý thuyết rõ ràng. Quy trình các bước đầy đủ, thuyết phục logic. Phân tích kết quả sâu sắc. |
| **Sản phẩm Kỹ thuật (Code & Model)** | **30%** | Chất lượng code (sạch, hiệu quả, có chú thích). Mức độ đầu tư vào dữ liệu. Hiệu năng của mô hình cuối cùng so với các baseline. |
| **Ứng dụng Web** | **30%** | Ứng dụng mô hình + tích hợp với API hoạt động ổn định, giao diện thân thiện, giải quyết đúng bài toán. |
| **Điểm Sáng tạo** | **10%** | Tạo ra sản phẩm đột phá và có giá trị thực tiễn cao. |

---

## ⚖️ QUY ĐỊNH CHUNG

> **Tính liêm chính học thuật:** Mọi hành vi đạo văn, sao chép mã nguồn hoặc nội dung báo cáo mà không trích dẫn nguồn sẽ bị xử lý với hình thức **cao nhất**.

---

## 🏆 KHUYẾN KHÍCH

Các cá nhân/nhóm được khuyến khích:
- Tham gia các **cuộc thi học thuật**
- Viết **bài báo khoa học**

---

> **Ghi chú:** File này được tổng hợp từ `ml-project.pdf` (4 trang) trong thư mục dự án.
