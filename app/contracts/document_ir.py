"""Canonical Document Intermediate Representation (Document IR - CORE-02).

Standardizes data models across Native, Scanned, and Mixed pages:
- PageClassification: NATIVE, SCANNED_FLATTENED, MIXED
- PageQuality: OK, NEEDS_ATTENTION, FAILED
- TokenIR: Single word or token with char offsets, bounding box, and provenance
- CanonicalEntity: Detected entity span with label and confidence score
- RegionPayload: Reviewable/redactable region with visual CropBox bounding boxes
- PageIR: Full page representation
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any


class PageClassification(str, Enum):
    NATIVE = "NATIVE"
    SCANNED_FLATTENED = "SCANNED_FLATTENED"
    MIXED = "MIXED"


class PageQuality(str, Enum):
    OK = "OK"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    FAILED = "FAILED"


@dataclass
class TokenIR:
    """A single token/word extracted from text content stream or OCR."""
    token_id: int
    text: str
    char_start: int
    char_end: int
    visual_bbox: List[float]  # [x0, y0, x1, y1] in visual top-left CropBox points
    source: str  # "native" or "ocr"
    ocr_confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalEntity:
    """A detected PII entity from ML NER or deterministic rules."""
    entity_id: str
    raw_label: str
    canonical_group: str  # PERSON, EMAIL, PHONE, ADDRESS, DATE, ID_NUMBER
    text: str
    char_start: int
    char_end: int
    score: float
    source: str  # "rule", "model", "hybrid"
    model_version: str
    page_number: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RegionPayload:
    """A spatial redaction region on a page (can encompass multiple bounding boxes for multi-line spans)."""
    region_id: str
    entity_id: Optional[str]
    canonical_group: str
    visual_rects: List[List[float]]  # List of [x0, y0, x1, y1] in visual CropBox points
    status: str = "PROPOSED"  # PROPOSED, ACCEPTED, REJECTED, MANUAL
    provenance: str = "auto"  # "auto" or "manual"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PageIR:
    """Intermediate Representation of a single document page."""
    page_number: int
    classification: PageClassification
    quality: PageQuality
    unrot_width: float
    unrot_height: float
    visual_width: float
    visual_height: float
    rotation_deg: int  # 0, 90, 180, 270
    cropbox: List[float]  # [x0, y0, x1, y1]
    has_untrusted_ocr_layer: bool = False
    tokens: List[TokenIR] = field(default_factory=list)
    entities: List[CanonicalEntity] = field(default_factory=list)
    regions: List[RegionPayload] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "classification": self.classification.value,
            "quality": self.quality.value,
            "unrot_width": self.unrot_width,
            "unrot_height": self.unrot_height,
            "visual_width": self.visual_width,
            "visual_height": self.visual_height,
            "rotation_deg": self.rotation_deg,
            "cropbox": self.cropbox,
            "has_untrusted_ocr_layer": self.has_untrusted_ocr_layer,
            "tokens": [t.to_dict() for t in self.tokens],
            "entities": [e.to_dict() for e in self.entities],
            "regions": [r.to_dict() for r in self.regions],
            "warnings": self.warnings,
        }
