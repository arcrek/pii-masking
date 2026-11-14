# Kế hoạch & Phân chia công việc - Tuần 10
## Chủ đề: Hardening Hệ Thống, Kiểm Thử An Toàn Độc Lập & Đánh Giá Toàn Diện

- **Giai đoạn**: `Phase 3: Hardening and evaluation`
- **Mục tiêu tuần (Sprint Goal)**: Đóng gói version dataset và lập báo cáo giới hạn dữ liệu (DATA-06), thực hiện đánh giá toàn diện mô hình NER và phân tích lỗi (ML-07), tiến hành pentest kiểm thử an toàn redaction độc lập với bộ đối kháng (QA-03), kiểm thử bảo mật phân quyền đa tài khoản và session (QA-04), kiểm thử khả năng chịu lỗi, race conditions và tranh chấp tác vụ (QA-05), đo lường benchmark hiệu năng, tài nguyên và công sức reviewer (QA-06), thiết lập hệ thống quan sát sức khỏe, metrics và cảnh báo (OPS-04).

---

## Bảng phân công công việc chi tiết trong tuần (Sprint Backlog)

| Mã Task | Tên công việc | Người thực hiện | Vai trò | Người Review | Người phối hợp | Độ ưu tiên | Quy mô | Tiêu chuẩn nghiệm thu (Acceptance Criteria) |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **DATA-06** | Version và báo cáo dữ liệu | **Dương Minh Đức** | `SE4` | ML1 | - | `P1` | `M` | Mọi kết quả tham chiếu được dataset version; phân biệt PDF tổng hợp và mẫu public thực tế |
| **ML-07** | Đánh giá và phân tích lỗi | **Nguyễn Đăng Đạt** | `ML1` | SE4 | SE4;CS2 | `P1` | `L` | Có báo cáo test cố định, latency và ví dụ lỗi; đánh giá text chuẩn và text OCR để tách nguyên nhân |
| **QA-03** | Kiểm thử an toàn redaction độc lập | **Hoàng Thị Kiều Ly** | `CS2` | SE3 | - | `P0` | `L` | Bộ fixture đối kháng phát hiện được engine lỗi; có kiểm tra thủ công độc lập với RED |
| **QA-04** | Kiểm thử quyền truy cập | **Hoàng Thị Kiều Ly** | `CS2` | SE4 | - | `P0` | `M` | Không đọc/sửa/tải artifact chéo tài khoản; input giả mạo và phiên hết hạn bị từ chối |
| **QA-05** | Kiểm thử lỗi và tranh chấp tác vụ | **Nguyễn Quang Anh** | `CS1` | CS2 | SE2;SE4 | `P0` | `L` | Không xuất snapshot cũ, không khôi phục file đã xóa và không báo hoàn tất giả khi thiếu trang |
| **QA-06** | Hiệu năng và chất lượng sử dụng | **Dương Minh Đức** | `SE4` | CS2 | SE1;SE2;SE3 | `P1` | `L` | Benchmark trên máy mục tiêu; không vượt giới hạn chốt; ghi thao tác sửa và thời gian so với làm thủ công |
| **OPS-04** | Quan sát và kiểm tra sức khỏe | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | SE1 | `P1` | `M` | Phát hiện worker/model chưa sẵn sàng; metrics không raw PII; có cảnh báo disk/queue phù hợp demo |

---

## Phân phối công việc cụ thể cho 7 thành viên trong tuần

### SE2: Nguyễn Đinh Phú Vinh (Backend & System Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **OPS-04** (Quan sát và kiểm tra sức khỏe)
- **Phối hợp liên module**: **QA-05**, **QA-06**
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng hệ thống quan sát sức khỏe, metrics và cảnh báo dịch vụ (OPS-04). Hỗ trợ CS1 trong các ca test tranh chấp tác vụ QA-05.

### SE1: Đỗ Minh Tấn (Frontend - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Phối hợp liên module**: **QA-06**, **OPS-04**
- **Chi tiết hoạt động trong tuần**: Khắc phục các điểm nghẽn UX/UI phát hiện từ benchmark QA-06; tối ưu hóa tốc độ tải và zoom trang PDF trên trình duyệt.

### SE4: Dương Minh Đức (Data & PDF Engine - ICT)

- **Công việc chính phụ trách (Owner)**: **DATA-06** (Version và báo cáo dữ liệu), **QA-06** (Hiệu năng và chất lượng sử dụng)
- **Trách nhiệm Review/Nghiệm thu**: **ML-07**, **QA-04**
- **Phối hợp liên module**: **ML-07**, **QA-05**
- **Chi tiết hoạt động trong tuần**: Chủ trì lập báo cáo phiên bản dữ liệu (DATA-06); chủ trì đo đạc benchmark hiệu năng và tài nguyên hệ thống (QA-06).

### SE3: Nguyễn Tuấn Vinh (Document / OCR - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **QA-03**
- **Phối hợp liên module**: **QA-06**
- **Chi tiết hoạt động trong tuần**: Phối hợp với ML1 phân tích lỗi do chất lượng OCR trong ML-07; kiểm tra độ trễ trích xuất văn bản trong QA-06.

### CS2: Hoàng Thị Kiều Ly (Security Verification - CS)

- **Công việc chính phụ trách (Owner)**: **QA-03** (Kiểm thử an toàn redaction độc lập), **QA-04** (Kiểm thử quyền truy cập)
- **Trách nhiệm Review/Nghiệm thu**: **QA-05**, **QA-06**
- **Phối hợp liên module**: **ML-07**
- **Chi tiết hoạt động trong tuần**: Chủ trì thực hiện kiểm thử an toàn redaction độc lập QA-03 với bộ ca đối kháng; chủ trì kiểm thử bảo mật phân quyền đa tài khoản QA-04.

### CS1: Nguyễn Quang Anh (Security Engineering - CS)

- **Công việc chính phụ trách (Owner)**: **QA-05** (Kiểm thử lỗi và tranh chấp tác vụ)
- **Trách nhiệm Review/Nghiệm thu**: **OPS-04**
- **Chi tiết hoạt động trong tuần**: Chủ trì thực hiện kiểm thử lỗi, timeout và tranh chấp tác vụ đồng thời QA-05. Rà soát lại threat model của toàn hệ thống.

### ML1: Nguyễn Đăng Đạt (Machine Learning Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **ML-07** (Đánh giá và phân tích lỗi)
- **Trách nhiệm Review/Nghiệm thu**: **DATA-06**
- **Chi tiết hoạt động trong tuần**: Chủ trì lập báo cáo đánh giá mô hình ML-07, phân tích ma trận nhầm lẫn (confusion matrix), độ trễ suy luận và đề xuất hướng tối ưu.

---

## Tiêu chuẩn nghiệm thu tuần (Definition of Done - DoD)

- [ ] Báo cáo DATA-06 hoàn thành: định danh rõ ràng phiên bản dataset, phân bố các nhóm nhãn và công bố các giới hạn dữ liệu.
- [ ] Báo cáo ML-07 chi tiết: bảng điểm F1/Precision/Recall theo từng loại thực thể, phân tích riêng biệt trên text native vs text OCR, phân tích lỗi định lượng.
- [ ] Báo cáo QA-03 kiểm thử đối kháng: xác nhận 100% các mẫu trong bộ test suite đối kháng không bị rò rỉ thông tin nhạy cảm.
- [ ] Báo cáo QA-04 xác nhận không có lỗ hổng IDOR, session hijacking, hay quyền truy cập bất hợp pháp giữa các tài khoản demo.
- [ ] Báo cáo QA-05 chứng minh hệ thống xử lý ổn định khi PDF lỗi, trang timeout, mạng đứt quãng và ngăn chặn race condition khi xuất.
- [ ] Báo cáo QA-06 cung cấp số liệu benchmark: latency theo trang, mức chiếm dụng RAM/CPU của worker, thời gian review trung bình.
- [ ] Hệ thống giám sát OPS-04 sẵn sàng: endpoint /healthz, /readyz, cảnh báo đầy ổ đĩa và theo dõi độ dài hàng đợi tác vụ.

---

## Rủi ro kỹ thuật & Điều kiện tiên quyết (Dependencies & Risks)

- **Các phụ thuộc cần hoàn thành từ tuần trước**: BE-03, BE-07, BE-08, BE-09, BE-10, BE-11, BE-12, DATA-04, DATA-05, FE-01, FE-12, ML-06, OCR-08, OCR-09, OPS-02, OPS-03, QA-02, RED-07, VER-05.
- **Nguyên tắc an toàn**: Luôn tuân thủ nguyên tắc không can thiệp đè lên file gốc, đảm bảo tính bất biến của dữ liệu và kiểm tra chặt chẽ trước khi xuất bản.
