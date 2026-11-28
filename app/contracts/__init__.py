"""Data and domain contracts for PII masking system (CORE-01, CORE-02, CORE-03)."""

from app.contracts.pii_taxonomy import (
    TAXONOMY_VERSION,
    CanonicalGroup,
    EXCLUDED_LABELS,
    VIETNAMESE_19_TO_CANONICAL,
    ENGLISH_25_TO_CANONICAL,
    ALL_CANONICAL_MAPPINGS,
    map_raw_label,
)
from app.contracts.geometry import (
    VisualRect,
    UnrotRect,
    visual_to_unrot_rect,
    unrot_to_visual_rect,
    clamp_and_pad_rect,
)
from app.contracts.document_ir import (
    PageClassification,
    PageQuality,
    TokenIR,
    CanonicalEntity,
    RegionPayload,
    PageIR,
)
from app.contracts.api import (
    ApiErrorResponse,
    DocumentUploadResponse,
    RegionUpdatePayload,
    ReviewRevisionCreateRequest,
    ReviewRevisionResponse,
    ExportRequest,
    ExportResponse,
    JobStatusResponse,
)

__all__ = [
    # Taxonomy
    "TAXONOMY_VERSION",
    "CanonicalGroup",
    "EXCLUDED_LABELS",
    "VIETNAMESE_19_TO_CANONICAL",
    "ENGLISH_25_TO_CANONICAL",
    "ALL_CANONICAL_MAPPINGS",
    "map_raw_label",
    # Geometry
    "VisualRect",
    "UnrotRect",
    "visual_to_unrot_rect",
    "unrot_to_visual_rect",
    "clamp_and_pad_rect",
    # Document IR
    "PageClassification",
    "PageQuality",
    "TokenIR",
    "CanonicalEntity",
    "RegionPayload",
    "PageIR",
    # API
    "ApiErrorResponse",
    "DocumentUploadResponse",
    "RegionUpdatePayload",
    "ReviewRevisionCreateRequest",
    "ReviewRevisionResponse",
    "ExportRequest",
    "ExportResponse",
    "JobStatusResponse",
]
