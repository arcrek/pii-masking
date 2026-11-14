# Kế hoạch & Phân chia công việc - Tuần 6
## Chủ đề: Tích hợp Model Serving, Hợp nhất Pipeline OCR/Native & Redaction Engine

- **Giai đoạn**: `Phase 2: Core product MVP`
- **Mục tiêu tuần (Sprint Goal)**: Đóng gói và triển khai suy luận mô hình NER trên server (ML-03), hợp nhất văn bản native và OCR cho trang mixed (OCR-09), ánh xạ thực thể phát hiện thành bounding box regions trên PDF (ML-08), thuật toán kết hợp ML và Regex luật bổ trợ (ML-06), hiển thị overlay vùng PII trực quan trên viewer (FE-06), danh sách và bộ lọc PII theo loại (FE-07), phát triển thuật toán xóa triệt để text/vector stream PDF (RED-03), xóa ảnh raster và lớp OCR ẩn (RED-04).

---

## Bảng phân công công việc chi tiết trong tuần (Sprint Backlog)

| Mã Task | Tên công việc | Người thực hiện | Vai trò | Người Review | Người phối hợp | Độ ưu tiên | Quy mô | Tiêu chuẩn nghiệm thu (Acceptance Criteria) |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **OCR-09** | Hợp nhất native và OCR | **Nguyễn Tuấn Vinh** | `SE3` | SE4 | - | `P1` | `L` | Không bỏ qua ảnh chỉ vì trang có text; một nội dung không nhân đôi do lớp OCR cũ |
| **ML-03** | Suy luận phát hiện PII | **Nguyễn Đinh Phú Vinh** | `SE2` | ML1 | SE4 | `P1` | `L` | Batch/empty/long text xử lý được; score không tự coi là probability; model load được ngoài Colab |
| **ML-08** | Ánh xạ entity thành vùng | **Nguyễn Tuấn Vinh** | `SE3` | SE1 | - | `P1` | `L` | Không chỉ tìm lần xuất hiện đầu tiên; đúng trang, đủ các dòng; lỗi mapping được báo, không âm thầm bỏ |
| **ML-06** | Kết hợp ML và luật | **Dương Minh Đức** | `SE4` | ML1 | SE2 | `P1` | `L` | So sánh ML/rules/hybrid; không dùng test để tune; kết quả ổn định với input lặp lại |
| **FE-06** | Overlay vùng PII | **Đỗ Minh Tấn** | `SE1` | SE3 | - | `P1` | `L` | Vùng bám đúng nội dung khi zoom/rotate/crop; không coi confidence là xác suất đã hiệu chỉnh |
| **FE-07** | Danh sách và lọc kết quả PII | **Đỗ Minh Tấn** | `SE1` | SE2 | - | `P1` | `M` | Danh sách và overlay đồng bộ; không tìm thấy PII vẫn yêu cầu duyệt trực quan |
| **RED-03** | Redaction nội dung native | **Dương Minh Đức** | `SE4` | CS2 | - | `P0` | `L` | Copy/search/extract không lấy lại nội dung mục tiêu; không chỉ phủ hình chữ nhật |
| **RED-04** | Redaction ảnh và lớp OCR | **Dương Minh Đức** | `SE4` | CS2 | - | `P0` | `L` | Ảnh trích xuất không còn nội dung mục tiêu; cả pixel và OCR layer bị xử lý; không tái gắn ảnh gốc |

---

## Phân phối công việc cụ thể cho 7 thành viên trong tuần

### SE2: Nguyễn Đinh Phú Vinh (Backend & System Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **ML-03** (Suy luận phát hiện PII)
- **Trách nhiệm Review/Nghiệm thu**: **FE-07**
- **Phối hợp liên module**: **ML-06**
- **Chi tiết hoạt động trong tuần**: Chủ trì đóng gói và tối ưu hóa module model inference serving ML-03; thiết kế API phục vụ suy luận cho pipeline backend.

### SE1: Đỗ Minh Tấn (Frontend - ICT)

- **Công việc chính phụ trách (Owner)**: **FE-06** (Overlay vùng PII), **FE-07** (Danh sách và lọc kết quả PII)
- **Trách nhiệm Review/Nghiệm thu**: **ML-08**
- **Chi tiết hoạt động trong tuần**: Lập trình vẽ bounding box overlay đè lên canvas PDF (FE-06); xây dựng danh sách thực thể và bộ lọc theo nhóm PII (FE-07).

### SE4: Dương Minh Đức (Data & PDF Engine - ICT)

- **Công việc chính phụ trách (Owner)**: **ML-06** (Kết hợp ML và luật), **RED-03** (Redaction nội dung native), **RED-04** (Redaction ảnh và lớp OCR)
- **Trách nhiệm Review/Nghiệm thu**: **OCR-09**
- **Phối hợp liên module**: **ML-03**
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng bộ giải quyết xung đột ML và Regex (ML-06); phát triển thuật toán xóa triệt để vector/text PDF (RED-03) và bóc tách ảnh/lớp OCR (RED-04).

### SE3: Nguyễn Tuấn Vinh (Document / OCR - ICT)

- **Công việc chính phụ trách (Owner)**: **OCR-09** (Hợp nhất native và OCR), **ML-08** (Ánh xạ entity thành vùng)
- **Trách nhiệm Review/Nghiệm thu**: **FE-06**
- **Chi tiết hoạt động trong tuần**: Chủ trì hoàn thiện hợp nhất dữ liệu trang mixed (OCR-09); lập trình module chuyển đổi entity spans thành bounding box PDF (ML-08).

### CS2: Hoàng Thị Kiều Ly (Security Verification - CS)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **RED-03**, **RED-04**
- **Chi tiết hoạt động trong tuần**: Tiến hành kiểm thử sơ bộ trên file PDF sau khi chạy qua RED-03 và RED-04 bằng các lệnh trích xuất văn bản dòng lệnh để kiểm tra độ sạch.

### CS1: Nguyễn Quang Anh (Security Engineering - CS)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Chi tiết hoạt động trong tuần**: Rà soát logic merge vùng trong RED-03/04 để đảm bảo không bỏ sót phần viền ngoài do làm tròn số học.

### ML1: Nguyễn Đăng Đạt (Machine Learning Lead - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **ML-03**, **ML-06**
- **Chi tiết hoạt động trong tuần**: Hỗ trợ SE2 tinh chỉnh tham số inference, threshold trong ML-03; hỗ trợ SE4 đánh giá chất lượng kết hợp hybrid trong ML-06.

---

## Tiêu chuẩn nghiệm thu tuần (Definition of Done - DoD)

- [ ] Module ML-03 tải checkpoint NER và chạy inference nhanh chóng trên CPU/GPU của demo server, xử lý batch và chuỗi dài ổn định.
- [ ] OCR-09 hợp nhất thông minh giữa text native và text trích xuất từ OCR trên trang hỗn hợp, khử trùng lặp dữ liệu.
- [ ] ML-08 chuyển đổi chính xác từng entity span nhiều dòng thành tập hợp các hình chữ nhật bounding box trên trang PDF tương ứng.
- [ ] ML-06 dung hòa xung đột giữa dự đoán của ML và kết quả Regex, ưu tiên nguồn có độ tin cậy cao và gắn nhãn nguồn gốc (provenance).
- [ ] Giao diện FE-06 vẽ các bounding box overlay chính xác tuyệt đối trên trang PDF, đổi màu theo loại nhãn PII và điểm tin cậy.
- [ ] FE-07 cung cấp sidebar hiển thị danh sách PII, cho phép lọc theo loại và click để tự động cuộn đến trang có thực thể.
- [ ] Thuật toán RED-03 xóa hoàn toàn toán tử hiển thị text (Tj, TJ) và vector path trong vùng redaction, ngăn trích xuất text dưới mọi hình thức.
- [ ] Thuật toán RED-04 cắt gọt/vẽ đè triệt để trên ảnh raster và làm sạch hoàn toàn text stream OCR ẩn bên dưới.

---

## Rủi ro kỹ thuật & Điều kiện tiên quyết (Dependencies & Risks)

- **Các phụ thuộc cần hoàn thành từ tuần trước**: CORE-02, FE-05, ML-01, ML-02, ML-04, ML-05, OCR-06, OCR-07, OCR-08, RED-02.
- **Nguyên tắc an toàn**: Luôn tuân thủ nguyên tắc không can thiệp đè lên file gốc, đảm bảo tính bất biến của dữ liệu và kiểm tra chặt chẽ trước khi xuất bản.
