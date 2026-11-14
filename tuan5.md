# Kế hoạch & Phân chia công việc - Tuần 5
## Chủ đề: Huấn luyện NER trên Colab Pro, Hình học Tọa độ PDF & Storage An toàn

- **Giai đoạn**: `Phase 2: Core product MVP`
- **Mục tiêu tuần (Sprint Goal)**: Trực tiếp chạy Colab Pro fine-tune mô hình NER tiếng Anh và quản lý checkpoint (ML-05 - Đạt chạy chính, Phú Vinh hỗ trợ kiến trúc), lưu trữ và truy xuất tài liệu bất biến kèm private storage (BE-05), phát triển PDF Viewer hoàn chỉnh (FE-05), khôi phục thứ tự đọc layout đa cột (OCR-06), chuẩn hóa hệ tọa độ PDF và dung sai tolerance (OCR-07), đánh giá chất lượng trang OCR (OCR-08), hợp nhất vùng trùng và tính toán padding an toàn (RED-02).

---

## Bảng phân công công việc chi tiết trong tuần (Sprint Backlog)

| Mã Task | Tên công việc | Người thực hiện | Vai trò | Người Review | Người phối hợp | Độ ưu tiên | Quy mô | Tiêu chuẩn nghiệm thu (Acceptance Criteria) |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **BE-05** | Lưu và truy xuất tài liệu | **Nguyễn Đinh Phú Vinh** | `SE2` | CS1 | - | `P1` | `M` | Preview/bản gốc được phân quyền, không thực thi JavaScript/action/attachment hay tải tài nguyên ngoài; có checksum; storage private và response không content sniffing |
| **FE-05** | PDF viewer | **Đỗ Minh Tấn** | `SE1` | SE3 | - | `P1` | `L` | Native/scan/mixed mở được, đúng số trang; viewer không thực thi active content/tải ngoài; zoom/rotate không sửa tọa độ lưu |
| **OCR-06** | Khôi phục thứ tự đọc | **Nguyễn Tuấn Vinh** | `SE3` | CS2 | - | `P1` | `L` | Bộ mẫu layout đã chọn có chuỗi văn bản và mapping đúng; giới hạn layout được công bố |
| **OCR-07** | Chuẩn hóa tọa độ PDF | **Nguyễn Tuấn Vinh** | `SE3` | SE4 | - | `P0` | `L` | Kiểm tra trang xoay/crop/DPI khác nhau; round-trip điểm và vùng trong tolerance đã định nghĩa |
| **OCR-08** | Đánh giá chất lượng trang | **Nguyễn Tuấn Vinh** | `SE3` | ML1 | - | `P1` | `M` | Không kết luận không có PII từ OCR rỗng; lỗi nguồn/trang được BE và FE thể hiện |
| **ML-05** | Fine-tune và quản lý checkpoint | **Nguyễn Đăng Đạt** | `ML1` | SE4 | SE2;SE4 | `P1` | `L` | Có seed/config/log/version; resume thành công; chọn checkpoint bằng validation và chạy được trên server |
| **RED-02** | Hợp nhất vùng và padding | **Nguyễn Quang Anh** | `CS1` | CS2 | SE4 | `P1` | `M` | Không xóa vùng ngoài yêu cầu do merge tùy tiện; padding có ca ký tự sát mép |

---

## Phân phối công việc cụ thể cho 7 thành viên trong tuần

### SE2: Nguyễn Đinh Phú Vinh (Backend & System Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **BE-05** (Lưu và truy xuất tài liệu)
- **Phối hợp liên module**: **ML-05**
- **Chi tiết hoạt động trong tuần**: Chủ trì xây dựng kho lưu trữ tài liệu bất biến, private storage và sinh link preview an toàn (BE-05). Phối hợp cùng ML1 rà soát format checkpoint model để chuẩn bị serving.

### SE1: Đỗ Minh Tấn (Frontend - ICT)

- **Công việc chính phụ trách (Owner)**: **FE-05** (PDF viewer)
- **Chi tiết hoạt động trong tuần**: Chủ trì phát triển PDF Viewer (FE-05) với khả năng render chính xác các loại PDF, xử lý zoom/rotate đồng bộ với hệ tọa độ.

### SE4: Dương Minh Đức (Data & PDF Engine - ICT)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **OCR-07**, **ML-05**
- **Phối hợp liên module**: **ML-05**, **RED-02**
- **Chi tiết hoạt động trong tuần**: Hỗ trợ SE3 kiểm tra công thức chuyển đổi tọa độ trong OCR-07; nghiên cứu thuật toán xóa đối tượng PDF cho tuần tiếp theo.

### SE3: Nguyễn Tuấn Vinh (Document / OCR - ICT)

- **Công việc chính phụ trách (Owner)**: **OCR-06** (Khôi phục thứ tự đọc), **OCR-07** (Chuẩn hóa tọa độ PDF), **OCR-08** (Đánh giá chất lượng trang)
- **Trách nhiệm Review/Nghiệm thu**: **FE-05**
- **Chi tiết hoạt động trong tuần**: Phát triển thuật toán khôi phục thứ tự đọc (OCR-06); chuẩn hóa tọa độ bounding box PDF (OCR-07); xây dựng bộ đánh giá chất lượng OCR (OCR-08).

### CS2: Hoàng Thị Kiều Ly (Security Verification - CS)

- **Công việc chính phụ trách (Owner)**: *Không trực tiếp làm owner task phát triển mới trong tuần này (tập trung phối hợp, review và chuẩn bị chuyên môn)*
- **Trách nhiệm Review/Nghiệm thu**: **OCR-06**, **RED-02**
- **Chi tiết hoạt động trong tuần**: Kiểm tra tính an toàn của storage BE-05; rà soát thuật toán padding của RED-02 để đảm bảo không cắt xén thiếu ký tự nhạy cảm.

### CS1: Nguyễn Quang Anh (Security Engineering - CS)

- **Công việc chính phụ trách (Owner)**: **RED-02** (Hợp nhất vùng và padding)
- **Trách nhiệm Review/Nghiệm thu**: **BE-05**
- **Chi tiết hoạt động trong tuần**: Chủ trì phát triển thuật toán hợp nhất vùng trùng và tính toán khoảng đệm padding an toàn (RED-02). Rà soát chính sách bảo mật storage BE-05.

### ML1: Nguyễn Đăng Đạt (Machine Learning Lead - ICT)

- **Công việc chính phụ trách (Owner)**: **ML-05** (Fine-tune và quản lý checkpoint)
- **Trách nhiệm Review/Nghiệm thu**: **OCR-08**
- **Chi tiết hoạt động trong tuần**: Trực tiếp thực thi huấn luyện mô hình NER trên Colab Pro (ML-05), giám sát quá trình hội tụ, đánh giá trên validation set và xuất model weights.

---

## Tiêu chuẩn nghiệm thu tuần (Definition of Done - DoD)

- [ ] Mô hình NER được fine-tune thành công trên Colab Pro (ML-05), có log huấn luyện, validation loss giảm ổn định, lưu checkpoint tối ưu.
- [ ] Hệ thống lưu trữ BE-05 bảo vệ file gốc bất biến, tạo URL truy cập có hạn (signed URL), chặn MIME sniffing và tải ngoài.
- [ ] PDF Viewer (FE-05) hiển thị mượt mà tài liệu native/scan/mixed, hỗ trợ phóng to, thu nhỏ, xoay trang mà không làm lệch tọa độ nội bộ.
- [ ] OCR-06 khôi phục đúng thứ tự đọc cho văn bản nhiều cột và layout tài liệu phức tạp.
- [ ] OCR-07 chuẩn hóa toàn bộ bounding box về hệ tọa độ chuẩn của PDF (PDF user space units), xử lý trơn tru trang bị xoay 90/180/270 độ.
- [ ] OCR-08 gắn cờ cảnh báo đối với các trang chất lượng scan kém, độ tin cậy thấp để yêu cầu người dùng duyệt thủ công.
- [ ] RED-02 tự động hợp nhất các vùng chữ nhật liền kề/chồng lấn và áp dụng padding an toàn tránh hở viền ký tự.

---

## Rủi ro kỹ thuật & Điều kiện tiên quyết (Dependencies & Risks)

- **Các phụ thuộc cần hoàn thành từ tuần trước**: BE-04, CORE-02, ML-02, OCR-02, OCR-03, OCR-04, OCR-05, OPS-01, RED-01.
- **Nguyên tắc an toàn**: Luôn tuân thủ nguyên tắc không can thiệp đè lên file gốc, đảm bảo tính bất biến của dữ liệu và kiểm tra chặt chẽ trước khi xuất bản.
