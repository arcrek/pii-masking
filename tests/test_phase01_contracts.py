"""Unit and contract validation tests for Phase 1 (CORE-01, CORE-02, CORE-03)."""

from __future__ import annotations

import re
import sqlite3
import unittest

from app.contracts.pii_taxonomy import (
    TAXONOMY_VERSION,
    CanonicalGroup,
    EXCLUDED_LABELS,
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
    ExportResponse,
    JobStatusResponse,
)
from app.db.models import SQL_SCHEMA_DDL
from evaluation.prepare_vn_data import OPENPII_19_LABELS
from evaluation.metrics import GRAVITEE_25_LABELS


class TestPhase01Contracts(unittest.TestCase):
    """Test suite ensuring strict cross-module contracts and invariants."""

    def test_core01_taxonomy_version_and_groups(self) -> None:
        self.assertEqual(TAXONOMY_VERSION, "1.0.0")
        groups = {g.value for g in CanonicalGroup}
        expected_groups = {"PERSON", "EMAIL", "PHONE", "ADDRESS", "DATE", "ID_NUMBER"}
        self.assertEqual(groups, expected_groups)
        self.assertIsInstance(EXCLUDED_LABELS, set)
        self.assertIn("URL", EXCLUDED_LABELS)

    def test_core01_vietnamese_19_labels_exhaustive_coverage(self) -> None:
        """Every label in OPENPII_19_LABELS must map to CanonicalGroup or EXCLUDED_LABELS."""
        for label in OPENPII_19_LABELS:
            group, is_excluded = map_raw_label(label, strict=True)
            self.assertTrue(
                (group is not None and not is_excluded) or (group is None and is_excluded),
                f"Vietnamese label {label} must either map to CanonicalGroup or be explicitly excluded",
            )

    def test_core01_english_25_labels_exhaustive_coverage(self) -> None:
        """Every label in GRAVITEE_25_LABELS must map to CanonicalGroup or EXCLUDED_LABELS."""
        for label in GRAVITEE_25_LABELS:
            group, is_excluded = map_raw_label(label, strict=True)
            self.assertTrue(
                (group is not None and not is_excluded) or (group is None and is_excluded),
                f"English label {label} must either map to CanonicalGroup or be explicitly excluded",
            )

    def test_core01_strict_mode_rejects_unknown_label(self) -> None:
        with self.assertRaises(ValueError):
            map_raw_label("UNKNOWN_RANDOM_LABEL", strict=True)

    def test_core02_geometry_corner_coordinates(self) -> None:
        """Verify concrete corner-coordinate mappings for 0, 90, 180, 270 clockwise rotations.
        
        Cross-checks PyMuPDF coordinate convention on page (W=612, H=792):
        - 0 deg:   Identity mapping
        - 90 deg:  vx = H - uy, vy = ux
        - 180 deg: vx = W - ux, vy = H - uy
        - 270 deg: vx = uy,     vy = W - ux
        """
        page_w = 612.0
        page_h = 792.0
        unrot = UnrotRect(0.0, 0.0, 100.0, 50.0)

        # 0 deg CW
        v0 = unrot_to_visual_rect(unrot, page_w, page_h, rotation_deg=0)
        self.assertEqual((v0.x0, v0.y0, v0.x1, v0.y1), (0.0, 0.0, 100.0, 50.0))
        u0 = visual_to_unrot_rect(v0, page_w, page_h, rotation_deg=0)
        self.assertEqual((u0.x0, u0.y0, u0.x1, u0.y1), (0.0, 0.0, 100.0, 50.0))

        # 90 deg CW (vx = H - uy, vy = ux):
        # vx0 = 792 - 50 = 742, vx1 = 792 - 0 = 792
        # vy0 = 0, vy1 = 100
        v90 = unrot_to_visual_rect(unrot, page_w, page_h, rotation_deg=90)
        self.assertEqual((v90.x0, v90.y0, v90.x1, v90.y1), (742.0, 0.0, 792.0, 100.0))
        u90 = visual_to_unrot_rect(v90, page_w, page_h, rotation_deg=90)
        self.assertEqual((u90.x0, u90.y0, u90.x1, u90.y1), (0.0, 0.0, 100.0, 50.0))

        # 180 deg CW (vx = W - ux, vy = H - uy):
        # vx0 = 612 - 100 = 512, vx1 = 612 - 0 = 612
        # vy0 = 792 - 50 = 742, vy1 = 792 - 0 = 792
        v180 = unrot_to_visual_rect(unrot, page_w, page_h, rotation_deg=180)
        self.assertEqual((v180.x0, v180.y0, v180.x1, v180.y1), (512.0, 742.0, 612.0, 792.0))
        u180 = visual_to_unrot_rect(v180, page_w, page_h, rotation_deg=180)
        self.assertEqual((u180.x0, u180.y0, u180.x1, u180.y1), (0.0, 0.0, 100.0, 50.0))

        # 270 deg CW (vx = uy, vy = W - ux):
        # vx0 = 0, vx1 = 50
        # vy0 = 612 - 100 = 512, vy1 = 612 - 0 = 612
        v270 = unrot_to_visual_rect(unrot, page_w, page_h, rotation_deg=270)
        self.assertEqual((v270.x0, v270.y0, v270.x1, v270.y1), (0.0, 512.0, 50.0, 612.0))
        u270 = visual_to_unrot_rect(v270, page_w, page_h, rotation_deg=270)
        self.assertEqual((u270.x0, u270.y0, u270.x1, u270.y1), (0.0, 0.0, 100.0, 50.0))

    def test_core02_geometry_roundtrip_all_rotations(self) -> None:
        """Verify round-trip coordinate preservation across 0, 90, 180, 270 rotations."""
        page_w = 612.0
        page_h = 792.0

        test_rects = [
            (50.0, 100.0, 200.0, 150.0),
            (0.0, 0.0, 100.0, 50.0),
            (300.0, 500.0, 500.0, 700.0),
        ]

        for rot in (0, 90, 180, 270):
            vis_w = page_h if rot in (90, 270) else page_w
            vis_h = page_w if rot in (90, 270) else page_h

            for rect in test_rects:
                v_rect = VisualRect(
                    min(rect[0], vis_w - 50),
                    min(rect[1], vis_h - 50),
                    min(rect[2], vis_w),
                    min(rect[3], vis_h),
                )

                unrot = visual_to_unrot_rect(v_rect, page_w, page_h, rotation_deg=rot)
                roundtrip = unrot_to_visual_rect(unrot, page_w, page_h, rotation_deg=rot)

                self.assertAlmostEqual(v_rect.x0, roundtrip.x0, places=2)
                self.assertAlmostEqual(v_rect.y0, roundtrip.y0, places=2)
                self.assertAlmostEqual(v_rect.x1, roundtrip.x1, places=2)
                self.assertAlmostEqual(v_rect.y1, roundtrip.y1, places=2)

    def test_core02_clamp_and_pad(self) -> None:
        rect = VisualRect(10.0, 10.0, 50.0, 50.0)
        padded = clamp_and_pad_rect(rect, max_width=100.0, max_height=100.0, padding=2.0)
        self.assertEqual((padded.x0, padded.y0, padded.x1, padded.y1), (8.0, 8.0, 52.0, 52.0))

        # Check edge clamping
        edge_rect = VisualRect(1.0, 1.0, 99.0, 99.0)
        clamped = clamp_and_pad_rect(edge_rect, max_width=100.0, max_height=100.0, padding=5.0)
        self.assertEqual((clamped.x0, clamped.y0, clamped.x1, clamped.y1), (0.0, 0.0, 100.0, 100.0))

        # Out of bounds rect must clamp safely and never invert bounds
        out_rect = VisualRect(500.0, 600.0, 700.0, 800.0)
        clamped_out = clamp_and_pad_rect(out_rect, max_width=300.0, max_height=400.0)
        self.assertLessEqual(clamped_out.x0, clamped_out.x1)
        self.assertLessEqual(clamped_out.y0, clamped_out.y1)
        self.assertEqual((clamped_out.x0, clamped_out.y0, clamped_out.x1, clamped_out.y1), (300.0, 400.0, 300.0, 400.0))

    def test_core02_document_ir_serialization(self) -> None:
        token = TokenIR(
            token_id=0,
            text="Nguyen",
            char_start=0,
            char_end=6,
            visual_bbox=[50.0, 50.0, 100.0, 65.0],
            source="native",
        )
        entity = CanonicalEntity(
            entity_id="e-001",
            raw_label="GIVENNAME",
            canonical_group="PERSON",
            text="Nguyen",
            char_start=0,
            char_end=6,
            score=0.98,
            source="rule",
            model_version="1.0.0",
        )
        page = PageIR(
            page_number=1,
            classification=PageClassification.NATIVE,
            quality=PageQuality.OK,
            unrot_width=595.0,
            unrot_height=842.0,
            visual_width=595.0,
            visual_height=842.0,
            rotation_deg=0,
            cropbox=[0.0, 0.0, 595.0, 842.0],
            tokens=[token],
            entities=[entity],
        )

        d = page.to_dict()
        self.assertEqual(d["page_number"], 1)
        self.assertEqual(d["classification"], "NATIVE")
        self.assertEqual(len(d["tokens"]), 1)
        self.assertEqual(d["tokens"][0]["text"], "Nguyen")
        self.assertEqual(d["entities"][0]["canonical_group"], "PERSON")

    def test_core03_database_ddl_and_partial_indexes(self) -> None:
        self.assertIn("uq_one_draft_per_doc", SQL_SCHEMA_DDL)
        self.assertIn("uq_jobs_active_idempotency", SQL_SCHEMA_DDL)
        self.assertIn("idx_jobs_active ON jobs (status, available_at)", SQL_SCHEMA_DDL)
        self.assertIn("deleted_at TIMESTAMP WITH TIME ZONE", SQL_SCHEMA_DDL)
        self.assertIn("max_attempts INTEGER NOT NULL DEFAULT 3", SQL_SCHEMA_DDL)

    def test_core03_database_ddl_sqlite_syntax_execution(self) -> None:
        """Validate that all DDL statements in SQL_SCHEMA_DDL execute cleanly in a SQL engine."""
        ddl_sqlite = SQL_SCHEMA_DDL
        ddl_sqlite = re.sub(r"TIMESTAMP WITH TIME ZONE", "TEXT", ddl_sqlite, flags=re.IGNORECASE)
        ddl_sqlite = re.sub(r"JSONB", "TEXT", ddl_sqlite, flags=re.IGNORECASE)
        ddl_sqlite = re.sub(r"UUID", "TEXT", ddl_sqlite, flags=re.IGNORECASE)
        ddl_sqlite = re.sub(r"BYTEA", "BLOB", ddl_sqlite, flags=re.IGNORECASE)
        ddl_sqlite = re.sub(r"BOOLEAN", "INTEGER", ddl_sqlite, flags=re.IGNORECASE)
        ddl_sqlite = re.sub(r"DOUBLE PRECISION", "REAL", ddl_sqlite, flags=re.IGNORECASE)

        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        statements = [s.strip() for s in ddl_sqlite.split(";") if s.strip()]
        executed = 0
        for stmt in statements:
            cursor.execute(stmt)
            executed += 1
        self.assertGreater(executed, 10)
        conn.close()

    def test_contracts_dto_serialization_and_defaults(self) -> None:
        """Verify API and IR DTOs instantiate, have correct defaults, and serialize."""
        region = RegionPayload(
            region_id="reg-001",
            entity_id="ent-001",
            canonical_group="PERSON",
            visual_rects=[[10.0, 10.0, 100.0, 50.0]],
        )
        self.assertEqual(region.status, "PROPOSED")
        r_dict = region.to_dict()
        self.assertEqual(r_dict["status"], "PROPOSED")

        err = ApiErrorResponse(error_code="UNAUTHORIZED", message="Invalid token")
        self.assertEqual(err.to_dict()["error_code"], "UNAUTHORIZED")

        upload = DocumentUploadResponse(
            document_id="doc-001",
            filename="sample.pdf",
            file_size_bytes=1024,
            status="QUEUED",
            created_at="2026-11-28T10:00:00Z",
            job_id="job-01",
        )
        self.assertEqual(upload.to_dict()["document_id"], "doc-001")

        export = ExportResponse(
            export_id="exp-01",
            document_id="doc-001",
            revision_no=1,
            download_url="/api/v1/download/exp-01",
            sha256_checksum="abc123",
            verification_status="PASS",
            created_at="2026-11-28T10:00:00Z",
        )
        self.assertEqual(export.to_dict()["verification_status"], "PASS")

        job = JobStatusResponse(
            job_id="job-02",
            document_id="doc-001",
            job_type="ANALYZE",
            status="RUNNING",
            attempt=1,
            max_attempts=3,
        )
        self.assertEqual(job.to_dict()["status"], "RUNNING")
