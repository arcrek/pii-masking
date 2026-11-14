# Kế hoạch & Phân chia công việc - Tuần 7
## Chủ đề: Điều phối Pipeline, Tác vụ Bất đồng bộ & Tương tác Duyệt Vùng PII

- **Giai đoạn**: `Phase 2: Core product MVP`
- **Mục tiêu tuần (Sprint Goal)**: Xây dựng pipeline orchestrator kết nối toàn diện Extraction -> OCR -> Detection -> Mapping (BE-06), cơ chế retry, idempotency và xử lý lỗi worker (BE-07), lưu trữ và đồng bộ quyết định duyệt với optimistic locking (BE-08), hiển thị danh sách tài liệu và tác vụ (FE-03), hiển thị tiến trình và lỗi theo từng trang (FE-04), giao diện chấp nhận/loại bỏ gợi ý PII (FE-08), công cụ khoanh vùng thủ công cho PII sót/chữ viết tay/chữ ký (FE-09).

---

## Bảng phân công công việc chi tiết trong tuần (Sprint Backlog)

| Mã Task | Tên công việc | Người thực hiện | Vai trò | Người Review | Người phối hợp | Độ ưu tiên | Quy mô | Tiêu chuẩn nghiệm thu (Acceptance Criteria) |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **BE-06** | Điều phối pipeline | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | - | `P1` | `L` | Có kết quả hoàn chỉnh hoặc lỗi có cấu trúc; không âm thầm bỏ trang; ghi version pipeline |
| **BE-07** | Thử lại và chống tác vụ trùng | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | - | `P1` | `L` | Retry không ghi đè kết quả mới; hai yêu cầu trùng không tạo hai artifact chính thức |
| **BE-08** | Lưu và đọc quyết định duyệt | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | - | `P1` | `M` | Vùng ngoài trang bị từ chối; sửa đồng thời được báo xung đột; mở lại không mất quyết định |
| **FE-03** | Danh sách tài liệu và tác vụ | **Đỗ Minh Tấn** | `SE1` | SE2 | - | `P1` | `M` | Không hiển thị tài liệu người khác; tải lại trang vẫn truy cập được tác vụ đã lưu |
| **FE-04** | Hiển thị tiến trình và lỗi theo trang | **Đỗ Minh Tấn** | `SE1` | SE2 | - | `P1` | `M` | Không hiển thị hoàn tất khi còn trang lỗi; retry hiển thị đúng tác vụ mới hoặc lần chạy mới |
| **FE-08** | Duyệt gợi ý | **Đỗ Minh Tấn** | `SE1` | SE2 | - | `P1` | `M` | Lựa chọn được lưu đúng revision; bỏ chọn không xóa kết quả phát hiện gốc |
| **FE-09** | Khoanh vùng thủ công | **Đỗ Minh Tấn** | `SE1` | SE3 | - | `P1` | `L` | Vùng nằm trong trang, tồn tại sau mở lại; tọa độ hiển thị và lưu khớp nhau |

---

## Phân phối công việc cụ thể cho 7 thành viên trong tuần

### SE2: Nguyễn Đinh Phú Vinh (Backend & System Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **BE-06** (Điều phối pipeline), **BE-07** (Thử lại và chống tác vụ trùng), **BE-08** (Lưu và đọc quyết định duyệt)
- **Trách nhiệm Review/Nghiệm thu**: **FE-03**, **FE-04**, **FE-08**
- **Chi tiết hoạt động trong tuần**: Chủ trì lập trình pipeline orchestrator (BE-06); xây dựng cơ chế retry, queue idempotency (BE-07); phát triển API quản lý review revision (BE-08).

### SE1: Đỗ Minh Tấn (Frontend - ICT)

- **Công việc chính phụ trách (Owner)**: **FE-03** (Danh sách tài liệu và tác vụ), **FE-04** (Hiển thị tiến trình và lỗi theo trang), **FE-08** (Duyệt gợi ý), **FE-09** (Khoanh vùng thủ công)
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng trang danh sách tài liệu (FE-03); component tiến trình trang (FE-04); tính năng duyệt gợi ý (FE-08) và công cụ khoanh vùng thủ công (FE-09).

### SE4: Dương Minh Đức (Data & PDF Engine - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Chi tiết hoạt động trong tuần**: Hỗ trợ tích hợp module redaction vào backend; kiểm tra tính tương thích giữa revision lưu trữ và dữ liệu đầu vào của engine xóa.

### SE3: Nguyễn Tuấn Vinh (Document / OCR - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **FE-09**
- **Chi tiết hoạt động trong tuần**: Hỗ trợ SE1 tinh chỉnh công cụ vẽ vùng thủ công (FE-09) để đảm bảo tọa độ kéo thả chuột ánh xạ chính xác về tọa độ trang PDF.

### CS2: Hoàng Thị Kiều Ly (Security Verification - CS)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Chi tiết hoạt động trong tuần**: Chuẩn bị sẵn sàng các script kiểm định tự động cho verification engine (VER-01 đến VER-06) để tích hợp vào tuần sau.

### CS1: Nguyễn Quang Anh (Security Engineering - CS)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **BE-06**, **BE-07**, **BE-08**
- **Chi tiết hoạt động trong tuần**: Rà soát kiểm tra quyền truy cập và kiểm tra chống xung đột (optimistic locking) trên BE-08.

### ML1: Nguyễn Đăng Đạt (Machine Learning Lead - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Chi tiết hoạt động trong tuần**: Phân tích các trường hợp người dùng từ chối gợi ý trên UI thử nghiệm để thu thập dữ liệu phục vụ báo cáo lỗi ML-07.

---

## Tiêu chuẩn nghiệm thu tuần (Definition of Done - DoD)

- [ ] BE-06 điều phối trọn vẹn luồng phân tích từ PDF thô đến tập candidate regions; lưu trạng thái chi tiết theo từng trang.
- [ ] BE-07 đảm bảo tính bất biến (idempotency), tự động thử lại khi tác vụ gián đoạn, ngăn ngừa chạy trùng lặp.
- [ ] BE-08 lưu trữ quyết định duyệt (accepted/rejected/manual) theo phiên bản (revision), phát hiện xung đột khi sửa đồng thời.
- [ ] FE-03 hiển thị danh sách tài liệu của tài khoản đang đăng nhập, cho phép mở lại tác vụ đang dở dang.
- [ ] FE-04 cập nhật realtime thanh tiến trình xử lý từng trang và hiển thị thông báo lỗi rõ ràng nếu có trang hỏng.
- [ ] FE-08 cho phép người dùng click duyệt, chấp nhận hoặc từ chối từng gợi ý PII hoặc duyệt nhanh theo nhóm.
- [ ] FE-09 cho phép người dùng vẽ thêm vùng chữ nhật thủ công để đánh dấu chữ viết tay, chữ ký hoặc thông tin máy học bỏ sót.

---

## Rủi ro kỹ thuật & Điều kiện tiên quyết (Dependencies & Risks)

- **Các phụ thuộc cần hoàn thành từ tuần trước**: BE-05, CORE-02, FE-05, FE-07, ML-08, OCR-09, OPS-03.
- **Nguyên tắc an toàn**: Luôn tuân thủ nguyên tắc không can thiệp đè lên file gốc, đảm bảo tính bất biến của dữ liệu và kiểm tra chặt chẽ trước khi xuất bản.
