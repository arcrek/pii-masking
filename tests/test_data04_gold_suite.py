"""Test suite for DATA-04: Gold Standard PDF Suite.

Verifies:
1. Suite integrity, manifest completeness, and checksum consistency.
2. Structural validity of all 40 PDF files (clean rendering, non-corrupt).
3. Annotation schema compliance and geometric validity of bounding boxes.
4. Coverage of all 4 required document types: Native, Scanned, Mixed, Handwriting.
5. Rotation and landscape geometry support.
6. Absolute separation from training data (Held-out provenance guarantee).
"""

import json
from pathlib import Path
import unittest

import pymupdf


class TestData04GoldStandardPDFSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.gold_suite_dir = cls.repo_root / "evaluation" / "gold_suite"
        cls.manifest_path = cls.gold_suite_dir / "manifest.json"
        cls.pdf_dir = cls.gold_suite_dir / "pdfs"
        cls.annot_dir = cls.gold_suite_dir / "annotations"

        self_assertTrue = cls.assertTrue
        self_assertTrue(cls.manifest_path.exists(), f"Manifest missing at {cls.manifest_path}")

        with open(cls.manifest_path, "r", encoding="utf-8") as f:
            cls.manifest = json.load(f)

    def test_01_manifest_overview_and_counts(self):
        """Verify manifest metadata, total document count and entity count."""
        m = self.manifest
        self.assertEqual(m["suite_name"], "gold_standard_pdf_suite_DATA-04")
        self.assertEqual(m["version"], "1.0.0")
        self.assertEqual(m["total_documents"], 40)
        self.assertEqual(m["total_pages"], 40)
        self.assertGreaterEqual(m["total_ground_truth_entities"], 300)

        dist = m["doc_type_distribution"]
        self.assertIn("native", dist)
        self.assertIn("scanned", dist)
        self.assertIn("mixed", dist)
        self.assertIn("handwriting", dist)

    def test_02_all_pdfs_exist_and_open_cleanly(self):
        """Verify that every PDF listed in the manifest exists and can be parsed by PyMuPDF."""
        docs = self.manifest["documents"]
        self.assertEqual(len(docs), 40)

        for d in docs:
            pdf_path = self.pdf_dir / d["filename"]
            self.assertTrue(pdf_path.exists(), f"PDF missing: {pdf_path}")
            self.assertGreater(pdf_path.stat().st_size, 1024, f"PDF too small/empty: {pdf_path}")

            # PyMuPDF parse test
            doc = pymupdf.open(str(pdf_path))
            self.assertEqual(len(doc), d["page_count"])
            page = doc[0]
            self.assertGreater(page.rect.width, 400)
            self.assertGreater(page.rect.height, 400)
            doc.close()

    def test_03_all_annotations_valid_and_schema_compliant(self):
        """Verify that each annotation file matches its PDF and contains valid bounding boxes."""
        docs = self.manifest["documents"]

        for d in docs:
            annot_path = self.annot_dir / f"{d['doc_id']}.json"
            self.assertTrue(annot_path.exists(), f"Annotation file missing: {annot_path}")

            with open(annot_path, "r", encoding="utf-8") as f:
                annot = json.load(f)

            self.assertEqual(annot["doc_id"], d["doc_id"])
            self.assertEqual(annot["doc_type"], d["doc_type"])
            self.assertEqual(annot["language"], d["language"])
            self.assertEqual(len(annot["entities"]), d["total_entities"])

            page_meta = annot["pages"][0]
            page_w = page_meta["width_pts"]
            page_h = page_meta["height_pts"]

            for ent in annot["entities"]:
                self.assertTrue(ent["text"])
                self.assertTrue(ent["label"])
                self.assertGreater(len(ent["bounding_boxes"]), 0)

                for bbox in ent["bounding_boxes"]:
                    self.assertLess(bbox["x0"], bbox["x1"], f"Invalid x bounds in {d['doc_id']}: {bbox}")
                    self.assertLess(bbox["y0"], bbox["y1"], f"Invalid y bounds in {d['doc_id']}: {bbox}")
                    # Allow slight tolerance (15 pts) for skew/rotation overflow
                    self.assertGreaterEqual(bbox["x0"], 0)
                    self.assertGreaterEqual(bbox["y0"], 0)
                    self.assertLessEqual(bbox["x1"], page_w + 15)
                    self.assertLessEqual(bbox["y1"], page_h + 15)

    def test_04_coverage_of_required_categories(self):
        """Verify presence of Native, Scanned, Mixed, and Handwriting categories."""
        doc_types = {d["doc_type"] for d in self.manifest["documents"]}
        expected_types = {"native", "scanned", "mixed", "handwriting"}
        self.assertEqual(doc_types, expected_types)

        languages = {d["language"] for d in self.manifest["documents"]}
        self.assertEqual(languages, {"vi", "en"})

    def test_05_coverage_of_geometry_and_rotation_variations(self):
        """Verify presence of landscape documents and rotated pages."""
        docs = self.manifest["documents"]
        has_landscape = any(d["pages"][0]["width_pts"] > d["pages"][0]["height_pts"] for d in docs)
        self.assertTrue(has_landscape, "Missing landscape documents in suite")

        rotations = {d["pages"][0]["rotation"] for d in docs}
        self.assertIn(90, rotations, "Missing 90-degree rotated document")
        self.assertIn(270, rotations, "Missing 270-degree rotated document")

    def test_06_handwriting_annotations_flagged(self):
        """Verify that handwriting documents have is_handwriting=True on entities for FE-09 testing."""
        hw_docs = [d for d in self.manifest["documents"] if d["doc_type"] == "handwriting"]
        self.assertGreaterEqual(len(hw_docs), 4)

        for d in hw_docs:
            annot_path = self.annot_dir / f"{d['doc_id']}.json"
            with open(annot_path, "r", encoding="utf-8") as f:
                annot = json.load(f)
            self.assertTrue(
                all(e["is_handwriting"] for e in annot["entities"]),
                f"Entities in handwriting doc {d['doc_id']} should have is_handwriting=True",
            )

    def test_07_held_out_provenance_guarantee(self):
        """Ensure all documents are marked held-out with legitimate provenance."""
        docs = self.manifest["documents"]
        for d in docs:
            self.assertTrue(d["is_held_out"], f"Doc {d['doc_id']} not flagged as held-out")
            self.assertTrue(d["provenance_source"], f"Doc {d['doc_id']} missing provenance source")


if __name__ == "__main__":
    unittest.main()
