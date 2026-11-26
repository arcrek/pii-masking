# Research Report 02: Format-Preserving Destructive PDF Redaction & Independent Verification

**Date:** 2026-11-26 | **Target Runtime:** Python 3.12 (Linux)

## Executive Findings

1. **Redaction Engine (`pymupdf>=1.25.0,<2.0`):** Pinning `>=1.25.0` avoids the 1.24.x `#3751` Chromium/Preview invisible-content regression while retaining `#3257` out-of-box deletion fixes. Use `add_redact_annot(rect, text=None, fill=(0, 0, 0), cross_out=False)` + `apply_redactions(images=PDF_REDACT_IMAGE_PIXELS, graphics=PDF_REDACT_LINE_ART_REMOVE_IF_COVERED, text=PDF_REDACT_TEXT_REMOVE)`.
2. **Critical PyMuPDF Traps to Guard Against:**
   - **Shared Image XObjects / `/SMask` / `/Resources` / Form XObjects:** Detect via `page.get_images(full=True)` across all pages (`referencer > 0` signals Form XObject) and decouple via `doc.xref_copy(src, dst)` (source first, target second!) before `apply_redactions` so pixel mutation on Page A never corrupts Page B.
   - **Tight-line clipping:** Call `pymupdf.TOOLS.set_small_glyph_heights(True)` before char/span bbox extraction.
   - **Incomplete `doc.scrub()`:** Explicitly delete all page annotations/widgets, clear page keys (`AA`, `Thumb`, `PieceInfo`, `Metadata`, `B`, `StructParents`), handle hidden OCG streams before removing `/OCProperties` (removing `/OCProperties` alone makes hidden layers visible!), and purge catalog keys (`AcroForm`, `OCProperties`, `StructTreeRoot`, `MarkInfo`, `OpenAction`, `AA`, `PieceInfo`, `Metadata`, `Outlines`, `PageLabels`, `Collection`, `Names/EmbeddedFiles`, `Names/JavaScript`, `AF`).
   - **Clean Non-Incremental Save:** `doc.save(out, garbage=4, deflate=True, clean=True, incremental=False)` (never `linear=True`, removed in 1.24+).
3. **Zero-Shared-Code Independent Verification Engine:**
   - **Text Layer (`pdfplumber` + `pdfminer.six`):** Operates in visually rotated top-left `CropBox` space; inspect `page.chars` intersection (not `within_bbox`, which misses straddling chars) + NFKC target sweep.
   - **Visual & Raw Image Layer (`poppler-utils` via `subprocess` + Pillow + NumPy):** `pdftoppm -png -r 300 -cropbox` (assert inset redacted region solid black `<= 5` luminance delta) + `pdfimages -png` (verify underlying raster pixels actually blanked, not merely covered by a vector box).
   - **Structural & Forensics Layer (`pikepdf` + `qpdf`):** Verify `eof_count == 1`, `qpdf --check` exit `0`, empty `/Info`, zero forbidden catalog/page keys, deep `pdf.objects` walk for `/JavaScript`/`/JS`/`/Launch`/`/EmbeddedFile`/`/ActualText`/`/Alt`, and test-suite `qpdf --stream-data=uncompress --object-streams=disable` byte audit.
4. **12 Baseline Adversarial Acceptance Fixtures (`DATA-05`, expanded to 13 in Phase 6 with vector-outlined text/signature fixture #13):** Shared image across pages, shared `/SMask`, same image placed twice on one page, shared `/Resources`, nested/shared Form XObjects, `3 Tr` invisible OCR (aligned + shifted), ligatures & split `TJ` kerning, tight line spacing, non-zero `CropBox` + `90°/180°/270°` rotation, full hidden-data payload (incl. `/StructTreeRoot` & hidden OCG), multi-`%%EOF` incremental save, and fake black-box overlay negative self-test.
