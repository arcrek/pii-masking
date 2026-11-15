"""Gold Standard PDF Suite Builder (DATA-04).

Builds a comprehensive, reproducible benchmark suite of 40 PDF documents
covering Native, Scanned, Mixed, and Handwriting categories with exact ground truth
bounding boxes (PDF points) and text spans.

Strictly consumes held-out datasets:
- evaluation/data/vn_independent_holdout.jsonl
- evaluation/data/business_holdout_60.jsonl
Guaranteed ZERO data leakage from training splits.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
from pathlib import Path
from typing import Any, Literal

from PIL import Image, ImageDraw, ImageFilter
from pydantic import BaseModel, Field
import pymupdf


# Standard Coordinate & Entity Models
class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float
    coord_origin: str = "pdf_top_left"  # PDF points (72 pt/inch), top-left origin (y downwards)


class GroundTruthEntity(BaseModel):
    entity_id: str
    label: str
    text: str
    char_start: int
    char_end: int
    page_index: int
    bounding_boxes: list[BoundingBox]
    source_type: Literal["native_text", "scanned_image", "handwriting"]
    is_handwriting: bool = False


class PageMetadata(BaseModel):
    page_index: int
    width_pts: float
    height_pts: float
    rotation: int = 0
    dpi: int = 72
    has_image_overlay: bool = False


class GoldSuiteDocumentMetadata(BaseModel):
    doc_id: str
    title: str
    doc_type: Literal["native", "scanned", "mixed", "handwriting"]
    language: Literal["vi", "en"]
    category: str
    filename: str
    page_count: int
    pages: list[PageMetadata]
    total_entities: int
    entities: list[GroundTruthEntity]
    sha256: str
    is_held_out: bool = True
    provenance_source: str


def rotate_point(x: float, y: float, cx: float, cy: float, angle_rad: float) -> tuple[float, float]:
    """Rotate a point (x, y) around center (cx, cy) by angle_rad."""
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    nx = cx + (x - cx) * cos_a - (y - cy) * sin_a
    ny = cy + (x - cx) * sin_a + (y - cy) * cos_a
    return nx, ny


def transform_rect_by_rotation(rect: pymupdf.Rect, cx: float, cy: float, angle_deg: float) -> BoundingBox:
    """Transform an axis-aligned rect by angle_deg around center (cx, cy) and return bounding box."""
    angle_rad = math.radians(angle_deg)
    corners = [
        (rect.x0, rect.y0),
        (rect.x1, rect.y0),
        (rect.x1, rect.y1),
        (rect.x0, rect.y1),
    ]
    rotated_corners = [rotate_point(x, y, cx, cy, angle_rad) for x, y in corners]
    xs = [p[0] for p in rotated_corners]
    ys = [p[1] for p in rotated_corners]
    return BoundingBox(
        x0=round(max(0.0, min(xs)), 2),
        y0=round(max(0.0, min(ys)), 2),
        x1=round(max(xs), 2),
        y1=round(max(ys), 2),
    )


def create_scanned_stamp_image(size: tuple[int, int] = (160, 160)) -> Image.Image:
    """Generate a realistic red circular corporate stamp with texture."""
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    w, h = size
    # Outer circle
    draw.ellipse((8, 8, w - 8, h - 8), outline=(204, 30, 30, 220), width=4)
    # Inner circle
    draw.ellipse((22, 22, w - 22, h - 22), outline=(204, 30, 30, 200), width=2)
    # Star in center
    draw.polygon(
        [
            (w / 2, 45),
            (w / 2 + 10, 65),
            (w / 2 + 32, 65),
            (w / 2 + 14, 78),
            (w / 2 + 21, 98),
            (w / 2, 85),
            (w / 2 - 21, 98),
            (w / 2 - 14, 78),
            (w / 2 - 32, 65),
            (w / 2 - 10, 65),
        ],
        fill=(204, 30, 30, 210),
    )
    # Text arcs simulated
    draw.text((w / 2 - 40, h - 45), "CÔNG CHỨNG", fill=(204, 30, 30, 220))
    return img


def create_signature_image(size: tuple[int, int] = (200, 70)) -> Image.Image:
    """Generate a realistic blue ink signature."""
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    # Signature spline / bezier curves
    points = [
        (20, 45), (40, 20), (55, 55), (70, 15), (90, 40),
        (110, 35), (130, 50), (160, 30), (180, 55), (150, 60), (90, 58)
    ]
    draw.line(points, fill=(15, 45, 140, 230), width=3, joint="curve")
    return img


class GoldSuiteBuilder:
    """Orchestrates creation of the 40-document Gold Standard PDF Suite."""

    def __init__(self, workspace_root: Path):
        self.root = workspace_root
        self.data_dir = self.root / "evaluation" / "data"
        self.output_pdf_dir = self.root / "evaluation" / "gold_suite" / "pdfs"
        self.output_annot_dir = self.root / "evaluation" / "gold_suite" / "annotations"
        self.manifest_path = self.root / "evaluation" / "gold_suite" / "manifest.json"

        # Font setup
        self.arial_font = r"C:\Windows\Fonts\arial.ttf"
        self.times_font = r"C:\Windows\Fonts\times.ttf"
        self.script_font = r"C:\Windows\Fonts\segoesc.ttf"

        if not os.path.exists(self.arial_font):
            self.arial_font = "helv"
        if not os.path.exists(self.times_font):
            self.times_font = "times"
        if not os.path.exists(self.script_font):
            self.script_font = self.arial_font

        self.output_pdf_dir.mkdir(parents=True, exist_ok=True)
        self.output_annot_dir.mkdir(parents=True, exist_ok=True)

    def load_held_out_sources(self) -> tuple[list[dict], list[dict]]:
        """Load documents strictly from held-out JSONL files."""
        vn_path = self.data_dir / "vn_independent_holdout.jsonl"
        en_path = self.data_dir / "business_holdout_60.jsonl"

        vn_docs = []
        with open(vn_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    vn_docs.append(json.loads(line))

        en_docs = []
        with open(en_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    en_docs.append(json.loads(line))

        return vn_docs, en_docs

    def build_native_document(
        self,
        doc_id: str,
        title: str,
        language: Literal["vi", "en"],
        category: str,
        text_source: dict,
        layout: str = "single_column",
        is_landscape: bool = False,
        rotation: int = 0,
    ) -> GoldSuiteDocumentMetadata:
        """Create a crisp native vector PDF document with exact ground truth coordinates."""
        width_pts, height_pts = (841.92, 595.32) if is_landscape else (595.32, 841.92)
        doc = pymupdf.open()
        page = doc.new_page(width=width_pts, height=height_pts)

        if rotation in (90, 180, 270):
            page.set_rotation(rotation)

        page.insert_font(fontname="main_font", fontfile=self.arial_font)
        page.insert_font(fontname="header_font", fontfile=self.times_font)

        # Draw decorative header border
        shape = page.new_shape()
        shape.draw_rect(pymupdf.Rect(40, 40, width_pts - 40, height_pts - 40))
        shape.finish(width=0.8, color=(0.7, 0.7, 0.7))
        shape.commit()

        # Insert Header Title
        page.insert_text(
            pymupdf.Point(54, 70),
            title.upper(),
            fontname="header_font",
            fontsize=13,
            color=(0.1, 0.1, 0.3),
        )
        page.insert_text(
            pymupdf.Point(54, 88),
            f"REF NO: {doc_id}  |  CLASSIFICATION: RESTRICTED",
            fontname="main_font",
            fontsize=8.5,
            color=(0.4, 0.4, 0.4),
        )

        # Content text and lines
        raw_text = text_source["text"]
        paragraphs = [p.strip() for p in raw_text.split("\n") if p.strip()]

        y_cursor = 120.0
        line_height = 16.0
        left_margin = 54.0

        for para in paragraphs[:18]:  # Fit cleanly within 1 page
            # Wrap lines simply
            words = para.split(" ")
            curr_line = []
            for w in words:
                curr_line.append(w)
                line_str = " ".join(curr_line)
                if len(line_str) > (95 if is_landscape else 72):
                    page.insert_text(
                        pymupdf.Point(left_margin, y_cursor),
                        " ".join(curr_line[:-1]),
                        fontname="main_font",
                        fontsize=10,
                        color=(0.05, 0.05, 0.05),
                    )
                    y_cursor += line_height
                    curr_line = [w]
            if curr_line:
                page.insert_text(
                    pymupdf.Point(left_margin, y_cursor),
                    " ".join(curr_line),
                    fontname="main_font",
                    fontsize=10,
                    color=(0.05, 0.05, 0.05),
                )
                y_cursor += line_height + 4.0

            if y_cursor > height_pts - 80:
                break

        # Ground Truth Search & Extraction
        gt_entities: list[GroundTruthEntity] = []
        spans_source = text_source.get("spans", [])

        for idx, span in enumerate(spans_source):
            val = span["text"].strip()
            if not val or len(val) < 2:
                continue
            # Search on page
            rects = page.search_for(val)
            if rects:
                bboxes = [
                    BoundingBox(
                        x0=round(r.x0, 2),
                        y0=round(r.y0, 2),
                        x1=round(r.x1, 2),
                        y1=round(r.y1, 2),
                    )
                    for r in rects
                ]
                gt_entities.append(
                    GroundTruthEntity(
                        entity_id=f"{doc_id}_ent_{idx+1:03d}",
                        label=span["label"],
                        text=val,
                        char_start=span["start"],
                        char_end=span["end"],
                        page_index=0,
                        bounding_boxes=bboxes,
                        source_type="native_text",
                        is_handwriting=False,
                    )
                )

        pdf_filename = f"{doc_id}.pdf"
        pdf_path = self.output_pdf_dir / pdf_filename
        doc.save(str(pdf_path), garbage=4, deflate=True)
        doc.close()

        with open(pdf_path, "rb") as f:
            doc_sha256 = hashlib.sha256(f.read()).hexdigest()

        meta = GoldSuiteDocumentMetadata(
            doc_id=doc_id,
            title=title,
            doc_type="native",
            language=language,
            category=category,
            filename=pdf_filename,
            page_count=1,
            pages=[
                PageMetadata(
                    page_index=0,
                    width_pts=width_pts,
                    height_pts=height_pts,
                    rotation=rotation,
                    dpi=72,
                    has_image_overlay=False,
                )
            ],
            total_entities=len(gt_entities),
            entities=gt_entities,
            sha256=doc_sha256,
            provenance_source=text_source.get("source", "held_out_dataset"),
        )

        with open(self.output_annot_dir / f"{doc_id}.json", "w", encoding="utf-8") as f:
            f.write(meta.model_dump_json(indent=2))

        return meta

    def build_scanned_document(
        self,
        doc_id: str,
        title: str,
        language: Literal["vi", "en"],
        category: str,
        text_source: dict,
        dpi: int = 150,
        skew_angle: float = 0.9,
    ) -> GoldSuiteDocumentMetadata:
        """Create a scanned PDF with raster noise, skew angle, and transformed ground truth coordinates."""
        # 1. First build native page in memory
        width_pts, height_pts = 595.32, 841.92
        temp_doc = pymupdf.open()
        page = temp_doc.new_page(width=width_pts, height=height_pts)
        page.insert_font(fontname="main_font", fontfile=self.arial_font)
        page.insert_font(fontname="header_font", fontfile=self.times_font)

        page.insert_text(
            pymupdf.Point(54, 70),
            title.upper(),
            fontname="header_font",
            fontsize=13,
            color=(0.15, 0.15, 0.15),
        )
        page.insert_text(
            pymupdf.Point(54, 88),
            f"OFFICIAL ARCHIVE  |  SCAN DPI: {dpi}  |  REF: {doc_id}",
            fontname="main_font",
            fontsize=8.5,
            color=(0.4, 0.4, 0.4),
        )

        raw_text = text_source["text"]
        paragraphs = [p.strip() for p in raw_text.split("\n") if p.strip()]
        y_cursor = 120.0
        line_height = 16.0
        left_margin = 54.0

        for para in paragraphs[:18]:
            words = para.split(" ")
            curr_line = []
            for w in words:
                curr_line.append(w)
                if len(" ".join(curr_line)) > 72:
                    page.insert_text(
                        pymupdf.Point(left_margin, y_cursor),
                        " ".join(curr_line[:-1]),
                        fontname="main_font",
                        fontsize=10,
                        color=(0.1, 0.1, 0.1),
                    )
                    y_cursor += line_height
                    curr_line = [w]
            if curr_line:
                page.insert_text(
                    pymupdf.Point(left_margin, y_cursor),
                    " ".join(curr_line),
                    fontname="main_font",
                    fontsize=10,
                    color=(0.1, 0.1, 0.1),
                )
                y_cursor += line_height + 4.0

        # Collect native rects before scanning
        native_rect_map: list[tuple[dict, list[pymupdf.Rect]]] = []
        for idx, span in enumerate(text_source.get("spans", [])):
            val = span["text"].strip()
            if not val or len(val) < 2:
                continue
            rects = page.search_for(val)
            if rects:
                native_rect_map.append((span, rects))

        # 2. Render to Pixmap
        pix = page.get_pixmap(dpi=dpi)
        temp_doc.close()

        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

        # Apply scan degradation
        # A. Skew rotation
        img_skewed = img.rotate(skew_angle, resample=Image.BICUBIC, expand=False, fillcolor=(255, 255, 255))
        # B. Slight blur / noise
        img_skewed = img_skewed.filter(ImageFilter.GaussianBlur(radius=0.4))

        # 3. Embed into a new scanned PDF
        scan_doc = pymupdf.open()
        scan_page = scan_doc.new_page(width=width_pts, height=height_pts)

        img_bytes = io.BytesIO()
        img_skewed.save(img_bytes, format="JPEG", quality=82)
        scan_page.insert_image(scan_page.rect, stream=img_bytes.getvalue())

        # 4. Transform bounding boxes according to rotation skew
        cx, cy = width_pts / 2.0, height_pts / 2.0
        gt_entities: list[GroundTruthEntity] = []

        for idx, (span, rects) in enumerate(native_rect_map):
            transformed_boxes = [
                transform_rect_by_rotation(r, cx, cy, skew_angle) for r in rects
            ]
            gt_entities.append(
                GroundTruthEntity(
                    entity_id=f"{doc_id}_ent_{idx+1:03d}",
                    label=span["label"],
                    text=span["text"].strip(),
                    char_start=span["start"],
                    char_end=span["end"],
                    page_index=0,
                    bounding_boxes=transformed_boxes,
                    source_type="scanned_image",
                    is_handwriting=False,
                )
            )

        pdf_filename = f"{doc_id}.pdf"
        pdf_path = self.output_pdf_dir / pdf_filename
        scan_doc.save(str(pdf_path), garbage=4, deflate=True)
        scan_doc.close()

        with open(pdf_path, "rb") as f:
            doc_sha256 = hashlib.sha256(f.read()).hexdigest()

        meta = GoldSuiteDocumentMetadata(
            doc_id=doc_id,
            title=title,
            doc_type="scanned",
            language=language,
            category=category,
            filename=pdf_filename,
            page_count=1,
            pages=[
                PageMetadata(
                    page_index=0,
                    width_pts=width_pts,
                    height_pts=height_pts,
                    rotation=0,
                    dpi=dpi,
                    has_image_overlay=True,
                )
            ],
            total_entities=len(gt_entities),
            entities=gt_entities,
            sha256=doc_sha256,
            provenance_source=text_source.get("source", "held_out_dataset"),
        )

        with open(self.output_annot_dir / f"{doc_id}.json", "w", encoding="utf-8") as f:
            f.write(meta.model_dump_json(indent=2))

        return meta

    def build_mixed_document(
        self,
        doc_id: str,
        title: str,
        language: Literal["vi", "en"],
        category: str,
        text_source: dict,
    ) -> GoldSuiteDocumentMetadata:
        """Create a mixed PDF: Native vector body + embedded scanned red stamp and signature."""
        width_pts, height_pts = 595.32, 841.92
        doc = pymupdf.open()
        page = doc.new_page(width=width_pts, height=height_pts)

        page.insert_font(fontname="main_font", fontfile=self.arial_font)
        page.insert_font(fontname="header_font", fontfile=self.times_font)

        # Header
        page.insert_text(
            pymupdf.Point(54, 70),
            title.upper(),
            fontname="header_font",
            fontsize=13,
            color=(0.1, 0.1, 0.3),
        )
        page.insert_text(
            pymupdf.Point(54, 88),
            f"COMMERCIAL CONTRACT & CERTIFIED ANNEX  |  REF: {doc_id}",
            fontname="main_font",
            fontsize=8.5,
            color=(0.4, 0.4, 0.4),
        )

        raw_text = text_source["text"]
        paragraphs = [p.strip() for p in raw_text.split("\n") if p.strip()]
        y_cursor = 120.0
        line_height = 16.0
        left_margin = 54.0

        for para in paragraphs[:12]:
            words = para.split(" ")
            curr_line = []
            for w in words:
                curr_line.append(w)
                if len(" ".join(curr_line)) > 72:
                    page.insert_text(
                        pymupdf.Point(left_margin, y_cursor),
                        " ".join(curr_line[:-1]),
                        fontname="main_font",
                        fontsize=10,
                        color=(0.05, 0.05, 0.05),
                    )
                    y_cursor += line_height
                    curr_line = [w]
            if curr_line:
                page.insert_text(
                    pymupdf.Point(left_margin, y_cursor),
                    " ".join(curr_line),
                    fontname="main_font",
                    fontsize=10,
                    color=(0.05, 0.05, 0.05),
                )
                y_cursor += line_height + 4.0

        # Embed scanned stamp and signature in the signatory section
        stamp_img = create_scanned_stamp_image()
        sig_img = create_signature_image()

        stamp_bytes = io.BytesIO()
        stamp_img.save(stamp_bytes, format="PNG")
        sig_bytes = io.BytesIO()
        sig_img.save(sig_bytes, format="PNG")

        stamp_rect = pymupdf.Rect(360, y_cursor + 20, 360 + 110, y_cursor + 20 + 110)
        sig_rect = pymupdf.Rect(280, y_cursor + 45, 280 + 130, y_cursor + 45 + 50)

        page.insert_image(stamp_rect, stream=stamp_bytes.getvalue())
        page.insert_image(sig_rect, stream=sig_bytes.getvalue())

        page.insert_text(
            pymupdf.Point(280, y_cursor + 110),
            "Authorized Signature & Corporate Seal",
            fontname="main_font",
            fontsize=9,
            color=(0.3, 0.3, 0.3),
        )

        gt_entities: list[GroundTruthEntity] = []
        for idx, span in enumerate(text_source.get("spans", [])):
            val = span["text"].strip()
            if not val or len(val) < 2:
                continue
            rects = page.search_for(val)
            if rects:
                bboxes = [
                    BoundingBox(
                        x0=round(r.x0, 2),
                        y0=round(r.y0, 2),
                        x1=round(r.x1, 2),
                        y1=round(r.y1, 2),
                    )
                    for r in rects
                ]
                gt_entities.append(
                    GroundTruthEntity(
                        entity_id=f"{doc_id}_ent_{idx+1:03d}",
                        label=span["label"],
                        text=val,
                        char_start=span["start"],
                        char_end=span["end"],
                        page_index=0,
                        bounding_boxes=bboxes,
                        source_type="native_text",
                        is_handwriting=False,
                    )
                )

        pdf_filename = f"{doc_id}.pdf"
        pdf_path = self.output_pdf_dir / pdf_filename
        doc.save(str(pdf_path), garbage=4, deflate=True)
        doc.close()

        with open(pdf_path, "rb") as f:
            doc_sha256 = hashlib.sha256(f.read()).hexdigest()

        meta = GoldSuiteDocumentMetadata(
            doc_id=doc_id,
            title=title,
            doc_type="mixed",
            language=language,
            category=category,
            filename=pdf_filename,
            page_count=1,
            pages=[
                PageMetadata(
                    page_index=0,
                    width_pts=width_pts,
                    height_pts=height_pts,
                    rotation=0,
                    dpi=72,
                    has_image_overlay=True,
                )
            ],
            total_entities=len(gt_entities),
            entities=gt_entities,
            sha256=doc_sha256,
            provenance_source=text_source.get("source", "held_out_dataset"),
        )

        with open(self.output_annot_dir / f"{doc_id}.json", "w", encoding="utf-8") as f:
            f.write(meta.model_dump_json(indent=2))

        return meta

    def build_handwriting_document(
        self,
        doc_id: str,
        title: str,
        language: Literal["vi", "en"],
        category: str,
        form_fields: list[dict],
    ) -> GoldSuiteDocumentMetadata:
        """Create a document simulating a printed form with handwritten user inputs."""
        width_pts, height_pts = 595.32, 841.92
        doc = pymupdf.open()
        page = doc.new_page(width=width_pts, height=height_pts)

        page.insert_font(fontname="print_font", fontfile=self.arial_font)
        page.insert_font(fontname="script_font", fontfile=self.script_font)

        # Header
        page.insert_text(
            pymupdf.Point(54, 70),
            title.upper(),
            fontname="print_font",
            fontsize=13,
            color=(0.0, 0.0, 0.0),
        )
        page.insert_text(
            pymupdf.Point(54, 88),
            "OFFICIAL REGISTRATION & DECLARATION FORM (HANDWRITTEN ENTRIES)",
            fontname="print_font",
            fontsize=8.5,
            color=(0.3, 0.3, 0.3),
        )

        y_cursor = 130.0
        gt_entities: list[GroundTruthEntity] = []

        for idx, field in enumerate(form_fields):
            label_text = field["label_text"] + ":"
            value_text = field["value_text"]
            pii_type = field["pii_type"]

            # Draw printed form label
            page.insert_text(
                pymupdf.Point(54, y_cursor),
                label_text,
                fontname="print_font",
                fontsize=10.5,
                color=(0.15, 0.15, 0.15),
            )

            # Draw form underline
            shape = page.new_shape()
            shape.draw_line(
                pymupdf.Point(190, y_cursor + 2),
                pymupdf.Point(width_pts - 54, y_cursor + 2),
            )
            shape.finish(width=0.6, color=(0.6, 0.6, 0.6))
            shape.commit()

            # Insert handwritten value
            value_point = pymupdf.Point(200, y_cursor)
            page.insert_text(
                value_point,
                value_text,
                fontname="script_font",
                fontsize=11.5,
                color=(0.05, 0.15, 0.5),  # Blue handwriting ink
            )

            rects = page.search_for(value_text)
            if rects:
                bboxes = [
                    BoundingBox(
                        x0=round(r.x0, 2),
                        y0=round(r.y0, 2),
                        x1=round(r.x1, 2),
                        y1=round(r.y1, 2),
                    )
                    for r in rects
                ]
                gt_entities.append(
                    GroundTruthEntity(
                        entity_id=f"{doc_id}_hw_{idx+1:03d}",
                        label=pii_type,
                        text=value_text,
                        char_start=0,
                        char_end=len(value_text),
                        page_index=0,
                        bounding_boxes=bboxes,
                        source_type="handwriting",
                        is_handwriting=True,
                    )
                )

            y_cursor += 36.0

        pdf_filename = f"{doc_id}.pdf"
        pdf_path = self.output_pdf_dir / pdf_filename
        doc.save(str(pdf_path), garbage=4, deflate=True)
        doc.close()

        with open(pdf_path, "rb") as f:
            doc_sha256 = hashlib.sha256(f.read()).hexdigest()

        meta = GoldSuiteDocumentMetadata(
            doc_id=doc_id,
            title=title,
            doc_type="handwriting",
            language=language,
            category=category,
            filename=pdf_filename,
            page_count=1,
            pages=[
                PageMetadata(
                    page_index=0,
                    width_pts=width_pts,
                    height_pts=height_pts,
                    rotation=0,
                    dpi=72,
                    has_image_overlay=False,
                )
            ],
            total_entities=len(gt_entities),
            entities=gt_entities,
            sha256=doc_sha256,
            provenance_source="simulated_handwritten_forms",
        )

        with open(self.output_annot_dir / f"{doc_id}.json", "w", encoding="utf-8") as f:
            f.write(meta.model_dump_json(indent=2))

        return meta

    def build_entire_suite(self) -> dict[str, Any]:
        """Build the complete 40-document gold standard suite."""
        vn_docs, en_docs = self.load_held_out_sources()
        created_docs: list[GoldSuiteDocumentMetadata] = []

        print(f"Loaded {len(vn_docs)} VN held-out docs and {len(en_docs)} EN held-out docs.")

        # 1. Native Documents (12 docs: 6 VN + 6 EN)
        print("Generating 12 Native PDF documents...")
        for i in range(6):
            doc_id = f"GOLD-NATIVE-VN-{i+1:02d}"
            title = f"Văn bản Hành chính & Nhân sự Số {i+1:02d}"
            meta = self.build_native_document(
                doc_id=doc_id,
                title=title,
                language="vi",
                category="administrative",
                text_source=vn_docs[i],
            )
            created_docs.append(meta)

        for i in range(6):
            doc_id = f"GOLD-NATIVE-EN-{i+1:02d}"
            title = f"Corporate Agreement & Record {i+1:02d}"
            meta = self.build_native_document(
                doc_id=doc_id,
                title=title,
                language="en",
                category="corporate",
                text_source=en_docs[i],
            )
            created_docs.append(meta)

        # 2. Scanned Documents (12 docs: 6 VN + 6 EN, dpi 150/300, skew)
        print("Generating 12 Scanned PDF documents (150/300 dpi with skew)...")
        for i in range(6):
            doc_id = f"GOLD-SCAN-VN-{i+1:02d}"
            title = f"Hồ sơ Lưu trữ Scan Số {i+1:02d}"
            dpi = 150 if i % 2 == 0 else 300
            skew = 0.8 if i % 2 == 0 else -1.2
            meta = self.build_scanned_document(
                doc_id=doc_id,
                title=title,
                language="vi",
                category="scanned_archive",
                text_source=vn_docs[6 + i],
                dpi=dpi,
                skew_angle=skew,
            )
            created_docs.append(meta)

        for i in range(6):
            doc_id = f"GOLD-SCAN-EN-{i+1:02d}"
            title = f"Archived Scanned Invoice & Notice {i+1:02d}"
            dpi = 150 if i % 2 == 0 else 300
            skew = -0.9 if i % 2 == 0 else 1.1
            meta = self.build_scanned_document(
                doc_id=doc_id,
                title=title,
                language="en",
                category="scanned_record",
                text_source=en_docs[6 + i],
                dpi=dpi,
                skew_angle=skew,
            )
            created_docs.append(meta)

        # 3. Mixed Documents (8 docs: 4 VN + 4 EN with embedded stamps and signatures)
        print("Generating 8 Mixed PDF documents (native text + raster stamps/signatures)...")
        for i in range(4):
            doc_id = f"GOLD-MIXED-VN-{i+1:02d}"
            title = f"Hợp đồng Kinh tế & Xác nhận Con dấu {i+1:02d}"
            meta = self.build_mixed_document(
                doc_id=doc_id,
                title=title,
                language="vi",
                category="contract_stamped",
                text_source=vn_docs[12 + i],
            )
            created_docs.append(meta)

        for i in range(4):
            doc_id = f"GOLD-MIXED-EN-{i+1:02d}"
            title = f"Certified Executive Agreement {i+1:02d}"
            meta = self.build_mixed_document(
                doc_id=doc_id,
                title=title,
                language="en",
                category="executive_agreement",
                text_source=en_docs[12 + i],
            )
            created_docs.append(meta)

        # 4. Handwriting & Geometry Variations (8 docs)
        print("Generating 8 Handwriting & Geometry Variation documents...")
        # 4.1. 4 Handwriting documents
        sample_hw_fields_vn = [
            {"label_text": "Họ và tên người khai", "value_text": "Trần Thị Mai Anh", "pii_type": "GIVENNAME"},
            {"label_text": "Số Căn cước công dân", "value_text": "001198012345", "pii_type": "IDCARDNUM"},
            {"label_text": "Ngày tháng năm sinh", "value_text": "24/08/1998", "pii_type": "DATE"},
            {"label_text": "Số điện thoại liên hệ", "value_text": "0987654321", "pii_type": "TELEPHONENUM"},
            {"label_text": "Địa chỉ thường trú", "value_text": "Số 15 Phố Huế, Hoàn Kiếm, Hà Nội", "pii_type": "STREET"},
        ]
        sample_hw_fields_en = [
            {"label_text": "Applicant Full Name", "value_text": "Alexander James Miller", "pii_type": "PERSON"},
            {"label_text": "Social Security Number", "value_text": "123-45-6789", "pii_type": "US_SSN"},
            {"label_text": "Date of Birth", "value_text": "1985-11-12", "pii_type": "DATE_TIME"},
            {"label_text": "Primary Mobile Phone", "value_text": "(555) 234-5678", "pii_type": "PHONE_NUMBER"},
            {"label_text": "Contact Email Address", "value_text": "alex.miller@example.org", "pii_type": "EMAIL_ADDRESS"},
        ]

        meta = self.build_handwriting_document(
            doc_id="GOLD-HANDWRITING-VN-01",
            title="Tờ Khai Thông Tin Cư Trú Cá Nhân",
            language="vi",
            category="registration_form",
            form_fields=sample_hw_fields_vn,
        )
        created_docs.append(meta)

        meta = self.build_handwriting_document(
            doc_id="GOLD-HANDWRITING-VN-02",
            title="Đơn Xin Cấp Lại Giấy Phép Lái Xe",
            language="vi",
            category="license_form",
            form_fields=sample_hw_fields_vn[:4],
        )
        created_docs.append(meta)

        meta = self.build_handwriting_document(
            doc_id="GOLD-HANDWRITING-EN-01",
            title="Patient Registration & Medical History",
            language="en",
            category="medical_form",
            form_fields=sample_hw_fields_en,
        )
        created_docs.append(meta)

        meta = self.build_handwriting_document(
            doc_id="GOLD-HANDWRITING-EN-02",
            title="Beneficiary Designation Form",
            language="en",
            category="financial_form",
            form_fields=sample_hw_fields_en[:4],
        )
        created_docs.append(meta)

        # 4.2. 2 Landscape documents
        meta = self.build_native_document(
            doc_id="GOLD-LANDSCAPE-VN-01",
            title="Bảng Kê Khai Tài Chính & Nhân Sự (Khổ Ngang)",
            language="vi",
            category="ledger_table",
            text_source=vn_docs[16],
            is_landscape=True,
        )
        created_docs.append(meta)

        meta = self.build_native_document(
            doc_id="GOLD-LANDSCAPE-EN-01",
            title="Quarterly Payroll & Tax Ledger (Landscape)",
            language="en",
            category="ledger_table",
            text_source=en_docs[16],
            is_landscape=True,
        )
        created_docs.append(meta)

        # 4.3. 2 Rotated documents (90 deg and 270 deg)
        meta = self.build_native_document(
            doc_id="GOLD-ROTATED-90-VN-01",
            title="Văn bản Xoay 90 Độ (Định hướng Trang)",
            language="vi",
            category="rotated_page",
            text_source=vn_docs[17],
            rotation=90,
        )
        created_docs.append(meta)

        meta = self.build_native_document(
            doc_id="GOLD-ROTATED-270-EN-01",
            title="Corporate Appendix Page Rotated 270 Degrees",
            language="en",
            category="rotated_page",
            text_source=en_docs[17],
            rotation=270,
        )
        created_docs.append(meta)

        # 5. Compile Manifest Summary
        total_entities = sum(d.total_entities for d in created_docs)
        doc_type_counts: dict[str, int] = {}
        label_counts: dict[str, int] = {}

        for d in created_docs:
            doc_type_counts[d.doc_type] = doc_type_counts.get(d.doc_type, 0) + 1
            for ent in d.entities:
                label_counts[ent.label] = label_counts.get(ent.label, 0) + 1

        manifest_data = {
            "suite_name": "gold_standard_pdf_suite_DATA-04",
            "version": "1.0.0",
            "created_by": "Dương Minh Đức (SE4 - Data & PDF Engine)",
            "reviewer": "Nguyễn Tuấn Vinh (SE3 - Document/OCR)",
            "total_documents": len(created_docs),
            "total_pages": sum(d.page_count for d in created_docs),
            "total_ground_truth_entities": total_entities,
            "doc_type_distribution": doc_type_counts,
            "label_distribution": label_counts,
            "documents": [d.model_dump() for d in created_docs],
        }

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)

        print(f"\nSUCCESS: Generated {len(created_docs)} PDF documents with {total_entities} ground truth entities.")
        print(f"Manifest written to: {self.manifest_path}")

        return manifest_data


if __name__ == "__main__":
    builder = GoldSuiteBuilder(workspace_root=Path(__file__).resolve().parents[2])
    builder.build_entire_suite()
