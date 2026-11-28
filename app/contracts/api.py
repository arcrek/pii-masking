"""API request and response schemas for /api/v1 (CORE-03)."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any


@dataclass
class ApiErrorResponse:
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentUploadResponse:
    document_id: str
    filename: str
    file_size_bytes: int
    status: str
    created_at: str
    job_id: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RegionUpdatePayload:
    region_id: str
    status: str  # "ACCEPTED", "REJECTED", "MANUAL"
    canonical_group: Optional[str] = None
    visual_rects: Optional[List[List[float]]] = None


@dataclass
class ReviewRevisionCreateRequest:
    regions: List[RegionUpdatePayload]
    comment: Optional[str] = None


@dataclass
class ReviewRevisionResponse:
    revision_no: int
    document_id: str
    status: str  # "DRAFT", "LOCKED", "SUPERSEDED"
    created_at: str
    locked_at: Optional[str] = None
    regions_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExportRequest:
    revision_no: int
    idempotency_key: Optional[str] = None


@dataclass
class ExportResponse:
    export_id: str
    document_id: str
    revision_no: int
    download_url: str
    sha256_checksum: str
    verification_status: str  # "PASS", "FAIL", "INCONCLUSIVE"
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JobStatusResponse:
    job_id: str
    document_id: str
    job_type: str  # "ANALYZE", "EXPORT"
    status: str  # "QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"
    attempt: int
    max_attempts: int
    error_message: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
