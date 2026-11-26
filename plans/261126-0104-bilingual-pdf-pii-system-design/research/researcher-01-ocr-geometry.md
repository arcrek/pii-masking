# Research Report 01: Self-Hosted CPU Bilingual (VI+EN) OCR & PyMuPDF Coordinate Mapping

**Date:** 2026-11-26 | **Target Stack:** Python 3.12, FastAPI, PyMuPDF (`pymupdf>=1.25.0`), CPU-only Docker

## Ranked Recommendation

1. **Day-1 Offline Zero-Custom-Model Baseline:** **Tesseract 5 (`vie+eng`, `tessdata_best`) via `pytesseract`** — already present in `docker/Dockerfile` (`tesseract-ocr`, `tesseract-ocr-vie`, `tesseract-ocr-eng`), covers 100% of 134+ Vietnamese diacritic forms natively, ~50–150 MB RAM, ~0.3–0.8 s/page CPU at 300 DPI. Trade-off: degrades on noisy, skewed, or tabular scans.
2. **Noisy-Scan Upgrade Contingency (Post-Red-Team: Phase 6 contingency only, not Phase 3 MVP):** **`rapidocr` (v3.10.x + `onnxruntime`) with a Vietnamese-complete 908-class ONNX recognizer** (e.g., `PP-OCRv5` DBNet detector + fine-tuned VI ONNX recognizer + `vi_dict.txt`, ~200–500 MB RAM, ~0.8–2.0 s/page CPU).
   - **Critical Warning:** Stock upstream `latin_PP-OCRv5_mobile_rec` (838 classes) omits ~70 precomposed Vietnamese compound-diacritic characters (PaddleOCR issues #15189, #15204, #18254). Never ship stock `latin` RapidOCR/PaddleOCR for Vietnamese PII detection without substituting a Vietnamese-complete ONNX recognizer and dictionary.
3. **Rejected for CPU Docker Microservices:** Native `paddleocr` + `paddlepaddle` (1–2 GB+ RAM, MKL-DNN concurrency spikes, Python 3.12 PaddleX wheel friction).

## PyMuPDF Inspection & Geometry Rules

- **Invisible OCR (`3 Tr`) Detection:** Use `page.get_texttrace()` across all PyMuPDF 1.24–2.x versions (`span["type"] == 3 or span["opacity"] == 0.0`). On PyMuPDF 1.25+, `rawdict` also exposes `char_flags` where `(char_flags & 24) == 0` indicates invisible text.
- **Embedded Image Placement:** Use `page.get_image_info(xrefs=True)` (provides placed `bbox`, `transform` 6-tuple, `xref`, `width`, `height`, `xres`, `yres`).
- **Four Coordinate Spaces & Exact Inverse Math:**
  - PyMuPDF extraction & `add_redact_annot()` use **unrotated top-left `cropbox` space**; `page.rect` and `page.get_pixmap()` use **visually rotated top-left `cropbox` space**.
  - `page.rotation_matrix` maps unrotated -> visual; `page.derotation_matrix` maps visual -> unrotated.
  - **OpenCV Transpose Trap:** OpenCV `cv2.getRotationMatrix2D` uses column vectors while PyMuPDF `Matrix` uses row vectors — transpose the 2×2 block when constructing `M_deskew`.
  - Inverse from deskewed 300 DPI pixels to PyMuPDF unrotated space: `M_deskew_to_unrot = (~M_deskew) * (~M_scale) * page.derotation_matrix`.
- **Docker Thread Caps & Debian Bookworm libs:** Use `libgl1` (not removed `libgl1-mesa-glx`), `libglib2.0-0`, `libgomp1`, `opencv-python-headless`, and `OMP_NUM_THREADS=2`, `OMP_THREAD_LIMIT=1`.
- **License Note:** PyMuPDF is dual-licensed AGPL-3.0 / commercial Artifex license; verify deployment compatibility.
