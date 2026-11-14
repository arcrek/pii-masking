# Kế hoạch & Phân chia công việc - Tuần 2
## Chủ đề: Hoàn thiện Hợp đồng Hệ thống, Ma trận Nghiệm thu & Chuẩn hóa Dữ liệu

- **Giai đoạn**: `Phase 1: Contracts and data foundations (Hoàn thành) -> Bắt đầu Phase 2`
- **Mục tiêu tuần (Sprint Goal)**: Chốt hợp đồng API & vòng đời tác vụ (CORE-03), ban hành ma trận nghiệm thu QA-01, chuẩn hóa định dạng annotation & mapping ký tự (DATA-02), chia tập train/val/test chống data leakage (DATA-03), cấu hình giới hạn tài nguyên & cách ly worker (OPS-03), xây dựng bộ phân loại trang PDF (OCR-01), thiết lập module xác thực tài khoản demo (BE-01).

---

## Bảng phân công công việc chi tiết trong tuần (Sprint Backlog)

| Mã Task | Tên công việc | Người thực hiện | Vai trò | Người Review | Người phối hợp | Độ ưu tiên | Quy mô | Tiêu chuẩn nghiệm thu (Acceptance Criteria) |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **CORE-03** | Chốt hợp đồng API và tác vụ | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | SE1;SE3 | `P0` | `M` | FE/BE/OCR/RED thống nhất contract; khóa trạng thái xuất khi phân tích chưa đầy đủ hoặc kiểm tra thất bại |
| **QA-01** | Ma trận nghiệm thu và ngưỡng chất lượng | **Nguyễn Quang Anh** | `CS1` | ML1 | CS2;SE2;SE4 | `P1` | `M` | Ngưỡng được chốt trước test cuối; có trace từng tiêu chí đến function code và evidence |
| **DATA-02** | Chuẩn hóa annotation | **Dương Minh Đức** | `SE4` | ML1 | - | `P1` | `L` | Kiểm tra span đúng substring; nêu nhãn không phủ đủ; ví dụ sai nhãn được rà soát |
| **DATA-03** | Tách train/validation/test | **Dương Minh Đức** | `SE4` | ML1 | - | `P1` | `M` | Có manifest tái lập, thống kê phân bố và dedup; test không dùng để tune hoặc chọn threshold |
| **OPS-03** | Giới hạn tài nguyên xử lý | **Nguyễn Quang Anh** | `CS1` | CS2 | SE2;SE3 | `P0` | `L` | Giới hạn và cách ly có trước khi parser/OCR xử lý file; timeout có lý do; không quyền truy cập ngoài storage cần thiết hoặc network tùy ý |
| **OCR-01** | Kiểm tra và phân loại trang | **Nguyễn Tuấn Vinh** | `SE3` | SE4 | - | `P1` | `M` | Bộ mẫu có ba loại và trang hỗn hợp được nhận diện; lớp OCR cũ không mặc định được tin cậy |
| **BE-01** | Quản lý tài khoản demo | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | - | `P1` | `M` | Không cần đăng ký công khai; không lưu mật khẩu dạng rõ; thử đăng nhập sai có giới hạn |

---

## Phân phối công việc cụ thể cho 7 thành viên trong tuần

### SE2: Nguyễn Đinh Phú Vinh (Backend & System Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **CORE-03** (Chốt hợp đồng API và tác vụ), **BE-01** (Quản lý tài khoản demo)
- **Phối hợp liên module**: **QA-01**, **OPS-03**
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng đặc tả hợp đồng API và trạng thái tác vụ (CORE-03); lập trình module quản lý tài khoản demo và cơ chế băm mật khẩu an toàn (BE-01). Phối hợp với CS1 cấu hình cgroups (OPS-03).

### SE1: Đỗ Minh Tấn (Frontend - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Phối hợp liên module**: **CORE-03**
- **Chi tiết hoạt động trong tuần**: Tham gia phản biện hợp đồng API (CORE-03) để đảm bảo thuận tiện cho client; bắt đầu dựng khung giao diện đăng nhập và layout tổng quan cho ứng dụng web.

### SE4: Dương Minh Đức (Data & PDF Engine - ICT)

- **Công việc chính phụ trách (Owner)**: **DATA-02** (Chuẩn hóa annotation), **DATA-03** (Tách train/validation/test)
- **Trách nhiệm Review/Nghiệm thu**: **OCR-01**
- **Phối hợp liên module**: **QA-01**
- **Chi tiết hoạt động trong tuần**: Chủ trì chuẩn hóa annotation, mapping nhãn và character offsets (DATA-02); thực hiện phân chia train/val/test và xây dựng manifest tái lập (DATA-03).

### SE3: Nguyễn Tuấn Vinh (Document / OCR - ICT)

- **Công việc chính phụ trách (Owner)**: **OCR-01** (Kiểm tra và phân loại trang)
- **Phối hợp liên module**: **CORE-03**, **OPS-03**
- **Chi tiết hoạt động trong tuần**: Chủ trì phát triển thuật toán phân loại trang PDF thành native, scanned hoặc mixed dựa trên phân tích cấu trúc đối tượng PDF (OCR-01).

### CS2: Hoàng Thị Kiều Ly (Security Verification - CS)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **OPS-03**
- **Phối hợp liên module**: **QA-01**
- **Chi tiết hoạt động trong tuần**: Tham gia rà soát ma trận nghiệm thu an ninh trong QA-01; thiết kế các ca kiểm thử bảo mật cho module tài khoản demo BE-01.

### CS1: Nguyễn Quang Anh (Security Engineering - CS)

- **Công việc chính phụ trách (Owner)**: **QA-01** (Ma trận nghiệm thu và ngưỡng chất lượng), **OPS-03** (Giới hạn tài nguyên xử lý)
- **Trách nhiệm Review/Nghiệm thu**: **CORE-03**, **BE-01**
- **Chi tiết hoạt động trong tuần**: Chủ trì ban hành ma trận nghiệm thu an toàn và chất lượng QA-01; thiết lập giới hạn tài nguyên và kiến trúc cách ly parser/OCR (OPS-03). Rà soát bảo mật auth cho BE-01.

### ML1: Nguyễn Đăng Đạt (Machine Learning Lead - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **QA-01**, **DATA-02**, **DATA-03**
- **Chi tiết hoạt động trong tuần**: Phối hợp với SE4 thẩm định nhãn và schema dữ liệu trong DATA-02; tiếp nhận phân chia train/val/test (DATA-03) để chuẩn bị kịch bản chạy baseline ML-01.

---

## Tiêu chuẩn nghiệm thu tuần (Definition of Done - DoD)

- [ ] OpenAPI/JSON schema đầy đủ cho toàn bộ luồng xử lý: Document, Page, Job, ReviewRevision, Export. Được FE, BE, OCR, RED thống nhất nghiệm thu.
- [ ] Ma trận nghiệm thu QA-01 hoàn thiện với các ngưỡng chất lượng (latency, độ chính xác, tiêu chuẩn an toàn không rò rỉ).
- [ ] Dataset annotation được chuẩn hóa với character offsets chính xác, kiểm tra span text khớp 100% với substring.
- [ ] Tập dữ liệu được chia tách rành mạch thành train/val/test theo manifest có khả năng tái lập hoàn toàn, không rò rỉ giữa các nguồn.
- [ ] Docker worker chạy dưới quyền non-root, thiết lập cgroups hạn chế CPU/RAM và timeout chống quá tải.
- [ ] Module phân loại trang (OCR-01) phân biệt chính xác trang native, scanned và mixed trên tập mẫu.
- [ ] Hệ thống xác thực demo (BE-01) sẵn sàng, mật khẩu được hash bằng bcrypt/argon2, có rate limit chống brute-force.

---

## Rủi ro kỹ thuật & Điều kiện tiên quyết (Dependencies & Risks)

- **Các phụ thuộc cần hoàn thành từ tuần trước**: CORE-01, CORE-02, DATA-01, OPS-01.
- **Nguyên tắc an toàn**: Luôn tuân thủ nguyên tắc không can thiệp đè lên file gốc, đảm bảo tính bất biến của dữ liệu và kiểm tra chặt chẽ trước khi xuất bản.
