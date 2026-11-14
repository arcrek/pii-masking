# Kế hoạch & Phân chia công việc - Tuần 1
## Chủ đề: Khởi động Dự án, Thiết lập Môi trường & Thống nhất Hợp đồng Nền tảng

- **Giai đoạn**: `Phase 1: Contracts and data foundations`
- **Mục tiêu tuần (Sprint Goal)**: Thiết lập môi trường phát triển & repo chung (OPS-01), định nghĩa chính sách PII & taxonomy 6 nhóm (CORE-01), thống nhất hợp đồng tài liệu & tọa độ PDF chuẩn (CORE-02), khảo sát dataset công khai/tổng hợp & giấy phép (DATA-01). Các nhóm khởi động nghiên cứu công nghệ cho Frontend, Mô hình NER và Khung kiểm thử bảo mật.

---

## Bảng phân công công việc chi tiết trong tuần (Sprint Backlog)

| Mã Task | Tên công việc | Người thực hiện | Vai trò | Người Review | Người phối hợp | Độ ưu tiên | Quy mô | Tiêu chuẩn nghiệm thu (Acceptance Criteria) |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **CORE-01** | Chốt chính sách PII | **Nguyễn Quang Anh** | `CS1` | ML1 | SE4 | `P0` | `M` | Có taxonomy versioned và quyết định phạm vi mã ID; từng nhãn có ví dụ và ranh giới rõ |
| **CORE-02** | Chốt hợp đồng tài liệu và tọa độ | **Nguyễn Tuấn Vinh** | `SE3` | SE4 | SE1 | `P0` | `M` | Có ví dụ thật cho trang xoay và thực thể nhiều dòng; thống nhất PDF units, gốc tọa độ, crop và phép biến đổi |
| **DATA-01** | Khảo sát dữ liệu và giấy phép | **Đỗ Minh Tấn** | `SE4` | CS1 | - | `P1` | `M` | Có danh mục dataset cùng giấy phép/version; không đưa dữ liệu nhạy cảm thật vào project |
| **OPS-01** | Môi trường và cấu hình phiên bản | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | ML1 | `P1` | `M` | Nhóm khởi chạy tái lập; model/config có version; không ghi secret vào artifact/log |

---

## Phân phối công việc cụ thể cho 7 thành viên trong tuần

### SE2: Nguyễn Đinh Phú Vinh (Backend & System Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **OPS-01** (Môi trường và cấu hình phiên bản)
- **Chi tiết hoạt động trong tuần**: Chủ trì thiết lập môi trường dev, Docker base, cấu hình repository và quy chuẩn commit/branching (OPS-01). Phối hợp với CS1 và SE3 chuẩn bị hợp đồng API cho tuần sau.

### SE1: Dương Minh Đức (Frontend - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Phối hợp liên module**: **CORE-02**
- **Chi tiết hoạt động trong tuần**: Khởi tạo project Frontend (React/Next.js/Vite + TailwindCSS), nghiên cứu tích hợp PDF.js, khảo sát cơ chế render canvas đè lên trang PDF. Đóng góp ý kiến cho hợp đồng tọa độ CORE-02.

### SE4: Đỗ Minh Tấn (Data & PDF Engine - ICT)

- **Công việc chính phụ trách (Owner)**: **DATA-01** (Khảo sát dữ liệu và giấy phép)
- **Trách nhiệm Review/Nghiệm thu**: **CORE-02**
- **Phối hợp liên module**: **CORE-01**
- **Chi tiết hoạt động trong tuần**: Chủ trì khảo sát các nguồn dữ liệu PII công khai (HuggingFace datasets, CoNLL, Enron, v.v.), kiểm tra giấy phép bản quyền và lập danh mục nguồn dữ liệu chuẩn (DATA-01).

### SE3: Nguyễn Tuấn Vinh (Document / OCR - ICT)

- **Công việc chính phụ trách (Owner)**: **CORE-02** (Chốt hợp đồng tài liệu và tọa độ)
- **Chi tiết hoạt động trong tuần**: Chủ trì soạn thảo đặc tả mô hình Document, Page, Token, Entity, Region; thống nhất hệ tọa độ chuẩn giữa PDF vector và màn hình hiển thị (CORE-02).

### CS2: Hoàng Thị Kiều Ly (Security Verification - CS)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Chi tiết hoạt động trong tuần**: Khảo sát các kỹ thuật rò rỉ dữ liệu PDF (PDF leak vectors, hidden text, metadata, residual OCR), nghiên cứu công cụ kiểm thử pdfminer/pdfplumber/qpdf, phác thảo kế hoạch pentest độc lập.

### CS1: Nguyễn Quang Anh (Security Engineering - CS)

- **Công việc chính phụ trách (Owner)**: **CORE-01** (Chốt chính sách PII)
- **Trách nhiệm Review/Nghiệm thu**: **DATA-01**, **OPS-01**
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng chính sách PII, định nghĩa 6 nhóm thực thể nhạy cảm, tiêu chuẩn nhãn và ranh giới loại trừ cho hệ thống (CORE-01). Tham gia rà soát bảo mật repo trong OPS-01.

### ML1: Nguyễn Đăng Đạt (Machine Learning Lead - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **CORE-01**
- **Phối hợp liên module**: **OPS-01**
- **Chi tiết hoạt động trong tuần**: Khảo sát các kiến trúc mô hình NER hiện đại (Presidio, RoBERTa-NER, DeBERTa, GLiNER), thiết lập môi trường Google Colab Pro, chuẩn bị GPU runtime và trao đổi về format annotation với SE4.

---

## Tiêu chuẩn nghiệm thu tuần (Definition of Done - DoD)

- [ ] Tài liệu chính sách PII có phiên bản (v1.0), định nghĩa rõ ràng 6 nhóm nhãn (Tên, Email, Điện thoại, Địa chỉ, Ngày sinh, Mã định danh), có ví dụ âm/dương cụ thể.
- [ ] Tài liệu hợp đồng tài liệu & tọa độ PDF: Thống nhất đơn vị đo (PDF points), gốc tọa độ (bottom-left vs top-left), phép biến đổi xoay (rotation) và crop box.
- [x] Repository chuẩn, phân quyền git, file .gitignore, cấu hình môi trường dev, container chuẩn hóa và tài liệu hướng dẫn setup môi trường.
- [ ] Báo cáo danh mục dataset PII (English public/synthetic), giấy phép sử dụng hợp lệ, không chứa dữ liệu nhạy cảm thật.

---

## Rủi ro kỹ thuật & Điều kiện tiên quyết (Dependencies & Risks)

- **Các phụ thuộc**: Toàn bộ công việc có thể triển khai ngay từ đầu tuần hoặc phụ thuộc khép kín trong tuần.
- **Nguyên tắc an toàn**: Luôn tuân thủ nguyên tắc không can thiệp đè lên file gốc, đảm bảo tính bất biến của dữ liệu và kiểm tra chặt chẽ trước khi xuất bản.
