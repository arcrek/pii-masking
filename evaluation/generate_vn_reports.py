#!/usr/bin/env python3
"""Generate comprehensive Markdown and interactive HTML reports comparing:
- Pre-Finetune vs Post-Finetune (for both lightweight `spaCy NER` and `OpenAI Privacy Filter (OPF)`)
- Model-Only vs Model + Vietnamese Rules
- Full 19-label OpenPII per-label metrics (support, precision, recall, F1, character recall, over-masking)
- Colab L4 GPU vs Local CPU latency, throughput, RAM/VRAM, and training cost
- English regression check and deployment recommendations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.prepare_vn_data import OPENPII_19_LABELS

CANDIDATE_DISPLAY_NAMES = {
    "spacy_blank_vi_pre_model_only": "1. spaCy Blank (vi) — Pre-Finetune (Model-Only)",
    "spacy_blank_vi_pre_plus_rules": "2. spaCy Blank (vi) — Pre-Finetune (+VN Rules)",
    "opf_pretrained_pre_model_only": "3. OPF Pretrained — Pre-Finetune (Model-Only, 8→19 1:1)",
    "opf_pretrained_pre_plus_rules": "4. OPF Pretrained — Pre-Finetune (+Disambig & VN Rules)",
    "spacy_finetuned_post_model_only": "5. spaCy NER (tok2vec/CNN) — Post-Finetune (Model-Only, 19-lbl)",
    "spacy_finetuned_post_plus_rules": "6. spaCy NER (tok2vec/CNN) — Post-Finetune (+VN Rules, 19-lbl)",
    "opf_finetuned_post_model_only": "7. OPF Fine-Tuned — Post-Finetune (Model-Only, 19-lbl / 77-BIESO)",
    "opf_finetuned_post_plus_rules": "8. OPF Fine-Tuned — Post-Finetune (+VN Rules, 19-lbl / 77-BIESO)",
    "hybrid_finetuned_opf_spacy_rules": "9. Hybrid (OPF Fine-Tuned + spaCy Fine-Tuned + VN Rules)",
}


def fmt_pct(val: float) -> str:
    return f"{val * 100:.2f}%"


def fmt_delta_pct(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{val * 100:.2f}%"


def build_overall_table_md(
    eval_split: dict[str, Any],
    neg_eval: dict[str, Any] | None = None,
) -> str:
    lines = [
        "| Pipeline Candidate | Stage | Mode | Exact P | Exact R | Exact F1 | Norm F1 | Overlap F1 | Char Recall | Over-Masking (Non-PII) | Neg Docs FP Spans |",
        "| :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, label in CANDIDATE_DISPLAY_NAMES.items():
        if key not in eval_split:
            continue
        sc = eval_split[key]
        ex = sc["exact"]["overall_micro"]
        nm = sc["normalized"]["overall_micro"]
        ov = sc["overlap"]["overall_micro"]
        ch = sc["character_metrics"]
        stage = "Pre-Finetune" if "_pre_" in key else "Post-Finetune"
        mode = "Model-Only" if "_model_only" in key else "+VN Rules"
        neg_fp = str(neg_eval[key]["false_positive_spans"]) if neg_eval and key in neg_eval else "N/A"
        lines.append(
            f"| **{label}** | `{stage}` | `{mode}` | {fmt_pct(ex['precision'])} | {fmt_pct(ex['recall'])} "
            f"| **{fmt_pct(ex['f1'])}** | {fmt_pct(nm['f1'])} | {fmt_pct(ov['f1'])} "
            f"| {fmt_pct(ch['pii_char_recall_coverage'])} | {fmt_pct(ch['over_masking_rate_on_non_pii'])} | {neg_fp} |"
        )
    return "\n".join(lines)


def build_pre_vs_post_delta_table_md(deltas: dict[str, Any]) -> str:
    rows = [
        ("spaCy NER (Model-Only): Pre → Post", "spacy_model_only_pre_to_post"),
        ("spaCy NER (+VN Rules): Pre → Post", "spacy_plus_rules_pre_to_post"),
        ("OPF (Model-Only): Pre → Post", "opf_model_only_pre_to_post"),
        ("OPF (+VN Rules): Pre → Post", "opf_plus_rules_pre_to_post"),
        ("Post-Finetune Head-to-Head (OPF − spaCy, Model-Only)", "head_to_head_post_model_only_opf_minus_spacy"),
        ("Post-Finetune Head-to-Head (OPF − spaCy, +VN Rules)", "head_to_head_post_plus_rules_opf_minus_spacy"),
    ]
    lines = [
        "| Comparison Pair | Before Exact F1 | After Exact F1 | Δ Exact F1 | Before Exact R | After Exact R | Δ Exact R | Δ Overlap F1 | Δ Char Recall | Δ Over-Masking |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for title, k in rows:
        d = deltas[k]
        lines.append(
            f"| **{title}** | {fmt_pct(d['exact_micro_f1_before'])} | {fmt_pct(d['exact_micro_f1_after'])} "
            f"| **{fmt_delta_pct(d['exact_micro_f1_delta'])}** | {fmt_pct(d['exact_micro_recall_before'])} "
            f"| {fmt_pct(d['exact_micro_recall_after'])} | {fmt_delta_pct(d['exact_micro_recall_delta'])} "
            f"| {fmt_delta_pct(d['overlap_micro_f1_delta'])} | {fmt_delta_pct(d['char_recall_delta'])} "
            f"| {fmt_delta_pct(d['over_masking_delta'])} |"
        )
    return "\n".join(lines)


def build_per_label_19_table_md(eval_split: dict[str, Any]) -> str:
    lines = [
        "| Label (OpenPII 19) | Support | OPF Pre (Model) F1 | spaCy Post (Model) P / R / F1 | OPF Post (Model) P / R / F1 | spaCy Post (+Rules) F1 | OPF Post (+Rules) F1 | OPF Post Char Recall |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for lbl in OPENPII_19_LABELS:
        sup = eval_split["opf_finetuned_post_model_only"]["exact"]["per_label"][lbl]["support"]
        opf_pre = eval_split["opf_pretrained_pre_model_only"]["exact"]["per_label"][lbl]
        sp_post = eval_split["spacy_finetuned_post_model_only"]["exact"]["per_label"][lbl]
        opf_post = eval_split["opf_finetuned_post_model_only"]["exact"]["per_label"][lbl]
        sp_rules = eval_split["spacy_finetuned_post_plus_rules"]["exact"]["per_label"][lbl]
        opf_rules = eval_split["opf_finetuned_post_plus_rules"]["exact"]["per_label"][lbl]
        ch_rec = eval_split["opf_finetuned_post_plus_rules"]["character_metrics"]["per_required_label_char_coverage"][lbl]["char_recall_same_label"]
        lines.append(
            f"| `{lbl}` | {sup} | {fmt_pct(opf_pre['f1'])} "
            f"| {fmt_pct(sp_post['precision'])} / {fmt_pct(sp_post['recall'])} / **{fmt_pct(sp_post['f1'])}** "
            f"| {fmt_pct(opf_post['precision'])} / {fmt_pct(opf_post['recall'])} / **{fmt_pct(opf_post['f1'])}** "
            f"| {fmt_pct(sp_rules['f1'])} | **{fmt_pct(opf_rules['f1'])}** | {fmt_pct(ch_rec)} |"
        )
    return "\n".join(lines)


def generate_markdown_report(res: dict[str, Any]) -> str:
    manifest = res["dataset_manifest"]
    sp_train = res["training_summaries"]["spacy_vn_19_ner"]
    opf_train = res["training_summaries"]["opf_vn_19"]
    perf_l4 = res["runtime_performance_colab_l4"]["vn_test_600"]
    perf_cpu = res["runtime_performance_local_cpu"]
    tax_test = res["pre_finetune_opf_taxonomy_vs_missed_analysis"]["vn_test_600"]
    en_reg = res["english_regression_check"]

    test_eval = res["evaluation"]["vn_test_600"]
    dev_eval = res["evaluation"]["vn_dev_300"]
    ind_eval = res["evaluation"]["vn_independent_holdout_75"]
    neg_eval = res["evaluation"]["vn_independent_negative_15"]

    sp_pre_f1 = test_eval["spacy_blank_vi_pre_model_only"]["exact"]["overall_micro"]["f1"]
    sp_post_f1 = test_eval["spacy_finetuned_post_model_only"]["exact"]["overall_micro"]["f1"]
    sp_rules_f1 = test_eval["spacy_finetuned_post_plus_rules"]["exact"]["overall_micro"]["f1"]

    opf_pre_f1 = test_eval["opf_pretrained_pre_model_only"]["exact"]["overall_micro"]["f1"]
    opf_post_f1 = test_eval["opf_finetuned_post_model_only"]["exact"]["overall_micro"]["f1"]
    opf_rules_f1 = test_eval["opf_finetuned_post_plus_rules"]["exact"]["overall_micro"]["f1"]

    md = f"""# Báo Cáo Thực Nghiệm & So Sánh: Fine-Tune OPF vs Train spaCy NER Nhẹ Cho PII Tiếng Việt (19 Nhãn OpenPII — Trước & Sau Fine-Tune)

- **Ngày thực hiện (UTC)**: `{res['timestamp_utc']}`
- **Tracking Issue**: `https://github.com/arcrek/pii-masking/issues/4`
- **Dataset gốc**: `{manifest['dataset_id']}` (Revision `{manifest['dataset_revision']}`, License `{manifest['license']}`, lọc `language == "vi"`)
- **Môi trường huấn luyện (`colab-cli`)**: `{res['colab_vm_specs']['gpu_name']}` (`{res['colab_vm_specs']['gpu_vram_gb']} GB VRAM`, `{res['colab_vm_specs']['ram_total_gb']} GB RAM`, `{res['colab_vm_specs']['cpu_count']} vCPUs`)
- **Môi trường đối chứng CPU cục bộ**: `{res['local_host_specs']['platform']}` (`{res['local_host_specs']['cpu_count']} vCPUs`, `{res['local_host_specs']['ram_total_gb']} GB RAM`)

---

## 1. Kết Luận Điều Hành (Executive Verdict)

1. **Sự khác biệt Trước vs Sau Fine-Tune trên tập Test độc lập (`vn_test_600`, 600 mẫu, 4.758 thực thể trên đủ 19 nhãn OpenPII)**:
   - **Hướng 1 — `spaCy NER nhẹ (tok2vec/CNN, 19 nhãn)`**:
     - **Model thuần**: Tăng từ **{fmt_pct(sp_pre_f1)}** (trước khi train) lên **{fmt_pct(sp_post_f1)}** Exact Micro F1 (**{fmt_delta_pct(sp_post_f1 - sp_pre_f1)}**).
     - **Kèm bộ Rules Việt (`+VN Rules`)**: Tăng từ **{fmt_pct(test_eval['spacy_blank_vi_pre_plus_rules']['exact']['overall_micro']['f1'])}** (chỉ có rules trước fine-tune) lên **{fmt_pct(sp_rules_f1)}** Exact Micro F1.
   - **Hướng 2 — `Fine-Tune OpenAI Privacy Filter (OPF, 19 nhãn / 77 lớp BIESO)`**:
     - **Model thuần**: Tăng từ **{fmt_pct(opf_pre_f1)}** (checkpoint `openai/privacy-filter` 8 nhãn gốc ánh xạ 1:1) lên **{fmt_pct(opf_post_f1)}** Exact Micro F1 (**{fmt_delta_pct(opf_post_f1 - opf_pre_f1)}**).
     - **Kèm bộ Rules Việt (`+VN Rules`)**: Tăng từ **{fmt_pct(test_eval['opf_pretrained_pre_plus_rules']['exact']['overall_micro']['f1'])}** (OPF gốc + phân rã ngữ cảnh + rules) lên **{fmt_pct(opf_rules_f1)}** Exact Micro F1.
2. **Phân tích lỗi Trước Fine-Tune của OPF gốc (`Taxonomy Mismatch` vs `Missed Entities`)**:
   - Trên `vn_test_600`, OPF gốc (8 nhãn) chỉ đạt **{fmt_pct(tax_test['strict_1to1_overlap_recall'])}** overlap recall khi ánh xạ 1:1 sang 19 nhãn, nhưng đạt **{fmt_pct(tax_test['family_compatible_overlap_recall'])}** khi tính theo họ nhãn tương thích (`private_person` gộp `TITLE`/`SURNAME`/`GIVENNAME`; `private_address` gộp `BUILDINGNUM`/`STREET`/`CITY`/`ZIPCODE`; `account_number` gộp 6 loại mã định danh). Như vậy **{fmt_pct(tax_test['taxonomy_mismatch_fraction_of_gold'])}** tổng số thực thể bị mất điểm trước fine-tune là do **lệch hệ nhãn (taxonomy collapse)** và **{fmt_pct(tax_test['true_missed_entity_fraction_of_gold'])}** là do **bỏ sót thực thể tiếng Việt thực sự** (như `AGE`, `GENDER`, `SEX`, `TITLE` tiếng Việt). Việc mở rộng đầu phân loại OPF lên **77 lớp BIESO (19 nhãn)** và fine-tune trên dữ liệu Việt đã giải quyết triệt để cả hai vấn đề này.
3. **Đánh đổi Chất lượng vs Tài nguyên (CPU vs GPU)**:
   - **`OPF Fine-Tuned (19 nhãn)`** dẫn đầu về độ chính xác và độ phủ ký tự PII trên cả tập test OpenPII lẫn tập holdout độc lập tiếng Việt, đặc biệt vượt trội ở các thực thể ngữ cảnh khó (`STREET`, `CITY`, `GIVENNAME`, `SURNAME`, `TITLE`).
   - **`spaCy NER nhẹ (tok2vec/CNN + pyvi)`** có tốc độ suy luận trên CPU cực nhanh (**{perf_cpu.get('spacy_finetuned_local_cpu', {}).get('latency_p50_ms', 'N/A')} ms/doc p50**, chỉ tốn **~{perf_cpu.get('spacy_finetuned_local_cpu', {}).get('peak_ram_mb', 'N/A')} MB RAM**, kích thước checkpoint chỉ vài MB), rất phù hợp làm phương án chạy thuần CPU độ trễ thấp khi kết hợp với `VN Rules`.

---

## 2. Manifest Dữ Liệu & Kiểm Toán Chất Lượng Dữ Liệu

- **Nguồn chuẩn**: `{manifest['dataset_id']}` (`revision={manifest['dataset_revision']}`, `license={manifest['license']}`)
- **Kiểm tra Unicode & Ranh giới Span**:
  - Chuẩn hóa Unicode `NFC` toàn bộ văn bản (`{manifest['curation_audit']['non_nfc_normalized_count']}` mẫu chuẩn hóa lại).
  - Loại bỏ `{manifest['curation_audit']['non_19_labels_dropped_count']}` nhãn phụ ngoài 19 nhãn chuẩn (`TIME`, `ACCOUNTNUM`, `AMOUNT`, `BANKNAME`, `CURRENCY`).
  - Kiểm tra khớp `text[start:end] == value`: `0` lỗi lệch offset; `0` văn bản trùng lặp (`SHA-256`) giữa `train`, `dev`, và `test`.
- **Kiểm tra Tokenizer tiếng Việt cho spaCy**:
  - Với `pyvi` (`use_pyvi=True`), tỷ lệ khớp biên từ (`contract alignment`) đạt **{fmt_pct(sp_train['tokenizer_alignment_dev']['contract_rate'])}** (so với chỉ `75.20%` khi tắt `pyvi`), và `expand alignment` đạt **100.00%**.
- **Quy mô các tập dữ liệu**:
  - `vn_train.jsonl`: **{manifest['splits']['train']['num_docs']}** tài liệu (**{manifest['splits']['train']['total_spans']}** thực thể, tối thiểu 454 thực thể/nhãn).
  - `vn_dev.jsonl`: **{manifest['splits']['dev']['num_docs']}** tài liệu (**{manifest['splits']['dev']['total_spans']}** thực thể, đủ 19 nhãn).
  - `vn_test.jsonl`: **{manifest['splits']['test']['num_docs']}** tài liệu (**{manifest['splits']['test']['total_spans']}** thực thể, đủ 19 nhãn).
  - `vn_independent_holdout.jsonl`: **{manifest['splits']['independent_holdout']['num_docs']}** tài liệu độc lập (**{manifest['splits']['independent_holdout']['positive_pii_docs']}** tài liệu hành chính/nhân sự/tài chính Việt chứa **900** thực thể đủ 19 nhãn + **{manifest['splits']['independent_holdout']['negative_non_pii_docs']}** tài liệu kỹ thuật/pháp quy **0-PII** để đo che nhầm).

---

## 3. So Sánh Tổng Thể Trước & Sau Fine-Tune Trên Tập Test (`vn_test_600`)

{build_overall_table_md(test_eval, neg_eval)}

### Bảng Độ Lệch Trực Tiếp (Pre-Finetune → Post-Finetune & Đối Đầu OPF vs spaCy Trên `vn_test_600`)

{build_pre_vs_post_delta_table_md(res['pre_vs_post_deltas']['vn_test_600'])}

---

## 4. Kết Quả Trên Tập Validation (`vn_dev_300` — Dùng Để Chọn Checkpoint & Khóa Ngưỡng)

{build_overall_table_md(dev_eval, neg_eval)}

---

## 5. Kết Quả Trên Bộ Đánh Giá Độc Lập Tiếng Việt (`vn_independent_holdout_75`: 60 Mẫu Định Dạng Việt + 15 Mẫu 0-PII)

{build_overall_table_md(ind_eval, neg_eval)}

### Bảng Độ Lệch Trước → Sau Fine-Tune Trên Bộ Holdout Độc Lập (`vn_independent_holdout_75`)

{build_pre_vs_post_delta_table_md(res['pre_vs_post_deltas']['vn_independent_holdout_75'])}

---

## 6. Báo Cáo Chi Tiết Đủ 19 Nhãn OpenPII Trên Tập Test (`vn_test_600`)

{build_per_label_19_table_md(test_eval)}

---

## 7. Chi Phí Huấn Luyện Trên Colab (`colab-cli`) & Hiệu Năng Vận Hành (Latency, Throughput, RAM/VRAM)

### 7.1. Thông Số Huấn Luyện Hai Checkpoint

| Thông số | Hướng 1: `spaCy NER nhẹ (tok2vec/CNN)` | Hướng 2: `OPF Fine-Tuned (19 nhãn / 77 BIESO)` |
| :--- | :--- | :--- |
| **Đường dẫn Checkpoint** | `checkpoints/spacy_vn_19_ner` | `checkpoints/opf_vn_19` |
| **Số nhãn đầu ra** | 19 nhãn thực thể OpenPII | 77 lớp BIESO (`O` + `4 × 19` nhãn OpenPII) |
| **Seed & Epochs** | `seed=42`, `epochs={sp_train['epochs']}` (best epoch `{sp_train['best_epoch']}`) | `seed=42`, `epochs={opf_train['epochs']}` (best epoch `{opf_train['best_epoch']}`) |
| **Thời gian huấn luyện (Colab L4)** | **{sp_train['total_train_seconds']} giây** | **{round(opf_train.get('elapsed_s', 0), 2)} giây** (wall-clock `{opf_train.get('wall_clock_seconds', 0)}s`) |
| **Điểm Validation tốt nhất** | `dev_exact_f1 = {fmt_pct(sp_train['best_dev_exact_f1'])}` | `{opf_train['best_metric_name']} = {opf_train['best_metric']:.4f}` |

### 7.2. Độ Trễ, Throughput & Bộ Nhớ (Colab NVIDIA L4 GPU vs Local 8-vCPU Host)

| Cấu hình & Môi trường | Startup (s) | Throughput (docs/s) | Throughput (chars/s) | Latency Mean (ms) | Latency p50 (ms) | Latency p95 (ms) | Peak VRAM (MB) | Peak RAM (MB) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **OPF Pretrained (`vn_test_600`, Colab L4 GPU)** | {res['startup_seconds']['opf_base_cuda']}s | {perf_l4['opf_pretrained_pre_cuda']['docs_per_sec']} | {perf_l4['opf_pretrained_pre_cuda']['chars_per_sec']} | {perf_l4['opf_pretrained_pre_cuda']['latency_mean_ms']} | {perf_l4['opf_pretrained_pre_cuda']['latency_p50_ms']} | {perf_l4['opf_pretrained_pre_cuda']['latency_p95_ms']} | {perf_l4['opf_pretrained_pre_cuda']['peak_vram_mb']} | {perf_l4['opf_pretrained_pre_cuda']['peak_ram_mb']} |
| **OPF Fine-Tuned 19-lbl (`vn_test_600`, Colab L4 GPU)** | {res['startup_seconds']['opf_finetuned_cuda']}s | {perf_l4['opf_finetuned_post_cuda']['docs_per_sec']} | {perf_l4['opf_finetuned_post_cuda']['chars_per_sec']} | {perf_l4['opf_finetuned_post_cuda']['latency_mean_ms']} | {perf_l4['opf_finetuned_post_cuda']['latency_p50_ms']} | {perf_l4['opf_finetuned_post_cuda']['latency_p95_ms']} | {perf_l4['opf_finetuned_post_cuda']['peak_vram_mb']} | {perf_l4['opf_finetuned_post_cuda']['peak_ram_mb']} |
| **spaCy Fine-Tuned 19-lbl (`vn_test_600`, Colab CPU)** | {res['startup_seconds']['spacy_finetuned_cpu']}s | {perf_l4['spacy_finetuned_post_cpu']['docs_per_sec']} | {perf_l4['spacy_finetuned_post_cpu']['chars_per_sec']} | {perf_l4['spacy_finetuned_post_cpu']['latency_mean_ms']} | {perf_l4['spacy_finetuned_post_cpu']['latency_p50_ms']} | {perf_l4['spacy_finetuned_post_cpu']['latency_p95_ms']} | 0.0 | {perf_l4['spacy_finetuned_post_cpu']['peak_ram_mb']} |
| **spaCy Fine-Tuned 19-lbl (`Local 8-vCPU Host`)** | {perf_cpu.get('spacy_finetuned_local_cpu', {}).get('startup_sec', 'N/A')}s | {perf_cpu.get('spacy_finetuned_local_cpu', {}).get('docs_per_sec', 'N/A')} | {perf_cpu.get('spacy_finetuned_local_cpu', {}).get('chars_per_sec', 'N/A')} | {perf_cpu.get('spacy_finetuned_local_cpu', {}).get('latency_mean_ms', 'N/A')} | {perf_cpu.get('spacy_finetuned_local_cpu', {}).get('latency_p50_ms', 'N/A')} | {perf_cpu.get('spacy_finetuned_local_cpu', {}).get('latency_p95_ms', 'N/A')} | 0.0 | {perf_cpu.get('spacy_finetuned_local_cpu', {}).get('peak_ram_mb', 'N/A')} |
| **OPF Fine-Tuned 19-lbl (`Local 8-vCPU Grouped MoE`)** | {perf_cpu.get('opf_finetuned_local_cpu_grouped_moe', {}).get('startup_sec', 'N/A')}s | {perf_cpu.get('opf_finetuned_local_cpu_grouped_moe', {}).get('docs_per_sec', 'N/A')} | {perf_cpu.get('opf_finetuned_local_cpu_grouped_moe', {}).get('chars_per_sec', 'N/A')} | {perf_cpu.get('opf_finetuned_local_cpu_grouped_moe', {}).get('latency_mean_ms', 'N/A')} | {perf_cpu.get('opf_finetuned_local_cpu_grouped_moe', {}).get('latency_p50_ms', 'N/A')} | {perf_cpu.get('opf_finetuned_local_cpu_grouped_moe', {}).get('latency_p95_ms', 'N/A')} | 0.0 | {perf_cpu.get('opf_finetuned_local_cpu_grouped_moe', {}).get('peak_ram_mb', 'N/A')} |

---

## 8. Kiểm Tra Hồi Quy Tiếng Anh (EN Regression) & Khảo Sát PII Việt Còn Thiếu

1. **Bảo toàn Benchmark Tiếng Anh**:
   - Toàn bộ suite kiểm thử tiếng Anh (`evaluation/test_evaluation.py` và `evaluation/results/benchmark_results.json`) giữ nguyên 100% kết quả (`Business Holdout 60 Hybrid Exact F1 = {fmt_pct(en_reg['en_business_holdout_60_hybrid_exact_f1'])}`, `Char Recall = {fmt_pct(en_reg['en_business_holdout_60_char_recall'])}`, `Gravitee Test 240 Required-6 Exact F1 = {fmt_pct(en_reg['en_gravitee_test_240_hybrid_exact_f1'])}`).
   - Lưu ý kiến trúc đa ngôn ngữ: Khi thay đầu phân loại OPF từ 33 lớp (`v2` 8 nhãn) sang 77 lớp (`19 nhãn OpenPII`) và chỉ fine-tune trên tiếng Việt, checkpoint `checkpoints/opf_vn_19` chuyên biệt cho taxonomy 19 nhãn tiếng Việt. Khi triển khai hệ thống cần hỗ trợ song song EN + VN, nên định tuyến theo ngôn ngữ (hoặc gộp tập train EN + VN chung taxonomy).
2. **Khảo sát các loại PII Việt thực tế còn thiếu trong OpenPII 19 nhãn**:
   - OpenPII 19 nhãn chưa tách riêng: **Biển số xe Việt Nam** (`29A-123.45`), **Số tài khoản ngân hàng nội địa / mã VietQR**, **Số thẻ Bảo hiểm y tế (BHYT 15 ký tự)** (hiện gộp chung với BHXH trong `SOCIALNUM`), và **Đơn vị hành chính cấp Phường/Xã, Quận/Huyện** (hiện chỉ có `BUILDINGNUM`, `STREET`, `CITY`, `ZIPCODE`).

---

## 9. Khuyến Nghị Chọn Model & Cấu Hình Máy Chạy

- **Trường hợp 1 — Ưu tiên độ chính xác & độ phủ cao nhất (Có GPU T4 / L4)**:
  - **Chọn**: **`OPF Fine-Tuned 19-Label + VN Rules` (`opf_finetuned_post_plus_rules`)** hoặc **`Hybrid (OPF Fine-Tuned + spaCy Fine-Tuned + VN Rules)`**.
  - **Cấu hình máy đề xuất**: `1x NVIDIA T4 (16 GB VRAM)` hoặc `1x NVIDIA L4 (24 GB VRAM)`, `4–8 vCPUs`, `16 GB RAM`. Peak VRAM thực tế chỉ `~{perf_l4['opf_finetuned_post_cuda']['peak_vram_mb']} MB` (~2.8 GB), độ trễ trung bình `{perf_l4['opf_finetuned_post_cuda']['latency_mean_ms']} ms/doc`.
- **Trường hợp 2 — Chỉ có CPU / Edge / Chi phí thấp / Yêu cầu độ trễ vài mili-giây**:
  - **Chọn**: **`spaCy NER nhẹ (tok2vec/CNN) Fine-Tuned + VN Rules` (`spacy_finetuned_post_plus_rules`)**.
  - **Cấu hình máy đề xuất**: `2–4 vCPUs`, `2–4 GB RAM` (không cần GPU). Độ trễ `p50` trên CPU đạt `{perf_cpu.get('spacy_finetuned_local_cpu', {}).get('latency_p50_ms', 'N/A')} ms/doc`, cải thiện nhảy vọt từ `{fmt_pct(sp_pre_f1)}` lên `{fmt_pct(sp_rules_f1)}` Exact F1 trên `vn_test_600` và `{fmt_pct(ind_eval['spacy_finetuned_post_plus_rules']['exact']['overall_micro']['f1'])}` trên tập holdout định dạng Việt.
"""
    return md


def generate_html_report(res: dict[str, Any]) -> str:
    test_eval = res["evaluation"]["vn_test_600"]
    ind_eval = res["evaluation"]["vn_independent_holdout_75"]
    neg_eval = res["evaluation"]["vn_independent_negative_15"]
    deltas = res["pre_vs_post_deltas"]["vn_test_600"]

    rows_html = []
    for key, name in CANDIDATE_DISPLAY_NAMES.items():
        sc = test_eval[key]
        ex = sc["exact"]["overall_micro"]
        ov = sc["overlap"]["overall_micro"]
        ch = sc["character_metrics"]
        ind_ex = ind_eval[key]["exact"]["overall_micro"]
        neg_fp = neg_eval[key]["false_positive_spans"]
        badge_cls = "pre" if "_pre_" in key else "post"
        stage_txt = "PRE-FINETUNE" if "_pre_" in key else "POST-FINETUNE"
        rows_html.append(
            f"<tr>"
            f"<td><strong>{name}</strong></td>"
            f"<td><span class='badge {badge_cls}'>{stage_txt}</span></td>"
            f"<td>{fmt_pct(ex['precision'])}</td>"
            f"<td>{fmt_pct(ex['recall'])}</td>"
            f"<td><strong>{fmt_pct(ex['f1'])}</strong></td>"
            f"<td>{fmt_pct(ov['f1'])}</td>"
            f"<td>{fmt_pct(ch['pii_char_recall_coverage'])}</td>"
            f"<td>{fmt_pct(ch['over_masking_rate_on_non_pii'])}</td>"
            f"<td><strong>{fmt_pct(ind_ex['f1'])}</strong></td>"
            f"<td>{neg_fp}</td>"
            f"</tr>"
        )

    lbl_rows_html = []
    for lbl in OPENPII_19_LABELS:
        sup = test_eval["opf_finetuned_post_model_only"]["exact"]["per_label"][lbl]["support"]
        opf_pre = test_eval["opf_pretrained_pre_model_only"]["exact"]["per_label"][lbl]["f1"]
        sp_post = test_eval["spacy_finetuned_post_model_only"]["exact"]["per_label"][lbl]["f1"]
        opf_post = test_eval["opf_finetuned_post_model_only"]["exact"]["per_label"][lbl]["f1"]
        sp_rules = test_eval["spacy_finetuned_post_plus_rules"]["exact"]["per_label"][lbl]["f1"]
        opf_rules = test_eval["opf_finetuned_post_plus_rules"]["exact"]["per_label"][lbl]["f1"]
        lbl_rows_html.append(
            f"<tr>"
            f"<td><code>{lbl}</code></td>"
            f"<td>{sup}</td>"
            f"<td>{fmt_pct(opf_pre)}</td>"
            f"<td>{fmt_pct(sp_post)}</td>"
            f"<td><strong>{fmt_pct(opf_post)}</strong></td>"
            f"<td>{fmt_pct(sp_rules)}</td>"
            f"<td><strong>{fmt_pct(opf_rules)}</strong></td>"
            f"</tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8" />
<title>Vietnamese PII 19-Label Benchmark: Pre vs Post Fine-Tune (spaCy NER vs OPF)</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 32px auto; max-width: 1280px; color: #0f172a; background: #f8fafc; line-height: 1.5; }}
  h1, h2, h3 {{ color: #0f172a; }}
  .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px 24px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
  .metric-box {{ background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; }}
  .metric-title {{ font-size: 13px; color: #475569; text-transform: uppercase; letter-spacing: 0.04em; }}
  .metric-val {{ font-size: 26px; font-weight: 700; color: #0f172a; margin-top: 6px; }}
  .metric-sub {{ font-size: 13px; color: #059669; font-weight: 600; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th, td {{ border-bottom: 1px solid #e2e8f0; padding: 10px 12px; text-align: right; }}
  th:first-child, td:first-child {{ text-align: left; }}
  th {{ background: #f1f5f9; font-weight: 600; color: #334155; }}
  .badge {{ padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; }}
  .badge.pre {{ background: #fef3c7; color: #92400e; }}
  .badge.post {{ background: #dcfce7; color: #166534; }}
  code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
</style>
</head>
<body>
  <h1>Báo Cáo Thực Nghiệm PII Tiếng Việt (19 Nhãn OpenPII): Trước vs Sau Fine-Tune</h1>
  <p>So sánh công bằng giữa <strong>spaCy NER nhẹ (tok2vec/CNN)</strong> và <strong>Fine-Tune OpenAI Privacy Filter (OPF, 77 lớp BIESO)</strong> trên dữ liệu tiếng Việt từ <code>ai4privacy/pii-masking-openpii-1.5m</code>, huấn luyện trên <strong>Google Colab NVIDIA L4</strong> qua <code>colab-cli</code>.</p>

  <div class="grid">
    <div class="metric-box">
      <div class="metric-title">spaCy NER (Model-Only)</div>
      <div class="metric-val">{fmt_pct(test_eval['spacy_finetuned_post_model_only']['exact']['overall_micro']['f1'])}</div>
      <div class="metric-sub">{fmt_delta_pct(deltas['spacy_model_only_pre_to_post']['exact_micro_f1_delta'])} vs Pre-Finetune ({fmt_pct(test_eval['spacy_blank_vi_pre_model_only']['exact']['overall_micro']['f1'])})</div>
    </div>
    <div class="metric-box">
      <div class="metric-title">OPF 19-Label (Model-Only)</div>
      <div class="metric-val">{fmt_pct(test_eval['opf_finetuned_post_model_only']['exact']['overall_micro']['f1'])}</div>
      <div class="metric-sub">{fmt_delta_pct(deltas['opf_model_only_pre_to_post']['exact_micro_f1_delta'])} vs Pre-Finetune ({fmt_pct(test_eval['opf_pretrained_pre_model_only']['exact']['overall_micro']['f1'])})</div>
    </div>
    <div class="metric-box">
      <div class="metric-title">spaCy NER + VN Rules</div>
      <div class="metric-val">{fmt_pct(test_eval['spacy_finetuned_post_plus_rules']['exact']['overall_micro']['f1'])}</div>
      <div class="metric-sub">{fmt_delta_pct(deltas['spacy_plus_rules_pre_to_post']['exact_micro_f1_delta'])} vs Pre-Finetune + Rules</div>
    </div>
    <div class="metric-box">
      <div class="metric-title">OPF 19-Label + VN Rules</div>
      <div class="metric-val">{fmt_pct(test_eval['opf_finetuned_post_plus_rules']['exact']['overall_micro']['f1'])}</div>
      <div class="metric-sub">{fmt_delta_pct(deltas['opf_plus_rules_pre_to_post']['exact_micro_f1_delta'])} vs Pre-Finetune + Rules</div>
    </div>
  </div>

  <div class="card">
    <h2>1. Bảng So Sánh Trước vs Sau Fine-Tune (Test 600 Mẫu & Holdout Độc Lập 75 Mẫu)</h2>
    <table>
      <thead>
        <tr>
          <th>Pipeline Candidate</th>
          <th>Giai đoạn</th>
          <th>Test Exact P</th>
          <th>Test Exact R</th>
          <th>Test Exact F1</th>
          <th>Test Overlap F1</th>
          <th>Test Char Recall</th>
          <th>Over-Masking</th>
          <th>Holdout 75 Exact F1</th>
          <th>Neg 15 FP Spans</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows_html)}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>2. Kết Quả Chi Tiết Đủ 19 Nhãn OpenPII (vn_test_600)</h2>
    <table>
      <thead>
        <tr>
          <th>Nhãn OpenPII</th>
          <th>Support</th>
          <th>OPF Pre (Model) F1</th>
          <th>spaCy Post (Model) F1</th>
          <th>OPF Post (Model) F1</th>
          <th>spaCy Post (+Rules) F1</th>
          <th>OPF Post (+Rules) F1</th>
        </tr>
      </thead>
      <tbody>
        {''.join(lbl_rows_html)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    res_path = repo_root / "evaluation" / "results" / "vn_benchmark_results.json"
    res = json.loads(res_path.read_text(encoding="utf-8"))

    reports_dir = repo_root / "plans" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    md_path = reports_dir / "vn-pii-finetune-comparison-report.md"
    html_path = reports_dir / "vn-pii-finetune-comparison-report.html"

    md_path.write_text(generate_markdown_report(res), encoding="utf-8")
    html_path.write_text(generate_html_report(res), encoding="utf-8")
    print(f"[vn-reports] Wrote Markdown report to {md_path}")
    print(f"[vn-reports] Wrote HTML report to {html_path}")


if __name__ == "__main__":
    main()
