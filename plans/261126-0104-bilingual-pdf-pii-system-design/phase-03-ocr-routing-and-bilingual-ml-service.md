---
phase: 3
title: "Phase 3: Page-Level 3-Way Extraction, Bilingual OCR & Singleton ML-Service"
status: todo
priority: P1
effort: "2w"
dependencies: [1, 2]
---

# Phase 3: Page-Level 3-Way Extraction, Bilingual OCR & Singleton ML-Service

**Maps to backlog:** `OCR-01..09`, `ML-03`, `ML-06`, `ML-08`, `BE-06`
**Primary owners:** `SE3` (page classification, native extract, OCR, geometry, region mapping), `SE2` (`ml-service` serving & pipeline orchestration), `SE4` (production hybrid rules), `ML1` (model validation)

## Goal

Build the isolated document analysis pipeline — page-level 3-way routing (`NATIVE` / `SCANNED_FLATTENED` / `MIXED`), PyMuPDF native extraction, 300 DPI + deskew bilingual Tesseract 5 (`vie+eng`, `tessdata_best`) OCR, char-offset normalization — and the authenticated singleton `ml-service` performing VI/EN language routing, production-safe hybrid NER+rule detection, 6-group projection, and multi-line PDF region mapping.

## Context & Existing Code Reuse

- Trained checkpoints & rules verified in repo:
  - Vietnamese lightweight CPU NER: [checkpoints/spacy_vn_19_ner](../../checkpoints/spacy_vn_19_ner) (4.3 MB, 770 MB peak RAM, 4.6 ms/doc, `0.9803` char recall, `0.8488` exact F1 with rules, passes all 5 locked gates).
  - Vietnamese high-accuracy MoE NER (optional via `docker-compose.opf.yml`): [checkpoints/opf_vn_19](../../checkpoints/opf_vn_19) (2.7 GB, 4.09 GB peak RAM, 356 ms/doc grouped MoE CPU, `0.9867` char recall, `0.8973` exact F1 with rules).
  - Benchmark rule modules to **factor cleanly** (not import blindly): [evaluation/vn_rules.py](../../evaluation/vn_rules.py) and [evaluation/hybrid_rules.py](../../evaluation/hybrid_rules.py).
- Research evidence ([researcher-01-ocr-geometry.md](./research/researcher-01-ocr-geometry.md)): Tesseract 5 (`vie+eng`, `tessdata_best`) covers all 134+ Vietnamese diacritic forms natively at 50–150 MB RAM and 0.3–0.8 s/page without custom ONNX weight curation; stock RapidOCR Latin omits ~70 Vietnamese compound diacritics.

## Requirements

- [ ] **R3.1 (`OCR-01` Page Classifier):** Classify each page independently using `page.get_texttrace()` (`visible_chars` where `type != 3 and opacity > 0`; `invisible_chars` where `type == 3 or opacity == 0`) and `page.get_image_info(xrefs=True)` (placed raster coverage ratio and image pixel dimensions). Flag `has_untrusted_ocr_layer = True` whenever `invisible_chars > 0`.
- [ ] **R3.2 (`OCR-02` Native Extraction):** Call `pymupdf.TOOLS.set_small_glyph_heights(True)` before extracting characters/words (`page.get_text("rawdict", flags=TEXTFLAGS_RAWDICT & ~TEXT_PRESERVE_IMAGES)`), filtering out `type == 3` invisible spans via `get_texttrace()` alignment, decomposing ligatures via NFKC while preserving exact character-to-glyph rects, and converting bboxes to canonical visual `CropBox` coordinates.
- [ ] **R3.3 (`OCR-03`, `OCR-04`, `OCR-07` Scanned/Flattened Path):** Render `page.rect` at 300 DPI (clamping max dimension to 4096 px), estimate skew angle via `deskew` + OpenCV warp with expanded canvas, apply transposed `M_deskew` matrix, run concrete `TesseractOcrEngine` (`vie+eng`, `tessdata_best`, `OMP_THREAD_LIMIT=1`) returning word polygons + confidences, and project word boxes back to visual `CropBox` coordinates. *(No speculative RapidOCR stub or `OCR_BACKEND` flag in MVP — kept strictly as a contingency in Risk Assessment.)* <!-- Red-Team Fix: Finding 14a -->
- [ ] **R3.4 (`OCR-09` Mixed-Page Merge):** On `MIXED` pages, extract native visible text **and** crop/render qualifying embedded raster images (`page.get_image_info(xrefs=True)`) at `>= 300` effective DPI through `TesseractOcrEngine`, project image OCR boxes back through each image's placement `transform` + `page.rotation_matrix`, deduplicate against native tokens when `IoU >= 0.5` with normalized text similarity, and preserve `source: "native" | "ocr"`.
- [ ] **R3.5 (`OCR-05`, `OCR-06`, `OCR-08` & Tombstone-Safe Previews):** Reconstruct reading order across columns/blocks, normalize text while retaining exact `char_start..char_end -> token_ids[]` index, emit per-page safe raster preview PNG (`150 DPI` visual `CropBox`) **strictly into the job staging directory `./storage/temp/analyze_{job_id}/previews/page_{n}.png`** (never writing directly to `./storage/private/` from the subprocess!), and record `PageQuality` warnings (`LOW_OCR_CONFIDENCE`, `EMPTY_IMAGE_PAGE`, `OCR_TIMEOUT`). <!-- Red-Team Fix: Finding 7 -->
- [ ] **R3.6 (`ML-03`, `ML-06` Authenticated Singleton `ml-service` & Production Rules):** <!-- Red-Team Fix: Finding 3, Finding 4, Finding 14b -->
  - Dedicated FastAPI service (`app/ml_service/main.py`) protected by internal bearer token `ML_SERVICE_TOKEN` and loading pinned models once at startup (base default `lightweight_cpu`: `spacy_vn_19_ner` + EN Presidio/`en_core_web_lg` + production rules; optional `opf_high_ram` via `docker-compose.opf.yml`: `opf_vn_19` grouped-MoE + local EN OPF + production rules).
  - Factor clean production rule extractors into `app/ml_service/rules/` (removing benchmark-overfitted `is_structured_payload_doc()` neural-NER bypasses, `NON_PII_STRUCTURED_KEYS` name/token exclusions, `"Nghị"`/`"năm"` VN overfits, and `max(sc, 0.995)` score clobbering).
  - In `lightweight_cpu`, combine **all** Presidio spans (preserving `PERSON`, `LOCATION`, `PHONE_NUMBER`, `DATE_TIME`, `US_SSN`, `US_PASSPORT`, `US_DRIVER_LICENSE`, `US_ITIN`, etc.) with `extract_deterministic_spans()` + `merge_contiguous_locations()` via a single unified `app/ml_service/hybrid.py` combiner (validated rule > higher-confidence NER > safety-wider union, preserving raw uncalibrated scores).
  - Route per page/block by language (`langid` + Vietnamese diacritic cues; dual-run fallback on mixed VI+EN blocks) and project every span through Phase 1 `app/contracts/pii_taxonomy.py` into 6 canonical groups + `raw_label` metadata.
- [ ] **R3.7 (`ML-08`, `BE-06` Offset Mapping & Transactional Commit):** Map returned `(char_start, char_end)` spans strictly via `token_ids[]` into multi-line `rects[]` on the exact page (never `page.search_for()`), flagging unmappable spans as structured warnings. In `analyze_job.py`, acquire `SELECT id FROM documents WHERE id = :id FOR UPDATE` verifying `deleted_at IS NULL`, atomically move staged previews from `./storage/temp/analyze_{job_id}/previews/` into `./storage/private/previews/{doc_id}/`, persist `document_pages` + `detected_entities` + initial `review_revisions(revision_no=1)`, and purge `./storage/temp/analyze_{job_id}/` in `finally`. <!-- Red-Team Fix: Finding 7 -->

## Architecture & Data Flow

```text
Worker Analyze Subprocess (scrubbed env={}, psutil RSS watchdog, staging dir only):
  For each page p in staged input.pdf:
    1. Classify page via get_texttrace() + get_image_info(xrefs=True)
       -> NATIVE: PyMuPDF visible text + char/word rects (set_small_glyph_heights=True)
       -> SCANNED_FLATTENED: 300 DPI render -> deskew -> TesseractOcrEngine -> inverse M_deskew/M_scale
       -> MIXED: Native extract + embedded-image crop OCR -> IoU dedup
    2. Save safe preview PNG (150 DPI visual CropBox) to ./storage/temp/analyze_{job_id}/previews/
    3. Emit PageIR JSON (normalized text + char-offset-to-token index + PageQuality flags)
Worker Parent Process (holds DB + ML_SERVICE_TOKEN):
  4. Send page text blocks -> ml-service POST /v1/detect (Authorization: Bearer $ML_SERVICE_TOKEN)
  5. Map entity offsets -> token_ids -> merged line rects[] in visual CropBox space
  6. PG TX (SELECT ... FROM documents WHERE id=:id FOR UPDATE):
       if deleted_at IS NOT NULL -> abort & purge temp dir
       else -> atomic move previews to ./storage/private/previews/{doc_id}/ + commit DB rows
```

## Files to Create / Modify

- Create: `app/ocr/__init__.py`
- Create: `app/ocr/classifier.py` (`classify_page` using `get_texttrace()` + `get_image_info(xrefs=True)`)
- Create: `app/ocr/native_extractor.py` (PyMuPDF visible text + `set_small_glyph_heights(True)` + NFKC char-span rects)
- Create: `app/ocr/tesseract_engine.py` (concrete `TesseractOcrEngine` using `vie+eng` `tessdata_best`, `OMP_THREAD_LIMIT=1`) <!-- Red-Team Fix: Finding 14a -->
- Create: `app/ocr/scanned_extractor.py` (300 DPI render, `deskew` + OpenCV warp, transposed `M_deskew` inverse transform)
- Create: `app/ocr/mixed_merger.py` (embedded image crop OCR + IoU deduplication + provenance preservation)
- Create: `app/ocr/normalizer.py` (reading-order sort, offset-to-token index, `PageQuality` scorer, staged preview PNG generator)
- Create: `app/ocr/pipeline.py` (standalone subprocess entrypoint `python -m app.ocr.pipeline <input_pdf> <staging_dir>`)
- Create: `app/ml_service/__init__.py`
- Create: `app/ml_service/lang_router.py` (offline VI/EN/MIXED block language router using diacritic cues + `langid`)
- Create: `app/ml_service/rules/__init__.py`, `app/ml_service/rules/vi_rules.py`, `app/ml_service/rules/en_rules.py` (clean production regex/validator extractors factored from `evaluation/` without benchmark-overfitted bypasses/exclusions) <!-- Red-Team Fix: Finding 3 -->
- Create: `app/ml_service/detectors.py` (loaders for `spacy_vn_19_ner`, Presidio/`en_core_web_lg`, optional `opf_vn_19`/EN OPF)
- Create: `app/ml_service/hybrid.py` (profile-aware unified `ML-06` overlap resolver preserving raw NER scores + 6-group projection) <!-- Red-Team Fix: Finding 3 -->
- Create: `app/ml_service/main.py` (FastAPI `ml-service` with `ML_SERVICE_TOKEN` auth: `GET /health`, `POST /v1/detect` with sliding window)
- Create: `app/worker/analyze_job.py` (runs `app.ocr.pipeline` subprocess, calls `ml-service`, runs `ML-08` mapper, commits previews + DB under `SELECT ... FOR UPDATE`)
- Create: `tests/test_phase03_ocr_ml_pipeline.py` (3-way routing, stale `3 Tr` rejection, mixed-page dedup, VI/EN routing, English `PERSON`/`LOCATION`/`US_PASSPORT`/`US_ITIN` recall in `lightweight_cpu`, structured-prefix `"SELECT ..."` / `"{"` non-bypass test, raw-score preservation, multi-line offset mapping, staged preview cleanup on delete)

## Implementation Steps

1. Implement `app/ocr/` (`classifier.py`, `native_extractor.py`, `tesseract_engine.py`, `scanned_extractor.py`, `mixed_merger.py`, `normalizer.py`, `pipeline.py`) against Phase 1 contracts, staging all preview PNGs inside `<staging_dir>/previews/`.
2. Factor clean production rules into `app/ml_service/rules/` (keeping `evaluation/vn_rules.py` and `evaluation/hybrid_rules.py` intact so existing evaluation tests stay untouched), then implement `lang_router.py`, `detectors.py`, `hybrid.py`, and authenticated `main.py`.
3. Implement `app/worker/analyze_job.py` with transactional `SELECT ... FOR UPDATE` tombstone check before moving staged previews to `./storage/private/previews/{doc_id}/`, and register `ANALYZE` in `app/worker/runner.py`.
4. Write and run `tests/test_phase03_ocr_ml_pipeline.py`, verifying zero regression on `evaluation/test_evaluation.py` and `evaluation/test_vn_evaluation.py`.

## Todo

- [ ] Implement `app/ocr/classifier.py` and `native_extractor.py` (`OCR-01`, `OCR-02`)
- [ ] Implement `tesseract_engine.py`, `scanned_extractor.py`, `mixed_merger.py`, `normalizer.py`, and `pipeline.py` (`OCR-03..09`)
- [ ] Factor clean production rules in `app/ml_service/rules/` (removing benchmark bypasses/exclusions) and implement `lang_router.py`, `detectors.py`, `hybrid.py`, and authenticated `ml-service` (`ML-03`, `ML-06`)
- [ ] Implement `app/worker/analyze_job.py` with `ML-08` offset-to-region mapping and tombstone-locked staged preview promotion (`BE-06`)
- [ ] Run `pytest tests/test_phase03_ocr_ml_pipeline.py` including EN `PERSON`/`US_PASSPORT` `lightweight_cpu` recall and structured-prefix non-bypass tests

## Risk Assessment & Load-Bearing Assumptions

| Load-Bearing Assumption | Observable Break Signal | Pre-Decided Response |
|---|---|---|
| Tesseract 5 (`tessdata_best`, `vie+eng`) achieves acceptable diacritic CER on scanned VI fixtures | Phase 6 `DATA-04` scanned benchmark reports CER `> 5%` or missed PII tokens on noisy/tabular VI scans | Substitute `RapidOCR` + a verified 908-class Vietnamese ONNX recognizer (`vi_dict.txt`) inside `app/ocr/tesseract_engine.py` (replacing the OCR module cleanly without changing `scanned_extractor.py`) |
| Page/block language router accurately separates VI vs. EN text | Bilingual invoices route Vietnamese names to EN detector (or EN to VN, dropping F1 toward `0.35`) | Lower mixed-block threshold to trigger dual-detector pass whenever block contains both ASCII English phrases and Vietnamese diacritics |
| Optional `opf_high_ram` override fits in `ml-service` RAM on the target demo host | `ml-service` exceeds container memory limit (`exit 137`) | Run base `lightweight_cpu` profile (`spacy_vn_19_ner` + EN Presidio/spaCy + rules, ~2 GB total) |

## Verification & Success Criteria

```bash
python3 -m pytest tests/test_phase03_ocr_ml_pipeline.py tests/test_phase01_contracts.py -v
python3 -m pytest evaluation/test_evaluation.py evaluation/test_vn_evaluation.py -v
```

- 3-way classifier achieves 100% accuracy across native, scanned, invisible-`3 Tr`-OCR scanned, and mixed fixtures.
- `lightweight_cpu` English pipeline detects `PERSON`, `LOCATION`, `US_PASSPORT`, `US_DRIVER_LICENSE`, and `US_ITIN`, and does NOT skip neural NER on pages starting with `"SELECT "` or `"{"`.
- `ml-service` rejects requests lacking `Authorization: Bearer $ML_SERVICE_TOKEN` with `401`.
- Multi-line wrapped entities and repeated identical PII strings map to exact distinct PDF bounding boxes, and staged previews are never promoted if `deleted_at` is set.
