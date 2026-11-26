---
title: "Bilingual PDF PII Detection & Secure Redaction System Design"
description: "End-to-end self-hosted CPU architecture and 6-phase implementation plan for bilingual (VI+EN) native/scanned/mixed PDF PII masking with human review, destructive redaction, and independent verification."
status: pending
priority: P1
effort: "10w (7-person MVP)"
branch: main
tags: [architecture, backend, frontend, database, ocr, ml, security, pdf]
blockedBy: []
blocks: []
created: 2026-11-26
---

# Bilingual PDF PII Detection & Secure Redaction System Design

## Overview

End-to-end system design and phased implementation plan for the self-hosted **PII Detection & Secure PDF Redaction MVP** web platform, aligning the 75-task functional backlog in [function-breakdown.md](../261101-1815-mvp-function-breakdown/function-breakdown.md) with the bilingual Vietnamese/English models evaluated in `evaluation/` and `checkpoints/`.

- **Visual workflow preview:** [advise-261126-0054-system-design-preview.html](../reports/advise-261126-0054-system-design-preview.html)
- **Research reports:** [OCR & PDF Geometry](./research/researcher-01-ocr-geometry.md) | [Redaction & Independent Verification](./research/researcher-02-redaction-verification.md)
- **Scope Challenge (`HOLD SCOPE`):** Existing scaffolding (`config/`, `configs/models.json`, `checkpoints/`, `evaluation/`, `docker/`, `frontend/`, `tests/test_ops01_environment.py`) is reused directly; zero unrequested abstractions (no Redis/Celery broker, no cloud OCR/LLM APIs, no speculative RapidOCR/plugin registries).

## Architecture Summary

- **4-Container Hardened Self-Hosted CPU Stack:** `api` (FastAPI + static React SPA built in Node multi-stage image), `postgres` (PostgreSQL 16 for state + `SELECT ... FOR UPDATE SKIP LOCKED` job queue + PII-free audit log), `worker` (runs clean `subprocess.Popen` tasks with scrubbed `env={}`, staging-dir isolation, and `psutil` RSS/heartbeat/cancel monitoring), and `ml-service` (authenticated singleton model server holding VI+EN models once in RAM; `lightweight_cpu` default self-contained build + optional `docker-compose.opf.yml` mounted-weights override). `worker`, `postgres`, and `ml-service` live strictly on a Docker `internal: true` network with zero outbound internet egress.
- **Input & Routing:** Page-level 3-way classification (`NATIVE`, `SCANNED_FLATTENED`, `MIXED`) via PyMuPDF `page.get_texttrace()` (`type == 3` invisible OCR detection) and `page.get_image_info(xrefs=True)`. Untrusted invisible OCR layers are ignored for detection and stripped in redacted zones.
- **Canonical Coordinates & Offsets:** All persisted `review_regions` and overlays use **visual (rotated) top-left `CropBox` coordinates** (`rect_visual = rect_unrotated * page.rotation_matrix`) so React viewer (`SVG viewBox`), `pdfplumber`, and `pdftoppm -cropbox` share one frame while PyMuPDF `add_redact_annot()` applies `page.derotation_matrix`. Entity spans map strictly via `char_offset -> token_ids -> rects[]`.
- **Output & Verification:** Format-preserving destructive redaction (solid black boxes, non-PII native text stays selectable, vector-outlined path safety, shared XObjects decoupled, recursive indirect-object hidden-data purge, non-incremental clean save) gated by a zero-shared-code independent Verification Engine (`pdfplumber` + CTM-mapped `pikepdf`/`poppler-utils` + `qpdf` + native/scanned `VER-06` residual loop creating immutable `revision_no + 1` drafts).

## Goals

| # | Goal | Priority |
|---|---|---|
| 1 | Lock unambiguous cross-module contracts (`CORE-01..03`) for exhaustive 6-group bilingual PII taxonomy, visual PDF coordinates, `ModelRegistry` parity, and PostgreSQL state/job schema | P1 |
| 2 | Deliver page-level 3-way extraction/OCR routing (`NATIVE`/`SCANNED_FLATTENED`/`MIXED`) and language-routed bilingual VI+EN detection with zero-egress container isolation and zero CPU OOM | P1 |
| 3 | Deliver CSRF-protected human-in-the-loop review, immutable revision locking, format-preserving destructive redaction, and independent fail-closed verification with zero leaks | P1 |

## Phases

| # | Phase | Status |
|---|---|---|
| 1 | [Phase 1: Contracts, Policy & Schema Foundations](./phase-01-start.md) | Pending |
| 2 | [Phase 2: Infrastructure, Auth/RBAC & PostgreSQL Job Queue](./phase-02-infra-auth-and-pg-queue.md) | Pending |
| 3 | [Phase 3: Page-Level 3-Way Extraction, Bilingual OCR & Singleton ML-Service](./phase-03-ocr-routing-and-bilingual-ml-service.md) | Pending |
| 4 | [Phase 4: Reviewer Web UI & Immutable Revision Locking](./phase-04-reviewer-ui-and-revision-locking.md) | Pending |
| 5 | [Phase 5: Format-Preserving Destructive Redaction & Independent Verification](./phase-05-destructive-redaction-and-independent-verification.md) | Pending |
| 6 | [Phase 6: Adversarial Security Suite, Race/Perf Hardening & Release Acceptance](./phase-06-adversarial-security-and-release-acceptance.md) | Pending |

## Extension Trace

- **Credible next variants:** (1) Standalone raster image inputs (`PNG`/`JPEG`/`TIFF`), and (2) adding a 3rd language detector.
- **Stable seams:** `PageExtractor` emits canonical `PageIR` (keeping `native` vs. `ocr` provenance and confidence distinct rather than flattening capabilities); `ml-service` exposes authenticated `POST /v1/detect(text, lang_hint) -> list[CanonicalEntity]`.
- **What changes / what stays unchanged:** Raster images touch only `BE-04` intake + a 1-page synthetic `SCANNED_FLATTENED` wrapper; a 3rd language touches only `ml-service` routing + `configs/models.json`. API, PostgreSQL schema, React UI, `RED`, and `VER` stay untouched. No dynamic plugin registry or factory layer is added.

## Success Criteria

- [ ] `CORE-01/02/03` contracts, PostgreSQL schema (with partial unique draft & retryable idempotency indexes), and 100%-covered VI+EN canonical label map signed off and verified by unit tests.
- [ ] All 4 containers (`api`, `postgres`, `worker`, `ml-service`) run 100% self-hosted on CPU with zero outbound egress (`internal: true`), zero OOM kills, and working React SPA serving.
- [ ] `NATIVE`, `SCANNED_FLATTENED` (including untrusted `render_mode == 3` OCR layers), `MIXED`, and manual-handwriting VI+EN fixtures complete upload -> analyze -> review -> lock -> redact -> verify -> download end-to-end.
- [ ] Independent Verification Engine (`VER-01..06`) passes with `0` text/vector/pixel/hidden-data/incremental-save leaks on all 13 `DATA-05` adversarial fixtures and catches fake-overlay redaction reliably.
- [ ] Hermetic `make test` (`tests/test_ops01_environment.py`, `evaluation/test_evaluation.py`, `evaluation/test_vn_evaluation.py`, Phase 1–6 unit suites), `make test-e2e` (RBAC, CSRF, concurrency/deletion race suites), `make lint`, and `make check-secrets` all pass.

## Red Team Review

### Session — 2026-11-26
**Findings:** 14 deduplicated (13 accepted, 1 rejected with nuance) across 4 Full-Tier lenses (Security Adversary / Fact Checker, Failure Mode Analyst / Flow Tracer, Assumption Destroyer / Scope Auditor, Scope & Complexity Critic / Contract Verifier)
**Severity breakdown:** 8 Critical, 5 High, 1 Medium

| # | Finding | Severity | Disposition | Applied To |
|---|---|---|---|---|
| 1 | Missing offline EN ML deps/weights, stale `pyproject.toml:35`, unpinned `tessdata_best`, `ModelRegistry` package/weight checks | Critical | Accept | Phase 1, Phase 2 |
| 2 | Misnamed/missing English `GRAVITEE_25_LABELS` (`US_PASSPORT`, `US_DRIVER_LICENSE`, `US_ITIN`, `IBAN_CODE`, `US_BANK_NUMBER`, `PASSWORD`) | Critical | Accept | Phase 1 |
| 3 | Reusing `evaluation/hybrid_rules.py` & `vn_rules.py` drops Presidio `PERSON`/`LOCATION` in `lightweight_cpu` & exposes benchmark bypasses | Critical | Accept | Phase 3 |
| 4 | Unsandboxed worker subprocess shares RW `/app`, multi-tenant `./storage`, `DATABASE_URL`, egress, & unauthenticated `ml-service` | Critical | Accept | Phase 2, Phase 3 |
| 5 | Hardcoded `JWT_SECRET_KEY` outside `production`, no startup `validate_security()`, missing CSRF on HttpOnly cookie auth | Critical | Accept | Phase 2, Phase 4 |
| 6 | Vector-outlined path bypass, XObject-level `/Metadata`/`/PieceInfo`/active keys unpurged, `VER-02` `pdfimages` missing CTM mapping | Critical | Accept | Phase 5, Phase 6 |
| 7 | Mid-extraction preview writes to `./storage/private/` violate `BE-11`, soft-delete retains PG PII rows, missing intake PDF-bomb caps | Critical | Accept | Phase 2, Phase 3 |
| 8 | `VER-06` mutating `LOCKED` -> `DRAFT` breaks immutability, blind on scanned/mixed pages, & drifts on PyMuPDF-vs-`pdfplumber` bboxes | Critical | Accept | Phase 1, Phase 5 |
| 9 | Unconditional `UNIQUE (idempotency_key)` bricks retries after transient failure; `jobs` lacks `max_attempts` dead-lettering | High | Accept | Phase 1, Phase 2, Phase 5 |
| 10 | `RLIMIT_AS=1GB` trips Linux virtual-memory reservation on 8-vCPU OpenCV/Tesseract & sync waits starve 30s lease heartbeats | High | Accept | Phase 2 |
| 11 | Unlayered `frontend/styles.css` breaks Tailwind v4, missing Node build/SPA mount, UID `10001` bind-mount error, `API_PORT` bug, shared `HEALTHCHECK` | High | Accept | Phase 2, Phase 4 |
| 12 | `.env`/storage/certs break `scripts/check_secrets.py` & `test_ops01_environment.py`; live tests in `tests/` break `make test` | High | Accept | Phase 2, Phase 6 |
| 13 | `config/logger.py` leaves root/`uvicorn`/`sqlalchemy`/`httpx` unscrubbed & misses unquoted secrets, `DATABASE_URL`, `Cookie`, US PII | High | Accept | Phase 2 |
| 14 | (14a) Remove speculative `RapidOcrViBackend` stub/flag/script; (14b) Drop `opf_high_ram` profile entirely | Medium | Accept (14a) / Reject (14b) | Phase 2, Phase 3, Phase 6 (`docker-compose.opf.yml` override) |

### Whole-Plan Consistency Sweep
- Files reread: `plan.md`, `phase-01-start.md`, `phase-02-infra-auth-and-pg-queue.md`, `phase-03-ocr-routing-and-bilingual-ml-service.md`, `phase-04-reviewer-ui-and-revision-locking.md`, `phase-05-destructive-redaction-and-independent-verification.md`, `phase-06-adversarial-security-and-release-acceptance.md`
- Decision deltas checked: 13
- Reconciled stale references: 13 (removed all references to `OCR_BACKEND`, `RapidOcrViBackend`, `scripts/benchmark_vi_ocr.py`, `RLIMIT_AS=1GB`, unconditional `UNIQUE (idempotency_key)`, direct `./storage/private/previews/` writes, in-place `LOCKED -> DRAFT` mutation, `PASSPORT`/`DRIVER_LICENSE`/`TAX_ID`, direct `evaluation/hybrid_rules.py` reuse, and 12-fixture count updated to 13 across all phases)
- Unresolved contradictions: 0

## Validation Log

### Verification Results
- **Tier:** Full (6 phases — Fact Checker, Flow Tracer, Scope Auditor, Contract Verifier executed during Red-Team Review; remaining `[UNVERIFIED]` claims resolved in Validation Session 1)
- **Claims checked:** 24 codebase citations + 3 `[UNVERIFIED]` items
- **Verified:** 27 | **Failed:** 0 | **Unverified:** 0

### Session 1 — 2026-11-26
**Trigger:** Post-red-team `--hard` Validation Gate resolving remaining `[UNVERIFIED]` items
**Questions asked:** 3

#### Questions & Answers

1. **[Assumptions]** Demo server RAM & model profile: How should we lock the default production deployment profile in Phase 2/3?
   - Options: Base build defaults to lightweight_cpu (~2 GB RAM: spacy_vn_19_ner + EN Presidio/en_core_web_lg + rules); keep opf_high_ram (12 GB+ RAM) as optional docker-compose.opf.yml override (Recommended) | Demo server has >=16 GB RAM guaranteed — make dual-OPF (opf_high_ram) the primary default profile in docker-compose.yml | Demo server has <=8 GB RAM — drop docker-compose.opf.yml completely and lock strictly to lightweight_cpu
   - **Answer:** Base build defaults to lightweight_cpu (~2 GB RAM: spacy_vn_19_ner + EN Presidio/en_core_web_lg + rules); keep opf_high_ram (12 GB+ RAM) as optional docker-compose.opf.yml override
   - **Rationale:** Guarantees reproducible offline builds on any developer laptop or 8 GB server while keeping the 12 GB+ OPF upgrade path ready via Compose override.

2. **[Scope]** CORE-01 secondary/excluded labels: Which default policy for optional VI+EN labels should Phase 1 lock into app/contracts/pii_taxonomy.py?
   - Options: Exclude AGE, GENDER, SEX, TITLE, ORGANIZATION, URL, IP_ADDRESS, MAC_ADDRESS, IMEI, FINANCIAL by default; map all government/financial IDs + PASSWORD into ID_NUMBER (pending formal CS1 sign-off) (Recommended) | Include ORGANIZATION, URL, IP_ADDRESS, and FINANCIAL in auto-redaction as well (higher recall, more review noise) | Strict 6-group minimal policy only (drop PASSWORD and US_LICENSE_PLATE from ID_NUMBER too; keep only CCCD/CMND/MST/BHXH/Passport/DriverLicense/SSN/CreditCard/IBAN/Bank)
   - **Answer:** Exclude AGE, GENDER, SEX, TITLE, ORGANIZATION, URL, IP_ADDRESS, MAC_ADDRESS, IMEI, FINANCIAL by default; map all government/financial IDs + PASSWORD into ID_NUMBER (pending formal CS1 sign-off)
   - **Rationale:** Keeps reviewer noise low on business PDFs while ensuring zero silent drops of high-risk government/financial IDs or credentials.

3. **[Risks]** Licensing constraint: Research confirmed PyMuPDF (already pinned in requirements.txt) is AGPL-3.0 / commercial. Is AGPL-3.0 acceptable for your project's deployment model?
   - Options: PyMuPDF AGPL-3.0 is acceptable (academic/capstone or AGPL-compliant deployment) — proceed with pymupdf>=1.25.0 for extraction & redaction (Recommended) | AGPL-3.0 is NOT acceptable (proprietary SaaS without commercial Artifex license) — stop and redesign RED/OCR around MIT/Apache/MPL stack (pypdfium2 + pikepdf + raster fallback)
   - **Answer:** PyMuPDF AGPL-3.0 is acceptable (academic/capstone or AGPL-compliant deployment) — proceed with pymupdf>=1.25.0 for extraction & redaction
   - **Rationale:** Unblocks format-preserving destructive vector & pixel redaction with `pymupdf>=1.25.0,<2.0`.

#### Confirmed Decisions
- Production model profile: `lightweight_cpu` base build + optional `docker-compose.opf.yml` (`opf_high_ram`) — deterministic builds with RAM upgrade path.
- `CORE-01` label policy: Exhaustive 19-label VI + 25-label EN map with secondary attributes excluded by default and all IDs + `PASSWORD` mapped to `ID_NUMBER`.
- PDF engine licensing: PyMuPDF (`>=1.25.0,<2.0`) AGPL-3.0 confirmed acceptable.

#### Impact on Phases
- Phase 1: Cleared `[UNVERIFIED]` tag in `R1.1` with confirmed default `EXCLUDED_LABELS` and `ID_NUMBER` scope.
- Phase 2: Cleared both `[UNVERIFIED]` tags in `R2.1` confirming `lightweight_cpu` base + `docker-compose.opf.yml` override and PyMuPDF AGPL-3.0 approval.

### Whole-Plan Consistency Sweep
- Files reread: `plan.md`, `phase-01-start.md`, `phase-02-infra-auth-and-pg-queue.md`, `phase-03-ocr-routing-and-bilingual-ml-service.md`, `phase-04-reviewer-ui-and-revision-locking.md`, `phase-05-destructive-redaction-and-independent-verification.md`, `phase-06-adversarial-security-and-release-acceptance.md`
- Decision deltas checked: 3
- Reconciled stale references: 3 (`[UNVERIFIED]` tags cleared across Phase 1 and Phase 2)
- Unresolved contradictions: 0

<!-- slug: bilingual-pdf-pii-system-design -->
