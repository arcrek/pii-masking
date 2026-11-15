# DATA-04: Bộ Tài Liệu PDF Chuẩn (Gold Standard PDF Suite)

- **Mã công việc**: `DATA-04`
- **Chủ trì (Owner)**: `SE4` — Dương Minh Đức (Data & PDF Engine Lead)
- **Người nghiệm thu (Reviewer)**: `SE3` — Nguyễn Tuấn Vinh (Document / OCR Lead)
- **Người phối hợp**: `SE1` — Đỗ Minh Tấn (Frontend Lead), `CS2` — Hoàng Thị Kiều Ly (Security Verification)
- **Milestone**: `Phase 2: Core product MVP` (`P1`)
- **Trạng thái**: `DONE` (Đã sinh dữ liệu, đã kiểm thử tự động đạt 7/7 test cases)

---

## 1. Mục Tiêu và Tiêu Chuẩn Nghiệm Thu (Acceptance Criteria)

Theo đặc tả hệ thống tại `plans/261101-1815-mvp-function-breakdown/function-breakdown.md` và `tuan3.md`:
1. **Dữ liệu Held-out Độc lập**: Tuyệt đối không sử dụng văn bản từ tập huấn luyện (`vn_train.jsonl`); 100% tài liệu được trích xuất từ các nguồn held-out độc lập (`vn_independent_holdout.jsonl` và `business_holdout_60.jsonl`).
2. **Bao phủ Đa dạng 4 Loại Tài liệu**:
   - **Native PDF**: Vector text sắc nét, font TrueType chuẩn, định dạng văn bản hành chính, hợp đồng và bảng biểu.
   - **Scanned PDF**: Tài liệu ảnh scan ở 2 mức phân giải tiêu chuẩn (150 DPI và 300 DPI), có độ nghiêng xoay (skew $\pm 0.8^\circ \to \pm 1.2^\circ$), nhiễu hạt và mờ biên.
   - **Mixed PDF**: Văn bản native có chèn ảnh raster (con dấu đỏ công chứng `CÔNG CHỨNG` và chữ ký mực xanh dạng vector/raster).
   - **Handwriting PDF**: Mẫu đơn có trường thông tin viết tay giả lập (bằng font cursive Segoe Script), gắn cờ `is_handwriting=True` để phục vụ kiểm thử tính năng khoanh vùng thủ công (`FE-09`).
3. **Ground Truth Chuẩn Từng Điểm (PDF Points)**:
   - Mỗi file PDF có 1 file JSON Ground Truth tương ứng trong `evaluation/gold_suite/annotations/`.
   - Tọa độ Bounding Box `[x0, y0, x1, y1]` chuẩn PDF points (72 pt/inch), hệ tọa độ gốc top-left chuẩn hóa, kèm text và nhãn PII chính xác.
4. **Hỗ trợ Biến đổi Hình học**: Bao gồm tài liệu khổ ngang (Landscape) và tài liệu xoay góc (`Rotation: 90°` và `Rotation: 270°`) để kiểm thử triệt để lỗi đảo ngược tọa độ.

---

## 2. Thống Kê Phân Bố Dữ Liệu Bộ PDF Chuẩn

Bộ dữ liệu được tạo bởi `engine/data/gold_suite_builder.py` và lưu trữ tại `evaluation/gold_suite/`:

| Chỉ số tổng quan | Giá trị thực tế | Ghi chú |
| :--- | :---: | :--- |
| **Tổng số file PDF** | **40 tài liệu** | 20 tài liệu Tiếng Việt (`vi`) + 20 tài liệu Tiếng Anh (`en`) |
| **Tổng số trang** | **40 trang** | Khổ chuẩn A4 Portrait (595.32 x 841.92 pt) & A4 Landscape (841.92 x 595.32 pt) |
| **Tổng số thực thể PII (Ground Truth)** | **305 thực thể** | Trung bình ~7.6 thực thể / tài liệu |
| **Độ bao phủ nhãn** | **Đầy đủ 19 nhãn OpenPII** | Bao quát 6 nhóm PII: Tên, SĐT, Email, Địa chỉ, Ngày sinh, Mã định danh |

### 2.1. Phân bố theo Định dạng Tài liệu (Document Type Distribution)
- **Native PDF**: **16 tài liệu** (gồm 12 tài liệu văn bản chuẩn + 2 tài liệu bảng biểu khổ ngang Landscape + 2 tài liệu xoay trang 90° và 270°).
- **Scanned PDF**: **12 tài liệu** (6 tài liệu 150 DPI + 6 tài liệu 300 DPI; mô phỏng độ nghiêng và suy giảm chất lượng quét).
- **Mixed PDF**: **8 tài liệu** (Hợp đồng có con dấu tròn đỏ và chữ ký scan nhúng trong luồng trang).
- **Handwriting PDF**: **4 tài liệu** (Đơn đăng ký cư trú, bằng lái, hồ sơ bệnh án có chữ viết tay và chữ ký).

### 2.2. Phân bố theo Nhóm Nhãn PII Chính (Top Entity Labels)
- `GIVENNAME` / `SURNAME` / `TITLE` / `PERSON`: **72 thực thể**
- `IDCARDNUM` / `US_SSN` / `PASSPORTNUM`: **38 thực thể**
- `DATE` / `DATE_TIME`: **34 thực thể**
- `TELEPHONENUM` / `PHONE_NUMBER`: **28 thực thể**
- `EMAIL` / `EMAIL_ADDRESS`: **26 thực thể**
- `STREET` / `CITY` / `LOCATION`: **36 thực thể**
- Các nhãn khác (`AGE`, `GENDER`, `SEX`, `TAXNUM`,...): **71 thực thể**

---

## 3. Cấu Trúc Thư Mục và Quy Cách Dữ Liệu

```
evaluation/gold_suite/
├── manifest.json              # Catalog tổng hợp toàn bộ 40 tài liệu và phân bố nhãn
├── pdfs/                      # Thư mục chứa 40 file PDF nhị phân
│   ├── GOLD-NATIVE-VN-01.pdf ... GOLD-NATIVE-VN-06.pdf
│   ├── GOLD-NATIVE-EN-01.pdf ... GOLD-NATIVE-EN-06.pdf
│   ├── GOLD-SCAN-VN-01.pdf ... GOLD-SCAN-VN-06.pdf
│   ├── GOLD-SCAN-EN-01.pdf ... GOLD-SCAN-EN-06.pdf
│   ├── GOLD-MIXED-VN-01.pdf ... GOLD-MIXED-VN-04.pdf
│   ├── GOLD-MIXED-EN-01.pdf ... GOLD-MIXED-EN-04.pdf
│   ├── GOLD-HANDWRITING-VN-01.pdf, GOLD-HANDWRITING-VN-02.pdf
│   ├── GOLD-HANDWRITING-EN-01.pdf, GOLD-HANDWRITING-EN-02.pdf
│   ├── GOLD-LANDSCAPE-VN-01.pdf, GOLD-LANDSCAPE-EN-01.pdf
│   ├── GOLD-ROTATED-90-VN-01.pdf
│   └── GOLD-ROTATED-270-EN-01.pdf
└── annotations/               # Thư mục chứa 40 file JSON ground truth tương ứng
    ├── GOLD-NATIVE-VN-01.json ...
    └── ...
```

### Quy cách Schema file Annotation Ground Truth (`annotations/*.json`):
```json
{
  "doc_id": "GOLD-NATIVE-VN-01",
  "title": "Văn bản Hành chính & Nhân sự Số 01",
  "doc_type": "native",
  "language": "vi",
  "category": "administrative",
  "filename": "GOLD-NATIVE-VN-01.pdf",
  "page_count": 1,
  "pages": [
    {
      "page_index": 0,
      "width_pts": 595.32,
      "height_pts": 841.92,
      "rotation": 0,
      "dpi": 72,
      "has_image_overlay": false
    }
  ],
  "total_entities": 9,
  "entities": [
    {
      "entity_id": "GOLD-NATIVE-VN-01_ent_001",
      "label": "TITLE",
      "text": "Ông",
      "char_start": 47,
      "char_end": 50,
      "page_index": 0,
      "bounding_boxes": [
        {
          "x0": 54.0,
          "y0": 139.14,
          "x1": 74.0,
          "y1": 152.53,
          "coord_origin": "pdf_top_left"
        }
      ],
      "source_type": "native_text",
      "is_handwriting": false
    }
  ],
  "sha256": "4e1a0b3f...",
  "is_held_out": true,
  "provenance_source": "vn_independent_holdout"
}
```

---

## 4. Hướng Dẫn Sử Dụng Cho Các Nhóm Chuyên Môn

### 4.1. Dành cho `SE3` (Nguyễn Tuấn Vinh — Document / OCR)
- **Kiểm thử Bóc tách Native (`OCR-02`)**: Sử dụng 16 tài liệu `GOLD-NATIVE-*` để đối chiếu độ khớp character bounding box và text span trích xuất.
- **Kiểm thử OCR Engine & Deskew (`OCR-03`, `OCR-04`)**: Sử dụng 12 tài liệu `GOLD-SCAN-*` để đo độ chính xác OCR và thuật toán nắn thẳng ảnh xoay lệch (deskew).
- **Kiểm thử Xoay trang (`OCR-07`)**: Sử dụng `GOLD-ROTATED-90-VN-01` và `GOLD-ROTATED-270-EN-01` để thẩm định công thức biến đổi ma trận tọa độ hiển thị.

### 4.2. Dành cho `SE1` (Đỗ Minh Tấn — Frontend)
- **Tích hợp PDF Viewer (`FE-05`)**: Kiểm tra khả năng render mượt mà cả văn bản vector và ảnh scan.
- **Kiểm thử Overlay Bounding Box (`FE-06`)**: Nạp trực tiếp tọa độ trong `annotations/*.json` lên canvas overlay, kiểm tra độ bám dính khi zoom (100%, 150%, 200%) và xoay trang.
- **Kiểm thử Khoanh vùng Thủ công (`FE-09`)**: Mở các file `GOLD-HANDWRITING-*` để thử nghiệm tính năng người dùng dùng chuột kéo vẽ bounding box đè lên chữ viết tay.

### 4.3. Dành cho `CS2` (Hoàng Thị Kiều Ly — Security Verification)
- **Pentest Redaction Engine (`QA-03`, `VER-01..04`)**: Sử dụng toàn bộ 40 file làm bộ dữ liệu đầu vào chuẩn để chạy kịch bản xóa PII và kiểm tra rò rỉ dữ liệu qua các công cụ `pdftotext`, `pdfminer`, `qpdf`, và trích xuất ảnh `pdfimages`.

---

## 5. Kết Quả Kiểm Thử Tự Động (Automated Test Verification)

Bộ test suite tự động tại `tests/test_data04_gold_suite.py` đã vượt qua 100%:
- `test_01_manifest_overview_and_counts`: Kiểm tra manifest đủ 40 tài liệu, >300 thực thể. (**PASSED**)
- `test_02_all_pdfs_exist_and_open_cleanly`: Mở thành công 40 file PDF bằng PyMuPDF, kích thước > 1KB, không lỗi cấu trúc. (**PASSED**)
- `test_03_all_annotations_valid_and_schema_compliant`: 100% annotation file có tọa độ hợp lệ `x0 < x1`, `y0 < y1`, nằm trong biên trang. (**PASSED**)
- `test_04_coverage_of_required_categories`: Đủ 4 định dạng (Native, Scanned, Mixed, Handwriting) và 2 ngôn ngữ (VI, EN). (**PASSED**)
- `test_05_coverage_of_geometry_and_rotation_variations`: Có đủ Landscape và trang xoay 90°, 270°. (**PASSED**)
- `test_06_handwriting_annotations_flagged`: 100% thực thể viết tay được gắn cờ `is_handwriting=True`. (**PASSED**)
- `test_07_held_out_provenance_guarantee`: Xác thực nguồn gốc hoàn toàn độc lập từ held-out set. (**PASSED**)

Toàn bộ 172 files trong repo đã được quét qua `scripts/check_secrets.py` với kết quả: **0 rò rỉ credentials / secrets**.
Sẵn sàng để `SE3` (Nguyễn Tuấn Vinh) review và nghiệm thu.
