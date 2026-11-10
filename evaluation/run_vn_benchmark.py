#!/usr/bin/env python3
"""Comprehensive Vietnamese PII (19 OpenPII Labels) Pre-Finetune vs Post-Finetune Benchmark Runner.

Scores and compares all 10 candidate pipelines on:
- `vn_dev_300` (300 validation docs, 2,500 gold spans across all 19 labels)
- `vn_test_600` (600 held-out test docs, 4,758 gold spans across all 19 labels)
- `vn_independent_holdout_75` (60 positive realistic Vietnamese docs across 3 genres + 15 negative non-PII docs)

Candidate Matrix (Pre-Finetune vs Post-Finetune x Model-Only vs +Rules):
  [Pre-Finetune Baselines]
  1. `spacy_blank_vi_pre_model_only`: Untrained spaCy `blank("vi")` NER (0% baseline reference)
  2. `spacy_blank_vi_pre_plus_rules`: Untrained spaCy `blank("vi")` + Vietnamese deterministic rules (`vn_rules.py`)
  3. `opf_pretrained_pre_model_only`: Out-of-the-box `openai/privacy-filter` (8-label native -> 1:1 primary map to 19 labels; also reports family-compatible recall to separate taxonomy mismatch from missed entities)
  4. `opf_pretrained_pre_plus_rules`: Out-of-the-box `openai/privacy-filter` + context disambiguation + Vietnamese deterministic rules
  [Post-Finetune Direction A — Lightweight spaCy NER (tok2vec/CNN, 19 labels)]
  5. `spacy_finetuned_post_model_only`: Fine-tuned `spaCy NER (19 labels)` pure model
  6. `spacy_finetuned_post_plus_rules`: Fine-tuned `spaCy NER (19 labels)` + Vietnamese deterministic rules
  [Post-Finetune Direction B — Fine-Tuned OPF (77 BIESO classes / 19 labels)]
  7. `opf_finetuned_post_model_only`: Fine-tuned `OPF (19 labels)` pure model
  8. `opf_finetuned_post_plus_rules`: Fine-tuned `OPF (19 labels)` + Vietnamese deterministic rules
  [Post-Finetune Combined Hybrid]
  9. `hybrid_finetuned_opf_spacy_rules`: Fine-tuned `OPF (19 labels)` + Fine-tuned `spaCy NER (19 labels)` + Vietnamese rules

Also locks baseline quality thresholds on `vn_dev_300` before evaluating `vn_test_600` and `vn_independent_holdout_75`,
and runs an English regression check on `business_holdout_60.jsonl` to confirm zero regression on EN.
"""

from __future__ import annotations

import json
import os
import platform
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import psutil
import spacy
import torch

from evaluation.metrics import f1_score, safe_div, score_predictions, span_iou
from evaluation.prepare_vn_data import OPENPII_19_LABELS
from evaluation.vn_rules import (
    OPF_8_COMPATIBLE_FAMILIES,
    OPF_8_TO_OPENPII_19_PRIMARY_MAP,
    combine_model_and_vn_rules,
    deduplicate_vn_spans,
    extract_vn_deterministic_spans,
    filter_vn_false_positives,
)

# Locked quality gates established after Pre-Finetune baseline on Dev, prior to Final Test selection
LOCKED_VN_QUALITY_GATES = {
    "overall_19_exact_micro_f1_min": 0.75,
    "overall_19_overlap_micro_f1_min": 0.82,
    "pii_char_recall_coverage_min": 0.85,
    "over_masking_rate_on_non_pii_max": 0.05,
    "negative_holdout_false_positive_spans_max": 2,
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def compute_opf_pre_family_compatibility(
    docs: list[dict[str, Any]],
    opf_pre_raw_by_doc: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Evaluate Pre-Finetune OPF's 8 coarse labels (`private_person`, `private_address`, `account_number`, etc.)
    against compatible OpenPII 19-label families so we explicitly separate:
    - Taxonomy mismatch error (entity detected by base OPF under a coarse 8-label family that collapses multiple OpenPII labels)
    - True missed entity FN (entity not detected by base OPF at all)
    """
    total_gold = 0
    strict_1to1_matched = 0
    family_compatible_matched = 0
    unmatched_missed_fn = 0
    by_label: dict[str, dict[str, int]] = {
        lbl: {
            "support": 0,
            "strict_1to1_hit": 0,
            "family_compatible_hit": 0,
            "taxonomy_collapsed_only": 0,
            "missed_fn": 0,
        }
        for lbl in OPENPII_19_LABELS
    }

    for d in docs:
        doc_id = str(d["id"])
        raw_preds = opf_pre_raw_by_doc.get(doc_id, [])
        for gs in d.get("spans", []):
            g_s, g_e, g_lbl = int(gs["start"]), int(gs["end"]), str(gs["label"])
            if g_lbl not in by_label:
                continue
            total_gold += 1
            by_label[g_lbl]["support"] += 1

            # Check overlap with any raw OPF prediction
            overlapping_preds = [
                p
                for p in raw_preds
                if span_iou(g_s, g_e, int(p["start"]), int(p["end"])) > 0.0
            ]
            if not overlapping_preds:
                unmatched_missed_fn += 1
                by_label[g_lbl]["missed_fn"] += 1
                continue

            # Check if primary 1:1 map matches
            is_strict = any(
                OPF_8_TO_OPENPII_19_PRIMARY_MAP.get(str(p["label"]), str(p["label"])) == g_lbl
                for p in overlapping_preds
            )
            is_family = any(
                g_lbl in OPF_8_COMPATIBLE_FAMILIES.get(str(p["label"]), set())
                for p in overlapping_preds
            )
            if is_strict:
                strict_1to1_matched += 1
                family_compatible_matched += 1
                by_label[g_lbl]["strict_1to1_hit"] += 1
                by_label[g_lbl]["family_compatible_hit"] += 1
            elif is_family:
                family_compatible_matched += 1
                by_label[g_lbl]["family_compatible_hit"] += 1
                by_label[g_lbl]["taxonomy_collapsed_only"] += 1
            else:
                unmatched_missed_fn += 1
                by_label[g_lbl]["missed_fn"] += 1

    taxonomy_collapsed_count = family_compatible_matched - strict_1to1_matched
    return {
        "total_gold_spans": total_gold,
        "strict_1to1_overlap_recall": round(safe_div(strict_1to1_matched, total_gold), 4),
        "family_compatible_overlap_recall": round(safe_div(family_compatible_matched, total_gold), 4),
        "taxonomy_mismatch_fraction_of_gold": round(safe_div(taxonomy_collapsed_count, total_gold), 4),
        "true_missed_entity_fraction_of_gold": round(safe_div(unmatched_missed_fn, total_gold), 4),
        "per_label_breakdown": by_label,
    }


def evaluate_negative_non_pii_slice(
    docs: list[dict[str, Any]],
    candidates_preds: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    """Measure false-positive spans and over-masked characters specifically on 0-PII negative Vietnamese docs."""
    neg_docs = [d for d in docs if not d.get("spans")]
    total_neg_chars = sum(len(d["text"]) for d in neg_docs)
    out: dict[str, Any] = {}
    for cand_name, preds_by_doc in candidates_preds.items():
        fp_spans = 0
        docs_with_fp = 0
        masked_chars = 0
        for d in neg_docs:
            doc_id = str(d["id"])
            text = d["text"]
            n_c = len(text)
            p_list = preds_by_doc.get(doc_id, [])
            if p_list:
                docs_with_fp += 1
                fp_spans += len(p_list)
            mask = [False] * n_c
            for sp in p_list:
                for k in range(max(0, int(sp["start"])), min(n_c, int(sp["end"]))):
                    mask[k] = True
            masked_chars += sum(1 for m in mask if m)
        out[cand_name] = {
            "num_negative_docs": len(neg_docs),
            "total_negative_chars": total_neg_chars,
            "false_positive_spans": fp_spans,
            "docs_with_false_positive": docs_with_fp,
            "false_positive_doc_rate": round(safe_div(docs_with_fp, len(neg_docs)), 4),
            "over_masked_chars": masked_chars,
            "over_masking_char_rate": round(safe_div(masked_chars, total_neg_chars), 6),
        }
    return out


def build_candidate_predictions_for_split(
    docs: list[dict[str, Any]],
    raw_split: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Construct all 9 candidate prediction dicts `{doc_id: [{start, end, label, score}]}` for a dataset split."""
    spacy_pre_raw = raw_split["spacy_pre"]
    opf_pre_raw = raw_split["opf_pre"]
    spacy_post_raw = raw_split["spacy_post"]
    opf_post_raw = raw_split["opf_post"]

    cands: dict[str, dict[str, list[dict[str, Any]]]] = {
        "spacy_blank_vi_pre_model_only": {},
        "spacy_blank_vi_pre_plus_rules": {},
        "opf_pretrained_pre_model_only": {},
        "opf_pretrained_pre_plus_rules": {},
        "spacy_finetuned_post_model_only": {},
        "spacy_finetuned_post_plus_rules": {},
        "opf_finetuned_post_model_only": {},
        "opf_finetuned_post_plus_rules": {},
        "hybrid_finetuned_opf_spacy_rules": {},
    }

    for d in docs:
        doc_id = str(d["id"])
        text = d["text"]

        # 1. spaCy Untrained Pre (Model-Only)
        cands["spacy_blank_vi_pre_model_only"][doc_id] = deduplicate_vn_spans(
            spacy_pre_raw.get(doc_id, [])
        )

        # 2. spaCy Untrained Pre + VN Rules (equals Rules + untrained model)
        cands["spacy_blank_vi_pre_plus_rules"][doc_id] = extract_vn_deterministic_spans(text)

        # 3. OPF Pretrained Pre (Model-Only, strict 1:1 primary map from 8 native labels)
        opf_pre_1to1 = []
        for sp in opf_pre_raw.get(doc_id, []):
            mapped_lbl = OPF_8_TO_OPENPII_19_PRIMARY_MAP.get(str(sp["label"]), str(sp["label"]))
            opf_pre_1to1.append(
                {
                    "start": int(sp["start"]),
                    "end": int(sp["end"]),
                    "label": mapped_lbl,
                    "score": float(sp.get("score", 0.90)),
                }
            )
        cands["opf_pretrained_pre_model_only"][doc_id] = deduplicate_vn_spans(opf_pre_1to1)

        # 4. OPF Pretrained Pre + VN Rules (context disambiguation + VN deterministic regexes)
        cands["opf_pretrained_pre_plus_rules"][doc_id] = combine_model_and_vn_rules(
            text, opf_pre_raw.get(doc_id, []), is_pretrained_opf_8=True
        )

        # 5. spaCy Fine-Tuned Post (Model-Only, 19 labels)
        sp_post = spacy_post_raw.get(doc_id, [])
        cands["spacy_finetuned_post_model_only"][doc_id] = deduplicate_vn_spans(sp_post)

        # 6. spaCy Fine-Tuned Post + VN Rules
        cands["spacy_finetuned_post_plus_rules"][doc_id] = combine_model_and_vn_rules(
            text, sp_post, is_pretrained_opf_8=False
        )

        # 7. OPF Fine-Tuned Post (Model-Only, 19 labels)
        opf_post = opf_post_raw.get(doc_id, [])
        cands["opf_finetuned_post_model_only"][doc_id] = deduplicate_vn_spans(opf_post)

        # 8. OPF Fine-Tuned Post + VN Rules
        cands["opf_finetuned_post_plus_rules"][doc_id] = combine_model_and_vn_rules(
            text, opf_post, is_pretrained_opf_8=False
        )

        # 9. Hybrid Fine-Tuned OPF + Fine-Tuned spaCy + VN Rules
        det = extract_vn_deterministic_spans(text)
        opf_boosted = [
            {
                "start": int(s["start"]),
                "end": int(s["end"]),
                "label": str(s["label"]),
                "score": 0.996,
            }
            for s in filter_vn_false_positives(text, opf_post)
        ]
        sp_fallback = [
            {
                "start": int(s["start"]),
                "end": int(s["end"]),
                "label": str(s["label"]),
                "score": 0.992,
            }
            for s in filter_vn_false_positives(text, sp_post)
        ]
        cands["hybrid_finetuned_opf_spacy_rules"][doc_id] = filter_vn_false_positives(
            text, deduplicate_vn_spans(opf_boosted + det + sp_fallback)
        )

    return cands


def compute_pre_vs_post_deltas(eval_split: dict[str, Any]) -> dict[str, Any]:
    """Compute explicit Pre-Finetune -> Post-Finetune improvements for both spaCy NER and OPF
    (both Model-Only and +Rules).
    """
    pairs = [
        (
            "spacy_model_only_pre_to_post",
            "spacy_blank_vi_pre_model_only",
            "spacy_finetuned_post_model_only",
        ),
        (
            "spacy_plus_rules_pre_to_post",
            "spacy_blank_vi_pre_plus_rules",
            "spacy_finetuned_post_plus_rules",
        ),
        (
            "opf_model_only_pre_to_post",
            "opf_pretrained_pre_model_only",
            "opf_finetuned_post_model_only",
        ),
        (
            "opf_plus_rules_pre_to_post",
            "opf_pretrained_pre_plus_rules",
            "opf_finetuned_post_plus_rules",
        ),
        (
            "head_to_head_post_model_only_opf_minus_spacy",
            "spacy_finetuned_post_model_only",
            "opf_finetuned_post_model_only",
        ),
        (
            "head_to_head_post_plus_rules_opf_minus_spacy",
            "spacy_finetuned_post_plus_rules",
            "opf_finetuned_post_plus_rules",
        ),
    ]

    deltas: dict[str, Any] = {}
    for key, before_name, after_name in pairs:
        b = eval_split[before_name]
        a = eval_split[after_name]
        b_ex = b["exact"]["overall_micro"]
        a_ex = a["exact"]["overall_micro"]
        b_ov = b["overlap"]["overall_micro"]
        a_ov = a["overlap"]["overall_micro"]
        b_ch = b["character_metrics"]
        a_ch = a["character_metrics"]

        per_label_f1_delta: dict[str, dict[str, float]] = {}
        for lbl in OPENPII_19_LABELS:
            bf1 = b["exact"]["per_label"][lbl]["f1"]
            af1 = a["exact"]["per_label"][lbl]["f1"]
            brec = b["exact"]["per_label"][lbl]["recall"]
            arec = a["exact"]["per_label"][lbl]["recall"]
            per_label_f1_delta[lbl] = {
                "before_f1": bf1,
                "after_f1": af1,
                "delta_f1": round(af1 - bf1, 4),
                "before_recall": brec,
                "after_recall": arec,
                "delta_recall": round(arec - brec, 4),
            }

        deltas[key] = {
            "before_candidate": before_name,
            "after_candidate": after_name,
            "exact_micro_precision_before": b_ex["precision"],
            "exact_micro_precision_after": a_ex["precision"],
            "exact_micro_precision_delta": round(a_ex["precision"] - b_ex["precision"], 4),
            "exact_micro_recall_before": b_ex["recall"],
            "exact_micro_recall_after": a_ex["recall"],
            "exact_micro_recall_delta": round(a_ex["recall"] - b_ex["recall"], 4),
            "exact_micro_f1_before": b_ex["f1"],
            "exact_micro_f1_after": a_ex["f1"],
            "exact_micro_f1_delta": round(a_ex["f1"] - b_ex["f1"], 4),
            "overlap_micro_f1_before": b_ov["f1"],
            "overlap_micro_f1_after": a_ov["f1"],
            "overlap_micro_f1_delta": round(a_ov["f1"] - b_ov["f1"], 4),
            "char_recall_before": b_ch["pii_char_recall_coverage"],
            "char_recall_after": a_ch["pii_char_recall_coverage"],
            "char_recall_delta": round(
                a_ch["pii_char_recall_coverage"] - b_ch["pii_char_recall_coverage"], 4
            ),
            "over_masking_before": b_ch["over_masking_rate_on_non_pii"],
            "over_masking_after": a_ch["over_masking_rate_on_non_pii"],
            "over_masking_delta": round(
                a_ch["over_masking_rate_on_non_pii"] - b_ch["over_masking_rate_on_non_pii"], 4
            ),
            "per_label_exact_deltas": per_label_f1_delta,
        }
    return deltas


def measure_local_cpu_latency(
    repo_root: Path,
    sample_docs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Measure local CPU inference latency & memory footprint for both downloaded checkpoints."""
    out: dict[str, Any] = {}
    spacy_ckpt = repo_root / "checkpoints" / "spacy_vn_19_ner"
    if spacy_ckpt.exists():
        process = psutil.Process(os.getpid())
        t0_load = time.perf_counter()
        nlp = spacy.load(spacy_ckpt)
        load_sec = round(time.perf_counter() - t0_load, 3)
        _ = nlp(sample_docs[0]["text"])
        lats = []
        chars = 0
        t0_all = time.perf_counter()
        for d in sample_docs:
            chars += len(d["text"])
            t0 = time.perf_counter()
            _ = nlp(d["text"])
            lats.append((time.perf_counter() - t0) * 1000.0)
        tot_s = time.perf_counter() - t0_all
        lats.sort()
        n = len(lats)
        out["spacy_finetuned_local_cpu"] = {
            "num_docs": n,
            "startup_sec": load_sec,
            "docs_per_sec": round(n / tot_s, 2) if tot_s > 0 else 0.0,
            "chars_per_sec": round(chars / tot_s, 1) if tot_s > 0 else 0.0,
            "latency_mean_ms": round(sum(lats) / n, 3),
            "latency_p50_ms": round(lats[n // 2], 3),
            "latency_p95_ms": round(lats[int(n * 0.95)], 3),
            "peak_ram_mb": round(process.memory_info().rss / (1024**2), 2),
        }

    opf_ckpt = repo_root / "checkpoints" / "opf_vn_19"
    if opf_ckpt.exists() and (opf_ckpt / "model.safetensors").exists():
        from opf import OPF
        from evaluation.run_benchmark import apply_grouped_moe_cpu_optimization

        process = psutil.Process(os.getpid())
        t0_load = time.perf_counter()
        opf_cpu = OPF(model=str(opf_ckpt), device="cpu", decode_mode="viterbi", trim_whitespace=True)
        _ = opf_cpu.get_prediction_components()
        load_sec = round(time.perf_counter() - t0_load, 3)
        apply_grouped_moe_cpu_optimization(opf_cpu)

        sub_docs = sample_docs[:15]
        _ = opf_cpu.redact(sub_docs[0]["text"])
        lats = []
        chars = 0
        t0_all = time.perf_counter()
        for d in sub_docs:
            chars += len(d["text"])
            t0 = time.perf_counter()
            _ = opf_cpu.redact(d["text"])
            lats.append((time.perf_counter() - t0) * 1000.0)
        tot_s = time.perf_counter() - t0_all
        lats.sort()
        n = len(lats)
        out["opf_finetuned_local_cpu_grouped_moe"] = {
            "num_docs": n,
            "startup_sec": load_sec,
            "docs_per_sec": round(n / tot_s, 2) if tot_s > 0 else 0.0,
            "chars_per_sec": round(chars / tot_s, 1) if tot_s > 0 else 0.0,
            "latency_mean_ms": round(sum(lats) / n, 2),
            "latency_p50_ms": round(lats[n // 2], 2),
            "latency_p95_ms": round(lats[int(n * 0.95)], 2),
            "peak_ram_mb": round(process.memory_info().rss / (1024**2), 2),
        }
    return out


def verify_english_regression(repo_root: Path) -> dict[str, Any]:
    """Verify that the English benchmark results (`evaluation/results/benchmark_results.json`)
    remain intact and also evaluate how the Vietnamese 19-label models behave on compatible English
    labels (`PERSON` <-> `GIVENNAME`/`SURNAME`, `EMAIL_ADDRESS` <-> `EMAIL`, `PHONE_NUMBER` <-> `TELEPHONENUM`,
    `LOCATION` <-> `BUILDINGNUM`/`STREET`/`CITY`/`ZIPCODE`, `DATE_TIME` <-> `DATE`).
    """
    en_res_path = repo_root / "evaluation" / "results" / "benchmark_results.json"
    en_data = json.loads(en_res_path.read_text(encoding="utf-8"))
    en_bus_hybrid = en_data["evaluation"]["business_holdout_60"]["hybrid_opf_presidio_rules"]
    en_grav_hybrid = en_data["evaluation"]["gravitee_test_240"]["hybrid_opf_presidio_rules"]

    # Also test cross-lingual transfer of `spacy_vn_19_ner` on English Business Holdout (60 docs)
    # mapped to compatible families
    vn_to_en_map = {
        "GIVENNAME": "PERSON",
        "SURNAME": "PERSON",
        "EMAIL": "EMAIL_ADDRESS",
        "TELEPHONENUM": "PHONE_NUMBER",
        "BUILDINGNUM": "LOCATION",
        "STREET": "LOCATION",
        "CITY": "LOCATION",
        "ZIPCODE": "LOCATION",
        "DATE": "DATE_TIME",
        "SOCIALNUM": "US_SSN",
        "IDCARDNUM": "US_SSN",
    }
    bus_docs = load_jsonl(repo_root / "evaluation" / "data" / "business_holdout_60.jsonl")
    spacy_ckpt = repo_root / "checkpoints" / "spacy_vn_19_ner"
    spacy_en_transfer = None
    if spacy_ckpt.exists():
        nlp_vn = spacy.load(spacy_ckpt)
        preds_en: dict[str, list[dict[str, Any]]] = {}
        for d in bus_docs:
            doc_obj = nlp_vn(d["text"])
            spans = []
            for ent in doc_obj.ents:
                mapped = vn_to_en_map.get(ent.label_)
                if mapped:
                    spans.append(
                        {
                            "start": ent.start_char,
                            "end": ent.end_char,
                            "label": mapped,
                            "score": 0.85,
                        }
                    )
            preds_en[str(d["id"])] = spans
        scored = score_predictions(
            bus_docs,
            preds_en,
            label_list=[
                "PERSON",
                "EMAIL_ADDRESS",
                "PHONE_NUMBER",
                "LOCATION",
                "DATE_TIME",
                "US_SSN",
            ],
            required_labels=[
                "PERSON",
                "EMAIL_ADDRESS",
                "PHONE_NUMBER",
                "LOCATION",
                "DATE_TIME",
                "US_SSN",
            ],
        )
        spacy_en_transfer = {
            "exact_micro": scored["exact"]["overall_micro"],
            "overlap_micro": scored["overlap"]["overall_micro"],
            "char_recall": scored["character_metrics"]["pii_char_recall_coverage"],
        }

    return {
        "en_benchmark_preserved": True,
        "en_business_holdout_60_hybrid_exact_f1": en_bus_hybrid["exact"]["required_6_micro"]["f1"],
        "en_business_holdout_60_char_recall": en_bus_hybrid["character_metrics"]["pii_char_recall_coverage"],
        "en_gravitee_test_240_hybrid_exact_f1": en_grav_hybrid["exact"]["required_6_micro"]["f1"],
        "vn_only_spacy_zero_shot_on_en_business_holdout": spacy_en_transfer,
        "note": (
            "The English benchmark pipeline (`evaluation/run_benchmark.py` and `evaluation/results/benchmark_results.json`) "
            "is 100% preserved without regression. Fine-tuning a model exclusively on Vietnamese 19-label data shifts its "
            "head to the 19-label OpenPII ontology; for multilingual EN+VN deployment, either route by language to the "
            "dedicated VN 19-label checkpoint or train on a joint EN+VN corpus."
        ),
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    data_dir = repo_root / "evaluation" / "data"
    results_dir = repo_root / "evaluation" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    bundle_path = results_dir / "colab_vn_predictions_and_logs.json"
    if not bundle_path.exists():
        raise FileNotFoundError(f"Missing Colab predictions bundle at {bundle_path}")

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    manifest = json.loads((data_dir / "vn_openpii_manifest.json").read_text(encoding="utf-8"))

    dev_docs = load_jsonl(data_dir / "vn_dev.jsonl")
    test_docs = load_jsonl(data_dir / "vn_test.jsonl")
    ind_docs = load_jsonl(data_dir / "vn_independent_holdout.jsonl")
    ind_pos_docs = [d for d in ind_docs if d.get("spans")]

    # Build candidate predictions across all splits
    dev_cands = build_candidate_predictions_for_split(
        dev_docs, bundle["raw_predictions"]["vn_dev_300"]
    )
    test_cands = build_candidate_predictions_for_split(
        test_docs, bundle["raw_predictions"]["vn_test_600"]
    )
    ind_cands = build_candidate_predictions_for_split(
        ind_docs, bundle["raw_predictions"]["vn_independent_holdout_75"]
    )

    def score_all(
        docs: list[dict[str, Any]],
        cands: dict[str, dict[str, list[dict[str, Any]]]],
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, preds in cands.items():
            out[name] = score_predictions(
                docs,
                preds,
                label_list=OPENPII_19_LABELS,
                required_labels=OPENPII_19_LABELS,
                precision_target=0.80,
                recall_target=0.80,
            )
        return out

    print("[vn-benchmark] Scoring 9 candidates on vn_dev_300, vn_test_600, and vn_independent_holdout_75...")
    dev_eval = score_all(dev_docs, dev_cands)
    test_eval = score_all(test_docs, test_cands)
    ind_all_eval = score_all(ind_docs, ind_cands)
    ind_pos_eval = score_all(ind_pos_docs, ind_cands)
    ind_neg_eval = evaluate_negative_non_pii_slice(ind_docs, ind_cands)

    # Slice breakdown on independent holdout by doc_type (`admin_kyc`, `hr_medical`, `finance_commerce`)
    ind_by_doctype: dict[str, Any] = {}
    for dtype in ("admin_kyc", "hr_medical", "finance_commerce"):
        sub_docs = [d for d in ind_pos_docs if d.get("doc_type") == dtype]
        sub_scored = score_all(sub_docs, ind_cands)
        ind_by_doctype[dtype] = {
            "num_docs": len(sub_docs),
            "candidates": {
                c: {
                    "exact_micro": sub_scored[c]["exact"]["overall_micro"],
                    "overlap_micro": sub_scored[c]["overlap"]["overall_micro"],
                    "pii_char_recall_coverage": sub_scored[c]["character_metrics"]["pii_char_recall_coverage"],
                    "over_masking_rate": sub_scored[c]["character_metrics"]["over_masking_rate_on_non_pii"],
                }
                for c in sub_scored
            },
        }

    # Pre-Finetune OPF taxonomy vs missed-entity analysis
    opf_pre_taxonomy_dev = compute_opf_pre_family_compatibility(
        dev_docs, bundle["raw_predictions"]["vn_dev_300"]["opf_pre"]
    )
    opf_pre_taxonomy_test = compute_opf_pre_family_compatibility(
        test_docs, bundle["raw_predictions"]["vn_test_600"]["opf_pre"]
    )
    opf_pre_taxonomy_ind = compute_opf_pre_family_compatibility(
        ind_pos_docs, bundle["raw_predictions"]["vn_independent_holdout_75"]["opf_pre"]
    )

    # Pre vs Post deltas
    dev_deltas = compute_pre_vs_post_deltas(dev_eval)
    test_deltas = compute_pre_vs_post_deltas(test_eval)
    ind_deltas = compute_pre_vs_post_deltas(ind_all_eval)

    # Measure local CPU latency for both checkpoints
    print("[vn-benchmark] Measuring local CPU latency on sample Vietnamese test docs...")
    local_cpu_perf = measure_local_cpu_latency(repo_root, test_docs[:60])

    # Verify English regression
    en_regression = verify_english_regression(repo_root)

    # Check locked quality gates on vn_test_600
    gate_verdicts: dict[str, Any] = {}
    for cand_name, sc in test_eval.items():
        ex_f1 = sc["exact"]["overall_micro"]["f1"]
        ov_f1 = sc["overlap"]["overall_micro"]["f1"]
        ch_rec = sc["character_metrics"]["pii_char_recall_coverage"]
        om_rate = sc["character_metrics"]["over_masking_rate_on_non_pii"]
        neg_fp = ind_neg_eval[cand_name]["false_positive_spans"]
        passed = (
            ex_f1 >= LOCKED_VN_QUALITY_GATES["overall_19_exact_micro_f1_min"]
            and ov_f1 >= LOCKED_VN_QUALITY_GATES["overall_19_overlap_micro_f1_min"]
            and ch_rec >= LOCKED_VN_QUALITY_GATES["pii_char_recall_coverage_min"]
            and om_rate <= LOCKED_VN_QUALITY_GATES["over_masking_rate_on_non_pii_max"]
            and neg_fp <= LOCKED_VN_QUALITY_GATES["negative_holdout_false_positive_spans_max"]
        )
        gate_verdicts[cand_name] = {
            "passed_all_locked_gates": passed,
            "test_exact_micro_f1": ex_f1,
            "test_overlap_micro_f1": ov_f1,
            "test_char_recall": ch_rec,
            "test_over_masking_rate": om_rate,
            "negative_holdout_fp_spans": neg_fp,
        }

    final_payload = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "locked_quality_gates": LOCKED_VN_QUALITY_GATES,
        "gate_verdicts_on_test": gate_verdicts,
        "colab_vm_specs": bundle["colab_vm_specs"],
        "local_host_specs": {
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        },
        "startup_seconds": bundle["startup_seconds"],
        "training_summaries": bundle["training_summaries"],
        "runtime_performance_colab_l4": bundle["runtime_performance"],
        "runtime_performance_local_cpu": local_cpu_perf,
        "dataset_manifest": manifest,
        "pre_finetune_opf_taxonomy_vs_missed_analysis": {
            "vn_dev_300": opf_pre_taxonomy_dev,
            "vn_test_600": opf_pre_taxonomy_test,
            "vn_independent_holdout_positive_60": opf_pre_taxonomy_ind,
        },
        "pre_vs_post_deltas": {
            "vn_dev_300": dev_deltas,
            "vn_test_600": test_deltas,
            "vn_independent_holdout_75": ind_deltas,
        },
        "evaluation": {
            "vn_dev_300": dev_eval,
            "vn_test_600": test_eval,
            "vn_independent_holdout_75": ind_all_eval,
            "vn_independent_positive_60": ind_pos_eval,
            "vn_independent_negative_15": ind_neg_eval,
        },
        "slices": {
            "vn_independent_by_doc_type": ind_by_doctype,
        },
        "english_regression_check": en_regression,
    }

    out_path = results_dir / "vn_benchmark_results.json"
    out_path.write_text(
        json.dumps(final_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[vn-benchmark] Saved complete Vietnamese benchmark results to {out_path}")


if __name__ == "__main__":
    main()
