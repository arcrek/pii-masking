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

    def test_single_text_detection_vietnamese_formatted_phone(self) -> None:
        """Vietnamese formatted phones (mobile & landline) must be detected and mapped to PHONE."""
        text = "Liên hệ với ông qua email test.user@example.com hoặc số điện thoại bàn 024-3825-1234 hoặc di động 0912 345 678 tại Hà Nội."
        entities = self.engine.predict(text)
        self.assertGreater(len(entities), 0)

        labels = {e.canonical_group for e in entities}
        self.assertIn("EMAIL", labels)
        self.assertIn("PHONE", labels)

        phone_texts = [e.text for e in entities if e.canonical_group == "PHONE"]
        self.assertIn("024-3825-1234", phone_texts)
        self.assertIn("0912 345 678", phone_texts)

        for e in entities:
            self.assertEqual(text[e.start:e.end], e.text)
            self.assertEqual(e.model_version, "1.0.0")
            self.assertIsInstance(e.score, float)
            self.assertGreater(e.score, 0.0)

    def test_single_text_detection_english_formatted_iban(self) -> None:
        """English PII and space-formatted IBAN must be detected cleanly without partial credit card masking."""
        text = "Please transfer fees to IBAN: DE89 3704 0044 0532 0130 00 or call +1-202-555-0199."
        entities = self.engine.predict(text, lang_hint="en")
        self.assertGreater(len(entities), 0)

        labels = {e.canonical_group for e in entities}
        self.assertIn("ID_NUMBER", labels)
        self.assertIn("PHONE", labels)

        # Full IBAN span must be preserved including DE89 prefix and 00 suffix
        iban_entities = [e for e in entities if e.raw_label == "IBAN_CODE"]
        self.assertEqual(len(iban_entities), 1)
        self.assertEqual(iban_entities[0].text, "DE89 3704 0044 0532 0130 00")
        self.assertEqual(text[iban_entities[0].start:iban_entities[0].end], "DE89 3704 0044 0532 0130 00")

    def test_vietnamese_tax_id_and_idcard_context_anchored(self) -> None:
        """Tax ID and CMND require context anchors to avoid false positives on arbitrary numbers."""
        # Uncontextualized 10-digit number must NOT be detected as TAXNUM
        uncontextualized = "Kiểm tra mã vận đơn 1234567890 trong hệ thống."
        entities_unctx = self.engine.predict(uncontextualized)
        tax_unctx = [e for e in entities_unctx if e.raw_label == "TAXNUM"]
        self.assertEqual(tax_unctx, [])

        # Context-anchored Tax ID and CMND must be detected
        contextualized = "Thông tin doanh nghiệp: Mã số thuế: 0101234567 và số CMND: 123456789."
        entities_ctx = self.engine.predict(contextualized)
        tax_ctx = [e for e in entities_ctx if e.raw_label == "TAXNUM"]
        self.assertEqual(len(tax_ctx), 1)
        self.assertEqual(tax_ctx[0].text, "0101234567")

        cmnd_ctx = [e for e in entities_ctx if e.raw_label == "IDCARDNUM"]
        self.assertEqual(len(cmnd_ctx), 1)
        self.assertEqual(cmnd_ctx[0].text, "123456789")

    def test_vietnamese_model_not_run_on_english_text(self) -> None:
        """Vietnamese spaCy model must NOT run on English text (Critical Finding 6)."""
        en_text = "John Smith can be reached at john.smith@company.com or 555-123-4567 in Seattle."
        model_results = self.engine._extract_model(en_text, lang="en")
        self.assertEqual(model_results, [])

        entities = self.engine.predict(en_text, lang_hint="en")
        self.assertGreater(len(entities), 0)
        labels = {e.canonical_group for e in entities}
        self.assertIn("EMAIL", labels)

    def test_excluded_labels_do_not_shadow_valid_pii_overlapping_spans(self) -> None:
        """Excluded labels (e.g. URL, TITLE) must be filtered BEFORE deduplication so they do not shadow valid PII."""
        # Simulate a scenario where an excluded label span (URL) overlaps a valid PII span (EMAIL)
        # If deduplication happened first, the longer URL span (30 chars) would shadow and delete the EMAIL span (20 chars)
        def mock_extract_rules(text: str, lang: str):
            return [
                {"start": 0, "end": 30, "raw_label": "URL", "score": 0.99, "source": "rule"},
                {"start": 5, "end": 25, "raw_label": "EMAIL", "score": 0.99, "source": "rule"},
            ]

        sample_text = "https://user@example.com/login"
        original_extract = self.engine._extract_rules
        try:
            self.engine._extract_rules = mock_extract_rules  # type: ignore[assignment]
            entities = self.engine.predict(sample_text)
            self.assertEqual(len(entities), 1)
            # EMAIL must be preserved despite being shadowed by the longer excluded URL candidate
            self.assertEqual(entities[0].canonical_group, "EMAIL")
            self.assertEqual(entities[0].raw_label, "EMAIL")
        finally:
            self.engine._extract_rules = original_extract  # type: ignore[assignment]

    def test_long_text_sliding_window_handling(self) -> None:
        """Long text exceeding chunk limit must be segmented, offset-aligned, and deduplicated."""
        padding = "Đây là văn bản tài liệu hợp đồng kinh tế không chứa thông tin nhạy cảm. " * 30
        pii_part = "Thông tin liên hệ khẩn cấp: nguyen.van.a@company.vn hoặc số 0987654321."
        long_text = padding + pii_part + padding

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

        # Confirm 024-3825-1234 is positively detected in batch results
        self.assertGreater(len(batch_res[2]), 0)
        self.assertEqual(batch_res[2][0].text, "024-3825-1234")
        self.assertEqual(batch_res[2][0].canonical_group, "PHONE")
