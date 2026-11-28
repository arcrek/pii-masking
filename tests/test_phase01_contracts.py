"""Unit and contract validation tests for Phase 1 (CORE-01, CORE-02, CORE-03)."""

from __future__ import annotations

import unittest
from pathlib import Path

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

    def test_core02_geometry_roundtrip_all_rotations(self) -> None:
        """Verify round-trip coordinate preservation across 0, 90, 180, 270 rotations."""
        page_w = 612.0  # Standard letter width
        page_h = 792.0  # Standard letter height

        test_rects = [
            (50.0, 100.0, 200.0, 150.0),
            (0.0, 0.0, 100.0, 50.0),
            (300.0, 500.0, 500.0, 700.0),
        ]

        for rot in (0, 90, 180, 270):
            # When rotated, visual dimensions swap for 90 and 270
            vis_w = page_h if rot in (90, 270) else page_w
            vis_h = page_w if rot in (90, 270) else page_h

            for rect in test_rects:
                # Limit initial rect to valid visual range
                v_rect = VisualRect(
                    min(rect[0], vis_w - 50),
                    min(rect[1], vis_h - 50),
                    min(rect[2], vis_w),
                    min(rect[3], vis_h),
                )

                # Convert visual -> unrotated -> visual
                unrot = visual_to_unrot_rect(v_rect, page_w, page_h, rotation_deg=rot)
                roundtrip = unrot_to_visual_rect(unrot, page_w, page_h, rotation_deg=rot)

                # Expect exact or near-exact floating point preservation (tolerance < 0.001 pt)
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
        self.assertIn("deleted_at TIMESTAMP WITH TIME ZONE", SQL_SCHEMA_DDL)
        self.assertIn("max_attempts INTEGER NOT NULL DEFAULT 3", SQL_SCHEMA_DDL)
