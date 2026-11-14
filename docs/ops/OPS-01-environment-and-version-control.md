# OPS-01: Môi trường và Cấu hình Phiên bản (Environment & Version Control)

- **Mã công việc**: `OPS-01`
- **Chủ trì (Owner)**: `SE2` — Nguyễn Đinh Phú Vinh (Backend & System Lead)
- **Reviewer**: `CS1` — Nguyễn Quang Anh (Security Engineering)
- **Người phối hợp**: `ML1` — Nguyễn Đăng Đạt (Machine Learning Lead)
- **Milestone**: `Phase 1: Contracts and data foundations` (`P1`)
- **Trạng thái**: `DONE` (Hoàn thành và đã kiểm chứng tự động)

---

## 1. Mục tiêu và Tiêu chuẩn Nghiệm thu (Acceptance Criteria)

Theo đặc tả hệ thống tại `plans/261101-1815-mvp-function-breakdown/function-breakdown.md` và `tuan1.md`:
1. **Khởi chạy tái lập (Reproducible Runtime)**: Toàn bộ thành viên (Backend, Frontend, ML, Security, OCR, Data) có thể khởi chạy môi trường phát triển nhất quán trên máy cá nhân, server riêng và Google Colab Pro.
2. **Quản lý phiên bản Model và Config (Version Pinning)**: Cấu hình hệ thống, pipeline xử lý và các mô hình học máy (NER, OPF, Rule-based) được định danh phiên bản rõ ràng theo chuẩn Semantic Versioning (`x.y.z`), lưu vết trong `configs/models.json` và quản lý qua `ModelRegistry`.
3. **Bảo mật Secret & Dữ liệu nhạy cảm (Zero-Secret Hygiene)**: Không bao giờ commit credential, token, private key hoặc dữ liệu nhạy cảm vào git hay in raw secret/PII ra log/artifact. Cung cấp công cụ rà soát tự động `scripts/check_secrets.py`.

---

## 2. Cấu trúc Triển khai (Directory Layout)

```
.
├── config/
│   ├── __init__.py           # Export các module cấu hình trung tâm
│   ├── system_config.py      # Quản lý cấu hình runtime, giới hạn tài nguyên và bảo mật (tự động nạp .env)
│   ├── model_registry.py     # Registry quản lý danh mục và phiên bản mô hình NER/OPF
│   ├── logger.py             # Bộ lọc log an toàn, tự động che giấu token, CCCD, thẻ, SĐT và email
│   └── health.py             # Server kiểm tra sức khỏe và readiness cho container
├── configs/
│   └── models.json           # Catalog danh mục model versioned
├── docker/
│   └── Dockerfile            # Multi-stage Dockerfile chạy non-root user (appuser:10001)
├── docker-compose.yml        # Docker compose khởi chạy API server & Worker bất đồng bộ
├── docs/
│   └── ops/
│       └── OPS-01-environment-and-version-control.md  # Tài liệu này
├── scripts/
│   └── check_secrets.py      # Tool quét phát hiện credential/secret rò rỉ (hỗ trợ --staged và git hook)
├── tests/
│   └── test_ops01_environment.py # Test suite tự động cho cấu hình, registry, logger, scanner (22 tests)
├── storage/
│   ├── private/              # Thư mục lưu trữ PDF và dữ liệu nội bộ (được gitignore)
│   └── temp/                 # Thư mục chứa file tạm trong pipeline (được gitignore)
├── .env.example              # Template cấu hình biến môi trường an toàn (không chứa secret thật)
├── .gitignore                # Chặn triệt để file bí mật, cache và storage
├── .dockerignore            # Chặn rò rỉ file môi trường, git và cache vào Docker build context
├── Makefile                  # Các lệnh tiêu chuẩn phục vụ nhóm (setup, test, lint, docker, scan, hook)
├── pyproject.toml            # Khai báo chuẩn PEP 621, tool pytest, ruff
├── requirements.txt          # Danh mục thư viện chính thức đã pin phiên bản
└── requirements-dev.txt      # Danh mục thư viện phục vụ test, lint và static analysis
```

---

## 3. Hướng dẫn Khởi tạo Môi trường (Setup Guide)

### 3.1. Môi trường phát triển cục bộ (Local Development)

Yêu cầu tiên quyết: Python 3.10+ (khuyến nghị 3.11 hoặc 3.12).

1. **Tạo và kích hoạt môi trường ảo (virtualenv)**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Cài đặt thư viện phụ thuộc**:
   ```bash
   make setup
   # hoặc: pip install -r requirements-dev.txt
   ```

3. **Cấu hình biến môi trường**:
   ```bash
   cp .env.example .env
   # Chỉnh sửa .env nếu cần thay đổi cổng hoặc đường dẫn storage cục bộ
   ```

4. **Chạy kiểm thử xác thực môi trường**:
   ```bash
   make test
   # hoặc: pytest -v
   ```

### 3.2. Môi trường Google Colab Pro (Machine Learning Workflow)

Dành cho ML1 (Nguyễn Đăng Đạt) khi huấn luyện và fine-tune mô hình NER:
- File script điều phối: `evaluation/colab_train_and_infer_vn.py`
- Khi đồng bộ kết quả từ Colab về repo:
  - Chỉ commit các artifact metadata và báo cáo: `checkpoints/<model_name>/meta.json`, `config.cfg`, `finetune_summary.json`.
  - File weights lớn như `model.safetensors` (>100MB) đã được cấu hình trong `.gitignore` để tránh phình to git tree.
  - Cập nhật model version vào `configs/models.json` sau khi hoàn tất fine-tune.

### 3.3. Môi trường Container (Docker & Docker Compose)

Dành cho kiểm thử tích hợp và triển khai máy chủ:
- Xây dựng Docker image (multi-stage build, tách build dependencies và runtime):
  ```bash
  make docker-build
  ```
- Khởi động cụm dịch vụ API và Worker nền:
  ```bash
  make docker-up
  ```
- Kiểm tra logs:
  ```bash
  docker compose logs -f api
  ```
- Dừng hệ thống:
  ```bash
  make docker-down
  ```

---

## 4. Quản lý Phiên bản Mô hình và Cấu hình (Model & Config Pinning)

### 4.1. Semantic Versioning cho Hệ thống
- `SYSTEM_VERSION`: Phiên bản tổng thể của sản phẩm MVP (bắt đầu từ `0.1.0`).
- `API_VERSION`: Phiên bản REST API (`v1`).
- `PIPELINE_VERSION`: Phiên bản pipeline xử lý bóc tách - nhận dạng - xóa - kiểm tra (`1.0.0`).

### 4.2. Catalog Mô hình trong `configs/models.json`
Mỗi mô hình inference hoặc bộ quy tắc phải đăng ký đầy đủ thông tin:
- `id`: Mã định danh duy nhất (ví dụ: `spacy_vn_19_ner`, `opf_vn_19`, `vn_rules_19`).
- `version`: Phiên bản ngữ nghĩa (Semantic version: `1.0.0`).
- `framework`: Framework thực thi (`spacy`, `safetensors`, `regex`).
- `label_space`: Đường dẫn file schema nhãn (`checkpoints/opf_vn_19_label_space.json`).
- `label_count`: Số lượng nhãn hỗ trợ (chuẩn 19 nhãn tiếng Việt).

### 4.3. Truy xuất qua `ModelRegistry` trong mã nguồn
```python
from config.model_registry import get_model_registry

registry = get_model_registry()

# Lấy metadata của model
model_meta = registry.get_model("spacy_vn_19_ner", version="1.0.0")
print(model_meta.get_full_id())  # 'spacy_vn_19_ner:1.0.0'

# Kiểm tra tính toàn vẹn của các checkpoint trên ổ cứng
status = registry.verify_checkpoints()
assert status["spacy_vn_19_ner:1.0.0"] is True
```

---

## 5. Chính sách Bảo mật Secret & Ghi Log (Security & Secret Hygiene)

1. **Quy tắc bất di bất dịch**:
   - **Tuyệt đối không commit** file `.env`, file private key (`*.pem`, `*.key`), certificate hoặc token truy cập vào git.
   - Thư mục `storage/private` và `storage/temp` luôn được cô lập, không lưu tài liệu PDF của người dùng lên git.
2. **Công cụ quét mã tự động**:
   Chạy lệnh kiểm tra trước khi commit hoặc merge code:
   ```bash
   make check-secrets
   # hoặc: python3 scripts/check_secrets.py --path .
   ```
   Script sẽ tự động quét:
   - Các file bị cấm (như `.env`, `credentials.json`, `id_rsa`).
   - Các chuỗi khóa bí mật (AWS key, GitHub token, RSA Private key, hardcoded passwords).
3. **Safe Logger (`config.logger`)**:
   Khi ghi log hệ thống, luôn sử dụng logger được bọc bộ lọc `SafeFormatter`:
   - Tự động thay thế `Bearer <token>` thành `Bearer [REDACTED_TOKEN]`.
   - Tự động thay thế số thẻ tín dụng thành `[REDACTED_CARD]`.
   - Tự động thay thế số CCCD/CMND thành `[REDACTED_CCCD]`.

---

## 6. Quy chuẩn Nhánh và Commit (Branching & Git Convention)

Tuân thủ Conventional Commits chuẩn để đảm bảo lịch sử git rõ ràng:
- `feat(<scope>): <nội dung>` — Thêm chức năng mới.
- `fix(<scope>): <nội dung>` — Sửa lỗi.
- `docs(<scope>): <nội dung>` — Cập nhật tài liệu, kế hoạch.
- `chore(<scope>): <nội dung>` — Công việc bảo trì, cấu hình, dependency.
- `test(<scope>): <nội dung>` — Thêm hoặc sửa kiểm thử.
- `refactor(<scope>): <nội dung>` — Tái cấu trúc mã nguồn không thay đổi chức năng.

Tên nhánh:
- `feat/<mã-task>-<mô-tả-ngắn>` (ví dụ: `feat/ops-01-environment-and-versioning`)
- `fix/<mã-task>-<mô-tả-ngắn>`
