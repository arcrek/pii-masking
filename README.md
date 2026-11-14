# PII Detection & Secure PDF Redaction MVP

Dự án MVP phát hiện PII (Personally Identifiable Information) và xóa nhạy cảm an toàn trên tài liệu PDF (Native, Scanned, Mixed).

## Danh sách thành viên & Phân công trách nhiệm

| Thành viên | Vai trò | Chuyên môn | Trách nhiệm chính | Số task |
| :--- | :---: | :---: | :--- | :---: |
| **Nguyễn Đinh Phú Vinh** | `SE2` | ICT | **Backend & System Lead**: API, Job Queue, Database, Docker server, tích hợp Model Serving; đồng thiết kế kiến trúc model | **16** |
| **Đỗ Minh Tấn** | `SE1` | ICT | **Frontend**: Giao diện Web, PDF viewer, reviewer overlay, khoanh vùng PII thủ công | **13** |
| **Dương Minh Đức** | `SE4` | ICT | **Data & PDF Engine**: Xây dựng Regex, chuẩn bị dataset, thuật toán bóc tách/xóa triệt để vector stream PDF | **12** |
| **Nguyễn Tuấn Vinh** | `SE3` | ICT | **Document / OCR**: Bóc tách text native, tích hợp OCR engine, tính toán tọa độ bounding box | **11** |
| **Hoàng Thị Kiều Ly** | `CS2` | CS | **Security Verification**: Pentest độc lập, tạo fixture đối kháng rà soát leak dữ liệu PDF sau xuất | **10** |
| **Nguyễn Quang Anh** | `CS1` | CS | **Security Engineering**: Chính sách PII, phân quyền RBAC, audit log, resource isolation | **9** |
| **Nguyễn Đăng Đạt** | `ML1` | ICT | **Machine Learning Lead**: Trực tiếp chạy Colab Pro, fine-tune checkpoint model NER, đánh giá F1/Recall | **4** |

---

## Tài liệu kế hoạch & Backlog chi tiết

Mọi người theo dõi chi tiết công việc, acceptance criteria và dependencies tại thư mục [`plans/261101-1815-mvp-function-breakdown/`](./plans/261101-1815-mvp-function-breakdown/):

* **[Function Backlog CSV](./plans/261101-1815-mvp-function-breakdown/function-backlog.csv)**: Bảng theo dõi 75 work packages, assignee, reviewer, priority, status.
* **[Function Breakdown](./plans/261101-1815-mvp-function-breakdown/function-breakdown.md)**: Đặc tả chi tiết từng mã công việc và tiêu chuẩn nghiệm thu (Acceptance Criteria).
* **[Kế hoạch tổng thể (Plan)](./plans/261101-1815-mvp-function-breakdown/plan.md)**: Mục tiêu và quy định làm việc của dự án.
* **Các Phase triển khai**:
  * [Phase 1: Contracts & Data Foundations](./plans/261101-1815-mvp-function-breakdown/phase-01-start.md)
  * [Phase 2: Core MVP](./plans/261101-1815-mvp-function-breakdown/phase-02-core-mvp.md)
  * [Phase 3: Hardening & Evaluation](./plans/261101-1815-mvp-function-breakdown/phase-03-hardening-evaluation.md)
  * [Phase 4: Release Acceptance](./plans/261101-1815-mvp-function-breakdown/phase-04-release-acceptance.md)

---

## Lộ trình thực hiện 11 tuần (Weekly Schedules)

Chi tiết phân chia công việc từng tuần cho 7 thành viên theo [`tuan1.md`](./tuan1.md) đến [`tuan11.md`](./tuan11.md):

* **[Tuần 1: Khởi động Dự án, Thiết lập Môi trường & Thống nhất Hợp đồng Nền tảng](./tuan1.md)**
* **[Tuần 2: Hoàn thiện Hợp đồng Hệ thống, Ma trận Nghiệm thu & Chuẩn hóa Dữ liệu](./tuan2.md)**
* **[Tuần 3: Quản lý Phiên & Phân quyền, Bóc tách Text Native, PDF Viewer & Dữ liệu Chuẩn](./tuan3.md)**
* **[Tuần 4: Tiếp nhận PDF An toàn, OCR Chữ in, Luật Bổ trợ & Bộ Ca Đối kháng](./tuan4.md)**
* **[Tuần 5: Huấn luyện NER trên Colab Pro, Hình học Tọa độ PDF & Storage An toàn](./tuan5.md)**
* **[Tuần 6: Tích hợp Model Serving, Hợp nhất Pipeline OCR/Native & Redaction Engine](./tuan6.md)**
* **[Tuần 7: Điều phối Pipeline, Tác vụ Bất đồng bộ & Tương tác Duyệt Vùng PII](./tuan7.md)**
* **[Tuần 8: Làm sạch Dữ liệu Ẩn, Khóa Snapshot Duyệt & Triển khai Demo Server](./tuan8.md)**
* **[Tuần 9: Verification Engine Độc Lập, Điều Phối Xuất An Toàn & E2E Flow](./tuan9.md)**
* **[Tuần 10: Hardening Hệ Thống, Kiểm Thử An Toàn Độc Lập & Đánh Giá Toàn Diện](./tuan10.md)**
* **[Tuần 11: Nghiệm Thu Phát Hành Toàn Diện, Runbook Vận Hành & Bàn Giao](./tuan11.md)**

