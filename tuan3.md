# Kế hoạch & Phân chia công việc - Tuần 3
## Chủ đề: Quản lý Phiên & Phân quyền, Bóc tách Text Native, PDF Viewer & Dữ liệu Chuẩn

- **Giai đoạn**: `Phase 2: Core product MVP`
- **Mục tiêu tuần (Sprint Goal)**: Xây dựng quản lý phiên và token (BE-02), kiểm soát phân quyền tài liệu theo owner chống IDOR (BE-03), hoàn thiện giao diện đăng nhập/đăng xuất (FE-01), bóc tách văn bản native với offset mapping chuẩn (OCR-02), render ảnh và deskew cho trang scan (OCR-03), xây dựng bộ dataset PDF chuẩn đa dạng cấu trúc (DATA-04), thiết lập baseline model có thể tái lập (ML-01), tiền xử lý và căn chỉnh token cho huấn luyện NER (ML-02).

---

## Bảng phân công công việc chi tiết trong tuần (Sprint Backlog)

| Mã Task | Tên công việc | Người thực hiện | Vai trò | Người Review | Người phối hợp | Độ ưu tiên | Quy mô | Tiêu chuẩn nghiệm thu (Acceptance Criteria) |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **BE-02** | Quản lý phiên truy cập | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | - | `P1` | `M` | API bảo vệ từ chối phiên hết hạn/đã thu hồi; đáp ứng chính sách phiên đã chọn |
| **BE-03** | Phân quyền tài liệu và artifact | **Nguyễn Quang Anh** | `CS1` | CS2 | SE2 | `P0` | `M` | Tài khoản A không đọc/sửa/xóa/tải tài liệu hay artifact của B dù biết ID |
| **FE-01** | Đăng nhập và đăng xuất | **Đỗ Minh Tấn** | `SE1` | CS2 | - | `P1` | `S` | Đăng nhập hợp lệ được; sai thông tin/hết phiên được xử lý; đăng xuất mất quyền truy cập |
| **OCR-02** | Trích xuất văn bản native | **Nguyễn Tuấn Vinh** | `SE3` | CS2 | - | `P1` | `L` | Có offset mapping; không mất nguồn vị trí do nối đoạn; báo lỗi khi không trích xuất được |
| **OCR-03** | Render và tiền xử lý OCR | **Nguyễn Tuấn Vinh** | `SE3` | SE4 | - | `P1` | `L` | Ảnh có kích thước và transform rõ; đảo biến đổi về trang gốc kiểm tra được |
| **DATA-04** | Bộ tài liệu PDF chuẩn | **Dương Minh Đức** | `SE4` | SE3 | SE1 | `P1` | `L` | Có ground truth text/regions; PDF đánh giá dùng nguồn held-out theo split, không dùng text train; phủ native/scan/mixed, handwriting thủ công và các layout/rotation/noise đã chọn |
| **ML-01** | Baseline có thể tái lập | **Nguyễn Đăng Đạt** | `ML1` | SE4 | SE4 | `P1` | `M` | Báo cáo cùng taxonomy/split; công bố entity không hỗ trợ thay vì coi là true negative |
| **ML-02** | Chuẩn bị dữ liệu huấn luyện | **Nguyễn Đăng Đạt** | `ML1` | SE4 | SE4 | `P1` | `L` | Không làm lệch offset; cửa sổ chồng lấn có quy tắc ghép và kiểm thử thực thể ở ranh giới |

---

## Phân phối công việc cụ thể cho 7 thành viên trong tuần

### SE2: Nguyễn Đinh Phú Vinh (Backend & System Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **BE-02** (Quản lý phiên truy cập)
- **Phối hợp liên module**: **BE-03**
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng quản lý phiên (BE-02). Phối hợp với CS1 triển khai middleware kiểm tra phân quyền (BE-03). Hỗ trợ ML1 thiết kế cấu trúc dữ liệu cho model.

### SE1: Đỗ Minh Tấn (Frontend - ICT)

- **Công việc chính phụ trách (Owner)**: **FE-01** (Đăng nhập và đăng xuất)
- **Phối hợp liên module**: **DATA-04**
- **Chi tiết hoạt động trong tuần**: Hoàn thiện giao diện đăng nhập, thông báo lỗi và luồng đăng xuất (FE-01). Nghiên cứu cơ chế cache và render trang PDF trên canvas.

### SE4: Dương Minh Đức (Data & PDF Engine - ICT)

- **Công việc chính phụ trách (Owner)**: **DATA-04** (Bộ tài liệu PDF chuẩn)
- **Trách nhiệm Review/Nghiệm thu**: **OCR-03**, **ML-01**, **ML-02**
- **Phối hợp liên module**: **ML-01**, **ML-02**
- **Chi tiết hoạt động trong tuần**: Chủ trì tổng hợp và gán nhãn ground truth cho bộ tài liệu PDF chuẩn DATA-04; hỗ trợ ML1 rà soát offset mapping trong ML-02.

### SE3: Nguyễn Tuấn Vinh (Document / OCR - ICT)

- **Công việc chính phụ trách (Owner)**: **OCR-02** (Trích xuất văn bản native), **OCR-03** (Render và tiền xử lý OCR)
- **Trách nhiệm Review/Nghiệm thu**: **DATA-04**
- **Chi tiết hoạt động trong tuần**: Phát triển module trích xuất text native từ content stream của PDF (OCR-02); phát triển module render ảnh trang và thuật toán deskew (OCR-03).

### CS2: Hoàng Thị Kiều Ly (Security Verification - CS)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **BE-03**, **FE-01**, **OCR-02**
- **Chi tiết hoạt động trong tuần**: Thiết kế các test case pentest chống truy cập chéo tài liệu (IDOR) cho BE-03; bắt đầu thu thập các mẫu PDF đặc thù cho bộ ca đối kháng.

### CS1: Nguyễn Quang Anh (Security Engineering - CS)

- **Công việc chính phụ trách (Owner)**: **BE-03** (Phân quyền tài liệu và artifact)
- **Trách nhiệm Review/Nghiệm thu**: **BE-02**
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng chính sách phân quyền truy cập và kiểm tra owner trên mọi endpoint (BE-03). Rà soát thời gian sống của token trong BE-02.

### ML1: Nguyễn Đăng Đạt (Machine Learning Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **ML-01** (Baseline có thể tái lập), **ML-02** (Chuẩn bị dữ liệu huấn luyện)
- **Chi tiết hoạt động trong tuần**: Chủ trì triển khai mô hình baseline rule-based + pretrained (ML-01); lập trình pipeline căn chỉnh token và tiền xử lý cho mô hình NER (ML-02).

---

## Tiêu chuẩn nghiệm thu tuần (Definition of Done - DoD)

- [ ] Hệ thống quản lý phiên (BE-02) hoạt động: phát hành JWT/session token an toàn, xử lý thu hồi token khi đăng xuất hoặc hết hạn.
- [ ] Quy tắc phân quyền (BE-03) được thực thi nghiêm ngặt: người dùng A tuyệt đối không thể đọc/sửa/tải tài liệu của người dùng B.
- [ ] Trang đăng nhập FE-01 hoàn thiện, kết nối API backend, xử lý lưu trữ token an toàn và tự động redirect khi hết hạn.
- [ ] Module OCR-02 trích xuất văn bản native với vị trí từng ký tự/từ (bounding box) và provenance mapping chuẩn xác.
- [ ] Module OCR-03 render trang scan thành ảnh chất lượng cao, tự động xoay và khử nghiêng (deskew), lưu trữ ma trận biến đổi.
- [ ] Bộ tài liệu PDF chuẩn DATA-04 hoàn thành với đầy đủ 3 loại (native, scan, mixed) và ground truth tọa độ.
- [ ] Baseline ML-01 chạy ổn định, ghi nhận điểm benchmark ban đầu trên cùng tập test cố định.
- [ ] Tập dữ liệu huấn luyện ML-02 hoàn tất căn chỉnh token (alignment) và phân đoạn cho văn bản dài.

---

## Rủi ro kỹ thuật & Điều kiện tiên quyết (Dependencies & Risks)

- **Các phụ thuộc cần hoàn thành từ tuần trước**: BE-01, CORE-02, DATA-03, OCR-01.
- **Nguyên tắc an toàn**: Luôn tuân thủ nguyên tắc không can thiệp đè lên file gốc, đảm bảo tính bất biến của dữ liệu và kiểm tra chặt chẽ trước khi xuất bản.
