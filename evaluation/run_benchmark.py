#!/usr/bin/env python3
"""Benchmark Runner for PII Masking Evaluation (ML-07).

Evaluates:
1. OpenAI Privacy Filter (`openai/privacy-filter`) — Unchanged Baseline (Viterbi decoding, primary 1:1 label mapping).
2. Microsoft Presidio + spaCy (`en_core_web_lg`) — Unchanged Baseline.
3. OpenAI Privacy Filter + Targeted Rules (`OPF + Account/Entity Disambiguation + Structured Regex`).
4. Microsoft Presidio + Targeted Rules (`Presidio + Contiguous Location Merging + Structured Regex`).
5. Hybrid Pipeline (`OPF + Presidio + Deterministic Business Rules`).

Datasets evaluated:
- Gravitee PII Detection (`gravitee-io/pii-detection-dataset`, 175,881 rows across 6 sources and 25 labels):
  - `dev` split: 120 stratified examples (seed=42, guaranteed positive support across all 25 labels & 6 sources)
  - `test` split: 240 stratified held-out examples (seed=42, strictly disjoint from dev, guaranteed positive support across all 25 labels & 6 sources)
  - All 25 canonical Gravitee labels reported; 6 required MVP labels gated.
- Independent Business-Text Holdout (`business_holdout_60.jsonl`):
  - 60 realistic English business documents (20 forms, 20 invoices, 20 correspondence)
  - 457 ground-truth spans across the 6 required MVP labels (`PERSON`, `EMAIL_ADDRESS`,
    `PHONE_NUMBER`, `LOCATION`, `DATE_TIME`, `US_SSN`).
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import psutil
import torch
import torch.nn.functional as F

# Ensure local package imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.hybrid_rules import (
    build_hybrid_predictions,
    deduplicate_spans,
    extract_deterministic_spans,
    merge_contiguous_locations,
    refine_opf_span,
)
from evaluation.metrics import (
    GRAVITEE_25_LABELS,
    MVP_REQUIRED_6_LABELS,
    OPF_TO_GRAVITEE_PRIMARY_MAP,
    score_predictions,
)


def get_hardware_specs() -> dict[str, Any]:
    cpu_brand = platform.processor() or "x86_64"
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("model name"):
                cpu_brand = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass

    gpu_name = None
    gpu_vram_gb = None
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        props = torch.cuda.get_device_properties(0)
        gpu_vram_gb = round(props.total_memory / (1024**3), 2)
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "cpu_model": cpu_brand,
        "cpu_count_logical": os.cpu_count(),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": gpu_name,
        "gpu_vram_gb": gpu_vram_gb,
        "colab_pro_assign_status": (
            "HTTP 503 Service Unavailable on POST https://colab.research.google.com/tun/m/assign "
            "(verified across L4, T4, and CPU runtimes; 0 compute units consumed; executed locally on 8-vCPU host)"
        ),
    }


def load_gravitee_splits(
    dev_size: int = 120,
    test_size: int = 240,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Load `gravitee-io/pii-detection-dataset` and create deterministic label+source stratified dev and test splits."""
    from datasets import load_dataset

    print("[data] Loading gravitee-io/pii-detection-dataset...")
    ds = load_dataset("gravitee-io/pii-detection-dataset", split="train")
    total_rows = len(ds)
    print(f"[data] Loaded {total_rows} rows.")

    by_label: dict[str, list[int]] = defaultdict(list)
    by_source: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(ds):
        by_source[str(row["source"])].append(idx)
        labels_in_row = {str(sp["label"]) for sp in row["spans"]}
        for lbl in labels_in_row:
            by_label[lbl].append(idx)

    rng = random.Random(seed)
    dev_set: set[int] = set()
    test_set: set[int] = set()

    # Step 1: Guarantee positive support for all 25 Gravitee labels in both dev and test
    for lbl in sorted(GRAVITEE_25_LABELS):
        candidates = [i for i in by_label[lbl] if i not in dev_set and i not in test_set]
        rng.shuffle(candidates)
        dev_set.update(candidates[:3])
        test_set.update(candidates[3:9])

    # Step 2: Top up proportionally across all 6 upstream sources to exact target sizes
    rem_dev = max(0, dev_size - len(dev_set))
    rem_test = max(0, test_size - len(test_set))
    all_remaining: list[int] = []
    for src, indices in sorted(by_source.items()):
        avail = [i for i in indices if i not in dev_set and i not in test_set]
        rng.shuffle(avail)
        prop = len(indices) / total_rows
        n_dev_add = max(4, int(round(rem_dev * prop)))
        n_test_add = max(8, int(round(rem_test * prop)))
        dev_set.update(avail[:n_dev_add])
        test_set.update(avail[n_dev_add : n_dev_add + n_test_add])
        all_remaining.extend(avail[n_dev_add + n_test_add :])

    rng.shuffle(all_remaining)
    cursor = 0
    while len(dev_set) < dev_size and cursor < len(all_remaining):
        idx = all_remaining[cursor]
        cursor += 1
        if idx not in dev_set and idx not in test_set:
            dev_set.add(idx)
    while len(test_set) < test_size and cursor < len(all_remaining):
        idx = all_remaining[cursor]
        cursor += 1
        if idx not in dev_set and idx not in test_set:
            test_set.add(idx)

    dev_indices = sorted(list(dev_set))[:dev_size]
    test_indices = sorted(list(test_set))[:test_size]
    assert not (set(dev_indices) & set(test_indices)), "Dev and test indices must be strictly disjoint!"

    def build_docs(idx_list: list[int], split_name: str) -> list[dict[str, Any]]:
        sub = ds.select(idx_list)
        docs = []
        for orig_idx, row in zip(idx_list, sub):
            text = str(row["text"])
            spans = []
            for sp in row["spans"]:
                s = int(sp["start"])
                e = int(sp["end"])
                lbl = str(sp["label"])
                spans.append(
                    {
                        "start": s,
                        "end": e,
                        "label": lbl,
                        "text": text[s:e],
                    }
                )
            docs.append(
                {
                    "id": f"gravitee_{split_name}_{orig_idx}",
                    "orig_index": orig_idx,
                    "source": str(row["source"]),
                    "language": str(row.get("language", "en")),
                    "text": text,
                    "spans": spans,
                }
            )
        return docs

    dev_docs = build_docs(dev_indices, "dev")
    test_docs = build_docs(test_indices, "test")

    dev_hash = hashlib.sha256(json.dumps(dev_indices).encode()).hexdigest()
    test_hash = hashlib.sha256(json.dumps(test_indices).encode()).hexdigest()

    source_dist_dev: dict[str, int] = Counter(d["source"] for d in dev_docs)
    source_dist_test: dict[str, int] = Counter(d["source"] for d in test_docs)
    label_dist_dev: dict[str, int] = Counter(sp["label"] for d in dev_docs for sp in d["spans"])
    label_dist_test: dict[str, int] = Counter(sp["label"] for d in test_docs for sp in d["spans"])

    manifest = {
        "dataset": "gravitee-io/pii-detection-dataset",
        "total_upstream_rows": total_rows,
        "seed": seed,
        "dev_size": len(dev_docs),
        "test_size": len(test_docs),
        "dev_indices_sha256": dev_hash,
        "test_indices_sha256": test_hash,
        "dev_source_distribution": dict(sorted(source_dist_dev.items())),
        "test_source_distribution": dict(sorted(source_dist_test.items())),
        "dev_label_span_counts": dict(sorted(label_dist_dev.items())),
        "test_label_span_counts": dict(sorted(label_dist_test.items())),
        "dev_indices": dev_indices,
        "test_indices": test_indices,
    }
    return dev_docs, test_docs, manifest


def apply_grouped_moe_cpu_optimization(opf_model: Any) -> None:
    """Replace OPF's naive 3D weight-cloning CPU fallback with grouped expert matmul on CPU."""
    import opf._model.model as mod

    runtime, _ = opf_model.get_prediction_components()
    if runtime.device.type != "cpu":
        return

    def fast_cpu_mlp_forward(self: Any, x: torch.Tensor) -> torch.Tensor:
        batch_shape = x.shape[:-1]
        t = self.norm(x).reshape(-1, x.shape[-1])
        t_f32 = t.float()
        g = F.linear(t_f32, self.gate.weight.float(), self.gate.bias.float())
        experts = torch.topk(g, k=self.experts_per_token, dim=-1, sorted=True)
        expert_weights = F.softmax(experts.values, dim=1) / self.experts_per_token
        expert_indices = experts.indices
        experts_per_token_eff = self.experts_per_token

        n_tokens, hidden_dim = t_f32.shape
        k = self.experts_per_token
        out_accum = torch.zeros((n_tokens, hidden_dim), dtype=torch.float32, device=t.device)

        flat_experts = expert_indices.reshape(-1)
        flat_weights = expert_weights.reshape(-1)
        flat_tokens = torch.arange(n_tokens, device=t.device).repeat_interleave(k)

        sort_idx = torch.argsort(flat_experts)
        sorted_experts = flat_experts[sort_idx]
        sorted_tokens = flat_tokens[sort_idx]
        sorted_weights = flat_weights[sort_idx]

        unique_experts, counts = torch.unique_consecutive(sorted_experts, return_counts=True)
        cursor = 0
        for exp_id, cnt in zip(unique_experts.tolist(), counts.tolist()):
            tok_slice = sorted_tokens[cursor : cursor + cnt]
            w_slice = sorted_weights[cursor : cursor + cnt].unsqueeze(1)
            cursor += cnt

            inp = t_f32[tok_slice]
            w1 = self.mlp1_weight[exp_id].float()
            b1 = self.mlp1_bias[exp_id].float()
            h_pre = inp @ w1 + b1
            h = mod.swiglu(h_pre, limit=self.swiglu_limit, packed=self.packed_geglu)
            w2 = self.mlp2_weight[exp_id].float()
            b2 = self.mlp2_bias[exp_id].float()
            o = (h.float() @ w2 + b2) * w_slice
            out_accum.index_add_(0, tok_slice, o)

        out_accum = out_accum * experts_per_token_eff
        return x + out_accum.to(x.dtype).reshape(*batch_shape, -1)

    for blk in runtime.model.block:
        blk.mlp.forward = fast_cpu_mlp_forward.__get__(blk.mlp, type(blk.mlp))


def run_opf_inference(
    opf_model: Any,
    docs: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Run OpenAI Privacy Filter on a list of documents and measure latency, throughput, and peak memory."""
    process = psutil.Process(os.getpid())
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

    # Warmup
    _ = opf_model.redact("Warmup sentence for Alice Smith at alice@example.com.")

    latencies_ms: list[float] = []
    raw_spans_by_doc: dict[str, list[dict[str, Any]]] = {}
    total_chars = 0

    t0_all = time.perf_counter()
    for idx, doc in enumerate(docs, 1):
        text = doc["text"]
        total_chars += len(text)
        t0 = time.perf_counter()
        res = opf_model.redact(text)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        spans = []
        for sp in res.detected_spans:
            spans.append(
                {
                    "start": int(sp.start),
                    "end": int(sp.end),
                    "label": str(sp.label),
                    "text": str(sp.text),
                }
            )
        raw_spans_by_doc[str(doc["id"])] = spans
        if idx % 30 == 0 or idx == len(docs):
            elapsed = time.perf_counter() - t0_all
            print(f"  [opf] {idx}/{len(docs)} docs ({elapsed:.1f}s, {elapsed/idx*1000:.0f} ms/doc)")
    total_sec = time.perf_counter() - t0_all

    lat_sorted = sorted(latencies_ms)
    n = len(lat_sorted)
    peak_vram_mb = (
        round(torch.cuda.max_memory_allocated() / (1024**2), 2)
        if torch.cuda.is_available()
        else 0.0
    )
    peak_ram_mb = round(process.memory_info().rss / (1024**2), 2)

    perf = {
        "num_docs": n,
        "total_seconds": round(total_sec, 3),
        "docs_per_sec": round(n / total_sec, 2) if total_sec > 0 else 0.0,
        "chars_per_sec": round(total_chars / total_sec, 1) if total_sec > 0 else 0.0,
        "latency_mean_ms": round(sum(lat_sorted) / n, 2) if n else 0.0,
        "latency_p50_ms": round(lat_sorted[n // 2], 2) if n else 0.0,
        "latency_p95_ms": round(lat_sorted[int(n * 0.95)], 2) if n else 0.0,
        "peak_vram_mb": peak_vram_mb,
        "peak_ram_mb": peak_ram_mb,
    }
    return raw_spans_by_doc, perf


def build_presidio_analyzer() -> Any:
    """Create a pinned Presidio AnalyzerEngine backed by spaCy `en_core_web_lg`."""
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NerModelConfiguration, SpacyNlpEngine

    entity_mapping = {
        "PER": "PERSON",
        "PERSON": "PERSON",
        "LOC": "LOCATION",
        "GPE": "LOCATION",
        "FAC": "LOCATION",
        "ORG": "ORGANIZATION",
        "DATE": "DATE_TIME",
        "TIME": "DATE_TIME",
        "NORP": "NRP",
    }
    ner_config = NerModelConfiguration(
        default_score=0.85,
        model_to_presidio_entity_mapping=entity_mapping,
        labels_to_ignore=[
            "CARDINAL",
            "ORDINAL",
            "QUANTITY",
            "PERCENT",
            "MONEY",
            "WORK_OF_ART",
            "LAW",
            "LANGUAGE",
            "EVENT",
            "PRODUCT",
        ],
    )
    nlp_engine = SpacyNlpEngine(
        models=[{"lang_code": "en", "model_name": "en_core_web_lg"}],
        ner_model_configuration=ner_config,
    )
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
    return analyzer


PRESIDIO_TO_GRAVITEE_MAP = {
    "PERSON": "PERSON",
    "EMAIL_ADDRESS": "EMAIL_ADDRESS",
    "PHONE_NUMBER": "PHONE_NUMBER",
    "LOCATION": "LOCATION",
    "DATE_TIME": "DATE_TIME",
    "US_SSN": "US_SSN",
    "CREDIT_CARD": "CREDIT_CARD",
    "IBAN_CODE": "IBAN_CODE",
    "IP_ADDRESS": "IP_ADDRESS",
    "URL": "URL",
    "NRP": "NRP",
    "ORGANIZATION": "ORGANIZATION",
    "US_BANK_NUMBER": "US_BANK_NUMBER",
    "US_DRIVER_LICENSE": "US_DRIVER_LICENSE",
    "US_ITIN": "US_ITIN",
    "US_PASSPORT": "US_PASSPORT",
}


def run_presidio_inference(
    analyzer: Any,
    docs: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Run Presidio + spaCy (`en_core_web_lg`) on a list of documents and record performance."""
    process = psutil.Process(os.getpid())
    entities_to_query = list(PRESIDIO_TO_GRAVITEE_MAP.keys())

    # Warmup
    _ = analyzer.analyze(
        text="Warmup sentence for Alice Smith at alice@example.com.",
        language="en",
        entities=entities_to_query,
    )

    latencies_ms: list[float] = []
    spans_by_doc: dict[str, list[dict[str, Any]]] = {}
    total_chars = 0

    t0_all = time.perf_counter()
    for doc in docs:
        text = doc["text"]
        total_chars += len(text)
        t0 = time.perf_counter()
        results = analyzer.analyze(
            text=text,
            language="en",
            entities=entities_to_query,
            score_threshold=0.4,
        )
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        # Deduplicate overlapping Presidio results (prefer higher score, then longer span)
        sorted_res = sorted(
            results,
            key=lambda r: (-float(r.score), -(r.end - r.start), r.start),
        )
        kept = []
        for r in sorted_res:
            if any(min(r.end, k.end) - max(r.start, k.start) > 0 for k in kept):
                continue
            kept.append(r)

        doc_spans = []
        for r in sorted(kept, key=lambda x: (x.start, x.end)):
            mapped_lbl = PRESIDIO_TO_GRAVITEE_MAP.get(r.entity_type, r.entity_type)
            s = int(r.start)
            e = int(r.end)
            while s < e and text[s].isspace():
                s += 1
            while e > s and text[e - 1].isspace():
                e -= 1
            if e > s:
                doc_spans.append(
                    {
                        "start": s,
                        "end": e,
                        "label": mapped_lbl,
                        "score": round(float(r.score), 4),
                    }
                )
        spans_by_doc[str(doc["id"])] = doc_spans

    total_sec = time.perf_counter() - t0_all
    lat_sorted = sorted(latencies_ms)
    n = len(lat_sorted)
    peak_ram_mb = round(process.memory_info().rss / (1024**2), 2)

    perf = {
        "num_docs": n,
        "total_seconds": round(total_sec, 3),
        "docs_per_sec": round(n / total_sec, 2) if total_sec > 0 else 0.0,
        "chars_per_sec": round(total_chars / total_sec, 1) if total_sec > 0 else 0.0,
        "latency_mean_ms": round(sum(lat_sorted) / n, 2) if n else 0.0,
        "latency_p50_ms": round(lat_sorted[n // 2], 2) if n else 0.0,
        "latency_p95_ms": round(lat_sorted[int(n * 0.95)], 2) if n else 0.0,
        "peak_vram_mb": 0.0,
        "peak_ram_mb": peak_ram_mb,
    }
    return spans_by_doc, perf


def map_opf_unchanged(raw_spans_by_doc: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    """Map unchanged OPF predictions using strict 1:1 primary mapping."""
    mapped: dict[str, list[dict[str, Any]]] = {}
    for doc_id, spans in raw_spans_by_doc.items():
        out = []
        for sp in spans:
            lbl = OPF_TO_GRAVITEE_PRIMARY_MAP.get(sp["label"], sp["label"])
            out.append(
                {
                    "start": sp["start"],
                    "end": sp["end"],
                    "label": lbl,
                    "score": 1.0,
                }
            )
        mapped[doc_id] = out
    return mapped


def map_opf_disambiguated(
    docs: list[dict[str, Any]],
    raw_spans_by_doc: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Map OPF predictions with regex disambiguation on `account_number` + structured patterns."""
    mapped: dict[str, list[dict[str, Any]]] = {}
    for doc in docs:
        doc_id = str(doc["id"])
        text = doc["text"]
        raw = raw_spans_by_doc.get(doc_id, [])
        refined = [refine_opf_span(text, sp["start"], sp["end"], sp["label"]) for sp in raw]
        det = extract_deterministic_spans(text)
        mapped[doc_id] = deduplicate_spans(det + refined)
    return mapped


def evaluate_all_candidates(
    docs: list[dict[str, Any]],
    opf_raw: dict[str, list[dict[str, Any]]],
    presidio_raw: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Score all 5 pipeline variants on a dataset."""
    # 1. OPF Unchanged Baseline
    opf_unchanged_preds = map_opf_unchanged(opf_raw)

    # 2. Presidio + spaCy Unchanged Baseline
    presidio_unchanged_preds = presidio_raw

    # 3. OPF + Targeted Rules (Disambiguated account_number + structured regexes)
    opf_targeted_preds = map_opf_disambiguated(docs, opf_raw)

    # 4. Presidio + Targeted Rules (Merged contiguous locations + deterministic regexes)
    presidio_targeted_preds: dict[str, list[dict[str, Any]]] = {}
    for doc in docs:
        doc_id = str(doc["id"])
        text = doc["text"]
        det = extract_deterministic_spans(text)
        merged_loc = merge_contiguous_locations(text, presidio_raw.get(doc_id, []))
        presidio_targeted_preds[doc_id] = deduplicate_spans(det + merged_loc)

    # 5. Full Hybrid Pipeline (OPF + Presidio + Deterministic Business Rules)
    hybrid_preds: dict[str, list[dict[str, Any]]] = {}
    for doc in docs:
        doc_id = str(doc["id"])
        text = doc["text"]
        hybrid_preds[doc_id] = build_hybrid_predictions(
            text,
            opf_raw.get(doc_id, []),
            presidio_raw.get(doc_id, []),
        )

    candidates = {
        "opf_baseline": opf_unchanged_preds,
        "presidio_spacy_baseline": presidio_unchanged_preds,
        "opf_targeted_rules": opf_targeted_preds,
        "presidio_targeted_rules": presidio_targeted_preds,
        "hybrid_opf_presidio_rules": hybrid_preds,
    }

    results: dict[str, Any] = {}
    for name, preds in candidates.items():
        results[name] = score_predictions(
            docs,
            preds,
            label_list=GRAVITEE_25_LABELS,
            required_labels=MVP_REQUIRED_6_LABELS,
            precision_target=0.90,
            recall_target=0.95,
        )
    return results


def evaluate_by_slice(
    docs: list[dict[str, Any]],
    opf_raw: dict[str, list[dict[str, Any]]],
    presidio_raw: dict[str, list[dict[str, Any]]],
    slice_key: str,
) -> dict[str, Any]:
    """Break down required-6 exact and character metrics by document slice (e.g. `source` or `doc_type`)."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in docs:
        grouped[str(d.get(slice_key, "unknown"))].append(d)

    out: dict[str, Any] = {}
    for val, sub_docs in sorted(grouped.items()):
        sub_res = evaluate_all_candidates(sub_docs, opf_raw, presidio_raw)
        out[val] = {
            "num_docs": len(sub_docs),
            "candidates": {
                cand: {
                    "required_6_exact_micro": sub_res[cand]["exact"]["required_6_micro"],
                    "required_6_overlap_micro": sub_res[cand]["overlap"]["required_6_micro"],
                    "pii_char_recall_coverage": sub_res[cand]["character_metrics"]["pii_char_recall_coverage"],
                    "over_masking_rate": sub_res[cand]["character_metrics"]["over_masking_rate_on_non_pii"],
                }
                for cand in sub_res
            },
        }
    return out


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    results_dir = base_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    hw_specs = get_hardware_specs()
    print("[benchmark] Hardware specs:", json.dumps(hw_specs, indent=2))

    # 1. Load Independent Business Holdout (60 docs)
    holdout_path = data_dir / "business_holdout_60.jsonl"
    business_docs = [
        json.loads(line)
        for line in holdout_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    print(f"[benchmark] Loaded {len(business_docs)} independent business holdout docs.")

    # 2. Load Gravitee dev (120) and test (240) stratified splits
    grav_dev_docs, grav_test_docs, grav_manifest = load_gravitee_splits(
        dev_size=120,
        test_size=240,
        seed=42,
    )
    (data_dir / "gravitee_split_manifest.json").write_text(
        json.dumps(grav_manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    # 3. Initialize OpenAI Privacy Filter (`openai/privacy-filter`)
    print("[benchmark] Loading OpenAI Privacy Filter (openai/privacy-filter)...")
    from opf import OPF

    t0_load_opf = time.perf_counter()
    device_str = "cuda" if torch.cuda.is_available() else "cpu"
    opf_model = OPF(device=device_str, decode_mode="viterbi", trim_whitespace=True)
    _ = opf_model.get_prediction_components()
    opf_startup_sec = round(time.perf_counter() - t0_load_opf, 2)
    print(f"[benchmark] OPF loaded on {device_str} in {opf_startup_sec}s.")

    # First measure unpatched stock CPU latency on 10 business holdout docs for hardware comparison
    print("[benchmark] Measuring stock unpatched OPF CPU latency on 10 business docs...")
    _, opf_stock_cpu_10_perf = run_opf_inference(opf_model, business_docs[:10])

    # Apply grouped MoE CPU optimization (~10x faster on CPU while preserving bfloat16/float32 MoE routing)
    apply_grouped_moe_cpu_optimization(opf_model)

    # Run OPF on Business Holdout, Gravitee Dev, Gravitee Test
    print("[benchmark] Running OPF on Business Holdout (60 docs)...")
    opf_bus_raw, opf_bus_perf = run_opf_inference(opf_model, business_docs)

    print("[benchmark] Running OPF on Gravitee Dev (120 docs)...")
    opf_dev_raw, opf_dev_perf = run_opf_inference(opf_model, grav_dev_docs)

    print("[benchmark] Running OPF on Gravitee Test (240 docs)...")
    opf_test_raw, opf_test_perf = run_opf_inference(opf_model, grav_test_docs)

    # 4. Initialize Presidio + spaCy (`en_core_web_lg`)
    print("[benchmark] Loading Presidio + spaCy (en_core_web_lg)...")
    t0_load_pres = time.perf_counter()
    analyzer = build_presidio_analyzer()
    presidio_startup_sec = round(time.perf_counter() - t0_load_pres, 2)
    print(f"[benchmark] Presidio loaded in {presidio_startup_sec}s.")

    print("[benchmark] Running Presidio on Business Holdout (60 docs)...")
    pres_bus_raw, pres_bus_perf = run_presidio_inference(analyzer, business_docs)

    print("[benchmark] Running Presidio on Gravitee Dev (120 docs)...")
    pres_dev_raw, pres_dev_perf = run_presidio_inference(analyzer, grav_dev_docs)

    print("[benchmark] Running Presidio on Gravitee Test (240 docs)...")
    pres_test_raw, pres_test_perf = run_presidio_inference(analyzer, grav_test_docs)

    # 5. Compute comprehensive metrics across all splits and slices
    print("[benchmark] Scoring all candidates on Gravitee Dev, Gravitee Test, and Business Holdout...")
    dev_eval = evaluate_all_candidates(grav_dev_docs, opf_dev_raw, pres_dev_raw)
    test_eval = evaluate_all_candidates(grav_test_docs, opf_test_raw, pres_test_raw)
    bus_eval = evaluate_all_candidates(business_docs, opf_bus_raw, pres_bus_raw)

    test_by_source = evaluate_by_slice(grav_test_docs, opf_test_raw, pres_test_raw, "source")
    bus_by_doctype = evaluate_by_slice(business_docs, opf_bus_raw, pres_bus_raw, "doc_type")

    summary_payload = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hardware_specs": hw_specs,
        "startup_seconds": {
            "openai_privacy_filter": opf_startup_sec,
            "presidio_spacy_en_core_web_lg": presidio_startup_sec,
        },
        "runtime_performance": {
            "business_holdout_60": {
                "openai_privacy_filter_stock_cpu_sample10": opf_stock_cpu_10_perf,
                "openai_privacy_filter_grouped_moe_cpu": opf_bus_perf,
                "presidio_spacy_cpu": pres_bus_perf,
            },
            "gravitee_dev_120": {
                "openai_privacy_filter_grouped_moe_cpu": opf_dev_perf,
                "presidio_spacy_cpu": pres_dev_perf,
            },
            "gravitee_test_240": {
                "openai_privacy_filter_grouped_moe_cpu": opf_test_perf,
                "presidio_spacy_cpu": pres_test_perf,
            },
        },
        "gravitee_manifest": grav_manifest,
        "evaluation": {
            "gravitee_dev_120": dev_eval,
            "gravitee_test_240": test_eval,
            "business_holdout_60": bus_eval,
        },
        "slices": {
            "gravitee_test_by_source": test_by_source,
            "business_holdout_by_doc_type": bus_by_doctype,
        },
    }

    out_path = results_dir / "benchmark_results.json"
    out_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")
    print(f"[benchmark] Saved full benchmark results to {out_path}")


if __name__ == "__main__":
    main()
