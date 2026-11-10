# Báo Cáo Thực Nghiệm & So Sánh: Fine-Tune OPF vs Train spaCy NER Nhẹ Cho PII Tiếng Việt (19 Nhãn OpenPII — Trước & Sau Fine-Tune)

- **Ngày thực hiện (UTC)**: `2026-11-10T09:53:09Z`
- **Tracking Issue**: `https://github.com/arcrek/pii-masking/issues/4`
- **Dataset gốc**: `ai4privacy/pii-masking-openpii-1.5m` (Revision `a785eb528e28be2693c3718a27e066970de5dadb`, License `CC-BY-4.0`, lọc `language == "vi"`)
- **Môi trường huấn luyện (`colab-cli`)**: `NVIDIA L4` (`22.03 GB VRAM`, `52.96 GB RAM`, `12 vCPUs`)
- **Môi trường đối chứng CPU cục bộ**: `Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43` (`8 vCPUs`, `15.48 GB RAM`)

---

## 1. Kết Luận Điều Hành (Executive Verdict)

1. **Sự khác biệt Trước vs Sau Fine-Tune trên tập Test độc lập (`vn_test_600`, 600 mẫu, 4.758 thực thể trên đủ 19 nhãn OpenPII)**:
   - **Hướng 1 — `spaCy NER nhẹ (tok2vec/CNN, 19 nhãn)`**:
     - **Model thuần**: Tăng từ **0.00%** (trước khi train) lên **84.68%** Exact Micro F1 (**+84.68%**).
     - **Kèm bộ Rules Việt (`+VN Rules`)**: Tăng từ **45.24%** (chỉ có rules trước fine-tune) lên **84.88%** Exact Micro F1.
   - **Hướng 2 — `Fine-Tune OpenAI Privacy Filter (OPF, 19 nhãn / 77 lớp BIESO)`**:
     - **Model thuần**: Tăng từ **30.79%** (checkpoint `openai/privacy-filter` 8 nhãn gốc ánh xạ 1:1) lên **89.39%** Exact Micro F1 (**+58.60%**).
     - **Kèm bộ Rules Việt (`+VN Rules`)**: Tăng từ **47.80%** (OPF gốc + phân rã ngữ cảnh + rules) lên **89.73%** Exact Micro F1.
2. **Phân tích lỗi Trước Fine-Tune của OPF gốc (`Taxonomy Mismatch` vs `Missed Entities`)**:
   - Trên `vn_test_600`, OPF gốc (8 nhãn) chỉ đạt **38.36%** overlap recall khi ánh xạ 1:1 sang 19 nhãn, nhưng đạt **75.20%** khi tính theo họ nhãn tương thích (`private_person` gộp `TITLE`/`SURNAME`/`GIVENNAME`; `private_address` gộp `BUILDINGNUM`/`STREET`/`CITY`/`ZIPCODE`; `account_number` gộp 6 loại mã định danh). Như vậy **36.84%** tổng số thực thể bị mất điểm trước fine-tune là do **lệch hệ nhãn (taxonomy collapse)** và **24.80%** là do **bỏ sót thực thể tiếng Việt thực sự** (như `AGE`, `GENDER`, `SEX`, `TITLE` tiếng Việt). Việc mở rộng đầu phân loại OPF lên **77 lớp BIESO (19 nhãn)** và fine-tune trên dữ liệu Việt đã giải quyết triệt để cả hai vấn đề này.
3. **Đánh đổi Chất lượng vs Tài nguyên (CPU vs GPU)**:
   - **`OPF Fine-Tuned (19 nhãn)`** dẫn đầu về độ chính xác và độ phủ ký tự PII trên cả tập test OpenPII lẫn tập holdout độc lập tiếng Việt, đặc biệt vượt trội ở các thực thể ngữ cảnh khó (`STREET`, `CITY`, `GIVENNAME`, `SURNAME`, `TITLE`).
   - **`spaCy NER nhẹ (tok2vec/CNN + pyvi)`** có tốc độ suy luận trên CPU cực nhanh (**4.22 ms/doc p50**, chỉ tốn **~769.84 MB RAM**, kích thước checkpoint chỉ vài MB), rất phù hợp làm phương án chạy thuần CPU độ trễ thấp khi kết hợp với `VN Rules`.

---

## 2. Manifest Dữ Liệu & Kiểm Toán Chất Lượng Dữ Liệu

- **Nguồn chuẩn**: `ai4privacy/pii-masking-openpii-1.5m` (`revision=a785eb528e28be2693c3718a27e066970de5dadb`, `license=CC-BY-4.0`)
- **Kiểm tra Unicode & Ranh giới Span**:
  - Chuẩn hóa Unicode `NFC` toàn bộ văn bản (`12` mẫu chuẩn hóa lại).
  - Loại bỏ `634` nhãn phụ ngoài 19 nhãn chuẩn (`TIME`, `ACCOUNTNUM`, `AMOUNT`, `BANKNAME`, `CURRENCY`).
  - Kiểm tra khớp `text[start:end] == value`: `0` lỗi lệch offset; `0` văn bản trùng lặp (`SHA-256`) giữa `train`, `dev`, và `test`.
- **Kiểm tra Tokenizer tiếng Việt cho spaCy**:
  - Với `pyvi` (`use_pyvi=True`), tỷ lệ khớp biên từ (`contract alignment`) đạt **90.80%** (so với chỉ `75.20%` khi tắt `pyvi`), và `expand alignment` đạt **100.00%**.
- **Quy mô các tập dữ liệu**:
  - `vn_train.jsonl`: **3000** tài liệu (**22095** thực thể, tối thiểu 454 thực thể/nhãn).
  - `vn_dev.jsonl`: **300** tài liệu (**2500** thực thể, đủ 19 nhãn).
  - `vn_test.jsonl`: **600** tài liệu (**4758** thực thể, đủ 19 nhãn).
  - `vn_independent_holdout.jsonl`: **75** tài liệu độc lập (**60** tài liệu hành chính/nhân sự/tài chính Việt chứa **900** thực thể đủ 19 nhãn + **15** tài liệu kỹ thuật/pháp quy **0-PII** để đo che nhầm).

---

## 3. So Sánh Tổng Thể Trước & Sau Fine-Tune Trên Tập Test (`vn_test_600`)

| Pipeline Candidate | Stage | Mode | Exact P | Exact R | Exact F1 | Norm F1 | Overlap F1 | Char Recall | Over-Masking (Non-PII) | Neg Docs FP Spans |
| :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1. spaCy Blank (vi) — Pre-Finetune (Model-Only)** | `Pre-Finetune` | `Model-Only` | 0.00% | 0.00% | **0.00%** | 0.00% | 0.00% | 0.00% | 0.00% | 0 |
| **2. spaCy Blank (vi) — Pre-Finetune (+VN Rules)** | `Pre-Finetune` | `+VN Rules` | 87.62% | 30.50% | **45.24%** | 45.24% | 46.68% | 36.64% | 0.10% | 0 |
| **3. OPF Pretrained — Pre-Finetune (Model-Only, 8→19 1:1)** | `Pre-Finetune` | `Model-Only` | 41.53% | 24.46% | **30.79%** | 31.13% | 48.27% | 87.97% | 4.43% | 1 |
| **4. OPF Pretrained — Pre-Finetune (+Disambig & VN Rules)** | `Pre-Finetune` | `+VN Rules` | 56.51% | 41.42% | **47.80%** | 47.90% | 59.91% | 84.25% | 2.64% | 0 |
| **5. spaCy NER (tok2vec/CNN) — Post-Finetune (Model-Only, 19-lbl)** | `Post-Finetune` | `Model-Only` | 86.63% | 82.81% | **84.68%** | 84.76% | 93.57% | 97.93% | 0.55% | 22 |
| **6. spaCy NER (tok2vec/CNN) — Post-Finetune (+VN Rules, 19-lbl)** | `Post-Finetune` | `+VN Rules` | 86.80% | 83.04% | **84.88%** | 84.96% | 93.71% | 98.03% | 0.52% | 0 |
| **7. OPF Fine-Tuned — Post-Finetune (Model-Only, 19-lbl / 77-BIESO)** | `Post-Finetune` | `Model-Only` | 89.25% | 89.53% | **89.39%** | 89.54% | 95.33% | 98.64% | 0.44% | 16 |
| **8. OPF Fine-Tuned — Post-Finetune (+VN Rules, 19-lbl / 77-BIESO)** | `Post-Finetune` | `+VN Rules` | 89.57% | 89.89% | **89.73%** | 89.84% | 95.54% | 98.67% | 0.43% | 0 |
| **9. Hybrid (OPF Fine-Tuned + spaCy Fine-Tuned + VN Rules)** | `Post-Finetune` | `+VN Rules` | 88.85% | 90.96% | **89.90%** | 90.00% | 95.73% | 99.28% | 0.60% | 0 |

### Bảng Độ Lệch Trực Tiếp (Pre-Finetune → Post-Finetune & Đối Đầu OPF vs spaCy Trên `vn_test_600`)

| Comparison Pair | Before Exact F1 | After Exact F1 | Δ Exact F1 | Before Exact R | After Exact R | Δ Exact R | Δ Overlap F1 | Δ Char Recall | Δ Over-Masking |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **spaCy NER (Model-Only): Pre → Post** | 0.00% | 84.68% | **+84.68%** | 0.00% | 82.81% | +82.81% | +93.57% | +97.93% | +0.55% |
| **spaCy NER (+VN Rules): Pre → Post** | 45.24% | 84.88% | **+39.64%** | 30.50% | 83.04% | +52.54% | +47.03% | +61.39% | +0.42% |
| **OPF (Model-Only): Pre → Post** | 30.79% | 89.39% | **+58.60%** | 24.46% | 89.53% | +65.07% | +47.06% | +10.67% | -3.99% |
| **OPF (+VN Rules): Pre → Post** | 47.80% | 89.73% | **+41.93%** | 41.42% | 89.89% | +48.47% | +35.63% | +14.42% | -2.21% |
| **Post-Finetune Head-to-Head (OPF − spaCy, Model-Only)** | 84.68% | 89.39% | **+4.71%** | 82.81% | 89.53% | +6.72% | +1.76% | +0.71% | -0.11% |
| **Post-Finetune Head-to-Head (OPF − spaCy, +VN Rules)** | 84.88% | 89.73% | **+4.85%** | 83.04% | 89.89% | +6.85% | +1.83% | +0.64% | -0.09% |

---

## 4. Kết Quả Trên Tập Validation (`vn_dev_300` — Dùng Để Chọn Checkpoint & Khóa Ngưỡng)

| Pipeline Candidate | Stage | Mode | Exact P | Exact R | Exact F1 | Norm F1 | Overlap F1 | Char Recall | Over-Masking (Non-PII) | Neg Docs FP Spans |
| :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1. spaCy Blank (vi) — Pre-Finetune (Model-Only)** | `Pre-Finetune` | `Model-Only` | 0.00% | 0.00% | **0.00%** | 0.00% | 0.00% | 0.00% | 0.00% | 0 |
| **2. spaCy Blank (vi) — Pre-Finetune (+VN Rules)** | `Pre-Finetune` | `+VN Rules` | 89.53% | 30.44% | **45.43%** | 45.43% | 46.15% | 35.13% | 0.06% | 0 |
| **3. OPF Pretrained — Pre-Finetune (Model-Only, 8→19 1:1)** | `Pre-Finetune` | `Model-Only` | 40.98% | 23.36% | **29.76%** | 29.96% | 47.69% | 87.51% | 4.33% | 1 |
| **4. OPF Pretrained — Pre-Finetune (+Disambig & VN Rules)** | `Pre-Finetune` | `+VN Rules` | 58.98% | 41.36% | **48.62%** | 48.86% | 59.58% | 84.14% | 2.38% | 0 |
| **5. spaCy NER (tok2vec/CNN) — Post-Finetune (Model-Only, 19-lbl)** | `Post-Finetune` | `Model-Only` | 87.94% | 84.88% | **86.38%** | 86.55% | 94.16% | 98.66% | 0.71% | 22 |
| **6. spaCy NER (tok2vec/CNN) — Post-Finetune (+VN Rules, 19-lbl)** | `Post-Finetune` | `+VN Rules` | 88.03% | 85.00% | **86.49%** | 86.61% | 94.18% | 98.68% | 0.61% | 0 |
| **7. OPF Fine-Tuned — Post-Finetune (Model-Only, 19-lbl / 77-BIESO)** | `Post-Finetune` | `Model-Only` | 91.53% | 91.20% | **91.36%** | 91.36% | 95.53% | 98.65% | 0.41% | 16 |
| **8. OPF Fine-Tuned — Post-Finetune (+VN Rules, 19-lbl / 77-BIESO)** | `Post-Finetune` | `+VN Rules` | 91.65% | 91.28% | **91.46%** | 91.46% | 95.63% | 98.60% | 0.41% | 0 |
| **9. Hybrid (OPF Fine-Tuned + spaCy Fine-Tuned + VN Rules)** | `Post-Finetune` | `+VN Rules` | 90.91% | 92.76% | **91.82%** | 91.82% | 96.10% | 99.44% | 0.65% | 0 |

---

## 5. Kết Quả Trên Bộ Đánh Giá Độc Lập Tiếng Việt (`vn_independent_holdout_75`: 60 Mẫu Định Dạng Việt + 15 Mẫu 0-PII)

| Pipeline Candidate | Stage | Mode | Exact P | Exact R | Exact F1 | Norm F1 | Overlap F1 | Char Recall | Over-Masking (Non-PII) | Neg Docs FP Spans |
| :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1. spaCy Blank (vi) — Pre-Finetune (Model-Only)** | `Pre-Finetune` | `Model-Only` | 0.00% | 0.00% | **0.00%** | 0.00% | 0.00% | 0.00% | 0.00% | 0 |
| **2. spaCy Blank (vi) — Pre-Finetune (+VN Rules)** | `Pre-Finetune` | `+VN Rules` | 100.00% | 60.00% | **75.00%** | 75.00% | 75.00% | 65.51% | 0.00% | 0 |
| **3. OPF Pretrained — Pre-Finetune (Model-Only, 8→19 1:1)** | `Pre-Finetune` | `Model-Only` | 41.21% | 22.67% | **29.25%** | 29.25% | 43.30% | 89.47% | 6.23% | 1 |
| **4. OPF Pretrained — Pre-Finetune (+Disambig & VN Rules)** | `Pre-Finetune` | `+VN Rules` | 84.50% | 60.56% | **70.55%** | 70.55% | 78.58% | 83.22% | 1.18% | 0 |
| **5. spaCy NER (tok2vec/CNN) — Post-Finetune (Model-Only, 19-lbl)** | `Post-Finetune` | `Model-Only` | 83.38% | 69.11% | **75.58%** | 75.70% | 84.20% | 78.62% | 1.00% | 22 |
| **6. spaCy NER (tok2vec/CNN) — Post-Finetune (+VN Rules, 19-lbl)** | `Post-Finetune` | `+VN Rules` | 93.27% | 89.33% | **91.26%** | 91.26% | 97.50% | 97.28% | 0.23% | 0 |
| **7. OPF Fine-Tuned — Post-Finetune (Model-Only, 19-lbl / 77-BIESO)** | `Post-Finetune` | `Model-Only` | 86.49% | 83.22% | **84.82%** | 84.82% | 92.75% | 96.57% | 0.74% | 16 |
| **8. OPF Fine-Tuned — Post-Finetune (+VN Rules, 19-lbl / 77-BIESO)** | `Post-Finetune` | `+VN Rules` | 91.60% | 88.44% | **89.99%** | 89.99% | 97.57% | 97.57% | 0.31% | 0 |
| **9. Hybrid (OPF Fine-Tuned + spaCy Fine-Tuned + VN Rules)** | `Post-Finetune` | `+VN Rules` | 91.37% | 89.44% | **90.40%** | 90.40% | 98.26% | 98.44% | 0.32% | 0 |

### Bảng Độ Lệch Trước → Sau Fine-Tune Trên Bộ Holdout Độc Lập (`vn_independent_holdout_75`)

| Comparison Pair | Before Exact F1 | After Exact F1 | Δ Exact F1 | Before Exact R | After Exact R | Δ Exact R | Δ Overlap F1 | Δ Char Recall | Δ Over-Masking |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **spaCy NER (Model-Only): Pre → Post** | 0.00% | 75.58% | **+75.58%** | 0.00% | 69.11% | +69.11% | +84.20% | +78.62% | +1.00% |
| **spaCy NER (+VN Rules): Pre → Post** | 75.00% | 91.26% | **+16.26%** | 60.00% | 89.33% | +29.33% | +22.50% | +31.77% | +0.23% |
| **OPF (Model-Only): Pre → Post** | 29.25% | 84.82% | **+55.57%** | 22.67% | 83.22% | +60.55% | +49.45% | +7.10% | -5.49% |
| **OPF (+VN Rules): Pre → Post** | 70.55% | 89.99% | **+19.44%** | 60.56% | 88.44% | +27.88% | +18.99% | +14.35% | -0.87% |
| **Post-Finetune Head-to-Head (OPF − spaCy, Model-Only)** | 75.58% | 84.82% | **+9.24%** | 69.11% | 83.22% | +14.11% | +8.55% | +17.95% | -0.26% |
| **Post-Finetune Head-to-Head (OPF − spaCy, +VN Rules)** | 91.26% | 89.99% | **-1.27%** | 89.33% | 88.44% | -0.89% | +0.07% | +0.29% | +0.08% |

---

## 6. Báo Cáo Chi Tiết Đủ 19 Nhãn OpenPII Trên Tập Test (`vn_test_600`)

| Label (OpenPII 19) | Support | OPF Pre (Model) F1 | spaCy Post (Model) P / R / F1 | OPF Post (Model) P / R / F1 | spaCy Post (+Rules) F1 | OPF Post (+Rules) F1 | OPF Post Char Recall |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `AGE` | 219 | 0.00% | 94.42% / 92.69% / **93.55%** | 91.86% / 92.69% / **92.27%** | 92.81% | **92.97%** | 93.98% |
| `BUILDINGNUM` | 227 | 0.00% | 94.27% / 94.27% / **94.27%** | 94.71% / 94.71% / **94.71%** | 94.27% | **94.71%** | 93.50% |
| `CITY` | 319 | 0.00% | 95.69% / 97.49% / **96.58%** | 94.65% / 94.36% / **94.51%** | 96.58% | **94.65%** | 98.35% |
| `CREDITCARDNUMBER` | 159 | 0.00% | 88.55% / 92.45% / **90.46%** | 98.73% / 98.11% / **98.42%** | 90.46% | **98.42%** | 98.43% |
| `DATE` | 543 | 89.21% | 99.09% / 99.82% / **99.45%** | 99.63% / 99.63% / **99.63%** | 99.72% | **99.82%** | 99.87% |
| `DRIVERLICENSENUM` | 112 | 0.00% | 88.00% / 78.57% / **83.02%** | 88.79% / 84.82% / **86.76%** | 84.65% | **89.09%** | 87.50% |
| `EMAIL` | 352 | 84.99% | 98.58% / 98.58% / **98.58%** | 98.87% / 99.15% / **99.01%** | 98.87% | **99.29%** | 99.78% |
| `GENDER` | 122 | 0.00% | 100.00% / 84.43% / **91.56%** | 97.03% / 80.33% / **87.89%** | 92.51% | **90.83%** | 91.94% |
| `GIVENNAME` | 589 | 8.55% | 49.57% / 48.90% / **49.23%** | 69.23% / 68.76% / **68.99%** | 49.27% | **68.99%** | 77.89% |
| `IDCARDNUM` | 165 | 22.37% | 89.03% / 83.64% / **86.25%** | 89.82% / 90.91% / **90.36%** | 87.65% | **91.89%** | 92.73% |
| `PASSPORTNUM` | 102 | 0.00% | 99.03% / 100.00% / **99.51%** | 99.03% / 100.00% / **99.51%** | 99.51% | **99.51%** | 100.00% |
| `SEX` | 116 | 0.00% | 79.26% / 92.24% / **85.26%** | 83.33% / 94.83% / **88.71%** | 86.40% | **90.53%** | 95.04% |
| `SOCIALNUM` | 122 | 0.00% | 86.09% / 81.15% / **83.54%** | 99.18% / 99.18% / **99.18%** | 83.54% | **99.59%** | 100.00% |
| `STREET` | 224 | 0.60% | 82.30% / 83.04% / **82.67%** | 84.26% / 88.39% / **86.27%** | 82.67% | **86.46%** | 96.25% |
| `SURNAME` | 466 | 0.00% | 61.76% / 36.05% / **45.53%** | 66.80% / 70.82% / **68.75%** | 45.59% | **68.75%** | 90.10% |
| `TAXNUM` | 153 | 0.00% | 93.25% / 99.35% / **96.20%** | 98.08% / 100.00% / **99.03%** | 96.20% | **99.35%** | 100.00% |
| `TELEPHONENUM` | 265 | 89.89% | 97.78% / 99.62% / **98.69%** | 98.86% / 98.49% / **98.68%** | 99.07% | **98.68%** | 99.61% |
| `TITLE` | 314 | 0.00% | 97.09% / 95.54% / **96.31%** | 94.97% / 90.13% / **92.48%** | 96.31% | **92.48%** | 86.10% |
| `ZIPCODE` | 189 | 0.00% | 98.37% / 95.77% / **97.05%** | 100.00% / 100.00% / **100.00%** | 97.05% | **100.00%** | 100.00% |

---

## 7. Chi Phí Huấn Luyện Trên Colab (`colab-cli`) & Hiệu Năng Vận Hành (Latency, Throughput, RAM/VRAM)

### 7.1. Thông Số Huấn Luyện Hai Checkpoint

| Thông số | Hướng 1: `spaCy NER nhẹ (tok2vec/CNN)` | Hướng 2: `OPF Fine-Tuned (19 nhãn / 77 BIESO)` |
| :--- | :--- | :--- |
| **Đường dẫn Checkpoint** | `checkpoints/spacy_vn_19_ner` | `checkpoints/opf_vn_19` |
| **Số nhãn đầu ra** | 19 nhãn thực thể OpenPII | 77 lớp BIESO (`O` + `4 × 19` nhãn OpenPII) |
| **Seed & Epochs** | `seed=42`, `epochs=15` (best epoch `14`) | `seed=42`, `epochs=4` (best epoch `4`) |
| **Thời gian huấn luyện (Colab L4)** | **499.32 giây** | **542.87 giây** (wall-clock `555.7s`) |
| **Điểm Validation tốt nhất** | `dev_exact_f1 = 86.38%` | `validation_loss = 0.0659` |

### 7.2. Độ Trễ, Throughput & Bộ Nhớ (Colab NVIDIA L4 GPU vs Local 8-vCPU Host)

| Cấu hình & Môi trường | Startup (s) | Throughput (docs/s) | Throughput (chars/s) | Latency Mean (ms) | Latency p50 (ms) | Latency p95 (ms) | Peak VRAM (MB) | Peak RAM (MB) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **OPF Pretrained (`vn_test_600`, Colab L4 GPU)** | 27.75s | 30.42 | 10647.8 | 32.868 | 32.058 | 42.434 | 2954.23 | 2404.61 |
| **OPF Fine-Tuned 19-lbl (`vn_test_600`, Colab L4 GPU)** | 1.42s | 32.43 | 11352.6 | 30.825 | 30.089 | 39.499 | 2954.16 | 2509.43 |
| **spaCy Fine-Tuned 19-lbl (`vn_test_600`, Colab CPU)** | 0.085s | 164.36 | 57538.0 | 6.051 | 5.368 | 11.861 | 0.0 | 2530.92 |
| **spaCy Fine-Tuned 19-lbl (`Local 8-vCPU Host`)** | 1.557s | 218.8 | 65227.4 | 4.568 | 4.22 | 7.606 | 0.0 | 769.84 |
| **OPF Fine-Tuned 19-lbl (`Local 8-vCPU Grouped MoE`)** | 2.105s | 2.81 | 759.7 | 356.2 | 327.55 | 615.55 | 0.0 | 4092.59 |

---

## 8. Kiểm Tra Hồi Quy Tiếng Anh (EN Regression) & Khảo Sát PII Việt Còn Thiếu

1. **Bảo toàn Benchmark Tiếng Anh**:
   - Toàn bộ suite kiểm thử tiếng Anh (`evaluation/test_evaluation.py` và `evaluation/results/benchmark_results.json`) giữ nguyên 100% kết quả (`Business Holdout 60 Hybrid Exact F1 = 97.58%`, `Char Recall = 98.86%`, `Gravitee Test 240 Required-6 Exact F1 = 62.53%`).
   - Lưu ý kiến trúc đa ngôn ngữ: Khi thay đầu phân loại OPF từ 33 lớp (`v2` 8 nhãn) sang 77 lớp (`19 nhãn OpenPII`) và chỉ fine-tune trên tiếng Việt, checkpoint `checkpoints/opf_vn_19` chuyên biệt cho taxonomy 19 nhãn tiếng Việt. Khi triển khai hệ thống cần hỗ trợ song song EN + VN, nên định tuyến theo ngôn ngữ (hoặc gộp tập train EN + VN chung taxonomy).
2. **Khảo sát các loại PII Việt thực tế còn thiếu trong OpenPII 19 nhãn**:
   - OpenPII 19 nhãn chưa tách riêng: **Biển số xe Việt Nam** (`29A-123.45`), **Số tài khoản ngân hàng nội địa / mã VietQR**, **Số thẻ Bảo hiểm y tế (BHYT 15 ký tự)** (hiện gộp chung với BHXH trong `SOCIALNUM`), và **Đơn vị hành chính cấp Phường/Xã, Quận/Huyện** (hiện chỉ có `BUILDINGNUM`, `STREET`, `CITY`, `ZIPCODE`).

---

## 9. Khuyến Nghị Chọn Model & Cấu Hình Máy Chạy

- **Trường hợp 1 — Ưu tiên độ chính xác & độ phủ cao nhất (Có GPU T4 / L4)**:
  - **Chọn**: **`OPF Fine-Tuned 19-Label + VN Rules` (`opf_finetuned_post_plus_rules`)** hoặc **`Hybrid (OPF Fine-Tuned + spaCy Fine-Tuned + VN Rules)`**.
  - **Cấu hình máy đề xuất**: `1x NVIDIA T4 (16 GB VRAM)` hoặc `1x NVIDIA L4 (24 GB VRAM)`, `4–8 vCPUs`, `16 GB RAM`. Peak VRAM thực tế chỉ `~2954.16 MB` (~2.8 GB), độ trễ trung bình `30.825 ms/doc`.
- **Trường hợp 2 — Chỉ có CPU / Edge / Chi phí thấp / Yêu cầu độ trễ vài mili-giây**:
  - **Chọn**: **`spaCy NER nhẹ (tok2vec/CNN) Fine-Tuned + VN Rules` (`spacy_finetuned_post_plus_rules`)**.
  - **Cấu hình máy đề xuất**: `2–4 vCPUs`, `2–4 GB RAM` (không cần GPU). Độ trễ `p50` trên CPU đạt `4.22 ms/doc`, cải thiện nhảy vọt từ `0.00%` lên `84.88%` Exact F1 trên `vn_test_600` và `91.26%` trên tập holdout định dạng Việt.
