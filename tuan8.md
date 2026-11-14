# Kế hoạch & Phân chia công việc - Tuần 8
## Chủ đề: Làm sạch Dữ liệu Ẩn, Khóa Snapshot Duyệt & Triển khai Demo Server

- **Giai đoạn**: `Phase 2: Core product MVP`
- **Mục tiêu tuần (Sprint Goal)**: Khóa snapshot đã duyệt không thể chỉnh sửa (BE-09), ghi nhật ký kiểm toán audit log an toàn (BE-12), giao diện xác nhận hoàn tất duyệt và cảnh báo sót (FE-10), loại bỏ hoàn toàn metadata, attachments, hidden layers, annotations (RED-05), ghi tệp PDF sạch không chứa lịch sử incremental (RED-06), đóng gói artifact xuất khẩu bất biến kèm checksum (RED-07), đóng gói và triển khai ứng dụng lên demo server với HTTPS và Docker (OPS-02).

---

## Bảng phân công công việc chi tiết trong tuần (Sprint Backlog)

| Mã Task | Tên công việc | Người thực hiện | Vai trò | Người Review | Người phối hợp | Độ ưu tiên | Quy mô | Tiêu chuẩn nghiệm thu (Acceptance Criteria) |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **BE-09** | Khóa snapshot đã duyệt | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | - | `P0` | `L` | Chặn khi trang phân tích lỗi/chưa duyệt hoặc có candidate mới chưa xử lý; sửa review làm snapshot xuất cũ mất hiệu lực; lưu revision bất biến |
| **BE-12** | Nhật ký xử lý | **Nguyễn Quang Anh** | `CS1` | CS2 | SE2 | `P1` | `M` | Không ghi raw PII, nội dung OCR, mật khẩu hoặc token vào log/báo cáo mặc định |
| **FE-10** | Xác nhận duyệt tài liệu | **Đỗ Minh Tấn** | `SE1` | SE2 | - | `P1` | `M` | Không xác nhận bản cũ khi vùng thay đổi hoặc có candidate mới; chỉ dẫn trở lại duyệt; trang chưa duyệt/lỗi và giới hạn chữ viết tay hiển thị rõ |
| **RED-05** | Làm sạch dữ liệu ẩn | **Nguyễn Quang Anh** | `CS1` | CS2 | SE4 | `P0` | `L` | Nội dung phải loại bỏ không còn trong artifact; cấu trúc không xử lý được bị từ chối rõ |
| **RED-06** | Ghi PDF sạch và bảo toàn nội dung | **Dương Minh Đức** | `SE4` | CS2 | - | `P0` | `L` | File mở được; không chứa bản gốc đính kèm/object cũ cần loại; page geometry và phần giữ lại được kiểm tra |
| **RED-07** | Artifact export bất biến | **Dương Minh Đức** | `SE4` | CS2 | - | `P1` | `M` | Artifact gắn đúng snapshot; lỗi giữa chừng không để file tải chính thức; đầu vào không bị sửa |
| **OPS-02** | Triển khai demo có đăng nhập | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | SE1 | `P1` | `M` | Demo truy cập HTTPS; file không public; deployment dùng model version cố định |

---

## Phân phối công việc cụ thể cho 7 thành viên trong tuần

### SE2: Nguyễn Đinh Phú Vinh (Backend & System Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **BE-09** (Khóa snapshot đã duyệt), **OPS-02** (Triển khai demo có đăng nhập)
- **Trách nhiệm Review/Nghiệm thu**: **FE-10**
- **Phối hợp liên module**: **BE-12**
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng module khóa snapshot (BE-09); thiết lập hạ tầng triển khai demo server HTTPS và Docker Compose (OPS-02).

### SE1: Đỗ Minh Tấn (Frontend - ICT)

- **Công việc chính phụ trách (Owner)**: **FE-10** (Xác nhận duyệt tài liệu)
- **Phối hợp liên module**: **OPS-02**
- **Chi tiết hoạt động trong tuần**: Chủ trì phát triển giao diện xác nhận hoàn tất duyệt tài liệu, hiển thị cảnh báo và chốt revision (FE-10).

### SE4: Dương Minh Đức (Data & PDF Engine - ICT)

- **Công việc chính phụ trách (Owner)**: **RED-06** (Ghi PDF sạch và bảo toàn nội dung), **RED-07** (Artifact export bất biến)
- **Phối hợp liên module**: **RED-05**
- **Chi tiết hoạt động trong tuần**: Chủ trì phát triển module ghi PDF sạch (RED-06) và đóng gói artifact xuất khẩu kèm checksum bất biến (RED-07). Hỗ trợ CS1 làm sạch dữ liệu ẩn trong RED-05.

### SE3: Nguyễn Tuấn Vinh (Document / OCR - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Chi tiết hoạt động trong tuần**: Phối hợp với SE4 kiểm tra độ toàn vẹn hình học trang PDF sau khi ghi sạch để đảm bảo không bị méo lệch tỷ lệ.

### CS2: Hoàng Thị Kiều Ly (Security Verification - CS)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **BE-12**, **RED-05**, **RED-06**, **RED-07**
- **Chi tiết hoạt động trong tuần**: Thử nghiệm tấn công khôi phục dữ liệu trên các file PDF tạo ra bởi RED-05/06 để chuẩn bị cho verification chính thức ở tuần 9.

### CS1: Nguyễn Quang Anh (Security Engineering - CS)

- **Công việc chính phụ trách (Owner)**: **BE-12** (Nhật ký xử lý), **RED-05** (Làm sạch dữ liệu ẩn)
- **Trách nhiệm Review/Nghiệm thu**: **BE-09**, **OPS-02**
- **Chi tiết hoạt động trong tuần**: Chủ trì phát triển module loại bỏ dữ liệu ẩn (RED-05); xây dựng hệ thống nhật ký kiểm toán không leak raw PII (BE-12).

### ML1: Nguyễn Đăng Đạt (Machine Learning Lead - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Chi tiết hoạt động trong tuần**: Hoàn thiện mã nguồn đánh giá mô hình, chuẩn bị sẵn sàng tập test cố định cho báo cáo ML-07 ở tuần 10.

---

## Tiêu chuẩn nghiệm thu tuần (Definition of Done - DoD)

- [ ] BE-09 khóa cứng snapshot của revision đã duyệt; bất kỳ chỉnh sửa nào sau đó đều tạo revision mới và hủy snapshot cũ.
- [ ] BE-12 ghi nhật ký đầy đủ (ai, làm gì, khi nào, mã tài liệu, kết quả) nhưng tuyệt đối không ghi dữ liệu PII thô hay token.
- [ ] FE-10 cung cấp màn hình tóm tắt trước khi xuất, cảnh báo các trang chưa duyệt hoặc các vùng chữ viết tay có thể còn sót.
- [ ] RED-05 làm sạch 100% metadata nhạy cảm, forms, JavaScript nhúng, annotation ghi chú và các object đính kèm trong PDF.
- [ ] RED-06 tái cấu trúc file PDF mới hoàn toàn (linearized/clean PDF), loại bỏ cây lịch sử cập nhật cũ (incremental update table).
- [ ] RED-07 xuất bản file artifact với mã băm SHA-256 cố định, ghi tệp qua thư mục tạm và chỉ kích hoạt khi hoàn thành trọn vẹn.
- [ ] OPS-02 dựng hoàn chỉnh hệ thống trên demo server: chạy qua Docker Compose, cấu hình Nginx HTTPS, bảo mật cổng lưu trữ.

---

## Rủi ro kỹ thuật & Điều kiện tiên quyết (Dependencies & Risks)

- **Các phụ thuộc cần hoàn thành từ tuần trước**: BE-02, BE-05, BE-06, BE-08, CORE-03, DATA-05, FE-08, FE-09, OPS-01, RED-03, RED-04.
- **Nguyên tắc an toàn**: Luôn tuân thủ nguyên tắc không can thiệp đè lên file gốc, đảm bảo tính bất biến của dữ liệu và kiểm tra chặt chẽ trước khi xuất bản.
