#!/usr/bin/env python3
"""Generate the Markdown and visual HTML reports for ML-07 PII Detection Evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CANDIDATE_NAMES = {
    "opf_baseline": "OpenAI Privacy Filter (Unchanged)",
    "presidio_spacy_baseline": "Presidio + spaCy en_core_web_lg (Unchanged)",
    "opf_targeted_rules": "OPF + Targeted Disambiguation & Rules",
    "presidio_targeted_rules": "Presidio + Targeted Location Merge & Rules",
    "hybrid_opf_presidio_rules": "Full Hybrid (OPF + Presidio + Rules)",
}

REQUIRED_6 = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "LOCATION",
    "DATE_TIME",
    "US_SSN",
]


def pct(val: float) -> str:
    return f"{val * 100:.2f}%"


def build_markdown_report(data: dict[str, Any]) -> str:
    hw = data["hardware_specs"]
    perf = data["runtime_performance"]
    bus_eval = data["evaluation"]["business_holdout_60"]
    grav_test_eval = data["evaluation"]["gravitee_test_240"]
    grav_dev_eval = data["evaluation"]["gravitee_dev_120"]
    manifest = data["gravitee_manifest"]
    slices_bus = data["slices"]["business_holdout_by_doc_type"]
    slices_grav = data["slices"]["gravitee_test_by_source"]

    lines: list[str] = [
        "# ML-07: PII Detection Model Evaluation & Fine-Tuning Decision Report",
        "",
        f"**Generated UTC**: `{data['timestamp_utc']}`  ",
        "**Scope**: English Business Documents (Forms, Invoices, Correspondence) — Text-Only Detection Evaluation  ",
        "**Candidates Evaluated**:",
        "1. **OpenAI Privacy Filter (`openai/privacy-filter`)** — Unchanged Baseline (Viterbi decoding, primary 1:1 label mapping).",
        "2. **Microsoft Presidio + spaCy (`en_core_web_lg`)** — Unchanged Baseline.",
        "3. **OPF + Targeted Disambiguation & Rules (`opf_targeted_rules`)** — Disambiguates OPF `account_number` into `US_SSN`, `IBAN_CODE`, `CREDIT_CARD`, and `US_BANK_NUMBER`, plus deterministic extractors for SSN, Email, Phone, Date, and US Street Addresses.",
        "4. **Presidio + Targeted Location Merge & Rules (`presidio_targeted_rules`)** — Merges fragmented `GPE`/`LOC` address spans and combines deterministic business regexes.",
        "5. **Full Hybrid Pipeline (`hybrid_opf_presidio_rules`)** — Combines OPF + Presidio + Deterministic Business Rules.",
        "",
        "---",
        "",
        "## 1. Executive Decision: Do We Need to Fine-Tune for MVP?",
        "",
        "### **Verdict: NO Fine-Tuning Required for MVP — Ship `OPF + Targeted Disambiguation & Rules` (or `Presidio + Targeted Rules` on CPU-Only Budget)**",
        "",
        "1. **Neither unchanged baseline passes the MVP gate out-of-the-box**, NOT because the underlying neural weights lack representation capacity for English business text, but because of **taxonomy & span-boundary policy mismatches**:",
        "   - **Unchanged `openai/privacy-filter`** achieves **0.00% exact recall on `US_SSN`** under strict 1:1 primary mapping because OPF's 8-label schema (`private_person`, `private_date`, `private_address`, `private_phone`, `private_email`, `account_number`, `secret`, `medical_Condition`) collapses `US_SSN`, `IBAN_CODE`, `CREDIT_CARD`, and invoice/bank numbers into a single `account_number` class. Even so, its **any-label character coverage on `US_SSN` is 98.36%** on the business holdout!",
        "   - **Unchanged `Presidio + en_core_web_lg`** achieves **0.00% exact F1 on full street `LOCATION`** on the business holdout (`100.00%` partial overlap recall) because spaCy's `GPE`/`LOC`/`FAC` NER tags only city and state tokens while leaving street numbers and ZIP codes untagged, and over-masks non-PII business text at **10.30%** (21x higher over-masking than OPF's **0.49%**).",
        "2. **With lightweight deterministic disambiguation and span-boundary rules (zero model weight training)**:",
        "   - **`OPF + Targeted Disambiguation & Rules`** jumps from **76.72% → 96.39% micro Exact F1** (`96.49%` precision, `96.28%` recall), **98.58% Overlap F1** (`98.68%` precision, `98.47%` recall), **98.74% character-level PII recall**, and **99.40% character precision** with only **0.49% over-masking rate** on the 60-document Independent Business Holdout.",
        "   - Under **partial/overlap span matching (IoU > 0)** and **character-level masking coverage**, `OPF + Targeted Rules` exceeds the **≥95% recall and ≥90% precision** target on **5 of 6 required labels** (`PERSON` 98.41% F1, `EMAIL_ADDRESS` 100.00% F1, `PHONE_NUMBER` 100.00% F1, `LOCATION` 95.45% F1, `DATE_TIME` 100.00% F1), with `US_SSN` at **100.00% precision and 93.44% recall** (96.61% F1; 98.36% character coverage).",
        "   - **`Presidio + Targeted Rules`** jumps from **71.33% → 93.59% micro Exact F1** and passes **all 6 of 6 required MVP labels under Overlap matching** (`PERSON` 95.74% recall / 90.00% precision, `EMAIL_ADDRESS` 100% / 100%, `PHONE_NUMBER` 100% / 100%, `LOCATION` 100% recall / 95.59% precision, `DATE_TIME` 98.25% recall / 100% precision, `US_SSN` 100% / 100%) while running in **18.01 ms/doc on CPU** (37x faster than OPF on CPU), though with a higher non-PII over-masking rate (**10.12%** vs OPF's **0.49%**).",
        "3. **When Fine-Tuning Would Become Necessary (Post-MVP Trigger Conditions)**:",
        "   - Fine-tuning `openai/privacy-filter` (or a token classifier on `gravitee-io/pii-detection-dataset`) is **only justified if**:",
        "     1. The product expands beyond the 6 core MVP labels to require native neural separation of all 25 Gravitee classes (specifically `AGE`, `COORDINATE`, `FINANCIAL`, `HONORIFIC`, `IMEI`, `MAC_ADDRESS`, `TITLE`, `US_LICENSE_PLATE`, where both OPF and Presidio score 0% without custom recognizers).",
        "     2. Strict exact-boundary `PERSON` recall on noisy multi-source corpora (`urchade/synthetic-pii-ner-mistral-v1`, `beki/privy`) must exceed 95% without title/honorific boundary differences.",
        "",
        "---",
        "",
        "## 2. Benchmark Environment & Reproducibility Manifest",
        "",
        "### 2.1 Hardware & Runtime Environment",
        f"- **Host OS / Kernel**: `{hw['platform']}`",
        f"- **CPU**: `{hw['cpu_model']}` (`{hw['cpu_count_logical']}` logical vCPUs)",
        f"- **System RAM**: `{hw['ram_total_gb']} GB`",
        f"- **Python / PyTorch**: Python `{hw['python_version']}`, PyTorch `{hw['torch_version']}`",
        f"- **Colab Pro Provisioning Note**: `{hw['colab_pro_assign_status']}`",
        "- **CPU MoE Optimization Discovery**: Stock `openai/privacy-filter` on CPU clones `[batch, 4, 640, 1280]` expert tensors per token (`6,154.42 ms/doc`). Grouping tokens by selected expert ID (`apply_grouped_moe_cpu_optimization` in `evaluation/run_benchmark.py`) reduced CPU inference latency by **9.05x** to **`679.69 ms/doc`** (`p50 = 654.61 ms`) while preserving MoE routing and `3.63 GB` peak RSS.",
        "",
        "### 2.2 Dataset & Split Manifests",
        "- **Dataset 1: Independent Business-Text Holdout (`evaluation/data/business_holdout_60.jsonl`)**",
        "  - **SHA-256**: `a634d46d04b00e4bff6025c2dd0962bdc6d98748250f228b465bb90d96ba35f7`",
        "  - **Composition**: 60 realistic English business documents (`20` HR/tax/onboarding forms, `20` B2B invoices & billing statements, `20` executive/legal/support correspondence emails).",
        "  - **Ground-Truth Spans**: `457` character-verified spans (`DATE_TIME`: 114, `PERSON`: 94, `LOCATION`: 65, `EMAIL_ADDRESS`: 62, `PHONE_NUMBER`: 61, `US_SSN`: 61).",
        "- **Dataset 2: Gravitee PII Detection (`gravitee-io/pii-detection-dataset`, 175,881 upstream rows)**",
        f"  - **Seed**: `{manifest['seed']}` (strictly disjoint `dev` and `test` splits stratified across all 25 labels and all 6 upstream sources)",
        f"  - **Dev Split (`gravitee_dev_120`)**: `{manifest['dev_size']}` docs (`sha256: {manifest['dev_indices_sha256']}`)",
        f"  - **Test Split (`gravitee_test_240`)**: `{manifest['test_size']}` docs (`sha256: {manifest['test_indices_sha256']}`)",
        "  - **Test Source Distribution**: " + ", ".join(f"`{k}`: {v}" for k, v in manifest["test_source_distribution"].items()),
        "",
        "---",
        "",
        "## 3. Primary Evaluation: Independent Business-Text Holdout (60 Docs, 457 Spans)",
        "",
        "### 3.1 Micro-Averaged Summary (Required 6 MVP Labels)",
        "",
        "| Pipeline Variant | Exact Precision | Exact Recall | Exact F1 | Normalized F1 | Overlap Precision | Overlap Recall | Overlap F1 | Char PII Recall | Char PII Precision | Non-PII Over-Masking Rate | Exact Gate (6/6) | Overlap Gate (6/6) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for cand, label in CANDIDATE_NAMES.items():
        m = bus_eval[cand]
        ex = m["exact"]["required_6_micro"]
        nm = m["normalized"]["required_6_micro"]
        ov = m["overlap"]["required_6_micro"]
        ch = m["character_metrics"]
        ex_pass = sum(
            1
            for l in REQUIRED_6
            if m["exact"]["per_label"][l]["precision"] >= 0.90
            and m["exact"]["per_label"][l]["recall"] >= 0.95
        )
        ov_pass = sum(
            1
            for l in REQUIRED_6
            if m["overlap"]["per_label"][l]["precision"] >= 0.90
            and m["overlap"]["per_label"][l]["recall"] >= 0.95
        )
        lines.append(
            f"| **{label}** | {pct(ex['precision'])} | {pct(ex['recall'])} | **{pct(ex['f1'])}** | {pct(nm['f1'])} | "
            f"{pct(ov['precision'])} | {pct(ov['recall'])} | **{pct(ov['f1'])}** | "
            f"**{pct(ch['pii_char_recall_coverage'])}** | {pct(ch['pii_char_precision'])} | {pct(ch['over_masking_rate_on_non_pii'])} | "
            f"`{ex_pass}/6` | **`{ov_pass}/6`** |"
        )

    lines.extend(
        [
            "",
            "### 3.2 Per-Label Breakdown on Business Holdout (Required 6 MVP Labels — Target: Recall ≥ 95%, Precision ≥ 90%)",
            "",
            "| Label (Support) | Metric Mode | OPF Baseline | Presidio Baseline | OPF + Targeted Rules | Presidio + Targeted Rules | Full Hybrid |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )

    for lbl in REQUIRED_6:
        sup = bus_eval["opf_baseline"]["exact"]["per_label"][lbl]["support"]
        for mode_key, mode_label in [("exact", "Exact Span"), ("overlap", "Overlap (IoU>0)")]:
            row_cells = []
            for cand in CANDIDATE_NAMES:
                cm = bus_eval[cand][mode_key]["per_label"][lbl]
                p, r, f1 = cm["precision"], cm["recall"], cm["f1"]
                passed = p >= 0.90 and r >= 0.95
                badge = "PASS" if passed else "MISS"
                row_cells.append(f"P={pct(p)} R={pct(r)} (**{pct(f1)}** `{badge}`)")
            lines.append(f"| **`{lbl}`** (`n={sup}`) | {mode_label} | " + " | ".join(row_cells) + " |")

    lines.extend(
        [
            "",
            "### 3.3 Business Holdout Slice Breakdown by Document Type (`form`, `invoice`, `correspondence`)",
            "",
            "| Document Slice | Docs | Spans | Variant | Exact Precision | Exact Recall | Exact F1 | Overlap F1 | Char PII Recall | Over-Masking Rate |",
            "| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )

    for dt, ddata in slices_bus.items():
        n_docs = ddata["num_docs"]
        for cand, label in CANDIDATE_NAMES.items():
            cm = ddata["candidates"][cand]
            ex = cm["required_6_exact_micro"]
            ov = cm["required_6_overlap_micro"]
            lines.append(
                f"| **`{dt}`** | {n_docs} | {ex['support']} | {label} | {pct(ex['precision'])} | {pct(ex['recall'])} | "
                f"**{pct(ex['f1'])}** | {pct(ov['f1'])} | {pct(cm['pii_char_recall_coverage'])} | {pct(cm['over_masking_rate'])} |"
            )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Secondary Benchmark: Held-Out Gravitee Test Split (`gravitee_test_240`, All 25 Labels)",
            "",
            "### 4.1 Required-6 Micro Summary on Gravitee Test (`n=240` docs, `635` required-6 spans) & Dev (`n=120` docs, `364` spans)",
            "",
            "| Split | Pipeline Variant | Exact Precision | Exact Recall | Exact F1 | Normalized F1 | Overlap Precision | Overlap Recall | Overlap F1 | Char PII Coverage | Over-Masking Rate |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )

    for split_label, split_dict in [("Gravitee Test (240)", grav_test_eval), ("Gravitee Dev (120)", grav_dev_eval)]:
        for cand, label in CANDIDATE_NAMES.items():
            m = split_dict[cand]
            ex = m["exact"]["required_6_micro"]
            nm = m["normalized"]["required_6_micro"]
            ov = m["overlap"]["required_6_micro"]
            ch = m["character_metrics"]
            lines.append(
                f"| **{split_label}** | {label} | {pct(ex['precision'])} | {pct(ex['recall'])} | **{pct(ex['f1'])}** | "
                f"{pct(nm['f1'])} | {pct(ov['precision'])} | {pct(ov['recall'])} | **{pct(ov['f1'])}** | "
                f"{pct(ch['pii_char_recall_coverage'])} | {pct(ch['over_masking_rate_on_non_pii'])} |"
            )

    lines.extend(
        [
            "",
            "### 4.2 All 25 Canonical Gravitee Labels on Held-Out Test Split (`gravitee_test_240`)",
            "",
            "| # | Gravitee Label | MVP Tier | Test Support | OPF Baseline Exact F1 (Ov F1) | Presidio Baseline Exact F1 (Ov F1) | OPF + Rules Exact F1 (Ov F1) | Presidio + Rules Exact F1 (Ov F1) | Full Hybrid Exact F1 (Ov F1) | Native Model Support Note |",
            "| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
        ]
    )

    all_25 = sorted(grav_test_eval["opf_baseline"]["exact"]["per_label"].keys())
    label_notes = {
        "PERSON": "Required MVP; OPF `private_person` & spaCy `PERSON`",
        "EMAIL_ADDRESS": "Required MVP; OPF `private_email` & Presidio regex",
        "PHONE_NUMBER": "Required MVP; OPF `private_phone` & Presidio `PhoneRecognizer`",
        "LOCATION": "Required MVP; OPF `private_address` & spaCy `GPE`/`LOC`",
        "DATE_TIME": "Required MVP; OPF `private_date` & spaCy `DATE`/`TIME`",
        "US_SSN": "Required MVP; OPF collapses into `account_number` (fixed by disambiguation rule)",
        "CREDIT_CARD": "OPF collapses into `account_number` (disambiguated to 67% OvF1)",
        "IBAN_CODE": "OPF collapses into `account_number` (disambiguated to 95% F1)",
        "IP_ADDRESS": "Presidio `IpRecognizer` achieves 95.65% F1; not in OPF 8-class schema",
        "URL": "Presidio `UrlRecognizer` achieves 85.71% OvF1",
        "NRP": "Mapped from spaCy `NORP`",
        "ORGANIZATION": "Mapped from spaCy `ORG`; intentionally excluded by OPF personal-PII policy",
        "PASSWORD": "Mapped from OPF `secret` (47.83% recall)",
        "US_BANK_NUMBER": "OPF `account_number` primary target (88.24% recall, low precision without disambiguation)",
        "US_DRIVER_LICENSE": "Presidio `UsDriverLicenseRecognizer` achieves 90.00% recall / 69.23% F1",
        "US_ITIN": "Presidio `UsItinRecognizer` + regex achieves 74.07% F1",
        "US_PASSPORT": "Presidio `UsPassportRecognizer` achieves 100% precision / 25% recall",
        "AGE": "Out-of-schema for both unchanged OPF and default Presidio",
        "COORDINATE": "Out-of-schema for both unchanged OPF and default Presidio",
        "FINANCIAL": "Out-of-schema for both unchanged OPF and default Presidio",
        "HONORIFIC": "Out-of-schema for both unchanged OPF and default Presidio (annotated inside/near PERSON)",
        "IMEI": "Out-of-schema for both unchanged OPF and default Presidio",
        "MAC_ADDRESS": "Out-of-schema for both unchanged OPF and default Presidio",
        "TITLE": "Out-of-schema for both unchanged OPF and default Presidio (job titles)",
        "US_LICENSE_PLATE": "Out-of-schema for both unchanged OPF and default Presidio",
    }

    for idx, lbl in enumerate(all_25, 1):
        tier = "**Required-6**" if lbl in REQUIRED_6 else "Extended-19"
        sup = grav_test_eval["opf_baseline"]["exact"]["per_label"][lbl]["support"]
        cells = []
        for cand in CANDIDATE_NAMES:
            ex_f1 = grav_test_eval[cand]["exact"]["per_label"][lbl]["f1"]
            ov_f1 = grav_test_eval[cand]["overlap"]["per_label"][lbl]["f1"]
            cells.append(f"{pct(ex_f1)} ({pct(ov_f1)})")
        lines.append(
            f"| {idx} | `{lbl}` | {tier} | {sup} | "
            + " | ".join(cells)
            + f" | {label_notes.get(lbl, '')} |"
        )

    lines.extend(
        [
            "",
            "### 4.3 Why Public Multi-Source Gravitee Scores Lower Than Clean Business Holdout (Root-Cause Analysis)",
            "",
            "1. **Synthetic Annotation Inconsistencies Across the 6 Upstream Sources (`slices.gravitee_test_by_source`)**:",
            "   - On `gretelai/gretel-pii-masking-en-v1`, `OPF + Targeted Rules` achieves **66.67% Exact F1 / 74.26% Overlap F1 / 88.93% character recall** (and Hybrid reaches **97.63% character recall**).",
            "   - On `DataikuNLP/kiji-pii-training-data`, OPF achieves **91.41% character PII coverage** (Hybrid **100.00%**), but exact span F1 is **38.40%** because `kiji` annotates salutations (`Mr.`, `Dr.`) and trailing punctuation inside `PERSON`/`LOCATION` spans.",
            "   - On `beki/privy` (SQL/JSON/API payloads) and `urchade/synthetic-pii-ner-mistral-v1`, non-PII labels like generic relative dates (`today`, `quarterly`, `2025 fiscal year`), organization names, and synthetic malformed strings are inconsistently tagged, causing **36.99% non-PII over-masking** in Presidio vs **8.04%** in OPF.",
            "",
            "---",
            "",
            "## 5. Error Taxonomy & Concrete Failure Examples (Business Holdout)",
            "",
            "| Pipeline Variant | Exact Matches (TP) | Boundary Shifts (IoU>0, Same Label) | Label Confusion / Policy Mismatch (IoU>0, Diff Label) | Missed Entities (Zero-Overlap FN) | False Alarms on Non-PII (Zero-Overlap FP) |",
            "| :--- | :---: | :---: | :---: | :---: | :---: |",
        ]
    )

    for cand, label in CANDIDATE_NAMES.items():
        cnt = bus_eval[cand]["error_taxonomy"]["counts"]
        lines.append(
            f"| **{label}** | **{cnt['exact_match']}** | {cnt['boundary_shift']} | "
            f"{cnt['label_confusion_or_policy']} | {cnt['missed_entity_fn']} | {cnt['false_alarm_fp']} |"
        )

    lines.extend(
        [
            "",
            "### Representative Error Examples Observed on Business Holdout",
            "1. **Policy Mismatch (`opf_baseline` → Fixed by `opf_targeted_rules`)**:",
            "   - `form_01`: Gold `US_SSN` `'412-58-9034'` → Unchanged OPF predicts `account_number` (mapped 1:1 to `US_BANK_NUMBER`). Disambiguating `account_number` with `SSN_REGEX` eliminates **60 of 64** label confusion errors.",
            "2. **Span Boundary Shift (`presidio_spacy_baseline` & `opf_baseline` → Fixed by `opf_targeted_rules`)**:",
            "   - `form_01`: Gold `LOCATION` `'742 Evergreen Terrace, Springfield, IL 62704'` → Unchanged OPF predicts `'742 Evergreen Terrace, Springfield, IL'` (omits ZIP code `'62704'`); Unchanged Presidio splits `'Springfield'` (`GPE`) and `'IL'` (`GPE`) and misses `'742 Evergreen Terrace'`. Combining `US_FULL_ADDRESS_REGEX` + contiguous location merging raises `LOCATION` Overlap F1 to **95.45% (`opf_targeted_rules`)** and **97.74% (`presidio_targeted_rules`)**.",
            "3. **False Alarms / Over-Masking (`presidio_spacy_baseline` vs `opf_targeted_rules`)**:",
            "   - Unchanged Presidio triggers **100 false-alarm spans** on the 60 business documents (e.g., flagging invoice headers, product names, and currency/date fragments), whereas `OPF + Targeted Rules` produces only **5 false alarms** across all 60 documents (`0.49%` non-PII character over-masking).",
            "",
            "---",
            "",
            "## 6. Runtime Latency, Throughput & Deployment Hardware Recommendation",
            "",
            "| Engine / Mode | Warm Startup (s) | Mean Latency (ms/doc) | p50 Latency (ms/doc) | p95 Latency (ms/doc) | Throughput (docs/s) | Throughput (chars/s) | Peak RSS RAM (MB) |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )

    p_stock = perf["business_holdout_60"]["openai_privacy_filter_stock_cpu_sample10"]
    p_opf_bus = perf["business_holdout_60"]["openai_privacy_filter_grouped_moe_cpu"]
    p_pres_bus = perf["business_holdout_60"]["presidio_spacy_cpu"]
    p_opf_test = perf["gravitee_test_240"]["openai_privacy_filter_grouped_moe_cpu"]
    p_pres_test = perf["gravitee_test_240"]["presidio_spacy_cpu"]

    lines.extend(
        [
            f"| **OPF Stock CPU (Unpatched BMM, Business Holdout)** | `{data['startup_seconds']['openai_privacy_filter']}s` | `{p_stock['latency_mean_ms']}` | `{p_stock['latency_p50_ms']}` | `{p_stock['latency_p95_ms']}` | `{p_stock['docs_per_sec']}` | `{p_stock['chars_per_sec']}` | `{p_stock['peak_ram_mb']}` |",
            f"| **OPF Grouped-MoE CPU (Business Holdout, 60 docs)** | `{data['startup_seconds']['openai_privacy_filter']}s` | **`{p_opf_bus['latency_mean_ms']}`** | **`{p_opf_bus['latency_p50_ms']}`** | `{p_opf_bus['latency_p95_ms']}` | `{p_opf_bus['docs_per_sec']}` | `{p_opf_bus['chars_per_sec']}` | `{p_opf_bus['peak_ram_mb']}` |",
            f"| **Presidio + spaCy `en_core_web_lg` CPU (Business Holdout, 60 docs)** | `{data['startup_seconds']['presidio_spacy_en_core_web_lg']}s` | **`{p_pres_bus['latency_mean_ms']}`** | **`{p_pres_bus['latency_p50_ms']}`** | `{p_pres_bus['latency_p95_ms']}` | **`{p_pres_bus['docs_per_sec']}`** | **`{p_pres_bus['chars_per_sec']}`** | `{p_pres_bus['peak_ram_mb']}` |",
            f"| **OPF Grouped-MoE CPU (Gravitee Test, 240 docs)** | `{data['startup_seconds']['openai_privacy_filter']}s` | `{p_opf_test['latency_mean_ms']}` | `{p_opf_test['latency_p50_ms']}` | `{p_opf_test['latency_p95_ms']}` | `{p_opf_test['docs_per_sec']}` | `{p_opf_test['chars_per_sec']}` | `{p_opf_test['peak_ram_mb']}` |",
            f"| **Presidio + spaCy `en_core_web_lg` CPU (Gravitee Test, 240 docs)** | `{data['startup_seconds']['presidio_spacy_en_core_web_lg']}s` | `{p_pres_test['latency_mean_ms']}` | `{p_pres_test['latency_p50_ms']}` | `{p_pres_test['latency_p95_ms']}` | `{p_pres_test['docs_per_sec']}` | `{p_pres_test['chars_per_sec']}` | `{p_pres_test['peak_ram_mb']}` |",
            "",
            "### Architecture & Deployment Recommendation",
            "1. **If GPU or Async Batch Worker (≤ 1s/doc SLA) is available**: Deploy **`OPF + Targeted Disambiguation & Rules` (`opf_targeted_rules`)** with the grouped-MoE patch (or Triton on T4/L4 GPU). It achieves the highest precision (**96.49% Exact / 99.40% Character Precision**) and the lowest non-PII over-masking rate (**0.49%** vs Presidio's **10.12%**), preventing destructive redaction of business context.",
            "2. **If Strict Synchronous CPU-Only Latency (< 30 ms/doc) is required**: Deploy **`Presidio + Targeted Rules` (`presidio_targeted_rules`)** with an allowlist/context filter for `PERSON` and `DATE_TIME` false positives. It runs at **18.01 ms/doc (`55.3 docs/s`)** on CPU and achieves **98.69% Overlap Recall** across the 6 required MVP entities.",
        ]
    )

    return "\n".join(lines) + "\n"


def build_html_report(data: dict[str, Any]) -> str:
    bus_eval = data["evaluation"]["business_holdout_60"]
    perf = data["runtime_performance"]["business_holdout_60"]
    hw = data["hardware_specs"]

    bus_rows_html = []
    for cand, label in CANDIDATE_NAMES.items():
        m = bus_eval[cand]
        ex = m["exact"]["required_6_micro"]
        ov = m["overlap"]["required_6_micro"]
        ch = m["character_metrics"]
        ex_pass = sum(
            1
            for l in REQUIRED_6
            if m["exact"]["per_label"][l]["precision"] >= 0.90
            and m["exact"]["per_label"][l]["recall"] >= 0.95
        )
        ov_pass = sum(
            1
            for l in REQUIRED_6
            if m["overlap"]["per_label"][l]["precision"] >= 0.90
            and m["overlap"]["per_label"][l]["recall"] >= 0.95
        )
        highlight = ' class="row-best"' if cand == "opf_targeted_rules" else ""
        bus_rows_html.append(
            f"<tr{highlight}>"
            f"<td>{label}</td>"
            f"<td>{pct(ex['precision'])}</td>"
            f"<td>{pct(ex['recall'])}</td>"
            f"<td><strong>{pct(ex['f1'])}</strong></td>"
            f"<td><strong>{pct(ov['f1'])}</strong></td>"
            f"<td>{pct(ch['pii_char_recall_coverage'])}</td>"
            f"<td>{pct(ch['over_masking_rate_on_non_pii'])}</td>"
            f"<td><span class='badge {'pass' if ov_pass >= 5 else 'warn'}'>{ex_pass}/6 Ex · {ov_pass}/6 Ov</span></td>"
            f"</tr>"
        )

    per_label_cards = []
    for lbl in REQUIRED_6:
        sup = bus_eval["opf_baseline"]["exact"]["per_label"][lbl]["support"]
        bars = []
        for cand, short_lbl, color_var in [
            ("opf_baseline", "OPF Base", "var(--muted-foreground, #64748b)"),
            ("presidio_spacy_baseline", "Presidio Base", "var(--chart-4, #94a3b8)"),
            ("opf_targeted_rules", "OPF + Rules", "var(--success, #10b981)"),
            ("presidio_targeted_rules", "Presidio + Rules", "var(--info, #3b82f6)"),
            ("hybrid_opf_presidio_rules", "Full Hybrid", "var(--chart-2, #8b5cf6)"),
        ]:
            ex = bus_eval[cand]["exact"]["per_label"][lbl]
            ov = bus_eval[cand]["overlap"]["per_label"][lbl]
            w_ex = max(2.0, ex["f1"] * 100)
            bars.append(
                f"<div class='bar-row'>"
                f"<div class='bar-label'>{short_lbl}</div>"
                f"<div class='bar-track'>"
                f"<div class='bar-fill' style='width:{w_ex:.1f}%; background:{color_var};'></div>"
                f"</div>"
                f"<div class='bar-val'>Ex {pct(ex['f1'])} · Ov {pct(ov['f1'])}</div>"
                f"</div>"
            )
        per_label_cards.append(
            f"<div class='card'>"
            f"<div class='card-title'>{lbl} <span class='sub'>(n={sup})</span></div>"
            + "".join(bars)
            + "</div>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>ML-07 PII Detection Model Evaluation &amp; Fine-Tuning Decision</title>
<style>
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0;
    padding: 0;
    font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
    color: var(--foreground, #f8fafc);
    line-height: 1.45;
  }}
  .verdict-box {{
    background: var(--card, rgba(30, 41, 59, 0.7));
    border: 1px solid var(--success, #10b981);
    border-radius: var(--radius, 10px);
    padding: 16px;
    margin-bottom: 16px;
  }}
  .verdict-title {{
    color: var(--success, #10b981);
    font-weight: 700;
    font-size: 15px;
    margin-bottom: 4px;
  }}
  .verdict-body {{ font-size: 12.5px; color: var(--foreground, #e2e8f0); }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 18px;
  }}
  .kpi {{
    background: var(--card, rgba(30, 41, 59, 0.7));
    border: 1px solid var(--border, #334155);
    border-radius: var(--radius, 10px);
    padding: 12px;
  }}
  .kpi-label {{ font-size: 11px; color: var(--muted-foreground, #94a3b8); text-transform: uppercase; letter-spacing: 0.03em; }}
  .kpi-value {{ font-size: 19px; font-weight: 700; margin: 4px 0; color: var(--primary, #38bdf8); }}
  .kpi-sub {{ font-size: 11px; color: var(--muted-foreground, #94a3b8); }}
  h2 {{ font-size: 14px; margin: 16px 0 8px 0; color: var(--foreground, #e2e8f0); }}
  table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--card, rgba(30, 41, 59, 0.7));
    border: 1px solid var(--border, #334155);
    border-radius: var(--radius, 8px);
    overflow: hidden;
    font-size: 11.5px;
    margin-bottom: 16px;
  }}
  th, td {{
    padding: 7px 8px;
    text-align: left;
    border-bottom: 1px solid var(--border, #334155);
  }}
  th {{ background: var(--secondary, rgba(15, 23, 42, 0.8)); color: var(--muted-foreground, #94a3b8); font-weight: 600; }}
  .row-best {{ background: rgba(16, 185, 129, 0.12); font-weight: 600; }}
  .badge {{
    display: inline-block;
    padding: 2px 6px;
    border-radius: 999px;
    font-size: 10.5px;
    font-weight: 600;
  }}
  .badge.pass {{ background: rgba(16, 185, 129, 0.2); color: var(--success, #10b981); }}
  .badge.warn {{ background: rgba(245, 158, 11, 0.2); color: var(--warning, #f59e0b); }}
  .cards-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    margin-bottom: 16px;
  }}
  .card {{
    background: var(--card, rgba(30, 41, 59, 0.7));
    border: 1px solid var(--border, #334155);
    border-radius: var(--radius, 10px);
    padding: 12px;
  }}
  .card-title {{ font-weight: 700; font-size: 12.5px; margin-bottom: 8px; }}
  .card-title .sub {{ color: var(--muted-foreground, #94a3b8); font-weight: 400; font-size: 11px; }}
  .bar-row {{
    display: grid;
    grid-template-columns: 88px 1fr 106px;
    align-items: center;
    gap: 6px;
    margin-bottom: 5px;
    font-size: 11px;
  }}
  .bar-label {{ color: var(--muted-foreground, #94a3b8); }}
  .bar-track {{
    height: 8px;
    background: var(--secondary, rgba(15, 23, 42, 0.9));
    border-radius: 99px;
    overflow: hidden;
  }}
  .bar-fill {{ height: 100%; border-radius: 99px; }}
  .bar-val {{ text-align: right; font-variant-numeric: tabular-nums; font-family: var(--font-mono, monospace); font-size: 10.5px; }}
</style>
</head>
<body>
  <div class="verdict-box">
    <div class="verdict-title">Verdict: No Fine-Tuning Required for MVP &mdash; Ship Targeted Disambiguation &amp; Boundary Rules</div>
    <div class="verdict-body">
      Unchanged baselines fail strict exact gates due to <strong>label taxonomy policy</strong> (OPF maps <code>US_SSN</code> into <code>account_number</code>; 98.36% char recall) and <strong>address boundary splitting</strong> (spaCy tags only city/state inside street addresses). Adding lightweight regex disambiguation + address boundary rules raises <strong>OPF Exact F1 from 76.72% &rarr; 96.39% (Overlap F1 98.58%, Char Recall 98.74%, Over-Masking 0.49%)</strong> and <strong>Presidio Overlap Recall to 98.69% (6/6 labels passing Overlap gate at 18.0 ms/doc CPU)</strong> without fine-tuning model weights.
    </div>
  </div>

  <div class="kpi-grid">
    <div class="kpi">
      <div class="kpi-label">OPF + Rules Exact F1</div>
      <div class="kpi-value" style="color:var(--success, #10b981);">96.39%</div>
      <div class="kpi-sub">Up from 76.72% (+19.7 pts) · 98.58% Ov F1</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Char Recall / Prec</div>
      <div class="kpi-value">98.7% / 99.4%</div>
      <div class="kpi-sub">OPF + Rules (9,086 / 9,202 chars)</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Over-Masking Rate</div>
      <div class="kpi-value" style="color:var(--chart-2, #a78bfa);">0.49% vs 10.1%</div>
      <div class="kpi-sub">OPF (5 FPs) vs Presidio (100 FPs)</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">CPU p50 Latency</div>
      <div class="kpi-value" style="color:var(--warning, #f59e0b);">17.4 vs 655 ms</div>
      <div class="kpi-sub">Presidio vs OPF Grouped-MoE ({hw['cpu_count_logical']} vCPU)</div>
    </div>
  </div>

  <h2>1. Independent Business-Text Holdout (60 Docs: 20 Forms, 20 Invoices, 20 Correspondence &mdash; 457 Spans)</h2>
  <table>
    <thead>
      <tr>
        <th>Pipeline Variant</th>
        <th>Exact P</th>
        <th>Exact R</th>
        <th>Exact F1</th>
        <th>Overlap F1</th>
        <th>Char Recall</th>
        <th>Over-Mask</th>
        <th>Gate (&ge;95% R, &ge;90% P)</th>
      </tr>
    </thead>
    <tbody>
      {''.join(bus_rows_html)}
    </tbody>
  </table>

  <h2>2. Per-Label Exact &amp; Overlap F1 Across the 6 Required MVP Entities (Business Holdout)</h2>
  <div class="cards-grid">
    {''.join(per_label_cards)}
  </div>

  <h2>3. Error Taxonomy (457 Gold Spans) &amp; CPU Runtime Profile ({hw['cpu_model']})</h2>
  <table>
    <thead>
      <tr>
        <th>Pipeline Variant</th>
        <th>Exact Match</th>
        <th>Boundary Shift</th>
        <th>Label Policy</th>
        <th>Missed (FN)</th>
        <th>False Alarm (FP)</th>
        <th>p50 / p95 Latency</th>
        <th>Peak RAM</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>OPF Baseline (Unchanged)</td>
        <td>341</td>
        <td>85</td>
        <td>64 (SSN&rarr;Acct)</td>
        <td>15</td>
        <td>5</td>
        <td>{perf['openai_privacy_filter_grouped_moe_cpu']['latency_p50_ms']} / {perf['openai_privacy_filter_grouped_moe_cpu']['latency_p95_ms']} ms</td>
        <td>{perf['openai_privacy_filter_grouped_moe_cpu']['peak_ram_mb']} MB</td>
      </tr>
      <tr>
        <td>Presidio + spaCy Baseline</td>
        <td>352</td>
        <td>203 (Addr split)</td>
        <td>5</td>
        <td>2</td>
        <td>100</td>
        <td>{perf['presidio_spacy_cpu']['latency_p50_ms']} / {perf['presidio_spacy_cpu']['latency_p95_ms']} ms</td>
        <td>{perf['presidio_spacy_cpu']['peak_ram_mb']} MB</td>
      </tr>
      <tr class="row-best">
        <td>OPF + Targeted Rules</td>
        <td>440 (96.3%)</td>
        <td>12</td>
        <td>4</td>
        <td>3</td>
        <td>5</td>
        <td>{perf['openai_privacy_filter_grouped_moe_cpu']['latency_p50_ms']} / {perf['openai_privacy_filter_grouped_moe_cpu']['latency_p95_ms']} ms</td>
        <td>{perf['openai_privacy_filter_grouped_moe_cpu']['peak_ram_mb']} MB</td>
      </tr>
      <tr>
        <td>Presidio + Targeted Rules</td>
        <td>431 (94.3%)</td>
        <td>20</td>
        <td>4</td>
        <td>2</td>
        <td>100</td>
        <td>{perf['presidio_spacy_cpu']['latency_p50_ms']} / {perf['presidio_spacy_cpu']['latency_p95_ms']} ms</td>
        <td>{perf['presidio_spacy_cpu']['peak_ram_mb']} MB</td>
      </tr>
      <tr>
        <td>Full Hybrid (OPF + Presidio + Rules)</td>
        <td>434 (95.0%)</td>
        <td>16</td>
        <td>8</td>
        <td>0</td>
        <td>100</td>
        <td>~672 / 974 ms</td>
        <td>4259.2 MB</td>
      </tr>
    </tbody>
  </table>
</body>
</html>
"""
    return html


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    res_path = repo_root / "evaluation" / "results" / "benchmark_results.json"
    data = json.loads(res_path.read_text(encoding="utf-8"))

    reports_dir = repo_root / "plans" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    md_path = reports_dir / "ml-07-pii-evaluation-report.md"
    html_path = reports_dir / "ml-07-pii-evaluation-report.html"

    md_path.write_text(build_markdown_report(data), encoding="utf-8")
    html_path.write_text(build_html_report(data), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {html_path}")


if __name__ == "__main__":
    main()
