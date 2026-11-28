"""Unit and integration tests for ML-03 PII Inference Engine."""

from __future__ import annotations

import unittest
from app.ml_service.inference import PiiInferenceEngine


class TestML03Inference(unittest.TestCase):
    """Test suite verifying ML-03 acceptance criteria and edge cases."""

    def setUp(self) -> None:
        self.engine = PiiInferenceEngine()

    def test_empty_and_whitespace_text_handling(self) -> None:
        """Empty or blank inputs must return an empty list without raising exceptions."""
        self.assertEqual(self.engine.predict(""), [])
        self.assertEqual(self.engine.predict("   \n\t  "), [])
        self.assertEqual(self.engine.predict_batch(["", "  ", "\n"]), [[], [], []])

    def test_single_text_detection_vietnamese(self) -> None:
        """Vietnamese PII must be detected and mapped to canonical groups."""
        text = "Liên hệ với ông qua email test.user@example.com hoặc số điện thoại 0912345678 tại Hà Nội."
        entities = self.engine.predict(text)
        self.assertGreater(len(entities), 0)

        labels = {e.canonical_group for e in entities}
        self.assertIn("EMAIL", labels)
        self.assertIn("PHONE", labels)

        # Ensure text span matches original substring
        for e in entities:
            self.assertEqual(text[e.start:e.end], e.text)
            self.assertEqual(e.model_version, "1.0.0")
            # Score must be non-zero float and not asserted as a calibrated probability
            self.assertIsInstance(e.score, float)
            self.assertGreater(e.score, 0.0)

    def test_single_text_detection_english(self) -> None:
        """English PII must be detected and mapped to canonical groups."""
        text = "Please reach out to support@mycorp.com or call +1-202-555-0199 for assistance."
        entities = self.engine.predict(text, lang_hint="en")
        self.assertGreater(len(entities), 0)

        labels = {e.canonical_group for e in entities}
        self.assertIn("EMAIL", labels)
        self.assertIn("PHONE", labels)

        for e in entities:
            self.assertEqual(text[e.start:e.end], e.text)

    def test_vietnamese_model_not_run_on_english_text(self) -> None:
        """Vietnamese spaCy model must NOT run on English text (Critical Finding 6)."""
        en_text = "John Smith can be reached at john.smith@company.com or 555-123-4567 in Seattle."
        # Model extraction method directly returns empty list for English
        model_results = self.engine._extract_model(en_text, lang="en")
        self.assertEqual(model_results, [])

        # End-to-end predict with lang_hint="en" must still detect English rules
        entities = self.engine.predict(en_text, lang_hint="en")
        self.assertGreater(len(entities), 0)
        labels = {e.canonical_group for e in entities}
        self.assertIn("EMAIL", labels)

    def test_excluded_labels_do_not_shadow_valid_pii(self) -> None:
        """Excluded labels (e.g., URL) must be filtered BEFORE deduplication so they do not shadow valid PII (Critical Finding 6)."""
        # Text containing both a URL and an EMAIL
        text = "Visit https://portal.example.org/contact or write to officer.safe@example.org for inquiries."
        entities = self.engine.predict(text, lang_hint="en")

        groups = [e.canonical_group for e in entities]
        # EMAIL must be detected and not shadowed
        self.assertIn("EMAIL", groups)
        # Excluded label URL must not be present in final entities
        for e in entities:
            self.assertNotEqual(e.raw_label, "URL")
            self.assertNotEqual(e.canonical_group, "URL")

    def test_long_text_sliding_window_handling(self) -> None:
        """Long text exceeding chunk limit must be segmented, offset-aligned, and deduplicated."""
        padding = "Đây là văn bản tài liệu hợp đồng kinh tế không chứa thông tin nhạy cảm. " * 30
        pii_part = "Thông tin liên hệ khẩn cấp: nguyen.van.a@company.vn hoặc số 0987654321."
        long_text = padding + pii_part + padding

        # Use small max_chunk_chars to force sliding window
        engine = PiiInferenceEngine(max_chunk_chars=300, chunk_overlap=50)
        entities = engine.predict(long_text)

        self.assertGreater(len(entities), 0)
        email_entities = [e for e in entities if e.canonical_group == "EMAIL"]
        self.assertEqual(len(email_entities), 1)
        self.assertEqual(email_entities[0].text, "nguyen.van.a@company.vn")
        self.assertEqual(long_text[email_entities[0].start:email_entities[0].end], "nguyen.van.a@company.vn")

    def test_batch_prediction_consistency(self) -> None:
        """Batch prediction returns results for each document matching individual prediction."""
        texts = [
            "Gửi email về contact@vinh.dev nhé.",
            "Nội dung không có thông tin PII nào cả.",
            "Số điện thoại bàn: 024-3825-1234.",
        ]
        batch_res = self.engine.predict_batch(texts)
        self.assertEqual(len(batch_res), len(texts))

        for text, res in zip(texts, batch_res):
            single_res = self.engine.predict(text)
            self.assertEqual(len(res), len(single_res))
            if res:
                self.assertEqual(res[0].text, single_res[0].text)
