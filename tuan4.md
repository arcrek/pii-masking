# Kế hoạch & Phân chia công việc - Tuần 4
## Chủ đề: Tiếp nhận PDF An toàn, OCR Chữ in, Luật Bổ trợ & Bộ Ca Đối kháng

- **Giai đoạn**: `Phase 2: Core product MVP`
- **Mục tiêu tuần (Sprint Goal)**: Xây dựng module tiếp nhận và kiểm tra file PDF chống injection/bomb (BE-04), giao diện upload PDF kèm hiển thị tiến trình (FE-02), tích hợp engine OCR chữ in tiếng Anh (OCR-04), chuẩn hóa văn bản OCR cho ML giữ nguyên mapping (OCR-05), phát triển bộ luật Regex bổ trợ (ML-04), xây dựng bộ ca redaction đối kháng (DATA-05), xây dựng module kiểm tra snapshot và xác thực vùng xóa (RED-01).

---

## Bảng phân công công việc chi tiết trong tuần (Sprint Backlog)

| Mã Task | Tên công việc | Người thực hiện | Vai trò | Người Review | Người phối hợp | Độ ưu tiên | Quy mô | Tiêu chuẩn nghiệm thu (Acceptance Criteria) |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **BE-04** | Tiếp nhận và kiểm tra PDF | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | - | `P1` | `L` | Từ chối có lý do với file không hỗ trợ; không dùng đường dẫn upload do client tự chỉ định |
| **FE-02** | Tải PDF lên | **Đỗ Minh Tấn** | `SE1` | SE2 | - | `P1` | `M` | Upload thành công trả về tài liệu; lỗi định dạng/dung lượng hiển thị được và cho thử lại |
| **OCR-04** | Nhận dạng chữ in tiếng Anh | **Nguyễn Tuấn Vinh** | `SE3` | CS2 | - | `P1` | `L` | Trả token/bbox/confidence; trang không đọc được hoặc timeout có trạng thái riêng |
| **OCR-05** | Chuẩn hóa văn bản cho ML | **Nguyễn Tuấn Vinh** | `SE3` | ML1 | - | `P1` | `L` | Mọi span mô hình dùng truy ngược được token gốc; không tìm lại vị trí bằng text matching đơn thuần |
| **ML-04** | Luật bổ trợ theo chính sách | **Dương Minh Đức** | `SE4` | ML1 | - | `P1` | `M` | Có ca đúng/sai gần giống; validation/checksum chỉ áp dụng cho hệ mã có quy tắc tương ứng |
| **DATA-05** | Bộ ca redaction đối kháng | **Hoàng Thị Kiều Ly** | `CS2` | CS1 | SE3;SE4 | `P1` | `L` | Mỗi ca có nội dung mục tiêu và cách truy xuất kỳ vọng; synthetic có nhãn không chứa PII thật |
| **RED-01** | Kiểm tra snapshot và vùng xóa | **Nguyễn Quang Anh** | `CS1` | CS2 | SE4 | `P1` | `M` | Từ chối snapshot sai hoặc vùng lỗi; không thay thế bản gốc bằng file đã xử lý |

---

## Phân phối công việc cụ thể cho 7 thành viên trong tuần

### SE2: Nguyễn Đinh Phú Vinh (Backend & System Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **BE-04** (Tiếp nhận và kiểm tra PDF)
- **Trách nhiệm Review/Nghiệm thu**: **FE-02**
- **Chi tiết hoạt động trong tuần**: Chủ trì lập trình module tiếp nhận, kiểm tra PDF và lưu trữ tạm an toàn (BE-04). Hỗ trợ chuẩn bị hạ tầng Colab Pro cho ML-05.

### SE1: Đỗ Minh Tấn (Frontend - ICT)

- **Công việc chính phụ trách (Owner)**: **FE-02** (Tải PDF lên)
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng UI upload PDF kèm validate kích thước/định dạng và xử lý thử lại khi mất kết nối (FE-02).

### SE4: Dương Minh Đức (Data & PDF Engine - ICT)

- **Công việc chính phụ trách (Owner)**: **ML-04** (Luật bổ trợ theo chính sách)
- **Phối hợp liên module**: **DATA-05**, **RED-01**
- **Chi tiết hoạt động trong tuần**: Chủ trì phát triển bộ luật Regex bổ trợ theo chính sách PII đã chốt (ML-04). Phối hợp với CS1 kiểm tra logic xác thực tọa độ trong RED-01.

### SE3: Nguyễn Tuấn Vinh (Document / OCR - ICT)

- **Công việc chính phụ trách (Owner)**: **OCR-04** (Nhận dạng chữ in tiếng Anh), **OCR-05** (Chuẩn hóa văn bản cho ML)
- **Phối hợp liên module**: **DATA-05**
- **Chi tiết hoạt động trong tuần**: Tích hợp OCR engine (Tesseract/PaddleOCR) cho chữ in tiếng Anh (OCR-04); xây dựng pipeline chuẩn hóa văn bản giữ ánh xạ nguồn (OCR-05).

### CS2: Hoàng Thị Kiều Ly (Security Verification - CS)

- **Công việc chính phụ trách (Owner)**: **DATA-05** (Bộ ca redaction đối kháng)
- **Trách nhiệm Review/Nghiệm thu**: **OCR-04**, **RED-01**
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng bộ ca redaction đối kháng DATA-05 với các kỹ thuật che giấu và rò rỉ dữ liệu PDF tinh vi.

### CS1: Nguyễn Quang Anh (Security Engineering - CS)

- **Công việc chính phụ trách (Owner)**: **RED-01** (Kiểm tra snapshot và vùng xóa)
- **Trách nhiệm Review/Nghiệm thu**: **BE-04**, **DATA-05**
- **Chi tiết hoạt động trong tuần**: Chủ trì phát triển module kiểm tra tính hợp lệ của snapshot và vùng redaction (RED-01). Rà soát bộ lọc file an toàn trong BE-04.

### ML1: Nguyễn Đăng Đạt (Machine Learning Lead - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **OCR-05**, **ML-04**
- **Chi tiết hoạt động trong tuần**: Phối hợp với SE3 thẩm định định dạng text chuẩn hóa từ OCR-05; chuẩn bị sẵn notebook và hyperparameter để fine-tune trên Colab Pro.

---

## Tiêu chuẩn nghiệm thu tuần (Definition of Done - DoD)

- [ ] Module BE-04 kiểm tra nghiêm ngặt magic bytes, số trang, kích thước file, từ chối file mã hóa hoặc chứa JavaScript độc hại.
- [ ] Giao diện FE-02 cho phép kéo thả file, kiểm tra dung lượng phía client và hiển thị thanh tiến trình upload trực quan.
- [ ] OCR-04 nhận dạng chữ in tiếng Anh trên các vùng ảnh, trả về danh sách token kèm bounding box và confidence score.
- [ ] OCR-05 chuẩn hóa khoảng trắng, ngắt dòng nhưng bảo toàn tuyệt đối liên kết ngược về token và tọa độ gốc.
- [ ] Bộ luật ML-04 bao phủ các mẫu chuẩn: Email, Phone, Date of Birth, SSN/ID có kiểm tra ngữ cảnh và checksum hợp lệ.
- [ ] Bộ ca đối kháng DATA-05 hoàn thành: chứa văn bản ẩn (white-on-white, tiny font), text đè sau ảnh, OCR layer cũ, metadata nhạy cảm.
- [ ] Module RED-01 xác thực tính hợp lệ của snapshot và vùng xóa (tọa độ hữu hạn, nằm trọn trong trang, provenance rõ ràng).

---

## Rủi ro kỹ thuật & Điều kiện tiên quyết (Dependencies & Risks)

- **Các phụ thuộc cần hoàn thành từ tuần trước**: BE-03, CORE-01, CORE-02, CORE-03, DATA-04, ML-01, OCR-02, OCR-03, OPS-01, OPS-03.
- **Nguyên tắc an toàn**: Luôn tuân thủ nguyên tắc không can thiệp đè lên file gốc, đảm bảo tính bất biến của dữ liệu và kiểm tra chặt chẽ trước khi xuất bản.
