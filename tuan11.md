# Kế hoạch & Phân chia công việc - Tuần 11
## Chủ đề: Nghiệm Thu Phát Hành Toàn Diện, Runbook Vận Hành & Bàn Giao

- **Giai đoạn**: `Phase 4: Release acceptance & Final Delivery`
- **Mục tiêu tuần (Sprint Goal)**: Tổ chức nghiệm thu phát hành chính thức toàn bộ dự án với tập kiểm thử cố định và tiêu chuẩn đóng cổng (QA-07), xây dựng quy trình phát hành, rollback, dọn dẹp và runbook vận hành chuẩn (OPS-05). Toàn bộ 7 thành viên hoàn thiện báo cáo kỹ thuật chuyên môn của mảng mình phụ trách, đóng gói mã nguồn và tổ chức tổng duyệt buổi demo sản phẩm.

---

## Bảng phân công công việc chi tiết trong tuần (Sprint Backlog)

| Mã Task | Tên công việc | Người thực hiện | Vai trò | Người Review | Người phối hợp | Độ ưu tiên | Quy mô | Tiêu chuẩn nghiệm thu (Acceptance Criteria) |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **QA-07** | Nghiệm thu phát hành | **Hoàng Thị Kiều Ly** | `CS2` | CS1 | ML1;SE1;SE2;SE3;SE4 | `P1` | `L` | Các gate bắt buộc đạt; có bằng chứng, giới hạn được công bố và kịch bản demo tái lập |
| **OPS-05** | Phát hành, rollback và dọn dữ liệu | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | SE4 | `P1` | `M` | Rollback đã thử; người vận hành biết xử lý job lỗi; backup không giữ file ngược chính sách xóa |

---

## Phân phối công việc cụ thể cho 7 thành viên trong tuần

### SE2: Nguyễn Đinh Phú Vinh (Backend & System Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **OPS-05** (Phát hành, rollback và dọn dữ liệu)
- **Phối hợp liên module**: **QA-07**
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng tài liệu runbook vận hành, quy trình rollback và backup/restore hệ thống (OPS-05). Tổng hợp tài liệu kiến trúc Backend & API docs.

### SE1: Đỗ Minh Tấn (Frontend - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Phối hợp liên module**: **QA-07**
- **Chi tiết hoạt động trong tuần**: Hoàn thiện tài liệu hướng dẫn người dùng cuối (User Manual); chuẩn bị kịch bản và dữ liệu mẫu để trình diễn trực tiếp giao diện Web.

### SE4: Dương Minh Đức (Data & PDF Engine - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Phối hợp liên module**: **QA-07**, **OPS-05**
- **Chi tiết hoạt động trong tuần**: Hoàn thiện báo cáo kỹ thuật Redaction Engine; tổng kết các thuật toán xử lý PDF stream và hướng dẫn mở rộng trong tương lai.

### SE3: Nguyễn Tuấn Vinh (Document / OCR - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Phối hợp liên module**: **QA-07**
- **Chi tiết hoạt động trong tuần**: Hoàn thiện báo cáo kỹ thuật Document & OCR pipeline; tổng kết giải pháp xử lý hình học và dung sai tọa độ trên PDF.

### CS2: Hoàng Thị Kiều Ly (Security Verification - CS)

- **Công việc chính phụ trách (Owner)**: **QA-07** (Nghiệm thu phát hành)
- **Chi tiết hoạt động trong tuần**: Chủ trì ký duyệt biên bản nghiệm thu phát hành QA-07; phát hành báo cáo thẩm định an ninh và kiểm thử đối kháng độc lập (Penetration & Redaction Security Report).

### CS1: Nguyễn Quang Anh (Security Engineering - CS)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **QA-07**, **OPS-05**
- **Chi tiết hoạt động trong tuần**: Hoàn thiện báo cáo kỹ thuật Security Engineering; tổng kết chính sách bảo vệ dữ liệu PII, ma trận phân quyền và kiểm soát rủi ro bảo mật.

### ML1: Nguyễn Đăng Đạt (Machine Learning Lead - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Phối hợp liên module**: **QA-07**
- **Chi tiết hoạt động trong tuần**: Hoàn thiện Model Card và báo cáo kỹ thuật Machine Learning; lưu trữ notebook huấn luyện trên Colab Pro và hướng dẫn tái lập mô hình.

---

## Tiêu chuẩn nghiệm thu tuần (Definition of Done - DoD)

- [ ] Biên bản nghiệm thu QA-07 được ký duyệt: tất cả các cổng chất lượng bắt buộc (P0 gates) đều đạt 100%, các tiêu chí P1 hoàn tất có bằng chứng kiểm định.
- [ ] Runbook vận hành OPS-05 hoàn thiện: hướng dẫn chi tiết quy trình deploy, sao lưu dữ liệu, khôi phục thảm họa (disaster recovery) và rollback khi có sự cố.
- [ ] Hệ thống chạy mượt mà trên môi trường demo, sẵn sàng trình diễn các kịch bản thực tế (native, scan, mixed, vẽ vùng thủ công, tải file sạch).
- [ ] Bộ tài liệu kỹ thuật của 7 thành viên được tổng hợp đầy đủ vào repository.
- [ ] Kho lưu trữ git được dọn sạch nhánh thừa, gắn tag release v1.0.0 chính thức.

---

## Rủi ro kỹ thuật & Điều kiện tiên quyết (Dependencies & Risks)

- **Các phụ thuộc cần hoàn thành từ tuần trước**: BE-11, DATA-06, ML-07, OPS-02, OPS-03, OPS-04, QA-03, QA-04, QA-05, QA-06.
- **Nguyên tắc an toàn**: Luôn tuân thủ nguyên tắc không can thiệp đè lên file gốc, đảm bảo tính bất biến của dữ liệu và kiểm tra chặt chẽ trước khi xuất bản.
