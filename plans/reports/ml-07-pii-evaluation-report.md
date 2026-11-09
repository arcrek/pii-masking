# ML-07: PII Detection Model Evaluation & Fine-Tuning Decision Report

**Generated UTC**: `2026-11-09T15:26:35Z`  
**Scope**: English Business Documents (Forms, Invoices, Correspondence) — Text-Only Detection Evaluation  
**Candidates Evaluated**:
1. **OpenAI Privacy Filter (`openai/privacy-filter`)** — Unchanged Baseline (Viterbi decoding, primary 1:1 label mapping).
2. **Microsoft Presidio + spaCy (`en_core_web_lg`)** — Unchanged Baseline.
3. **OPF + Targeted Disambiguation & Rules (`opf_targeted_rules`)** — Disambiguates OPF `account_number` into `US_SSN`, `IBAN_CODE`, `CREDIT_CARD`, and `US_BANK_NUMBER`, plus deterministic extractors for SSN, Email, Phone, Date, and US Street Addresses.
4. **Presidio + Targeted Location Merge & Rules (`presidio_targeted_rules`)** — Merges fragmented `GPE`/`LOC` address spans and combines deterministic business regexes.
5. **Full Hybrid Pipeline (`hybrid_opf_presidio_rules`)** — Combines OPF + Presidio + Deterministic Business Rules.

---

## 1. Executive Decision: Do We Need to Fine-Tune for MVP?

### **Verdict: NO Fine-Tuning Required for MVP — Ship `OPF + Targeted Disambiguation & Rules` (or `Presidio + Targeted Rules` on CPU-Only Budget)**

1. **Neither unchanged baseline passes the MVP gate out-of-the-box**, NOT because the underlying neural weights lack representation capacity for English business text, but because of **taxonomy & span-boundary policy mismatches**:
   - **Unchanged `openai/privacy-filter`** achieves **0.00% exact recall on `US_SSN`** under strict 1:1 primary mapping because OPF's 8-label schema (`private_person`, `private_date`, `private_address`, `private_phone`, `private_email`, `account_number`, `secret`, `medical_Condition`) collapses `US_SSN`, `IBAN_CODE`, `CREDIT_CARD`, and invoice/bank numbers into a single `account_number` class. Even so, its **any-label character coverage on `US_SSN` is 98.36%** on the business holdout!
   - **Unchanged `Presidio + en_core_web_lg`** achieves **0.00% exact F1 on full street `LOCATION`** on the business holdout (`100.00%` partial overlap recall) because spaCy's `GPE`/`LOC`/`FAC` NER tags only city and state tokens while leaving street numbers and ZIP codes untagged, and over-masks non-PII business text at **10.30%** (21x higher over-masking than OPF's **0.49%**).
2. **With lightweight deterministic disambiguation and span-boundary rules (zero model weight training)**:
   - **`OPF + Targeted Disambiguation & Rules`** jumps from **76.72% → 96.39% micro Exact F1** (`96.49%` precision, `96.28%` recall), **98.58% Overlap F1** (`98.68%` precision, `98.47%` recall), **98.74% character-level PII recall**, and **99.40% character precision** with only **0.49% over-masking rate** on the 60-document Independent Business Holdout.
   - Under **partial/overlap span matching (IoU > 0)** and **character-level masking coverage**, `OPF + Targeted Rules` exceeds the **≥95% recall and ≥90% precision** target on **5 of 6 required labels** (`PERSON` 98.41% F1, `EMAIL_ADDRESS` 100.00% F1, `PHONE_NUMBER` 100.00% F1, `LOCATION` 95.45% F1, `DATE_TIME` 100.00% F1), with `US_SSN` at **100.00% precision and 93.44% recall** (96.61% F1; 98.36% character coverage).
   - **`Presidio + Targeted Rules`** jumps from **71.33% → 93.59% micro Exact F1** and passes **all 6 of 6 required MVP labels under Overlap matching** (`PERSON` 95.74% recall / 90.00% precision, `EMAIL_ADDRESS` 100% / 100%, `PHONE_NUMBER` 100% / 100%, `LOCATION` 100% recall / 95.59% precision, `DATE_TIME` 98.25% recall / 100% precision, `US_SSN` 100% / 100%) while running in **18.01 ms/doc on CPU** (37x faster than OPF on CPU), though with a higher non-PII over-masking rate (**10.12%** vs OPF's **0.49%**).
3. **When Fine-Tuning Would Become Necessary (Post-MVP Trigger Conditions)**:
   - Fine-tuning `openai/privacy-filter` (or a token classifier on `gravitee-io/pii-detection-dataset`) is **only justified if**:
     1. The product expands beyond the 6 core MVP labels to require native neural separation of all 25 Gravitee classes (specifically `AGE`, `COORDINATE`, `FINANCIAL`, `HONORIFIC`, `IMEI`, `MAC_ADDRESS`, `TITLE`, `US_LICENSE_PLATE`, where both OPF and Presidio score 0% without custom recognizers).
     2. Strict exact-boundary `PERSON` recall on noisy multi-source corpora (`urchade/synthetic-pii-ner-mistral-v1`, `beki/privy`) must exceed 95% without title/honorific boundary differences.

---

## 2. Benchmark Environment & Reproducibility Manifest

### 2.1 Hardware & Runtime Environment
- **Host OS / Kernel**: `Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43`
- **CPU**: `11th Gen Intel(R) Core(TM) i7-1185G7 @ 3.00GHz` (`8` logical vCPUs)
- **System RAM**: `15.48 GB`
- **Python / PyTorch**: Python `3.12.14`, PyTorch `2.15.0+cpu`
- **Colab Pro Provisioning Note**: `HTTP 503 Service Unavailable on POST https://colab.research.google.com/tun/m/assign (verified across L4, T4, and CPU runtimes; 0 compute units consumed; executed locally on 8-vCPU host)`
- **CPU MoE Optimization Discovery**: Stock `openai/privacy-filter` on CPU clones `[batch, 4, 640, 1280]` expert tensors per token (`6,154.42 ms/doc`). Grouping tokens by selected expert ID (`apply_grouped_moe_cpu_optimization` in `evaluation/run_benchmark.py`) reduced CPU inference latency by **9.05x** to **`679.69 ms/doc`** (`p50 = 654.61 ms`) while preserving MoE routing and `3.63 GB` peak RSS.

### 2.2 Dataset & Split Manifests
- **Dataset 1: Independent Business-Text Holdout (`evaluation/data/business_holdout_60.jsonl`)**
  - **SHA-256**: `a634d46d04b00e4bff6025c2dd0962bdc6d98748250f228b465bb90d96ba35f7`
  - **Composition**: 60 realistic English business documents (`20` HR/tax/onboarding forms, `20` B2B invoices & billing statements, `20` executive/legal/support correspondence emails).
  - **Ground-Truth Spans**: `457` character-verified spans (`DATE_TIME`: 114, `PERSON`: 94, `LOCATION`: 65, `EMAIL_ADDRESS`: 62, `PHONE_NUMBER`: 61, `US_SSN`: 61).
- **Dataset 2: Gravitee PII Detection (`gravitee-io/pii-detection-dataset`, 175,881 upstream rows)**
  - **Seed**: `42` (strictly disjoint `dev` and `test` splits stratified across all 25 labels and all 6 upstream sources)
  - **Dev Split (`gravitee_dev_120`)**: `120` docs (`sha256: 70dffd951dccb8c2130a48e2c9650466582118b86f5588b0ad41fbd980152166`)
  - **Test Split (`gravitee_test_240`)**: `240` docs (`sha256: 43bb69ad6468610173584a57c7db5a88d4d6d93d8816aaf0d23d2f833f7d1a5c`)
  - **Test Source Distribution**: `DataikuNLP/kiji-pii-training-data`: 14, `beki/privy`: 101, `gravitee/synthetic-llm-v1`: 13, `gretelai/gretel-pii-masking-en-v1`: 49, `gretelai/synthetic_pii_finance_multilingual`: 29, `urchade/synthetic-pii-ner-mistral-v1`: 34

---

## 3. Primary Evaluation: Independent Business-Text Holdout (60 Docs, 457 Spans)

### 3.1 Micro-Averaged Summary (Required 6 MVP Labels)

| Pipeline Variant | Exact Precision | Exact Recall | Exact F1 | Normalized F1 | Overlap Precision | Overlap Recall | Overlap F1 | Char PII Recall | Char PII Precision | Non-PII Over-Masking Rate | Exact Gate (6/6) | Overlap Gate (6/6) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **OpenAI Privacy Filter (Unchanged)** | 78.94% | 74.62% | **76.72%** | 77.62% | 87.50% | 82.71% | **85.04%** | **94.66%** | 99.37% | 0.49% | `1/6` | **`2/6`** |
| **Presidio + spaCy en_core_web_lg (Unchanged)** | 66.42% | 77.02% | **71.33%** | 71.73% | 84.91% | 98.47% | **91.19%** | **85.96%** | 87.25% | 10.30% | `3/6` | **`3/6`** |
| **OPF + Targeted Disambiguation & Rules** | 96.49% | 96.28% | **96.39%** | 97.04% | 98.68% | 98.47% | **98.58%** | **98.74%** | 99.40% | 0.49% | `3/6` | **`5/6`** |
| **Presidio + Targeted Location Merge & Rules** | 92.89% | 94.31% | **93.59%** | 94.03% | 97.20% | 98.69% | **97.94%** | **98.39%** | 88.85% | 10.12% | `4/6` | **`6/6`** |
| **Full Hybrid (OPF + Presidio + Rules)** | 92.93% | 94.97% | **93.94%** | 94.59% | 96.15% | 98.25% | **97.19%** | **99.43%** | 88.60% | 10.49% | `3/6` | **`4/6`** |

### 3.2 Per-Label Breakdown on Business Holdout (Required 6 MVP Labels — Target: Recall ≥ 95%, Precision ≥ 90%)

| Label (Support) | Metric Mode | OPF Baseline | Presidio Baseline | OPF + Targeted Rules | Presidio + Targeted Rules | Full Hybrid |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`PERSON`** (`n=94`) | Exact Span | P=92.63% R=93.62% (**93.12%** `MISS`) | P=73.53% R=79.79% (**76.53%** `MISS`) | P=92.63% R=93.62% (**93.12%** `MISS`) | P=75.00% R=79.79% (**77.32%** `MISS`) | P=79.81% R=88.30% (**83.84%** `MISS`) |
| **`PERSON`** (`n=94`) | Overlap (IoU>0) | P=97.89% R=98.94% (**98.41%** `PASS`) | P=88.24% R=95.74% (**91.84%** `MISS`) | P=97.89% R=98.94% (**98.41%** `PASS`) | P=90.00% R=95.74% (**92.78%** `PASS`) | P=88.46% R=97.87% (**92.93%** `MISS`) |
| **`EMAIL_ADDRESS`** (`n=62`) | Exact Span | P=98.39% R=98.39% (**98.39%** `PASS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=98.39% R=98.39% (**98.39%** `PASS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=98.39% R=98.39% (**98.39%** `PASS`) |
| **`EMAIL_ADDRESS`** (`n=62`) | Overlap (IoU>0) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=100.00% R=100.00% (**100.00%** `PASS`) |
| **`PHONE_NUMBER`** (`n=61`) | Exact Span | P=93.10% R=88.52% (**90.76%** `MISS`) | P=100.00% R=98.36% (**99.17%** `PASS`) | P=98.36% R=98.36% (**98.36%** `PASS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=98.36% R=98.36% (**98.36%** `PASS`) |
| **`PHONE_NUMBER`** (`n=61`) | Overlap (IoU>0) | P=96.55% R=91.80% (**94.12%** `MISS`) | P=100.00% R=98.36% (**99.17%** `PASS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=100.00% R=100.00% (**100.00%** `PASS`) |
| **`LOCATION`** (`n=65`) | Exact Span | P=29.46% R=50.77% (**37.29%** `MISS`) | P=0.00% R=0.00% (**0.00%** `MISS`) | P=89.55% R=92.31% (**90.91%** `MISS`) | P=88.24% R=92.31% (**90.23%** `MISS`) | P=85.92% R=93.85% (**89.71%** `MISS`) |
| **`LOCATION`** (`n=65`) | Overlap (IoU>0) | P=55.36% R=95.38% (**70.06%** `MISS`) | P=57.52% R=100.00% (**73.03%** `MISS`) | P=94.03% R=96.92% (**95.45%** `PASS`) | P=95.59% R=100.00% (**97.74%** `PASS`) | P=91.55% R=100.00% (**95.59%** `PASS`) |
| **`DATE_TIME`** (`n=114`) | Exact Span | P=100.00% R=92.11% (**95.89%** `MISS`) | P=71.21% R=82.46% (**76.42%** `MISS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=100.00% R=98.25% (**99.12%** `PASS`) | P=100.00% R=98.25% (**99.12%** `PASS`) |
| **`DATE_TIME`** (`n=114`) | Overlap (IoU>0) | P=100.00% R=92.11% (**95.89%** `MISS`) | P=84.85% R=98.25% (**91.06%** `MISS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=100.00% R=98.25% (**99.12%** `PASS`) | P=100.00% R=98.25% (**99.12%** `PASS`) |
| **`US_SSN`** (`n=61`) | Exact Span | P=0.00% R=0.00% (**0.00%** `MISS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=100.00% R=93.44% (**96.61%** `MISS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=100.00% R=93.44% (**96.61%** `MISS`) |
| **`US_SSN`** (`n=61`) | Overlap (IoU>0) | P=0.00% R=0.00% (**0.00%** `MISS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=100.00% R=93.44% (**96.61%** `MISS`) | P=100.00% R=100.00% (**100.00%** `PASS`) | P=100.00% R=93.44% (**96.61%** `MISS`) |

### 3.3 Business Holdout Slice Breakdown by Document Type (`form`, `invoice`, `correspondence`)

| Document Slice | Docs | Spans | Variant | Exact Precision | Exact Recall | Exact F1 | Overlap F1 | Char PII Recall | Over-Masking Rate |
| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`correspondence`** | 20 | 169 | OpenAI Privacy Filter (Unchanged) | 83.13% | 78.70% | **80.85%** | 88.15% | 96.15% | 0.81% |
| **`correspondence`** | 20 | 169 | Presidio + spaCy en_core_web_lg (Unchanged) | 67.19% | 76.33% | **71.47%** | 89.75% | 87.35% | 7.68% |
| **`correspondence`** | 20 | 169 | OPF + Targeted Disambiguation & Rules | 95.73% | 92.90% | **94.29%** | 97.90% | 98.35% | 0.81% |
| **`correspondence`** | 20 | 169 | Presidio + Targeted Location Merge & Rules | 94.55% | 92.31% | **93.41%** | 97.60% | 97.73% | 7.68% |
| **`correspondence`** | 20 | 169 | Full Hybrid (OPF + Presidio + Rules) | 93.90% | 91.12% | **92.49%** | 96.70% | 99.41% | 8.16% |
| **`form`** | 20 | 145 | OpenAI Privacy Filter (Unchanged) | 74.65% | 73.10% | **73.87%** | 84.32% | 96.17% | 0.03% |
| **`form`** | 20 | 145 | Presidio + spaCy en_core_web_lg (Unchanged) | 69.46% | 80.00% | **74.36%** | 92.95% | 86.11% | 10.41% |
| **`form`** | 20 | 145 | OPF + Targeted Disambiguation & Rules | 97.95% | 98.62% | **98.28%** | 99.66% | 99.93% | 0.03% |
| **`form`** | 20 | 145 | Presidio + Targeted Location Merge & Rules | 96.60% | 97.93% | **97.26%** | 99.32% | 99.09% | 9.94% |
| **`form`** | 20 | 145 | Full Hybrid (OPF + Presidio + Rules) | 97.96% | 99.31% | **98.63%** | 99.32% | 100.00% | 9.96% |
| **`invoice`** | 20 | 143 | OpenAI Privacy Filter (Unchanged) | 78.46% | 71.33% | **74.73%** | 82.05% | 91.60% | 0.57% |
| **`invoice`** | 20 | 143 | Presidio + spaCy en_core_web_lg (Unchanged) | 62.57% | 74.83% | **68.15%** | 91.08% | 84.33% | 13.33% |
| **`invoice`** | 20 | 143 | OPF + Targeted Disambiguation & Rules | 95.89% | 97.90% | **96.89%** | 98.27% | 97.97% | 0.57% |
| **`invoice`** | 20 | 143 | Presidio + Targeted Location Merge & Rules | 87.50% | 93.01% | **90.17%** | 96.95% | 98.41% | 13.24% |
| **`invoice`** | 20 | 143 | Full Hybrid (OPF + Presidio + Rules) | 87.18% | 95.10% | **90.97%** | 95.65% | 98.90% | 13.81% |

---

## 4. Secondary Benchmark: Held-Out Gravitee Test Split (`gravitee_test_240`, All 25 Labels)

### 4.1 Required-6 Micro Summary on Gravitee Test (`n=240` docs, `635` required-6 spans) & Dev (`n=120` docs, `364` spans)

| Split | Pipeline Variant | Exact Precision | Exact Recall | Exact F1 | Normalized F1 | Overlap Precision | Overlap Recall | Overlap F1 | Char PII Coverage | Over-Masking Rate |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gravitee Test (240)** | OpenAI Privacy Filter (Unchanged) | 43.25% | 44.88% | **44.05%** | 47.76% | 55.84% | 57.95% | **56.88%** | 67.96% | 4.82% |
| **Gravitee Test (240)** | Presidio + spaCy en_core_web_lg (Unchanged) | 33.07% | 45.83% | **38.42%** | 38.81% | 45.57% | 63.15% | **52.94%** | 64.91% | 8.83% |
| **Gravitee Test (240)** | OPF + Targeted Disambiguation & Rules | 44.34% | 51.81% | **47.79%** | 51.56% | 55.80% | 65.20% | **60.13%** | 69.85% | 4.90% |
| **Gravitee Test (240)** | Presidio + Targeted Location Merge & Rules | 34.03% | 45.98% | **39.12%** | 39.52% | 46.74% | 63.15% | **53.72%** | 65.68% | 8.87% |
| **Gravitee Test (240)** | Full Hybrid (OPF + Presidio + Rules) | 34.54% | 57.01% | **43.02%** | 45.87% | 45.61% | 75.28% | **56.80%** | 86.93% | 12.32% |
| **Gravitee Dev (120)** | OpenAI Privacy Filter (Unchanged) | 47.85% | 51.92% | **49.80%** | 52.44% | 59.49% | 64.56% | **61.92%** | 70.16% | 5.81% |
| **Gravitee Dev (120)** | Presidio + spaCy en_core_web_lg (Unchanged) | 36.96% | 46.70% | **41.26%** | 41.26% | 49.35% | 62.36% | **55.10%** | 64.30% | 10.46% |
| **Gravitee Dev (120)** | OPF + Targeted Disambiguation & Rules | 47.14% | 56.59% | **51.44%** | 53.93% | 57.67% | 69.23% | **62.92%** | 71.18% | 5.99% |
| **Gravitee Dev (120)** | Presidio + Targeted Location Merge & Rules | 36.70% | 45.88% | **40.78%** | 40.78% | 49.45% | 61.81% | **54.95%** | 65.21% | 10.50% |
| **Gravitee Dev (120)** | Full Hybrid (OPF + Presidio + Rules) | 37.81% | 62.64% | **47.16%** | 49.22% | 47.93% | 79.40% | **59.77%** | 88.37% | 14.81% |

### 4.2 All 25 Canonical Gravitee Labels on Held-Out Test Split (`gravitee_test_240`)

| # | Gravitee Label | MVP Tier | Test Support | OPF Baseline Exact F1 (Ov F1) | Presidio Baseline Exact F1 (Ov F1) | OPF + Rules Exact F1 (Ov F1) | Presidio + Rules Exact F1 (Ov F1) | Full Hybrid Exact F1 (Ov F1) | Native Model Support Note |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 1 | `AGE` | Extended-19 | 22 | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | Out-of-schema for both unchanged OPF and default Presidio |
| 2 | `COORDINATE` | Extended-19 | 16 | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | Out-of-schema for both unchanged OPF and default Presidio |
| 3 | `CREDIT_CARD` | Extended-19 | 27 | 0.00% (0.00%) | 45.71% (45.71%) | 62.96% (66.67%) | 45.71% (45.71%) | 67.92% (67.92%) | OPF collapses into `account_number` (disambiguated to 67% OvF1) |
| 4 | `DATE_TIME` | **Required-6** | 189 | 57.23% (61.01%) | 48.64% (61.22%) | 61.54% (65.09%) | 50.84% (61.34%) | 57.65% (68.29%) | Required MVP; OPF `private_date` & spaCy `DATE`/`TIME` |
| 5 | `EMAIL_ADDRESS` | **Required-6** | 47 | 75.56% (88.89%) | 75.95% (81.01%) | 76.60% (93.62%) | 75.95% (81.01%) | 76.09% (93.48%) | Required MVP; OPF `private_email` & Presidio regex |
| 6 | `FINANCIAL` | Extended-19 | 40 | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | Out-of-schema for both unchanged OPF and default Presidio |
| 7 | `HONORIFIC` | Extended-19 | 10 | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | Out-of-schema for both unchanged OPF and default Presidio (annotated inside/near PERSON) |
| 8 | `IBAN_CODE` | Extended-19 | 20 | 0.00% (0.00%) | 88.89% (88.89%) | 95.00% (95.00%) | 88.89% (88.89%) | 94.74% (94.74%) | OPF collapses into `account_number` (disambiguated to 95% F1) |
| 9 | `IMEI` | Extended-19 | 20 | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | Out-of-schema for both unchanged OPF and default Presidio |
| 10 | `IP_ADDRESS` | Extended-19 | 23 | 0.00% (0.00%) | 95.65% (95.65%) | 0.00% (0.00%) | 95.65% (95.65%) | 22.22% (22.22%) | Presidio `IpRecognizer` achieves 95.65% F1; not in OPF 8-class schema |
| 11 | `LOCATION` | **Required-6** | 134 | 23.17% (48.65%) | 12.55% (35.42%) | 23.17% (48.65%) | 8.98% (35.10%) | 21.67% (45.82%) | Required MVP; OPF `private_address` & spaCy `GPE`/`LOC` |
| 12 | `MAC_ADDRESS` | Extended-19 | 24 | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | Out-of-schema for both unchanged OPF and default Presidio |
| 13 | `NRP` | Extended-19 | 18 | 0.00% (0.00%) | 14.81% (14.81%) | 0.00% (0.00%) | 14.81% (14.81%) | 16.00% (16.00%) | Mapped from spaCy `NORP` |
| 14 | `ORGANIZATION` | Extended-19 | 93 | 0.00% (0.00%) | 15.06% (25.10%) | 0.00% (0.00%) | 15.06% (25.10%) | 16.09% (26.67%) | Mapped from spaCy `ORG`; intentionally excluded by OPF personal-PII policy |
| 15 | `PASSWORD` | Extended-19 | 23 | 19.30% (24.56%) | 0.00% (0.00%) | 19.30% (24.56%) | 0.00% (0.00%) | 20.00% (25.45%) | Mapped from OPF `secret` (47.83% recall) |
| 16 | `PERSON` | **Required-6** | 166 | 42.83% (56.10%) | 30.40% (48.00%) | 42.83% (56.10%) | 30.40% (48.00%) | 34.93% (48.29%) | Required MVP; OPF `private_person` & spaCy `PERSON` |
| 17 | `PHONE_NUMBER` | **Required-6** | 43 | 57.69% (71.15%) | 50.00% (51.92%) | 62.39% (75.23%) | 48.60% (56.07%) | 55.74% (65.57%) | Required MVP; OPF `private_phone` & Presidio `PhoneRecognizer` |
| 18 | `TITLE` | Extended-19 | 17 | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | Out-of-schema for both unchanged OPF and default Presidio (job titles) |
| 19 | `URL` | Extended-19 | 35 | 22.22% (22.22%) | 58.23% (86.08%) | 22.22% (22.22%) | 58.23% (86.08%) | 45.83% (66.67%) | Presidio `UrlRecognizer` achieves 85.71% OvF1 |
| 20 | `US_BANK_NUMBER` | Extended-19 | 17 | 8.36% (8.36%) | 27.27% (36.36%) | 8.16% (8.16%) | 27.27% (36.36%) | 9.71% (9.71%) | OPF `account_number` primary target (88.24% recall, low precision without disambiguation) |
| 21 | `US_DRIVER_LICENSE` | Extended-19 | 20 | 0.00% (0.00%) | 69.23% (69.23%) | 0.00% (0.00%) | 69.23% (69.23%) | 0.00% (0.00%) | Presidio `UsDriverLicenseRecognizer` achieves 90.00% recall / 69.23% F1 |
| 22 | `US_ITIN` | Extended-19 | 16 | 0.00% (0.00%) | 64.00% (64.00%) | 64.29% (64.29%) | 64.00% (64.00%) | 74.07% (74.07%) | Presidio `UsItinRecognizer` + regex achieves 74.07% F1 |
| 23 | `US_LICENSE_PLATE` | Extended-19 | 23 | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | 0.00% (0.00%) | Out-of-schema for both unchanged OPF and default Presidio |
| 24 | `US_PASSPORT` | Extended-19 | 32 | 0.00% (0.00%) | 40.00% (40.00%) | 0.00% (0.00%) | 40.00% (40.00%) | 0.00% (0.00%) | Presidio `UsPassportRecognizer` achieves 100% precision / 25% recall |
| 25 | `US_SSN` | **Required-6** | 56 | 0.00% (0.00%) | 61.90% (66.67%) | 45.45% (45.45%) | 65.12% (69.77%) | 46.85% (46.85%) | Required MVP; OPF collapses into `account_number` (fixed by disambiguation rule) |

### 4.3 Why Public Multi-Source Gravitee Scores Lower Than Clean Business Holdout (Root-Cause Analysis)

1. **Synthetic Annotation Inconsistencies Across the 6 Upstream Sources (`slices.gravitee_test_by_source`)**:
   - On `gretelai/gretel-pii-masking-en-v1`, `OPF + Targeted Rules` achieves **66.67% Exact F1 / 74.26% Overlap F1 / 88.93% character recall** (and Hybrid reaches **97.63% character recall**).
   - On `DataikuNLP/kiji-pii-training-data`, OPF achieves **91.41% character PII coverage** (Hybrid **100.00%**), but exact span F1 is **38.40%** because `kiji` annotates salutations (`Mr.`, `Dr.`) and trailing punctuation inside `PERSON`/`LOCATION` spans.
   - On `beki/privy` (SQL/JSON/API payloads) and `urchade/synthetic-pii-ner-mistral-v1`, non-PII labels like generic relative dates (`today`, `quarterly`, `2025 fiscal year`), organization names, and synthetic malformed strings are inconsistently tagged, causing **36.99% non-PII over-masking** in Presidio vs **8.04%** in OPF.

---

## 5. Error Taxonomy & Concrete Failure Examples (Business Holdout)

| Pipeline Variant | Exact Matches (TP) | Boundary Shifts (IoU>0, Same Label) | Label Confusion / Policy Mismatch (IoU>0, Diff Label) | Missed Entities (Zero-Overlap FN) | False Alarms on Non-PII (Zero-Overlap FP) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **OpenAI Privacy Filter (Unchanged)** | **341** | 85 | 64 | 15 | 5 |
| **Presidio + spaCy en_core_web_lg (Unchanged)** | **352** | 203 | 5 | 2 | 100 |
| **OPF + Targeted Disambiguation & Rules** | **440** | 12 | 4 | 3 | 5 |
| **Presidio + Targeted Location Merge & Rules** | **431** | 20 | 4 | 2 | 100 |
| **Full Hybrid (OPF + Presidio + Rules)** | **434** | 16 | 8 | 0 | 100 |

### Representative Error Examples Observed on Business Holdout
1. **Policy Mismatch (`opf_baseline` → Fixed by `opf_targeted_rules`)**:
   - `form_01`: Gold `US_SSN` `'412-58-9034'` → Unchanged OPF predicts `account_number` (mapped 1:1 to `US_BANK_NUMBER`). Disambiguating `account_number` with `SSN_REGEX` eliminates **60 of 64** label confusion errors.
2. **Span Boundary Shift (`presidio_spacy_baseline` & `opf_baseline` → Fixed by `opf_targeted_rules`)**:
   - `form_01`: Gold `LOCATION` `'742 Evergreen Terrace, Springfield, IL 62704'` → Unchanged OPF predicts `'742 Evergreen Terrace, Springfield, IL'` (omits ZIP code `'62704'`); Unchanged Presidio splits `'Springfield'` (`GPE`) and `'IL'` (`GPE`) and misses `'742 Evergreen Terrace'`. Combining `US_FULL_ADDRESS_REGEX` + contiguous location merging raises `LOCATION` Overlap F1 to **95.45% (`opf_targeted_rules`)** and **97.74% (`presidio_targeted_rules`)**.
3. **False Alarms / Over-Masking (`presidio_spacy_baseline` vs `opf_targeted_rules`)**:
   - Unchanged Presidio triggers **100 false-alarm spans** on the 60 business documents (e.g., flagging invoice headers, product names, and currency/date fragments), whereas `OPF + Targeted Rules` produces only **5 false alarms** across all 60 documents (`0.49%` non-PII character over-masking).

---

## 6. Runtime Latency, Throughput & Deployment Hardware Recommendation

| Engine / Mode | Warm Startup (s) | Mean Latency (ms/doc) | p50 Latency (ms/doc) | p95 Latency (ms/doc) | Throughput (docs/s) | Throughput (chars/s) | Peak RSS RAM (MB) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **OPF Stock CPU (Unpatched BMM, Business Holdout)** | `2.21s` | `6154.42` | `6292.11` | `6754.17` | `0.16` | `54.6` | `3627.66` |
| **OPF Grouped-MoE CPU (Business Holdout, 60 docs)** | `2.21s` | **`679.69`** | **`654.61`** | `950.58` | `1.47` | `500.9` | `3631.95` |
| **Presidio + spaCy `en_core_web_lg` CPU (Business Holdout, 60 docs)** | `3.08s` | **`18.01`** | **`17.35`** | `23.26` | **`55.3`** | **`18828.0`** | `4255.28` |
| **OPF Grouped-MoE CPU (Gravitee Test, 240 docs)** | `2.21s` | `900.96` | `805.08` | `1821.5` | `1.11` | `594.1` | `3638.31` |
| **Presidio + spaCy `en_core_web_lg` CPU (Gravitee Test, 240 docs)** | `3.08s` | `24.31` | `18.81` | `62.81` | `41.04` | `21968.3` | `4259.18` |

### Architecture & Deployment Recommendation
1. **If GPU or Async Batch Worker (≤ 1s/doc SLA) is available**: Deploy **`OPF + Targeted Disambiguation & Rules` (`opf_targeted_rules`)** with the grouped-MoE patch (or Triton on T4/L4 GPU). It achieves the highest precision (**96.49% Exact / 99.40% Character Precision**) and the lowest non-PII over-masking rate (**0.49%** vs Presidio's **10.12%**), preventing destructive redaction of business context.
2. **If Strict Synchronous CPU-Only Latency (< 30 ms/doc) is required**: Deploy **`Presidio + Targeted Rules` (`presidio_targeted_rules`)** with an allowlist/context filter for `PERSON` and `DATE_TIME` false positives. It runs at **18.01 ms/doc (`55.3 docs/s`)** on CPU and achieves **98.69% Overlap Recall** across the 6 required MVP entities.
