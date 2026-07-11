# Đề cương sơ bộ đồ án<br> Môn Nhập môn học máy
# Đề tài: Dự đoán chất lượng không khí Việt Nam và cảnh báo nguy cơ mắc bệnh hô hấp

Nhóm sinh viên: Nhóm 11

Danh sách thành viên:

| MSSV     | Họ và tên |
|---|---|
| 23120062 | Trần Kim Ngọc
| 23120063 | Nguyễn Thành Nguyên
| 23120084 | Nguyễn Mạnh Thắng
| 23120059 | Trần Đình Luân
| 23120064 | Nguyễn Thiện Nhân



## I. Giới thiệu đề tài

- Vấn đề thực tiễn và tính cấp thiết:
  - Ô nhiễm không khí đang là vấn đề nghiêm trọng tại các đô thị lớn như Hà Nội và
TP.HCM, ảnh hưởng trực tiếp đến sức khỏe hàng triệu người dân mỗi ngày. Chỉ số
AQI tại nhiều khu vực thường xuyên vượt ngưỡng an toàn, đặc biệt vào mùa khô. Tuy
nhiên, hiện nay người dân vẫn thiếu một công cụ dự đoán sớm và cảnh báo kịp thời
bằng tiếng Việt, phù hợp với đặc thù khí hậu và địa lý Việt Nam.
Yêu cầu đặt ra:
   - Cần có công cụ dự đoán nồng độ PM2.5 của các thành phố lớn tại Việt Nam trong
phạm vi 1-3 ngày tới dựa trên dữ liệu đã ghi nhận và tình hình khí tượng.
  - Xác định được mức độ ô nhiễm không khí đó có thể gây ra nguy cơ mắc bệnh
hô hấp ở mức độ nào, và nên khuyến cáo gì cho người dùng.


- Ý tưởng
  - Đề tài hướng đến việc thoả mãn các yêu cầu trên, qua việc xây dựng hệ thống học
máy có khả năng dự đoán nồng độ PM2.5 trong 1-3 ngày tới và tự động đưa ra cảnh báo
sức khỏe phù hợp với từng nhóm đối tượng, góp phần nâng cao ý thức bảo vệ sức
khỏe cộng đồng.

- Ý nghĩa
  - Hệ thống cung cấp cho người dân công cụ dự báo chất lượng không khí dễ tiếp cận,
giúp chủ động bảo vệ sức khỏe, đặc biệt với các nhóm dễ bị tổn thương như trẻ em,
người cao tuổi và người có bệnh nền.


## II. Dữ liệu dự kiến

Nguồn thu thập:
- AQICN (aqicn.org): API miễn phí, cung cấp dữ liệu lịch sử AQI của nhiều trạm đo
tại Việt Nam (Hà Nội, TP.HCM, Đà Nẵng, Huế...)
- Open-Meteo / Visual Crossing: Dữ liệu khí tượng bổ sung (nhiệt độ, độ ẩm, tốc độ
gió, lượng mưa)

Đặc trưng dự kiến: PM2.5, PM10, CO, NO₂, SO₂, O₃, nhiệt độ, độ ẩm, hướng gió, giờ trong
ngày, ngày trong tuần, mùa, giá trị AQI của những thời điểm trước (1h, 3h, 6h,...)

Quy mô: Dữ liệu theo giờ, trải dài nhiều năm, nhiều trạm đo tại các tỉnh thành lớn


## III. Hướng tiếp cận

Nhóm giải quyết bài toán:
- Hồi quy: Dự đoán nồng độ PM2.5 (µg/m³) cụ thể trong 24–48 giờ tới


PM2.5 được chọn làm biến mục tiêu thay vì chỉ số AQI tổng hợp dựa trên 3 lý do chính:
- Hiệu ứng che khuất (masking effect) của AQI: do AQI lấy giá trị lớn nhất trong các chỉ số phụ (PM2.5, PM10, O₃, NO₂, SO₂, CO), có những thời điểm PM2.5 tăng đột biến nhưng AQI gần như không đổi vì O₃ giảm mạnh, dẫn đến cảnh báo sức khỏe sai lệch.
- Chuỗi PM2.5 có tính tự tương quan và chu kỳ rõ ràng hơn AQI (vốn bị làm mượt quá mức bởi trung bình trượt 24 giờ, tạo ảo giác dễ dự đoán nhưng vô dụng trong thực tế).
- PM2.5 là chất ô nhiễm có tác động trực tiếp và nghiêm trọng nhất đến hệ hô hấp tại các đô thị Việt Nam, nên dự báo trực tiếp nồng độ PM2.5 mang lại giá trị cảnh báo sức khỏe theo thời gian thực cao hơn so với AQI.


## IV. Sản phẩm dự kiến

Ứng dụng web cho phép người dùng với các chức năng:
- Chọn địa điểm (Hà Nội, TP.HCM, Đà Nẵng...) hoặc nhập địa chỉ cụ thể ở các thành
phố lớn để xem PM2.5 hiện tại và dự đoán.
- Xem biểu đồ xu hướng ô nhiễm theo giờ / ngày / tuần
- Nhận cảnh báo được cá nhân hoá, phân loại nguy cơ dựa trên thông tin thể trạng được
người dùng cung cấp và khuyến nghị sức khoẻ phù hợp.