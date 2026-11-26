---
phase: 5
title: "Phase 5: Format-Preserving Destructive Redaction & Independent Verification"
status: todo
priority: P1
effort: "2w"
dependencies: [1, 2, 3, 4]
---

# Phase 5: Format-Preserving Destructive Redaction & Independent Verification

**Maps to backlog:** `RED-01..07`, `VER-01..06`, `BE-10`
**Primary owners:** `SE4` + `CS1` (`RED-01..07`), `CS2` (`VER-01..06` — strictly independent codebase), `SE2` (`BE-10` atomic export orchestration)

## Goal

Implement format-preserving destructive PDF redaction (vector text & outlined-path removal, pixel zeroing, shared XObject decoupling, recursive hidden-data sanitization across all indirect objects, non-incremental save) and a completely independent zero-PyMuPDF Verification Engine (`pdfplumber` + `poppler-utils` + `pikepdf`/`qpdf` + native/scanned residual PII scan) enforced as a fail-closed gate before any export is downloadable.

## Context & Research Evidence

From [researcher-02-redaction-verification.md](./research/researcher-02-redaction-verification.md):
- Pin `pymupdf>=1.25.0,<2.0` to avoid the 1.24.x `#3751` Chromium/Preview invisible-content regression.
- `doc.scrub()` misses `/StructTreeRoot` (`/ActualText`/`/Alt`), `/OCProperties`, `/AcroForm` deletion, `/Outlines`, `/OpenAction`, `/AA`, `/PieceInfo`, non-link annotations, and **XObject-level `/Metadata`/`/PieceInfo`**, `/URI`, `/GoToR`, `/GoToE`, `/SubmitForm`, `/RichMedia`, `/XFA`, `/DSS`.
- Deleting `/OCProperties` without first removing hidden OCG streams makes previously hidden layers **visible**.
- Shared Image XObjects, shared `/SMask`s, shared `/Resources` dicts, and shared Form XObjects must be decoupled via `doc.xref_copy(src, dst)` before `apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)`.
- `VER-01..05` must share **zero** PyMuPDF code with `RED`.

## Requirements

- [ ] **R5.1 (`RED-01`, `RED-02`):** Validate locked `review_revision` exists, matches `document_id`, is `LOCKED`, and every region is finite within page bounds; apply configurable safety padding (default `1.0 pt` horizontal, `0.5 pt` vertical) clamped to `CropBox`, merging only overlapping/adjacent same-line regions.
- [ ] **R5.2 (`RED-03`, `RED-04` Destructive Vector, Outlined-Path & Pixel Redaction):** <!-- Red-Team Fix: Finding 6 -->
  - Convert stored visual `CropBox` rects to PyMuPDF unrotated coords (`rect * page.derotation_matrix`).
  - Before applying redactions, inspect `page.get_images(full=True)` across all pages to detect shared Image XObjects, shared `/SMask`, shared `/Resources` dicts, same-page multi-placement images, and shared Form XObjects (`referencer > 0`); clone & rebind affected xrefs via `doc.xref_copy(src, dst)`.
  - Check vector drawings (`page.get_drawings()`) intersecting redaction rects: use `PDF_REDACT_LINE_ART_REMOVE_IF_COVERED` when no non-gridline vector glyph/signature straddles the rect boundary, and switch to `PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED` (or safely raster-bake only the intersecting region/path) for manual signature/outlined-text boxes so zero vector PII survives underneath a black rectangle.
  - Apply `page.add_redact_annot(unrot_rect, text=None, fill=(0, 0, 0), cross_out=False)` followed by `page.apply_redactions(images=PDF_REDACT_IMAGE_PIXELS, graphics=..., text=PDF_REDACT_TEXT_REMOVE)`.
  - Strip invisible `3 Tr` spans overlapping redacted zones; fail closed (`UNSUPPORTED_PDF_STRUCTURE`) if Form XObject nesting exceeds depth 10 and cannot be verified.
- [ ] **R5.3 (`RED-05`, `RED-06`, `RED-07` Recursive Hidden-Data Sanitization & Clean Save):** <!-- Red-Team Fix: Finding 6 -->
  - Delete all remaining annotations and widgets on every page; clear page-level `/AA`, `/Thumb`, `/PieceInfo`, `/Metadata`, `/B`, `/StructParents`.
  - Handle hidden OCG layers safely before removing `/OCProperties`: strip off-by-default hidden OCG streams or fail closed (`UNSUPPORTED_OCG_STRUCTURE`) so deleting `/OCProperties` never reveals hidden layers.
  - Run `doc.scrub(...)`, `doc.set_metadata({})`, `doc.del_xml_metadata()`, `doc.set_toc([])`, purge catalog keys (`AcroForm`, `OCProperties`, `StructTreeRoot`, `MarkInfo`, `OpenAction`, `AA`, `PieceInfo`, `Metadata`, `Outlines`, `PageLabels`, `Collection`, `Names/EmbeddedFiles`, `Names/JavaScript`, `Names/AP`, `Names/Dests`, `Names/URLS`, `AF`, `DSS`, `XFA`), **and recursively strip `/Metadata`, `/PieceInfo`, `/URI`, `/GoToR`, `/GoToE`, `/SubmitForm`, `/RichMedia`, `/JavaScript`, `/JS`, `/Launch` across all indirect objects (including Image/Form XObjects and Fonts)**.
  - Save non-incrementally to `./storage/temp/export_{job_id}/redacted.pdf` with `garbage=4, deflate=True, clean=True, incremental=False`, compute SHA-256, and never mutate `./storage/private/originals/{doc_id}.pdf`.
- [ ] **R5.4 (`VER-01..05` Zero-Shared-Code Verification Engine — owned by `CS2`):** <!-- Red-Team Fix: Finding 6 -->
  - **Enforce module isolation:** `app/verification/` MUST NOT import `pymupdf` or `fitz` directly or transitively (keep `app/ocr/__init__.py` free of eager `pymupdf` imports so `TesseractOcrEngine` imports cleanly; verified by both an AST import lint test and a runtime `"pymupdf" not in sys.modules and "fitz" not in sys.modules` check).
  - **`VER-01` Text Check (`pdfplumber`/`pdfminer.six`):** Check `page.chars` intersection against every redacted `visual_rect` (catching boundary-straddling chars and `3 Tr` invisible OCR residue) + full-page NFKC sweep on unambiguous redacted targets.
  - **`VER-02` Visual, CTM-Mapped Raw Image & Re-OCR Check (`pdftoppm -png -r 300 -cropbox` + `pdfplumber`/`pikepdf` image placement CTMs + `pikepdf.PdfImage`/`pdfimages` + Pillow/NumPy + `TesseractOcrEngine`):** Verify inset rendered redacted regions are solid black (`max_abs_diff <= 5`); project each redacted `visual_rect` through each embedded image's independent `pdfplumber`/`pikepdf` placement CTM into exact raw image pixel coords to verify underlying raster bytes are zeroed; re-OCR redacted crops to confirm zero legible text.
  - **`VER-03` Structural & Forensics Check (`pikepdf` + `qpdf --check` + raw bytes):** Verify `eof_count == 1`, `qpdf --check` exit `0`, empty/absent `/Info`, zero forbidden catalog/page keys, deep `pdf.objects` walk confirming zero `/JavaScript`, `/JS`, `/Launch`, `/EmbeddedFile`, `/ActualText`, `/Alt`, `/Metadata`, `/PieceInfo`, `/URI`, `/GoToR`, `/GoToE`, `/SubmitForm`, `/RichMedia`, `/XFA`, `/DSS`, and verify zero non-redaction vector strokes survive inside manual/outlined-text redaction boxes.
  - **`VER-04` Integrity Check:** Verify output opens cleanly in `pikepdf` and `pdfplumber`, page count and visual page dimensions match original, and non-redacted sample text remains extractable within tolerance.
  - **`VER-05` Verdict Aggregator:** Emit PII-free `VerificationReport` (`PASS` | `FAIL` | `INCONCLUSIVE`) with per-check statuses and revision/pipeline/model versions; any mandatory `FAIL` or `INCONCLUSIVE` blocks publish.
- [ ] **R5.5 (`VER-06`, `BE-10` Bilingual Native+Scanned Residual Loop & Immutable-Revision Atomic Publish):** <!-- Red-Team Fix: Finding 8, Finding 9 -->
  - **Verdict precedence:** `VER-06` executes **only when `VER-01..05 == PASS`** (and `FAIL` strictly outranks `INCONCLUSIVE`), so a residual finding can never downgrade a hard redaction failure or create a new draft from a broken redaction.
  - In `app/verification/residual_check.py`, build an independent post-redaction text+offset stream using **both** `pdfplumber` native characters (with a `pdfplumber` char-offset-to-`visual_rect` mapper) **and** full-page post-redaction OCR from `VER-02`'s 300 DPI `pdftoppm` renders for `SCANNED_FLATTENED`/`MIXED` pages.
  - Call `ml-service` (`ML_SERVICE_TOKEN` authenticated) on post-redaction text; suppress candidates matching previously user-rejected regions via `page_no` + **`IoU >= 0.5`** (or center inclusion within `<= 6 pt` vertical tolerance to absorb PyMuPDF-vs-`pdfplumber` glyph-height differences) + **normalized SHA-256 text hash** (never storing raw PII).
  - If **any new unreviewed candidate** is found, **never mutate the `LOCKED` revision back to `DRAFT`**: acquire `SELECT id FROM documents WHERE id = :id FOR UPDATE`, abort cleanly if a newer `revision_no` already exists, otherwise transition the `LOCKED` revision to `SUPERSEDED`, insert a new `DRAFT` revision (`revision_no + 1`, honoring `uq_one_draft_per_doc`) cloning prior regions + appending new residual candidates, mark verification `INCONCLUSIVE`, and discard the temp PDF.
  - Only when `VER-01..05 == PASS` and `VER-06` yields 0 new candidates, acquire `SELECT id FROM documents WHERE id = :id FOR UPDATE`, confirm `deleted_at IS NULL` and `review_revisions.id` is still latest `LOCKED`, atomically move `./storage/temp/export_{job_id}/redacted.pdf` into `./storage/private/exports/{artifact_id}.pdf`, record `export_artifacts`, and enable `GET /api/v1/documents/{id}/exports/{artifact_id}/download`. Export idempotency uses Phase 1's partial unique index (`uq_jobs_active_idempotency`), allowing retries after transient failures.

## Architecture & Module Boundary

```text
app/redaction/  (SE4 + CS1, runs in isolated subprocess, uses pymupdf>=1.25.0)
  -> reads staged copy of immutable original + locked ReviewRevision
  -> writes ./storage/temp/export_{job_id}/redacted.pdf

app/verification/  (CS2, runs in isolated subprocess, FORBIDDEN from importing pymupdf/fitz!)
  -> Layer 1: pdfplumber / pdfminer.six (char intersection + char-offset mapper)
  -> Layer 2: pdftoppm (-cropbox -r 300) + pikepdf/pdfplumber image CTM raw-pixel check + Tesseract re-OCR
  -> Layer 3: pikepdf deep object walk + qpdf --check + raw %%EOF == 1
  -> Layer 4 (parent calls ml-service): VER-06 native + scanned residual scan with IoU+hash rejection filter

app/worker/export_job.py  (SE2, BE-10)
  -> PG TX (SELECT ... FROM documents WHERE id=:id FOR UPDATE):
       - PASS + not deleted + still latest LOCKED -> atomic move to ./storage/private/exports/
       - New VER-06 residual -> mark LOCKED -> SUPERSEDED, insert DRAFT (revision_no + 1), unlink temp
       - FAIL / INCONCLUSIVE / deleted / stale -> unlink temp, never publish
```

## Files to Create / Modify

- Create: `app/redaction/__init__.py`
- Create: `app/redaction/validator.py` (`RED-01`, `RED-02` snapshot validation, clamping, safe same-line merge + padding)
- Create: `app/redaction/xobject_decoupler.py` (`RED-04` shared Image XObject, `/SMask`, `/Resources`, Form XObject detection & `xref_copy` decoupling)
- Create: `app/redaction/sanitizer.py` (`RED-05` hidden OCG handling, annotations/widgets removal, `doc.scrub`, recursive indirect-object `/Metadata`/`/PieceInfo`/active-key purge) <!-- Red-Team Fix: Finding 6 -->
- Create: `app/redaction/engine.py` (`RED-03`, `RED-04`, `RED-06`, `RED-07` standalone subprocess entrypoint `python -m app.redaction.engine`)
- Create: `app/verification/__init__.py`
- Create: `app/verification/text_check.py` (`VER-01` `pdfplumber`/`pdfminer.six` char-intersection & invisible text leak check + char-offset mapper)
- Create: `app/verification/image_check.py` (`VER-02` `pdftoppm -cropbox`, CTM-mapped `pikepdf.PdfImage`/`pdfimages` raw pixel check, NumPy solid-black check, crop & full-page re-OCR) <!-- Red-Team Fix: Finding 6, Finding 8 -->
- Create: `app/verification/structure_check.py` (`VER-03` `pikepdf` deep object walk with expanded forbidden keys, `qpdf --check`, `%%EOF == 1`) <!-- Red-Team Fix: Finding 6 -->
- Create: `app/verification/integrity_check.py` (`VER-04` page count, geometry & non-redacted preservation)
- Create: `app/verification/residual_check.py` (`VER-06` native + scanned post-redaction offset mapper & IoU+SHA-256 rejected-candidate filter) <!-- Red-Team Fix: Finding 8 -->
- Create: `app/verification/engine.py` (`VER-05` standalone subprocess entrypoint `python -m app.verification.engine`)
- Create: `app/worker/export_job.py` (`BE-10` orchestrating `RED` subprocess -> `VER` subprocess -> `VER-06` -> transactional `SELECT ... FOR UPDATE` publish / `SUPERSEDED`+new-`DRAFT` creation)
- Create: `app/api/routes/exports.py` (`POST /documents/{id}/exports`, `GET /documents/{id}/exports/{artifact_id}`, `GET /documents/{id}/exports/{artifact_id}/download`, `GET /documents/{id}/verification`)
- Modify: `app/worker/runner.py` and `app/main.py` (register `REDACT_VERIFY` job handler and `exports` router)
- Create: `tests/test_phase05_redaction_verification.py` (AST isolation lint asserting zero `pymupdf`/`fitz` imports in `app/verification/`, fake-overlay negative test, `VER-06` native+scanned residual test confirming immutable `LOCKED -> SUPERSEDED` + `revision_no + 1` and zero infinite loop on rejected items with 3 pt bbox drift, export retry after transient failure, atomic publish tombstone test)

## Implementation Steps

1. Implement `app/redaction/` (`validator.py`, `xobject_decoupler.py`, `sanitizer.py`, `engine.py`) with strict `pymupdf>=1.25.0`, outlined-vector-path protection, recursive XObject metadata purge, and `incremental=False, garbage=4, deflate=True, clean=True`.
2. Implement zero-PyMuPDF `app/verification/` (`text_check.py`, `image_check.py` with CTM-mapped raw image pixel check, `structure_check.py` with expanded forbidden keys, `integrity_check.py`, `residual_check.py` with native+scanned offset mapping and IoU+hash rejection filter, `engine.py`).
3. Implement `app/worker/export_job.py` and `app/api/routes/exports.py` enforcing `SELECT ... FOR UPDATE` on `documents`, immutable `LOCKED -> SUPERSEDED` + new `DRAFT` on residual detections, partial-unique retryable export idempotency, and `finally` temp cleanup.
4. Write and run `tests/test_phase05_redaction_verification.py`.

## Todo

- [ ] Implement `app/redaction/validator.py` and `xobject_decoupler.py` (`RED-01`, `RED-02`, `RED-04`)
- [ ] Implement `app/redaction/sanitizer.py` (recursive indirect-object purge + hidden OCG handling) and `engine.py` (`RED-03`, `RED-05`, `RED-06`, `RED-07`)
- [ ] Implement zero-PyMuPDF `app/verification/` layers including CTM-mapped raw image pixel checks and native+scanned `VER-06` (`VER-01..06`)
- [ ] Implement `app/worker/export_job.py` (immutable `SUPERSEDED`+new-`DRAFT`, atomic tombstone publish) and `app/api/routes/exports.py` (`BE-10`)
- [ ] Run `tests/test_phase05_redaction_verification.py` and confirm zero import coupling between `RED` and `VER`

## Security Considerations

- Temp export directories (`./storage/temp/export_{job_id}/`) are unlinked in a `finally` block whenever verification fails, times out, or encounters a stale revision / deletion tombstone.
- Never store leaked plaintext strings in `VerificationReport` JSON or logs; store only page number, region ID, check code, leak count, and SHA-256 text hashes (`BE-12`).
- Fail closed (`UNSUPPORTED_PDF_STRUCTURE` / `UNSUPPORTED_OCG_STRUCTURE`) on PDFs whose hidden OCGs or >10-level nested Form XObjects cannot be safely verified.

## Risk Assessment & Load-Bearing Assumptions

| Load-Bearing Assumption | Observable Break Signal | Pre-Decided Response |
|---|---|---|
| Hidden OCG layers can be stripped without revealing hidden content when `/OCProperties` is removed | Adversarial OCG fixture leaks hidden layer text onto rendered page after sanitization | Strip hidden OCG content streams via MuPDF OCG visibility API before purging `/OCProperties`, or fail closed with `UNSUPPORTED_OCG_STRUCTURE` per CS1 policy |
| Same-page duplicate Image XObject placements can be decoupled cleanly | Fixture with 1 image drawn twice on Page 1 corrupts unredacted instance | Rewrite content-stream `Do` operator to cloned XObject name, or rasterize only that image placement safely |
| `VER-02` `pdfplumber`/`pikepdf` image CTM matches PyMuPDF placement on rotated/cropped pages | CTM pixel projection drifts >2 px on `/Rotate 90` + non-zero `/CropBox` fixture | Unit-test `pikepdf` CTM-to-visual-rect projection directly against `tests/test_phase01_contracts.py` geometry fixtures before Phase 6 |

## Verification & Success Criteria

```bash
python3 -m pytest tests/test_phase05_redaction_verification.py -v
```

- AST import check confirms `0` imports of `pymupdf` or `fitz` under `app/verification/`.
- Fake black-rectangle overlay fixture is caught and marked `FAIL` by both `VER-01` and `VER-02`.
- Real destructive redaction passes `VER-01..05` (`PASS`) while keeping non-redacted native text extractable in `pdfplumber`.
- Residual PII loop (`VER-06`) detects unredacted PII on both native and scanned pages, transitions `LOCKED -> SUPERSEDED` + creates `revision_no + 1` `DRAFT` (never mutating `LOCKED`), and does NOT loop on previously rejected candidates with <=5 pt bbox drift.
- Retrying an export after a simulated transient failure succeeds cleanly without `UniqueViolation`.
