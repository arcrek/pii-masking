"""Span, overlap, and character-level PII evaluation metrics and error taxonomy."""

from __future__ import annotations

import math
import string
from dataclasses import dataclass
from typing import Any


GRAVITEE_25_LABELS = [
    "AGE",
    "COORDINATE",
    "CREDIT_CARD",
    "DATE_TIME",
    "EMAIL_ADDRESS",
    "FINANCIAL",
    "HONORIFIC",
    "IBAN_CODE",
    "IMEI",
    "IP_ADDRESS",
    "LOCATION",
    "MAC_ADDRESS",
    "NRP",
    "ORGANIZATION",
    "PASSWORD",
    "PERSON",
    "PHONE_NUMBER",
    "TITLE",
    "URL",
    "US_BANK_NUMBER",
    "US_DRIVER_LICENSE",
    "US_ITIN",
    "US_LICENSE_PLATE",
    "US_PASSPORT",
    "US_SSN",
]

MVP_REQUIRED_6_LABELS = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "LOCATION",
    "DATE_TIME",
    "US_SSN",
]

# Explicit mapping from OpenAI Privacy Filter (8 native labels) to Gravitee 25 labels
OPF_TO_GRAVITEE_PRIMARY_MAP = {
    "private_person": "PERSON",
    "private_email": "EMAIL_ADDRESS",
    "private_phone": "PHONE_NUMBER",
    "private_address": "LOCATION",
    "private_date": "DATE_TIME",
    "private_url": "URL",
    "account_number": "US_BANK_NUMBER",  # Note: OPF collapses SSN, CC, IBAN, Bank into account_number
    "secret": "PASSWORD",
}

# Family equivalence sets for relaxed / policy-aware analysis of OPF's coarse labels
OPF_ACCOUNT_FAMILY = {
    "US_SSN",
    "US_ITIN",
    "US_BANK_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "US_PASSPORT",
    "US_DRIVER_LICENSE",
    "FINANCIAL",
}


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    label: str
    text: str = ""
    score: float = 1.0


def normalize_span_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """Trim leading/trailing whitespace and outer punctuation for normalized boundary comparison."""
    s = max(0, min(len(text), start))
    e = max(s, min(len(text), end))
    strip_chars = string.whitespace + ",.;:!?\"'()[]{}"
    while s < e and text[s] in strip_chars:
        s += 1
    while e > s and text[e - 1] in strip_chars:
        e -= 1
    return s, e


def span_iou(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    inter = max(0, min(a_end, b_end) - max(a_start, b_start))
    if inter == 0:
        return 0.0
    union = (a_end - a_start) + (b_end - b_start) - inter
    return inter / union if union > 0 else 0.0


def safe_div(num: float, den: float) -> float:
    return num / den if den > 0 else 0.0


def f1_score(precision: float, recall: float) -> float:
    return (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Compute 95% Wilson score confidence interval for a binomial proportion."""
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1.0 + (z * z) / total
    center = (p + (z * z) / (2.0 * total)) / denom
    half = (z * math.sqrt((p * (1.0 - p) + (z * z) / (4.0 * total)) / total)) / denom
    return (max(0.0, round(center - half, 4)), min(1.0, round(center + half, 4)))


def score_predictions(
    documents: list[dict[str, Any]],
    predictions_by_doc: dict[str, list[dict[str, Any]]],
    label_list: list[str],
    required_labels: list[str] | None = None,
    precision_target: float = 0.90,
    recall_target: float = 0.95,
) -> dict[str, Any]:
    """Compute exact span, normalized span, partial overlap, character-level coverage,
    over-masking rate, and error taxonomy across documents.
    """
    if required_labels is None:
        required_labels = MVP_REQUIRED_6_LABELS

    exact_stats = {lbl: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for lbl in label_list}
    norm_stats = {lbl: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for lbl in label_list}
    overlap_stats = {lbl: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for lbl in label_list}
    harmonized_stats = {lbl: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for lbl in label_list}

    total_chars = 0
    gold_pii_chars = 0
    pred_masked_chars = 0
    covered_gold_pii_chars = 0
    unnecessary_masked_chars = 0

    # Per-required-label character recall
    char_stats_by_label = {
        lbl: {"gold_chars": 0, "covered_any_label": 0, "covered_same_label": 0}
        for lbl in required_labels
    }

    # Error taxonomy counters and sample errors
    error_counts = {
        "exact_match": 0,
        "boundary_shift": 0,
        "label_confusion_or_policy": 0,
        "missed_entity_fn": 0,
        "false_alarm_fp": 0,
    }
    error_samples: dict[str, list[dict[str, Any]]] = {
        "boundary_shift": [],
        "label_confusion_or_policy": [],
        "missed_entity_fn": [],
        "false_alarm_fp": [],
    }

    for doc in documents:
        doc_id = str(doc.get("id", ""))
        text = doc["text"]
        n_chars = len(text)
        total_chars += n_chars

        gold_spans = [
            Span(
                start=int(s["start"]),
                end=int(s["end"]),
                label=str(s["label"]),
                text=text[int(s["start"]) : int(s["end"])],
            )
            for s in doc.get("spans", [])
            if str(s["label"]) in exact_stats
        ]
        pred_raw = predictions_by_doc.get(doc_id, [])
        pred_spans = [
            Span(
                start=int(s["start"]),
                end=int(s["end"]),
                label=str(s["label"]),
                text=text[int(s["start"]) : int(s["end"])],
                score=float(s.get("score", 1.0)),
            )
            for s in pred_raw
            if str(s["label"]) in exact_stats and int(s["end"]) > int(s["start"])
        ]

        # Character-level masks
        gold_mask = [False] * n_chars
        pred_mask = [False] * n_chars
        for gs in gold_spans:
            for idx in range(max(0, gs.start), min(n_chars, gs.end)):
                gold_mask[idx] = True
        for ps in pred_spans:
            for idx in range(max(0, ps.start), min(n_chars, ps.end)):
                pred_mask[idx] = True

        for idx in range(n_chars):
            g = gold_mask[idx]
            p = pred_mask[idx]
            if g:
                gold_pii_chars += 1
                if p:
                    covered_gold_pii_chars += 1
            if p:
                pred_masked_chars += 1
                if not g:
                    unnecessary_masked_chars += 1

        # Per-required-label character coverage
        for gs in gold_spans:
            if gs.label in char_stats_by_label:
                s_idx = max(0, gs.start)
                e_idx = min(n_chars, gs.end)
                span_len = max(0, e_idx - s_idx)
                char_stats_by_label[gs.label]["gold_chars"] += span_len
                any_cov = sum(1 for k in range(s_idx, e_idx) if pred_mask[k])
                char_stats_by_label[gs.label]["covered_any_label"] += any_cov
                same_cov = 0
                for k in range(s_idx, e_idx):
                    if any(ps.label == gs.label and ps.start <= k < ps.end for ps in pred_spans):
                        same_cov += 1
                char_stats_by_label[gs.label]["covered_same_label"] += same_cov

        # 1. Exact span evaluation per label
        for lbl in label_list:
            g_lbl = {(g.start, g.end) for g in gold_spans if g.label == lbl}
            p_lbl = {(p.start, p.end) for p in pred_spans if p.label == lbl}
            tp = len(g_lbl & p_lbl)
            fp = len(p_lbl - g_lbl)
            fn = len(g_lbl - p_lbl)
            exact_stats[lbl]["tp"] += tp
            exact_stats[lbl]["fp"] += fp
            exact_stats[lbl]["fn"] += fn
            exact_stats[lbl]["support"] += len(g_lbl)

            # 2. Normalized boundary span evaluation per label
            g_norm = {normalize_span_bounds(text, g.start, g.end) for g in gold_spans if g.label == lbl}
            p_norm = {normalize_span_bounds(text, p.start, p.end) for p in pred_spans if p.label == lbl}
            tp_n = len(g_norm & p_norm)
            fp_n = len(p_norm - g_norm)
            fn_n = len(g_norm - p_norm)
            norm_stats[lbl]["tp"] += tp_n
            norm_stats[lbl]["fp"] += fp_n
            norm_stats[lbl]["fn"] += fn_n
            norm_stats[lbl]["support"] += len(g_lbl)

            # 3. Partial overlap (IoU > 0, greedy 1-to-1 matching) per label
            g_list = [g for g in gold_spans if g.label == lbl]
            p_list = [p for p in pred_spans if p.label == lbl]
            matched_p: set[int] = set()
            tp_o = 0
            for g in g_list:
                best_j = -1
                best_iou = 0.0
                for j, p in enumerate(p_list):
                    if j in matched_p:
                        continue
                    iou = span_iou(g.start, g.end, p.start, p.end)
                    if iou > best_iou:
                        best_iou = iou
                        best_j = j
                if best_j != -1 and best_iou > 0.0:
                    matched_p.add(best_j)
                    tp_o += 1
            overlap_stats[lbl]["tp"] += tp_o
            overlap_stats[lbl]["fp"] += len(p_list) - tp_o
            overlap_stats[lbl]["fn"] += len(g_list) - tp_o
            overlap_stats[lbl]["support"] += len(g_list)

        # 4. Harmonized multi-source evaluation (handles split/merged multi-token entities
        # such as Kiji/Gretel split First+Last PERSON or Street+City+State+Zip LOCATION,
        # and OPF account_number / PERSON+HONORIFIC family equivalence)
        def labels_harmonized_compatible(g_lbl_name: str, p_lbl_name: str) -> bool:
            if g_lbl_name == p_lbl_name:
                return True
            if g_lbl_name in OPF_ACCOUNT_FAMILY and p_lbl_name in OPF_ACCOUNT_FAMILY:
                return True
            if {g_lbl_name, p_lbl_name} <= {"PERSON", "HONORIFIC"}:
                return True
            if {g_lbl_name, p_lbl_name} <= {"LOCATION", "COORDINATE"}:
                return True
            return False

        matched_pred_indices: set[int] = set()
        for g in gold_spans:
            harmonized_stats[g.label]["support"] += 1
            overlapping_preds = [
                j
                for j, p in enumerate(pred_spans)
                if labels_harmonized_compatible(g.label, p.label)
                and span_iou(g.start, g.end, p.start, p.end) > 0.0
            ]
            if overlapping_preds:
                harmonized_stats[g.label]["tp"] += 1
                matched_pred_indices.update(overlapping_preds)
            else:
                harmonized_stats[g.label]["fn"] += 1

        for j, p in enumerate(pred_spans):
            if j not in matched_pred_indices:
                harmonized_stats[p.label]["fp"] += 1

        # Error taxonomy classification on gold vs pred spans
        used_preds: set[int] = set()
        for g in gold_spans:
            # Check exact match first
            exact_j = -1
            for j, p in enumerate(pred_spans):
                if j not in used_preds and p.start == g.start and p.end == g.end and p.label == g.label:
                    exact_j = j
                    break
            if exact_j != -1:
                used_preds.add(exact_j)
                error_counts["exact_match"] += 1
                continue

            # Check overlapping same-label (boundary shift)
            bound_j = -1
            for j, p in enumerate(pred_spans):
                if j not in used_preds and p.label == g.label and span_iou(g.start, g.end, p.start, p.end) > 0:
                    bound_j = j
                    break
            if bound_j != -1:
                used_preds.add(bound_j)
                error_counts["boundary_shift"] += 1
                if len(error_samples["boundary_shift"]) < 15:
                    p = pred_spans[bound_j]
                    error_samples["boundary_shift"].append(
                        {
                            "doc_id": doc_id,
                            "gold_label": g.label,
                            "gold_text": g.text,
                            "pred_label": p.label,
                            "pred_text": p.text,
                        }
                    )
                continue

            # Check overlapping different-label (label confusion / policy mismatch)
            conf_j = -1
            for j, p in enumerate(pred_spans):
                if j not in used_preds and span_iou(g.start, g.end, p.start, p.end) > 0:
                    conf_j = j
                    break
            if conf_j != -1:
                used_preds.add(conf_j)
                error_counts["label_confusion_or_policy"] += 1
                if len(error_samples["label_confusion_or_policy"]) < 15:
                    p = pred_spans[conf_j]
                    error_samples["label_confusion_or_policy"].append(
                        {
                            "doc_id": doc_id,
                            "gold_label": g.label,
                            "gold_text": g.text,
                            "pred_label": p.label,
                            "pred_text": p.text,
                        }
                    )
                continue

            # Otherwise missed entity (FN)
            error_counts["missed_entity_fn"] += 1
            if len(error_samples["missed_entity_fn"]) < 15:
                ctx_s = max(0, g.start - 25)
                ctx_e = min(n_chars, g.end + 25)
                error_samples["missed_entity_fn"].append(
                    {
                        "doc_id": doc_id,
                        "gold_label": g.label,
                        "gold_text": g.text,
                        "context": text[ctx_s:ctx_e],
                    }
                )

        # Remaining unmatched predictions are false alarms (FP)
        for j, p in enumerate(pred_spans):
            if j not in used_preds:
                # Check if it overlaps any already-matched gold span (split span)
                if any(span_iou(g.start, g.end, p.start, p.end) > 0 for g in gold_spans):
                    error_counts["boundary_shift"] += 1
                else:
                    error_counts["false_alarm_fp"] += 1
                    if len(error_samples["false_alarm_fp"]) < 15:
                        ctx_s = max(0, p.start - 25)
                        ctx_e = min(n_chars, p.end + 25)
                        error_samples["false_alarm_fp"].append(
                            {
                                "doc_id": doc_id,
                                "pred_label": p.label,
                                "pred_text": p.text,
                                "context": text[ctx_s:ctx_e],
                            }
                        )

    def summarize_table(raw_table: dict[str, dict[str, int]]) -> dict[str, Any]:
        per_label: dict[str, Any] = {}
        total_tp = total_fp = total_fn = total_sup = 0
        req_tp = req_fp = req_fn = req_sup = 0

        for lbl, st in raw_table.items():
            tp, fp, fn, sup = st["tp"], st["fp"], st["fn"], st["support"]
            prec = safe_div(tp, tp + fp)
            rec = safe_div(tp, tp + fn)
            f1 = f1_score(prec, rec)
            per_label[lbl] = {
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "support": sup,
                "precision_ci95": wilson_ci(tp, tp + fp),
                "recall_ci95": wilson_ci(tp, tp + fn),
                "meets_target": bool(
                    sup > 0 and prec >= precision_target and rec >= recall_target
                ),
            }
            total_tp += tp
            total_fp += fp
            total_fn += fn
            total_sup += sup
            if lbl in required_labels:
                req_tp += tp
                req_fp += fp
                req_fn += fn
                req_sup += sup

        micro_p = safe_div(total_tp, total_tp + total_fp)
        micro_r = safe_div(total_tp, total_tp + total_fn)
        micro_f1 = f1_score(micro_p, micro_r)

        active_labels = [v for v in per_label.values() if v["support"] > 0]
        macro_p = safe_div(sum(v["precision"] for v in active_labels), len(active_labels))
        macro_r = safe_div(sum(v["recall"] for v in active_labels), len(active_labels))
        macro_f1 = safe_div(sum(v["f1"] for v in active_labels), len(active_labels))

        req_micro_p = safe_div(req_tp, req_tp + req_fp)
        req_micro_r = safe_div(req_tp, req_tp + req_fn)
        req_micro_f1 = f1_score(req_micro_p, req_micro_r)

        req_active = [per_label[lbl] for lbl in required_labels if per_label[lbl]["support"] > 0]
        req_macro_p = safe_div(sum(v["precision"] for v in req_active), len(req_active))
        req_macro_r = safe_div(sum(v["recall"] for v in req_active), len(req_active))
        req_macro_f1 = safe_div(sum(v["f1"] for v in req_active), len(req_active))

        passed_required = [
            lbl for lbl in required_labels if per_label[lbl]["meets_target"]
        ]

        return {
            "per_label": per_label,
            "overall_micro": {
                "precision": round(micro_p, 4),
                "recall": round(micro_r, 4),
                "f1": round(micro_f1, 4),
                "support": total_sup,
            },
            "overall_macro": {
                "precision": round(macro_p, 4),
                "recall": round(macro_r, 4),
                "f1": round(macro_f1, 4),
                "active_labels": len(active_labels),
            },
            "required_6_micro": {
                "precision": round(req_micro_p, 4),
                "recall": round(req_micro_r, 4),
                "f1": round(req_micro_f1, 4),
                "support": req_sup,
            },
            "required_6_macro": {
                "precision": round(req_macro_p, 4),
                "recall": round(req_macro_r, 4),
                "f1": round(req_macro_f1, 4),
            },
            "required_6_passed_count": len(passed_required),
            "required_6_passed_labels": passed_required,
        }

    non_pii_chars = max(0, total_chars - gold_pii_chars)
    char_summary = {
        "total_chars": total_chars,
        "gold_pii_chars": gold_pii_chars,
        "pred_masked_chars": pred_masked_chars,
        "covered_gold_pii_chars": covered_gold_pii_chars,
        "unnecessary_masked_chars": unnecessary_masked_chars,
        "pii_char_recall_coverage": round(safe_div(covered_gold_pii_chars, gold_pii_chars), 4),
        "pii_char_precision": round(safe_div(covered_gold_pii_chars, pred_masked_chars), 4),
        "over_masking_rate_on_non_pii": round(safe_div(unnecessary_masked_chars, non_pii_chars), 4),
        "per_required_label_char_coverage": {
            lbl: {
                "gold_chars": st["gold_chars"],
                "char_recall_any_mask": round(safe_div(st["covered_any_label"], st["gold_chars"]), 4),
                "char_recall_same_label": round(safe_div(st["covered_same_label"], st["gold_chars"]), 4),
            }
            for lbl, st in char_stats_by_label.items()
        },
    }

    return {
        "exact": summarize_table(exact_stats),
        "normalized": summarize_table(norm_stats),
        "overlap": summarize_table(overlap_stats),
        "harmonized": summarize_table(harmonized_stats),
        "character_metrics": char_summary,
        "error_taxonomy": {
            "counts": error_counts,
            "samples": error_samples,
        },
    }
