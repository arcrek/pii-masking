#!/usr/bin/env python3
"""Colab GPU Orchestrator for Vietnamese PII (19 OpenPII Labels):
1. Pre-Finetune Inference (`openai/privacy-filter` out-of-the-box 8-label model & `spaCy blank('vi')` untrained NER)
   on `vn_dev`, `vn_test`, and `vn_independent_holdout`.
2. Fine-Tuning Direction A: Lightweight `spaCy NER` (`tok2vec` + `EntityRecognizer`, 19 labels) on `vn_train` (3,000 docs)
   with validation selection on `vn_dev` (300 docs).
3. Fine-Tuning Direction B: `OpenAI Privacy Filter (OPF)` with custom 19-label BIESO head (77 output classes)
   on `vn_opf_train` (3,000 docs) with validation selection on `vn_opf_dev` (300 docs).
4. Post-Finetune Inference (`spaCy Finetuned 19-label` & `OPF Finetuned 19-label`, reloaded from disk checkpoints)
   on `vn_dev`, `vn_test`, and `vn_independent_holdout`, plus CPU vs GPU latency/memory profiling.
"""

from __future__ import annotations

import json
import os
import platform
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import psutil
import spacy
from spacy.training import Example
from spacy.util import compounding, minibatch
import torch

OPENPII_19_LABELS: list[str] = [
    "AGE",
    "BUILDINGNUM",
    "CITY",
    "CREDITCARDNUMBER",
    "DATE",
    "DRIVERLICENSENUM",
    "EMAIL",
    "GENDER",
    "GIVENNAME",
    "IDCARDNUM",
    "PASSPORTNUM",
    "SEX",
    "SOCIALNUM",
    "STREET",
    "SURNAME",
    "TAXNUM",
    "TELEPHONENUM",
    "TITLE",
    "ZIPCODE",
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def get_vm_specs() -> dict[str, Any]:
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    gpu_vram_gb = (
        round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
        if torch.cuda.is_available()
        else 0.0
    )
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "spacy_version": spacy.__version__,
        "cpu_count": os.cpu_count(),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": gpu_name,
        "gpu_vram_gb": gpu_vram_gb,
    }


def check_spacy_alignment(nlp: Any, docs: list[dict[str, Any]]) -> dict[str, Any]:
    """Audit how well spaCy's Vietnamese tokenizer aligns with character-level gold spans."""
    total_spans = 0
    strict_aligned = 0
    contract_aligned = 0
    expand_aligned = 0
    for d in docs:
        doc_obj = nlp.make_doc(d["text"])
        for sp in d["spans"]:
            total_spans += 1
            s, e, lbl = int(sp["start"]), int(sp["end"]), str(sp["label"])
            if doc_obj.char_span(s, e, label=lbl, alignment_mode="strict") is not None:
                strict_aligned += 1
            if doc_obj.char_span(s, e, label=lbl, alignment_mode="contract") is not None:
                contract_aligned += 1
            if doc_obj.char_span(s, e, label=lbl, alignment_mode="expand") is not None:
                expand_aligned += 1
    return {
        "total_spans": total_spans,
        "strict_aligned": strict_aligned,
        "strict_rate": round(strict_aligned / total_spans, 4) if total_spans else 0.0,
        "contract_aligned": contract_aligned,
        "contract_rate": round(contract_aligned / total_spans, 4) if total_spans else 0.0,
        "expand_aligned": expand_aligned,
        "expand_rate": round(expand_aligned / total_spans, 4) if total_spans else 0.0,
    }


def run_spacy_inference(
    nlp: Any,
    docs: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Run spaCy NER pipeline on `docs` and return `{doc_id: [{start, end, label, score}]}` + perf stats."""
    process = psutil.Process(os.getpid())
    if docs:
        _ = nlp(docs[0]["text"])

    latencies_ms: list[float] = []
    preds_by_doc: dict[str, list[dict[str, Any]]] = {}
    total_chars = 0

    t0_all = time.perf_counter()
    for d in docs:
        text = d["text"]
        total_chars += len(text)
        t0 = time.perf_counter()
        doc_obj = nlp(text)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        spans = []
        for ent in doc_obj.ents:
            s, e = int(ent.start_char), int(ent.end_char)
            while s < e and text[s].isspace():
                s += 1
            while e > s and text[e - 1].isspace():
                e -= 1
            if e > s:
                spans.append(
                    {
                        "start": s,
                        "end": e,
                        "label": str(ent.label_),
                        "text": text[s:e],
                        "score": 0.90,
                    }
                )
        preds_by_doc[str(d["id"])] = spans
    total_sec = time.perf_counter() - t0_all

    lat_sorted = sorted(latencies_ms)
    n = len(lat_sorted)
    perf = {
        "num_docs": n,
        "total_seconds": round(total_sec, 4),
        "docs_per_sec": round(n / total_sec, 2) if total_sec > 0 else 0.0,
        "chars_per_sec": round(total_chars / total_sec, 1) if total_sec > 0 else 0.0,
        "latency_mean_ms": round(sum(lat_sorted) / n, 3) if n else 0.0,
        "latency_p50_ms": round(lat_sorted[n // 2], 3) if n else 0.0,
        "latency_p95_ms": round(lat_sorted[int(n * 0.95)], 3) if n else 0.0,
        "peak_vram_mb": 0.0,
        "peak_ram_mb": round(process.memory_info().rss / (1024**2), 2),
    }
    return preds_by_doc, perf


def compute_quick_micro_f1(
    docs: list[dict[str, Any]],
    preds_by_doc: dict[str, list[dict[str, Any]]],
) -> dict[str, float]:
    tp = fp = fn = 0
    for d in docs:
        gold = {(int(s["start"]), int(s["end"]), str(s["label"])) for s in d["spans"]}
        pred = {
            (int(s["start"]), int(s["end"]), str(s["label"]))
            for s in preds_by_doc.get(str(d["id"]), [])
        }
        tp += len(gold & pred)
        fp += len(pred - gold)
        fn += len(gold - pred)
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4)}


def train_spacy_vn_ner(
    train_docs: list[dict[str, Any]],
    dev_docs: list[dict[str, Any]],
    output_dir: Path,
    epochs: int = 15,
    seed: int = 42,
) -> dict[str, Any]:
    """Train lightweight spaCy blank('vi') tok2vec/CNN NER on 19 OpenPII labels and save best checkpoint."""
    print(f"[spacy-train] Initializing blank('vi') NER with 19 OpenPII labels (seed={seed})...")
    spacy.util.fix_random_seed(seed)
    rng = random.Random(seed)

    nlp = spacy.blank("vi")
    ner = nlp.add_pipe("ner")
    for lbl in OPENPII_19_LABELS:
        ner.add_label(lbl)

    alignment_train = check_spacy_alignment(nlp, train_docs)
    alignment_dev = check_spacy_alignment(nlp, dev_docs)
    print(f"[spacy-train] Tokenizer alignment (train): {alignment_train}")

    # Build spaCy Example objects using expand alignment fallback for sub-token punctuation boundaries
    train_examples: list[Example] = []
    for d in train_docs:
        text = d["text"]
        doc_obj = nlp.make_doc(text)
        ents = []
        occupied: set[int] = set()
        for sp in d["spans"]:
            s, e, lbl = int(sp["start"]), int(sp["end"]), str(sp["label"])
            span = doc_obj.char_span(s, e, label=lbl, alignment_mode="contract")
            if span is None:
                span = doc_obj.char_span(s, e, label=lbl, alignment_mode="expand")
            if span is not None and len(span) > 0:
                tok_range = set(range(span.start, span.end))
                if not (tok_range & occupied):
                    occupied.update(tok_range)
                    ents.append((span.start_char, span.end_char, lbl))
        train_examples.append(Example.from_dict(doc_obj, {"entities": ents}))

    optimizer = nlp.initialize(lambda: train_examples[:256])
    epoch_logs: list[dict[str, Any]] = []
    best_f1 = -1.0
    best_epoch = 0

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    t0_train = time.perf_counter()
    for ep in range(1, epochs + 1):
        t0_ep = time.perf_counter()
        rng.shuffle(train_examples)
        losses: dict[str, float] = {}
        batches = minibatch(train_examples, size=compounding(8.0, 32.0, 1.002))
        for batch in batches:
            nlp.update(batch, drop=0.2, sgd=optimizer, losses=losses)

        dev_preds, _ = run_spacy_inference(nlp, dev_docs)
        dev_metrics = compute_quick_micro_f1(dev_docs, dev_preds)
        ep_sec = round(time.perf_counter() - t0_ep, 2)
        ep_entry = {
            "epoch": ep,
            "train_loss_ner": round(float(losses.get("ner", 0.0)), 2),
            "dev_exact_precision": dev_metrics["precision"],
            "dev_exact_recall": dev_metrics["recall"],
            "dev_exact_f1": dev_metrics["f1"],
            "elapsed_sec": ep_sec,
        }
        epoch_logs.append(ep_entry)
        print(
            f"[spacy-train] Epoch {ep:02d}/{epochs:02d} | loss={ep_entry['train_loss_ner']:.1f} "
            f"| dev_P={dev_metrics['precision']:.4f} dev_R={dev_metrics['recall']:.4f} dev_F1={dev_metrics['f1']:.4f} ({ep_sec}s)"
        )
        if dev_metrics["f1"] > best_f1:
            best_f1 = dev_metrics["f1"]
            best_epoch = ep
            nlp.to_disk(output_dir)

    total_train_sec = round(time.perf_counter() - t0_train, 2)
    summary = {
        "model_architecture": "spacy_blank_vi_tok2vec_ner_cnn",
        "spacy_version": spacy.__version__,
        "seed": seed,
        "epochs": epochs,
        "best_epoch": best_epoch,
        "best_dev_exact_f1": best_f1,
        "total_train_seconds": total_train_sec,
        "num_train_docs": len(train_docs),
        "num_dev_docs": len(dev_docs),
        "labels": OPENPII_19_LABELS,
        "tokenizer_alignment_train": alignment_train,
        "tokenizer_alignment_dev": alignment_dev,
        "epoch_metrics": epoch_logs,
    }
    (output_dir / "spacy_finetune_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[spacy-train] Saved best spaCy checkpoint (epoch {best_epoch}, F1={best_f1:.4f}) to {output_dir}")
    return summary


def run_opf_inference_on_docs(
    opf_model: Any,
    docs: list[dict[str, Any]],
    tag: str = "opf",
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Run OPF instance on `docs` and collect spans + latency/VRAM/RAM stats."""
    process = psutil.Process(os.getpid())
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

    if docs:
        _ = opf_model.redact(docs[0]["text"])

    latencies_ms: list[float] = []
    spans_by_doc: dict[str, list[dict[str, Any]]] = {}
    total_chars = 0

    t0_all = time.perf_counter()
    for idx, d in enumerate(docs, 1):
        text = d["text"]
        total_chars += len(text)
        t0 = time.perf_counter()
        res = opf_model.redact(text)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        doc_spans = []
        for sp in res.detected_spans:
            doc_spans.append(
                {
                    "start": int(sp.start),
                    "end": int(sp.end),
                    "label": str(sp.label),
                    "text": str(sp.text),
                    "score": 0.92,
                }
            )
        spans_by_doc[str(d["id"])] = doc_spans
        if idx % 150 == 0 or idx == len(docs):
            el = time.perf_counter() - t0_all
            print(f"  [{tag}] {idx}/{len(docs)} docs ({el:.1f}s, {el/idx*1000:.1f} ms/doc)")

    total_sec = time.perf_counter() - t0_all
    lat_sorted = sorted(latencies_ms)
    n = len(lat_sorted)
    peak_vram_mb = (
        round(torch.cuda.max_memory_allocated() / (1024**2), 2)
        if torch.cuda.is_available()
        else 0.0
    )
    perf = {
        "num_docs": n,
        "total_seconds": round(total_sec, 4),
        "docs_per_sec": round(n / total_sec, 2) if total_sec > 0 else 0.0,
        "chars_per_sec": round(total_chars / total_sec, 1) if total_sec > 0 else 0.0,
        "latency_mean_ms": round(sum(lat_sorted) / n, 3) if n else 0.0,
        "latency_p50_ms": round(lat_sorted[n // 2], 3) if n else 0.0,
        "latency_p95_ms": round(lat_sorted[int(n * 0.95)], 3) if n else 0.0,
        "peak_vram_mb": peak_vram_mb,
        "peak_ram_mb": round(process.memory_info().rss / (1024**2), 2),
    }
    return spans_by_doc, perf


def main() -> None:
    work_dir = Path("/content/vn_pii_work")
    data_dir = work_dir / "data"
    out_dir = work_dir / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    vm_specs = get_vm_specs()
    print("[colab-job] VM specs:", json.dumps(vm_specs, indent=2))

    train_docs = load_jsonl(data_dir / "vn_train.jsonl")
    dev_docs = load_jsonl(data_dir / "vn_dev.jsonl")
    test_docs = load_jsonl(data_dir / "vn_test.jsonl")
    ind_docs = load_jsonl(data_dir / "vn_independent_holdout.jsonl")

    # =========================================================================
    # STEP 1: PRE-FINETUNE BASELINE INFERENCE (Untrained spaCy vi & Base OPF)
    # =========================================================================
    print("\n=== STEP 1A: Pre-Finetune Blank/Untrained spaCy ('vi') ===")
    spacy.util.fix_random_seed(42)
    nlp_untrained = spacy.blank("vi")
    ner_untrained = nlp_untrained.add_pipe("ner")
    for lbl in OPENPII_19_LABELS:
        ner_untrained.add_label(lbl)
    nlp_untrained.initialize()

    spacy_pre_dev, spacy_pre_dev_perf = run_spacy_inference(nlp_untrained, dev_docs)
    spacy_pre_test, spacy_pre_test_perf = run_spacy_inference(nlp_untrained, test_docs)
    spacy_pre_ind, spacy_pre_ind_perf = run_spacy_inference(nlp_untrained, ind_docs)

    print("\n=== STEP 1B: Pre-Finetune Out-of-the-Box OPF (`openai/privacy-filter`) ===")
    from opf import OPF

    t0_load_base = time.perf_counter()
    opf_base = OPF(device="cuda", decode_mode="viterbi", trim_whitespace=True)
    _ = opf_base.get_prediction_components()
    opf_base_startup_sec = round(time.perf_counter() - t0_load_base, 2)
    print(f"[colab-job] Loaded base OPF on CUDA in {opf_base_startup_sec}s.")

    opf_pre_dev, opf_pre_dev_perf = run_opf_inference_on_docs(opf_base, dev_docs, tag="opf-pre-dev")
    opf_pre_test, opf_pre_test_perf = run_opf_inference_on_docs(opf_base, test_docs, tag="opf-pre-test")
    opf_pre_ind, opf_pre_ind_perf = run_opf_inference_on_docs(opf_base, ind_docs, tag="opf-pre-ind")

    # Free base OPF GPU memory before training
    del opf_base
    torch.cuda.empty_cache()

    # =========================================================================
    # STEP 2: TRAIN DIRECTION A — LIGHTWEIGHT SPACY NER (19 LABELS)
    # =========================================================================
    print("\n=== STEP 2: Training Lightweight spaCy NER (19 OpenPII Labels) ===")
    spacy_ckpt_dir = out_dir / "spacy_vn_19_ner"
    spacy_train_summary = train_spacy_vn_ner(
        train_docs=train_docs,
        dev_docs=dev_docs,
        output_dir=spacy_ckpt_dir,
        epochs=15,
        seed=42,
    )

    # Verify reload from disk and run Post-Finetune spaCy inference
    t0_load_spacy = time.perf_counter()
    nlp_finetuned = spacy.load(spacy_ckpt_dir)
    spacy_post_startup_sec = round(time.perf_counter() - t0_load_spacy, 3)
    print(f"[colab-job] Reloaded fine-tuned spaCy checkpoint in {spacy_post_startup_sec}s. Labels: {nlp_finetuned.get_pipe('ner').labels}")

    spacy_post_dev, spacy_post_dev_perf = run_spacy_inference(nlp_finetuned, dev_docs)
    spacy_post_test, spacy_post_test_perf = run_spacy_inference(nlp_finetuned, test_docs)
    spacy_post_ind, spacy_post_ind_perf = run_spacy_inference(nlp_finetuned, ind_docs)

    # =========================================================================
    # STEP 3: TRAIN DIRECTION B — FINE-TUNE OPF WITH 19 LABELS (77 BIESO CLASSES)
    # =========================================================================
    print("\n=== STEP 3: Fine-Tuning OPF with Custom 19-Label Space (77 BIESO classes) ===")
    opf_ckpt_dir = out_dir / "opf_vn_19"
    label_space_json = data_dir / "opf_vn_19_label_space.json"
    opf_train_jsonl = data_dir / "vn_opf_train.jsonl"
    opf_dev_jsonl = data_dir / "vn_opf_dev.jsonl"

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

    cmd = [
        sys.executable,
        "-m",
        "opf",
        "train",
        str(opf_train_jsonl),
        "--validation-dataset",
        str(opf_dev_jsonl),
        "--label-space-json",
        str(label_space_json),
        "--device",
        "cuda",
        "--n-ctx",
        "1024",
        "--epochs",
        "4",
        "--batch-size",
        "8",
        "--grad-accum-steps",
        "2",
        "--learning-rate",
        "1.5e-4",
        "--weight-decay",
        "0.01",
        "--shuffle-seed",
        "42",
        "--output-dir",
        str(opf_ckpt_dir),
        "--overwrite-output",
    ]
    print("[opf-train] Running command:", " ".join(cmd))
    t0_opf_train = time.perf_counter()
    proc = subprocess.run(cmd, text=True, capture_output=True)
    opf_train_wall_sec = round(time.perf_counter() - t0_opf_train, 2)
    print(proc.stdout)
    if proc.returncode != 0:
        print("[opf-train] STDERR:", proc.stderr, file=sys.stderr)
        raise RuntimeError(f"opf train failed with exit code {proc.returncode}")

    (opf_ckpt_dir / "train_stdout.log").write_text(proc.stdout, encoding="utf-8")
    opf_finetune_summary = json.loads((opf_ckpt_dir / "finetune_summary.json").read_text(encoding="utf-8"))
    opf_finetune_summary["wall_clock_seconds"] = opf_train_wall_sec

    # =========================================================================
    # STEP 4: RELOAD FINE-TUNED 19-LABEL OPF CHECKPOINT & RUN POST-FINETUNE INFERENCE
    # =========================================================================
    print("\n=== STEP 4: Reloading Fine-Tuned 19-Label OPF Checkpoint & Running Inference ===")
    t0_load_ft_opf = time.perf_counter()
    opf_ft = OPF(model=str(opf_ckpt_dir), device="cuda", decode_mode="viterbi", trim_whitespace=True)
    runtime_ft, _ = opf_ft.get_prediction_components()
    opf_post_startup_sec = round(time.perf_counter() - t0_load_ft_opf, 2)
    print(
        f"[colab-job] Reloaded fine-tuned OPF checkpoint in {opf_post_startup_sec}s. "
        f"Span classes ({len(runtime_ft.label_info.span_class_names)}): {runtime_ft.label_info.span_class_names}"
    )

    opf_post_dev, opf_post_dev_perf = run_opf_inference_on_docs(opf_ft, dev_docs, tag="opf-post-dev")
    opf_post_test, opf_post_test_perf = run_opf_inference_on_docs(opf_ft, test_docs, tag="opf-post-test")
    opf_post_ind, opf_post_ind_perf = run_opf_inference_on_docs(opf_ft, ind_docs, tag="opf-post-ind")

    # Package all raw predictions, performance metrics, and training summaries into a single JSON artifact
    predictions_bundle = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "colab_vm_specs": vm_specs,
        "startup_seconds": {
            "opf_base_cuda": opf_base_startup_sec,
            "opf_finetuned_cuda": opf_post_startup_sec,
            "spacy_finetuned_cpu": spacy_post_startup_sec,
        },
        "training_summaries": {
            "spacy_vn_19_ner": spacy_train_summary,
            "opf_vn_19": opf_finetune_summary,
        },
        "runtime_performance": {
            "vn_dev_300": {
                "spacy_untrained_pre": spacy_pre_dev_perf,
                "opf_pretrained_pre_cuda": opf_pre_dev_perf,
                "spacy_finetuned_post_cpu": spacy_post_dev_perf,
                "opf_finetuned_post_cuda": opf_post_dev_perf,
            },
            "vn_test_600": {
                "spacy_untrained_pre": spacy_pre_test_perf,
                "opf_pretrained_pre_cuda": opf_pre_test_perf,
                "spacy_finetuned_post_cpu": spacy_post_test_perf,
                "opf_finetuned_post_cuda": opf_post_test_perf,
            },
            "vn_independent_holdout_75": {
                "spacy_untrained_pre": spacy_pre_ind_perf,
                "opf_pretrained_pre_cuda": opf_pre_ind_perf,
                "spacy_finetuned_post_cpu": spacy_post_ind_perf,
                "opf_finetuned_post_cuda": opf_post_ind_perf,
            },
        },
        "raw_predictions": {
            "vn_dev_300": {
                "spacy_pre": spacy_pre_dev,
                "opf_pre": opf_pre_dev,
                "spacy_post": spacy_post_dev,
                "opf_post": opf_post_dev,
            },
            "vn_test_600": {
                "spacy_pre": spacy_pre_test,
                "opf_pre": opf_pre_test,
                "spacy_post": spacy_post_test,
                "opf_post": opf_post_test,
            },
            "vn_independent_holdout_75": {
                "spacy_pre": spacy_pre_ind,
                "opf_pre": opf_pre_ind,
                "spacy_post": spacy_post_ind,
                "opf_post": opf_post_ind,
            },
        },
    }

    bundle_path = out_dir / "colab_vn_predictions_and_logs.json"
    bundle_path.write_text(
        json.dumps(predictions_bundle, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[colab-job] Wrote complete predictions & logs bundle to {bundle_path}")


if __name__ == "__main__":
    main()
