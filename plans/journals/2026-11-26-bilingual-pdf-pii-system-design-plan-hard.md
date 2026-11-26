---
title: Bilingual PDF PII System Design Plan (--hard)
date: 2026-11-26
summary: "Completed /ak-advise + /ak-plan --hard with 2 researchers, 4 Full-Tier red-team reviewers (13 accepted fixes), and Validation Gate (0 failed/unverified claims)."
---

# Bilingual PDF PII System Design Plan (--hard)

## What happened
- Completed advisory scoping (`/ak-advise`) and `--hard` planning (`/ak-plan --hard`) for the self-hosted bilingual (VI+EN) PII Detection & Secure PDF Redaction MVP.
- Scaffolded `plans/261126-0104-bilingual-pdf-pii-system-design/` with 6 implementation phases and 2 technical research reports (`researcher-01-ocr-geometry.md`, `researcher-02-redaction-verification.md`).
- Ran 4 parallel Full-Tier red-team reviewers (Security Adversary, Failure Mode Analyst, Assumption Destroyer, Scope & Complexity Critic), deduplicated 14 evidence-backed findings, and applied 13 accepted fixes across Phases 1–6 (catching critical offline EN ML dependency gaps, `GRAVITEE_25_LABELS` mapping mismatches, `evaluation/hybrid_rules.py` Presidio drops & benchmark shortcuts, worker/network/CSRF isolation, vector-path & XObject-metadata leaks, `VER-02` CTM mapping, `VER-06` immutable-revision & scanned-page blindness, retryable partial-unique `idempotency_key`, `psutil` RSS/heartbeat monitoring, Tailwind v4 CSS layering, and hermetic `make test` separation).
- Resolved all 3 remaining `[UNVERIFIED]` items in Validation Session 1 (`lightweight_cpu` base + optional `docker-compose.opf.yml`, `CORE-01` default excluded-label set, and PyMuPDF AGPL-3.0 approval).

## Decision
- Locked the 4-container zero-egress CPU architecture (`api`, `postgres`, `worker`, `ml-service`) with page-level 3-way routing (`NATIVE`/`SCANNED_FLATTENED`/`MIXED`), single visual top-left `CropBox` coordinate frame, format-preserving destructive redaction (`pymupdf>=1.25.0,<2.0`), and zero-PyMuPDF independent verification (`pdfplumber` + `poppler-utils` + `pikepdf`/`qpdf`).

## Next steps
- Await user approval to execute `/ak-cook plans/261126-0104-bilingual-pdf-pii-system-design/plan.md`, revise any phase, or stop here.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
