---
phase: 1
title: "Phase 1: Contracts, Policy & Schema Foundations"
status: todo
priority: P1
effort: "1w"
dependencies: []
---

# Phase 1: Contracts, Policy & Schema Foundations

**Maps to backlog:** `CORE-01`, `CORE-02`, `CORE-03`, `QA-01`
**Primary owners:** `CS1` (taxonomy/policy), `SE3` (document & coordinate contract), `SE2` (API & PostgreSQL schema)

## Goal

Lock the exact cross-module data contracts — canonical 6-group bilingual PII policy, visual/unrotated PDF coordinate & char-offset IR, PostgreSQL relational + job-queue schema, `ModelRegistry` package/weight verification, and OpenAPI schemas — so all 7 team members can build in parallel without integration drift.

## Context & Existing Code Reuse

- Existing config & registry: [config/system_config.py](../../config/system_config.py), [config/model_registry.py](../../config/model_registry.py), [configs/models.json](../../configs/models.json).
- Existing Vietnamese 19-label schema: [checkpoints/opf_vn_19_label_space.json](../../checkpoints/opf_vn_19_label_space.json).
- Existing English 25-label benchmark mapping: [evaluation/metrics.py](../../evaluation/metrics.py) (`GRAVITEE_25_LABELS`, `OPF_TO_GRAVITEE_PRIMARY_MAP`), [evaluation/run_benchmark.py](../../evaluation/run_benchmark.py) (`PRESIDIO_TO_GRAVITEE_MAP`).

## Requirements

- [ ] **R1.1 (`CORE-01`):** Versioned canonical 6-group UI taxonomy (`PERSON`, `EMAIL`, `PHONE`, `ADDRESS`, `DATE`, `ID_NUMBER`) exhaustively mapping **every** label in `OPENPII_19_LABELS`, `GRAVITEE_25_LABELS`, `PRESIDIO_TO_GRAVITEE_MAP`, and `OPF_TO_GRAVITEE_PRIMARY_MAP` into either a `CanonicalGroup` or an explicit, audited `EXCLUDED_LABELS` set (`AGE`, `GENDER`, `SEX`, `TITLE`, `HONORIFIC`, `NRP`, `ORGANIZATION`, `URL`, `private_url`, `IP_ADDRESS`, `MAC_ADDRESS`, `IMEI`, `FINANCIAL` excluded by default; all government/financial IDs, `PASSWORD`, and OPF `account_number`/`secret` mapped to `ID_NUMBER`, pending formal CS1 sign-off), while preserving `raw_label` in entity metadata. <!-- Red-Team Fix: Finding 2 --> <!-- Updated: Validation Session 1 - Locked default excluded-label policy and ID_NUMBER scope -->
- [ ] **R1.2 (`CORE-02`):** Canonical `PageIR` Pydantic models capturing `page_classification` (`NATIVE` | `SCANNED_FLATTENED` | `MIXED`), `page_quality` (`OK` | `NEEDS_ATTENTION` | `FAILED`), `mediabox`, `cropbox`, `rotation_deg` (`0|90|180|270`), `visual_rect`, `tokens[]` (with `source: native|ocr`, `char_start`, `char_end`, `visual_bbox`, `ocr_confidence`), and `regions[]` (with `rects[]` in visual top-left `CropBox` points).
- [ ] **R1.3 (`CORE-02` Geometry Law):** Pure-math forward/inverse coordinate utilities converting between (a) PyMuPDF unrotated `cropbox` space (`add_redact_annot`), (b) visual rotated top-left `CropBox` space (`FE` viewer, `pdfplumber`, `pdftoppm -cropbox`), (c) 300 DPI + OpenCV deskewed pixel space (accounting for row-vector vs. column-vector transpose), and (d) canonical ISO 32000-1 PDF user space.
- [ ] **R1.4 (`CORE-03` PostgreSQL Schema):** PostgreSQL 16 relational + job-queue DDL & SQLAlchemy 2.0 models + initial Alembic migration covering `users`, `sessions`, `login_rate_limits`, `documents`, `document_pages`, `detected_entities`, `review_revisions`, `review_regions`, `jobs`, `export_artifacts`, `verification_reports`, and `audit_logs` — including partial unique indexes for single active `DRAFT` per document and retryable `idempotency_key` plus `max_attempts` dead-lettering. <!-- Red-Team Fix: Finding 8, Finding 9 -->
- [ ] **R1.5 (`CORE-03` Model Registry Parity):** Extend [config/model_registry.py](../../config/model_registry.py) and [configs/models.json](../../configs/models.json) with `taxonomy_version`, `checkpoints/en_gravitee_25_label_space.json`, `source_type` (`local` | `package`), weight-file integrity checks (`model.safetensors` for `safetensors` models, `meta.json` for spaCy models, `spacy.util.is_package()` for pip-installed `en_core_web_lg`), and `reload=True`, while keeping all `tests/test_ops01_environment.py` assertions green. <!-- Red-Team Fix: Finding 1 -->
- [ ] **R1.6 (`CORE-03` API & `QA-01` Gates):** Versioned `/api/v1` Pydantic request/response schemas and `docs/architecture/system-design-contracts.md` locking acceptance thresholds (coordinate error `<= 1.5 pt`, zero leaks on 13-fixture `DATA-05`, locked VI/EN F1 & recall gates, max 25 MB / 100 pages / 300s job timeout).

## Architecture & Data Contracts

### Exhaustive Canonical 6-Group Label Mapping (Default Proposed for `CORE-01`) <!-- Red-Team Fix: Finding 2 -->

| Canonical UI Group | Vietnamese 19-Label Sources (`opf_vn_19_label_space.json`) | English Sources (`GRAVITEE_25_LABELS` / Presidio / `OPF_TO_GRAVITEE_PRIMARY_MAP`) |
|---|---|---|
| `PERSON` | `GIVENNAME`, `SURNAME` | `PERSON`, `private_person` |
| `EMAIL` | `EMAIL` | `EMAIL_ADDRESS`, `private_email` |
| `PHONE` | `TELEPHONENUM` | `PHONE_NUMBER`, `private_phone` |
| `ADDRESS` | `BUILDINGNUM`, `STREET`, `CITY`, `ZIPCODE` | `LOCATION`, `COORDINATE`, `private_address` |
| `DATE` | `DATE` | `DATE_TIME`, `private_date` |
| `ID_NUMBER` | `IDCARDNUM`, `TAXNUM`, `SOCIALNUM`, `PASSPORTNUM`, `DRIVERLICENSENUM`, `CREDITCARDNUMBER` | `US_SSN`, `US_PASSPORT`, `US_DRIVER_LICENSE`, `US_ITIN`, `CREDIT_CARD`, `IBAN_CODE`, `US_BANK_NUMBER`, `US_LICENSE_PLATE`, `PASSWORD`, `account_number`, `secret` |
| `EXCLUDED_LABELS` *(audited default — pending CS1 sign-off)* | `AGE`, `GENDER`, `SEX`, `TITLE` | `AGE`, `HONORIFIC`, `TITLE`, `NRP`, `ORGANIZATION`, `URL`, `private_url`, `IP_ADDRESS`, `MAC_ADDRESS`, `IMEI`, `FINANCIAL` |

### Coordinate Space Invariant (Single Visual Frame)
- **Stored in DB & sent to FE / `VER-01` / `VER-02`:** `visual_rect = (x0, y0, x1, y1)` in **top-left `CropBox` points after `/Rotate`**, alongside `visual_width`, `visual_height`, and `rotation_deg`.
- **Converted inside `RED-03/04`:** `unrot_rect = visual_rect * page.derotation_matrix` before calling `page.add_redact_annot(...)`.
- **Converted inside `OCR-07`:** `unrot_quad = ocr_quad * (~M_deskew) * (~M_scale) * page.derotation_matrix`, then `visual_rect = (unrot_quad * page.rotation_matrix).rect`.

## Files to Create / Modify

- Create: `docs/architecture/system-design-contracts.md` (consolidated `CORE-01/02/03` + `QA-01` spec with worked 90°-rotated & multi-line examples)
- Create: `checkpoints/en_gravitee_25_label_space.json` (`span_class_names` for `GRAVITEE_25_LABELS`) <!-- Red-Team Fix: Finding 1 -->
- Create: `app/__init__.py`
- Create: `app/contracts/__init__.py`
- Create: `app/contracts/pii_taxonomy.py` (versioned taxonomy map, `CanonicalGroup`, `EXCLUDED_LABELS`, exhaustive `map_raw_label` raising on unknown label in tests)
- Create: `app/contracts/document_ir.py` (`PageClassification`, `PageQuality`, `TokenIR`, `PageIR`, `CanonicalEntity`, `RegionPayload`)
- Create: `app/contracts/geometry.py` (`VisualRect`, `UnrotRect`, OpenCV-to-PyMuPDF transposed deskew matrix builder, forward/inverse transforms, IoU & padding clamp)
- Create: `app/contracts/api.py` (FastAPI `/api/v1` request/response Pydantic schemas & error codes)
- Create: `app/db/__init__.py`
- Create: `app/db/models.py` (SQLAlchemy 2.0 ORM models including `jobs` with `max_attempts`, `lease_expires_at`, `attempt`, `idempotency_key`, `login_rate_limits`)
- Create: `alembic.ini`, `alembic/env.py`, `alembic/versions/0001_initial_schema.py`
- Create: `tests/test_phase01_contracts.py` (100% label coverage of `OPENPII_19_LABELS` + `GRAVITEE_25_LABELS`, geometry round-trip across 0°/90°/180°/270° + non-zero `CropBox` + deskew angles, Pydantic & registry checks)
- Modify: `config/model_registry.py` (add `taxonomy_version`, `source_type` handling for `package` vs `local`, real weight-file checks, `reload=True`) <!-- Red-Team Fix: Finding 1 -->
- Modify: `configs/models.json` (add `taxonomy_version` and EN `presidio_en_core_web_lg` package entry using `checkpoints/en_gravitee_25_label_space.json`; defer registering `en_rules_25` until Phase 3 creates `app/ml_service/rules/en_rules.py` so `ModelRegistry.verify_checkpoints()` stays green in Phase 1) <!-- Red-Team Fix: Finding 1 -->

## Implementation Steps

1. Draft `app/contracts/pii_taxonomy.py` with `TAXONOMY_VERSION = "1.0.0"`, `CanonicalGroup`, exhaustive VI-19 + EN-25 + OPF maps, and explicit `EXCLUDED_LABELS`. Verify 100% coverage in `tests/test_phase01_contracts.py` against `checkpoints/opf_vn_19_label_space.json` and `evaluation/metrics.py:GRAVITEE_25_LABELS`.
2. Implement `app/contracts/geometry.py` with exact PyMuPDF row-vector matrix helpers (`build_page_transforms`, `ocr_quad_to_visual_rect`, `visual_rect_to_unrot_rect`, `clamp_and_pad_rect`), explicitly transposing OpenCV's `cv2.getRotationMatrix2D` 2×2 block.
3. Implement `app/contracts/document_ir.py` and `app/contracts/api.py` enforcing strict bounds checks (`0 <= x0 < x1 <= visual_width`, non-empty `rects[]`, distinct `ocr_confidence` vs. `model_score`).
4. Define `app/db/models.py` and Alembic migration `0001_initial_schema.py` with:
   - `UNIQUE (document_id, revision_no)` on `review_revisions`
   - Partial unique index `CREATE UNIQUE INDEX uq_one_draft_per_doc ON review_revisions (document_id) WHERE status = 'DRAFT'` <!-- Red-Team Fix: Finding 8 -->
   - `deleted_at TIMESTAMP WITH TIME ZONE` tombstone on `documents`
   - Partial index on `jobs (status, available_at) WHERE status IN ('QUEUED', 'RUNNING')` for fast `SKIP LOCKED` claims
   - Partial unique index `CREATE UNIQUE INDEX uq_jobs_active_idempotency ON jobs (idempotency_key) WHERE status IN ('QUEUED', 'RUNNING', 'SUCCEEDED')` so failed/cancelled jobs can be retried cleanly <!-- Red-Team Fix: Finding 9 -->
   - `max_attempts INTEGER NOT NULL DEFAULT 3` on `jobs` for poison-pill dead-lettering <!-- Red-Team Fix: Finding 9 -->
5. Add `checkpoints/en_gravitee_25_label_space.json`, extend `config/model_registry.py`, and update `configs/models.json` while preserving `registry_version == "1.0.0"` and existing VI keys verified by `tests/test_ops01_environment.py`.
6. Write `docs/architecture/system-design-contracts.md` and `tests/test_phase01_contracts.py`.

## Todo

- [ ] Implement `app/contracts/pii_taxonomy.py` with 100% coverage of `OPENPII_19_LABELS` and `GRAVITEE_25_LABELS` and confirm `CORE-01` excluded-label policy with CS1
- [ ] Implement `app/contracts/geometry.py` with 0°/90°/180°/270° + non-zero `CropBox` + deskew round-trip tests
- [ ] Implement `app/contracts/document_ir.py` and `app/contracts/api.py`
- [ ] Implement `app/db/models.py` and Alembic migration `0001_initial_schema.py` with partial unique indexes and `max_attempts`
- [ ] Add `checkpoints/en_gravitee_25_label_space.json` and update `config/model_registry.py` + `configs/models.json`
- [ ] Write `docs/architecture/system-design-contracts.md` (`CORE-01/02/03` & `QA-01`)
- [ ] Run `pytest tests/test_phase01_contracts.py tests/test_ops01_environment.py` and verify zero regressions

## Risk Assessment & Load-Bearing Assumptions

| Load-Bearing Assumption | Observable Break Signal | Pre-Decided Response |
|---|---|---|
| Visual top-left `CropBox` frame aligns `FE` viewer, `pdfplumber`, and `pdftoppm -cropbox` within `<= 1.5 pt` | Round-trip test on `/MediaBox [0 0 612 792]` + `/CropBox [50 50 562 742]` + `/Rotate 90/270` exceeds `1.5 pt` | Fix affine sign/origin formula in `app/contracts/geometry.py` before Phase 3 begins; block downstream OCR/FE merge until green |
| CS1 approves `EXCLUDED_LABELS` default set | CS1 requires one or more excluded labels active under `CORE-01` | Move label from `EXCLUDED_LABELS` into `CanonicalGroup` map in `app/contracts/pii_taxonomy.py` and bump `TAXONOMY_VERSION`; zero schema migration needed |

## Verification & Success Criteria

```bash
python3 -m pytest tests/test_phase01_contracts.py tests/test_ops01_environment.py -v
ruff check app/ config/ tests/
```

- Every label in `OPENPII_19_LABELS` and `GRAVITEE_25_LABELS` is explicitly mapped or explicitly listed in `EXCLUDED_LABELS` (`0` silent drops).
- Geometry round-trip error across synthetic 0°/90°/180°/270° rotated, cropped, and ±5° deskewed test pages is `<= 1.5 pt`.
- `alembic upgrade head --sql` emits valid PostgreSQL DDL including `uq_one_draft_per_doc` and `uq_jobs_active_idempotency`.
