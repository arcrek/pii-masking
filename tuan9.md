# Kế hoạch & Phân chia công việc - Tuần 9
## Chủ đề: Verification Engine Độc Lập, Điều Phối Xuất An Toàn & E2E Flow

- **Giai đoạn**: `Phase 2 Completion (Cổng Nghiệm thu Core MVP)`
- **Mục tiêu tuần (Sprint Goal)**: Xây dựng trọn bộ Verification Engine độc lập gồm 6 chốt chặn: kiểm tra text còn sót (VER-01), kiểm tra ảnh & OCR đầu ra (VER-02), kiểm tra cấu trúc & dữ liệu ẩn (VER-03), kiểm tra độ toàn vẹn trang (VER-04), tổng hợp báo cáo kiểm định (VER-05), quét PII còn sót (VER-06). Xây dựng cổng chặn xuất an toàn BE-10, quản lý vòng đời và dọn file tạm (BE-11), giao diện xuất/tải kết quả (FE-11), giao diện xóa tài liệu (FE-12), kiểm thử luồng sản phẩm E2E trọn vẹn (QA-02).

---

## Bảng phân công công việc chi tiết trong tuần (Sprint Backlog)

| Mã Task | Tên công việc | Người thực hiện | Vai trò | Người Review | Người phối hợp | Độ ưu tiên | Quy mô | Tiêu chuẩn nghiệm thu (Acceptance Criteria) |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **VER-01** | Kiểm tra text còn sót | **Hoàng Thị Kiều Ly** | `CS2` | SE3 | - | `P1` | `L` | Phát hiện fixture chỉ phủ màu; không đánh fail nếu chuỗi trùng ở vùng được phép giữ |
| **VER-02** | Kiểm tra ảnh và OCR đầu ra | **Hoàng Thị Kiều Ly** | `CS2` | SE3 | SE4 | `P1` | `L` | Phát hiện pixel chưa xóa hoặc OCR layer còn sót; failure/inconclusive không thành pass |
| **VER-03** | Kiểm tra cấu trúc và dữ liệu ẩn | **Hoàng Thị Kiều Ly** | `CS2` | CS1 | - | `P1` | `L` | Fixture dữ liệu ẩn rò rỉ bị fail; công bố những cấu trúc được phép/không được phép còn lại |
| **VER-04** | Kiểm tra độ toàn vẹn đầu ra | **Hoàng Thị Kiều Ly** | `CS2` | SE3 | - | `P1` | `M` | File hỏng, trang thiếu và thay đổi ngoài vùng vượt tolerance bị phát hiện |
| **VER-05** | Tổng hợp kiểm tra và báo cáo | **Hoàng Thị Kiều Ly** | `CS2` | CS1 | - | `P0` | `M` | Bất kỳ fail/inconclusive bắt buộc đều chặn xuất; không tuyên bố hết PII; không tự cấp pass cho check chưa chạy |
| **VER-06** | Quét PII còn sót | **Hoàng Thị Kiều Ly** | `CS2` | ML1 | SE2;SE4 | `P1` | `M` | Gợi ý mới chưa được duyệt làm snapshot xuất mất hiệu lực và yêu cầu duyệt revision mới; không lặp lại gợi ý đã bị từ chối trên nội dung không đổi; không chứng minh hết PII |
| **BE-10** | Điều phối xuất và tải an toàn | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | - | `P0` | `L` | Chỉ phát hành khi mandatory checks đạt, revision còn hiệu lực và không có gợi ý mới chưa duyệt; kiểm tra dấu đã xóa ngay trước publish; không phát hành file tạm |
| **BE-11** | Vòng đời và xóa dữ liệu | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | - | `P0` | `L` | Xóa áp dụng cả tài liệu chưa xử lý/xuất; đánh dấu đã xóa, hủy job và dọn mọi artifact; job không tái tạo file sau xóa |
| **FE-11** | Xuất và tải kết quả | **Đỗ Minh Tấn** | `SE1` | CS2 | - | `P1` | `M` | Chỉ tải artifact đúng revision đã kiểm tra; phân biệt lỗi với không phát hiện thêm PII |
| **FE-12** | Xóa tài liệu | **Đỗ Minh Tấn** | `SE1` | CS2 | - | `P1` | `S` | Sau xóa không mở được bản gốc, preview hoặc kết quả; hiển thị tiến trình xóa nếu chưa xong |
| **QA-02** | E2E luồng sản phẩm | **Đỗ Minh Tấn** | `SE1` | CS2 | SE2;SE3;SE4 | `P1` | `L` | Cả ba loại tài liệu chạy trọn luồng; trường hợp không có gợi ý vẫn cần duyệt |

---

## Phân phối công việc cụ thể cho 7 thành viên trong tuần

### SE2: Nguyễn Đinh Phú Vinh (Backend & System Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **BE-10** (Điều phối xuất và tải an toàn), **BE-11** (Vòng đời và xóa dữ liệu)
- **Phối hợp liên module**: **VER-06**, **QA-02**
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng cổng điều phối xuất và tải an toàn BE-10; hoàn thiện cơ chế dọn dẹp vòng đời dữ liệu và hủy job BE-11.

### SE1: Đỗ Minh Tấn (Frontend - ICT)

- **Công việc chính phụ trách (Owner)**: **FE-11** (Xuất và tải kết quả), **FE-12** (Xóa tài liệu), **QA-02** (E2E luồng sản phẩm)
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng giao diện xuất và tải kết quả (FE-11); giao diện xác nhận xóa dữ liệu (FE-12); phối hợp thực hiện kiểm thử E2E trọn luồng (QA-02).

### SE4: Dương Minh Đức (Data & PDF Engine - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Phối hợp liên module**: **VER-02**, **VER-06**, **QA-02**
- **Chi tiết hoạt động trong tuần**: Hỗ trợ CS2 trong việc phân tích các ca fail của verification engine; tinh chỉnh engine redaction nếu phát hiện điểm hở.

### SE3: Nguyễn Tuấn Vinh (Document / OCR - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **VER-01**, **VER-02**, **VER-04**
- **Phối hợp liên module**: **QA-02**
- **Chi tiết hoạt động trong tuần**: Hỗ trợ CS2 trong module OCR đầu ra (VER-02) và kiểm tra độ toàn vẹn hình học file xuất (VER-04).

### CS2: Hoàng Thị Kiều Ly (Security Verification - CS)

- **Công việc chính phụ trách (Owner)**: **VER-01** (Kiểm tra text còn sót), **VER-02** (Kiểm tra ảnh và OCR đầu ra), **VER-03** (Kiểm tra cấu trúc và dữ liệu ẩn), **VER-04** (Kiểm tra độ toàn vẹn đầu ra), **VER-05** (Tổng hợp kiểm tra và báo cáo), **VER-06** (Quét PII còn sót)
- **Trách nhiệm Review/Nghiệm thu**: **FE-11**, **FE-12**, **QA-02**
- **Chi tiết hoạt động trong tuần**: Chủ trì phát triển và kích hoạt toàn bộ hệ thống kiểm định độc lập: VER-01, VER-02, VER-03, VER-04, VER-05, VER-06.

### CS1: Nguyễn Quang Anh (Security Engineering - CS)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **VER-03**, **VER-05**, **BE-10**, **BE-11**
- **Chi tiết hoạt động trong tuần**: Rà soát điều kiện phát hành trong BE-10; kiểm tra việc xóa triệt để file trên đĩa và thu hồi phiên truy cập trong BE-11.

### ML1: Nguyễn Đăng Đạt (Machine Learning Lead - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **VER-06**
- **Chi tiết hoạt động trong tuần**: Phối hợp với CS2 tối ưu hóa thuật toán quét PII còn sót (VER-06) nhằm hạn chế tối đa báo động giả.

---

## Tiêu chuẩn nghiệm thu tuần (Definition of Done - DoD)

- [ ] Hệ thống kiểm định VER-01 -> VER-06 hoạt động độc lập: phát hiện được ngay lập tức các lỗi che phủ giả, OCR sót hoặc rò rỉ metadata.
- [ ] VER-05 tổng hợp báo cáo kiểm định (PASS / FAIL / INCONCLUSIVE); bất kỳ lỗi nào thuộc kiểm tra bắt buộc đều lập tức chặn xuất bản.
- [ ] VER-06 phát hiện các thực thể PII nghi vấn ngoài vùng đã xóa để yêu cầu mở vòng duyệt bổ sung nếu cần thiết.
- [ ] BE-10 đóng vai trò chốt chặn an toàn: chỉ cho phép tải artifact khi verification PASS 100% và snapshot revision còn hiệu lực.
- [ ] BE-11 xử lý xóa sạch dữ liệu theo yêu cầu: xóa file gốc, file tạm, cache OCR và database records, không thể phục hồi.
- [ ] FE-11 cho phép người dùng kích hoạt xuất, theo dõi kết quả kiểm định và tải file PDF an toàn về máy.
- [ ] FE-12 xử lý xóa tài liệu an toàn từ giao diện người dùng và vô hiệu hóa các liên kết tải cũ.
- [ ] QA-02 nghiệm thu trọn vẹn luồng E2E trên cả 3 loại tài liệu (native, scan, mixed) từ lúc tải lên đến khi tải file sạch về.

---

## Rủi ro kỹ thuật & Điều kiện tiên quyết (Dependencies & Risks)

- **Các phụ thuộc cần hoàn thành từ tuần trước**: BE-03, BE-05, BE-07, BE-09, DATA-04, DATA-05, FE-10, ML-06, OPS-02, RED-07.
- **Nguyên tắc an toàn**: Luôn tuân thủ nguyên tắc không can thiệp đè lên file gốc, đảm bảo tính bất biến của dữ liệu và kiểm tra chặt chẽ trước khi xuất bản.
