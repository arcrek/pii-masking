"""Database ORM models and schema DDL (CORE-03).

Schema covers:
- users: Demo / system accounts with Argon2/bcrypt password hash
- sessions: Active login sessions with revocation support
- login_rate_limits: Login rate-limiting entries keyed by (username, client_ip)
- documents: Uploaded documents with soft deletion (deleted_at)
- document_pages: Page-level metadata, unrot_width, unrot_height, mediabox, cropbox
- detected_entities: Raw PII entities detected by ML/rules with text_hash
- review_revisions: Document review revision snapshots with pipeline_version and model_version
- review_regions: Reviewer approved/modified redaction regions (default status PROPOSED)
- jobs: Asynchronous processing jobs with available_at, max_attempts, and idempotency
- export_artifacts: Generated redacted PDF artifacts with checksum
- verification_reports: Independent verification results
- audit_logs: PII-free operational audit logging
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

# PostgreSQL 16 DDL Scripts with Partial Unique Indexes
SQL_SCHEMA_DDL = """
-- Users & Auth
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'reviewer',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_jti VARCHAR(64) UNIQUE NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    user_agent TEXT,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS login_rate_limits (
    key VARCHAR(128) PRIMARY KEY, -- hash of (username, client_ip)
    attempts INTEGER NOT NULL DEFAULT 1,
    locked_until TIMESTAMP WITH TIME ZONE,
    last_attempt_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Documents & Pages
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY,
    owner_id VARCHAR(36) NOT NULL REFERENCES users(id),
    original_filename VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    sha256_checksum VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_INTAKE', -- PENDING_INTAKE, ANALYZED, REJECTED, REDACTED
    page_count INTEGER NOT NULL DEFAULT 0,
    storage_path VARCHAR(512) NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE, -- Tombstone soft-delete
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_pages (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    classification VARCHAR(32) NOT NULL, -- NATIVE, SCANNED_FLATTENED, MIXED
    quality VARCHAR(32) NOT NULL DEFAULT 'OK', -- OK, NEEDS_ATTENTION, FAILED
    unrot_width DOUBLE PRECISION NOT NULL,
    unrot_height DOUBLE PRECISION NOT NULL,
    visual_width DOUBLE PRECISION NOT NULL,
    visual_height DOUBLE PRECISION NOT NULL,
    rotation_deg INTEGER NOT NULL DEFAULT 0,
    mediabox JSONB,
    cropbox JSONB,
    has_untrusted_ocr_layer BOOLEAN NOT NULL DEFAULT FALSE,
    preview_path VARCHAR(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_doc_page UNIQUE (document_id, page_number)
);

-- Entities & Revisions
CREATE TABLE IF NOT EXISTS detected_entities (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    raw_label VARCHAR(64) NOT NULL,
    canonical_group VARCHAR(32) NOT NULL,
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    text_hash VARCHAR(64),
    confidence_score DOUBLE PRECISION NOT NULL,
    source VARCHAR(32) NOT NULL, -- rule, model, hybrid
    model_version VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_revisions (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    revision_no INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT', -- DRAFT, LOCKED, SUPERSEDED
    pipeline_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    model_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    locked_by_user_id VARCHAR(36) REFERENCES users(id),
    locked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_doc_revision UNIQUE (document_id, revision_no)
);

-- Partial unique index: Only one active DRAFT per document allowed (Finding 8)
CREATE UNIQUE INDEX IF NOT EXISTS uq_one_draft_per_doc ON review_revisions (document_id) WHERE status = 'DRAFT';

CREATE TABLE IF NOT EXISTS review_regions (
    id VARCHAR(36) PRIMARY KEY,
    revision_id VARCHAR(36) NOT NULL REFERENCES review_revisions(id) ON DELETE CASCADE,
    entity_id VARCHAR(36) REFERENCES detected_entities(id) ON DELETE SET NULL,
    page_number INTEGER NOT NULL,
    canonical_group VARCHAR(32) NOT NULL,
    visual_rects JSONB NOT NULL, -- array of [x0, y0, x1, y1]
    status VARCHAR(32) NOT NULL DEFAULT 'PROPOSED', -- PROPOSED, ACCEPTED, REJECTED, MANUAL
    provenance VARCHAR(32) NOT NULL DEFAULT 'auto', -- auto, manual
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Jobs & Queue (PostgreSQL SKIP LOCKED Queue)
CREATE TABLE IF NOT EXISTS jobs (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    job_type VARCHAR(32) NOT NULL, -- ANALYZE, EXPORT
    status VARCHAR(32) NOT NULL DEFAULT 'QUEUED', -- QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED
    attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3, -- Finding 9
    available_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    lease_expires_at TIMESTAMP WITH TIME ZONE,
    idempotency_key VARCHAR(128),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Partial index for active jobs
CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs (status, available_at) WHERE status IN ('QUEUED', 'RUNNING');

-- Partial unique index for idempotency: failed/cancelled jobs can be retried cleanly (Finding 9)
CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_active_idempotency ON jobs (idempotency_key) WHERE status IN ('QUEUED', 'RUNNING', 'SUCCEEDED');

-- Output & Verification
CREATE TABLE IF NOT EXISTS export_artifacts (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    revision_id VARCHAR(36) NOT NULL REFERENCES review_revisions(id),
    storage_path VARCHAR(512) NOT NULL,
    sha256_checksum VARCHAR(64) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS verification_reports (
    id VARCHAR(36) PRIMARY KEY,
    export_id VARCHAR(36) NOT NULL REFERENCES export_artifacts(id) ON DELETE CASCADE,
    overall_status VARCHAR(32) NOT NULL, -- PASS, FAIL, INCONCLUSIVE
    details JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(32) NOT NULL,
    resource_id VARCHAR(36),
    status VARCHAR(32) NOT NULL,
    metadata JSONB, -- Strictly NO raw PII
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""


@dataclass
class UserModel:
    id: str
    username: str
    password_hash: str
    role: str = "reviewer"
    is_active: bool = True
    created_at: Optional[datetime.datetime] = None


@dataclass
class SessionModel:
    id: str
    user_id: str
    token_jti: str
    ip_address: str
    user_agent: Optional[str]
    expires_at: datetime.datetime
    is_revoked: bool = False
    created_at: Optional[datetime.datetime] = None


@dataclass
class DocumentModel:
    id: str
    owner_id: str
    original_filename: str
    file_size_bytes: int
    sha256_checksum: str
    storage_path: str
    status: str = "PENDING_INTAKE"
    page_count: int = 0
    deleted_at: Optional[datetime.datetime] = None
    created_at: Optional[datetime.datetime] = None


@dataclass
class JobModel:
    id: str
    document_id: str
    job_type: str
    status: str = "QUEUED"
    attempt: int = 0
    max_attempts: int = 3
    idempotency_key: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
