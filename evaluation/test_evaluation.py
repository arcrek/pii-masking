#!/usr/bin/env python3
"""Unit tests for PII evaluation metrics, business holdout integrity, and hybrid rules."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from evaluation.generate_business_holdout import REQUIRED_LABELS, generate_documents
from evaluation.hybrid_rules import (
    build_hybrid_predictions,
    extract_deterministic_spans,
    refine_opf_span,
)
from evaluation.metrics import (
    GRAVITEE_25_LABELS,
    MVP_REQUIRED_6_LABELS,
    score_predictions,
)


class TestEvaluationSuite(unittest.TestCase):
    def test_business_holdout_integrity(self) -> None:
        docs = generate_documents()
        self.assertEqual(len(docs), 60)
        for doc in docs:
            text = doc["text"]
            spans = doc["spans"]
            self.assertTrue(len(spans) >= 5, f"Too few spans in {doc['id']}")
            # Verify non-overlapping and exact substring match
            sorted_spans = sorted(spans, key=lambda s: (s["start"], s["end"]))
            for i, sp in enumerate(sorted_spans):
                self.assertIn(sp["label"], REQUIRED_LABELS)
                self.assertEqual(text[sp["start"] : sp["end"]], sp["text"])
                if i > 0:
                    prev = sorted_spans[i - 1]
                    self.assertGreaterEqual(sp["start"], prev["end"], f"Overlap in {doc['id']}")

    def test_deterministic_rules_on_business_holdout(self) -> None:
        docs = generate_documents()
        preds_by_doc = {}
        for doc in docs:
            preds_by_doc[doc["id"]] = extract_deterministic_spans(doc["text"])

        res = score_predictions(
            docs,
            preds_by_doc,
            label_list=GRAVITEE_25_LABELS,
            required_labels=MVP_REQUIRED_6_LABELS,
        )
        # Deterministic rules alone should achieve >98% F1 on US_SSN, EMAIL_ADDRESS, PHONE_NUMBER, DATE_TIME
        for lbl in ("US_SSN", "EMAIL_ADDRESS", "PHONE_NUMBER", "DATE_TIME"):
            f1 = res["exact"]["per_label"][lbl]["f1"]
            self.assertGreaterEqual(f1, 0.98, f"Expected >=0.98 F1 for {lbl}, got {f1}")

    def test_opf_account_number_refinement(self) -> None:
        text = "SSN: 412-58-9034 and IBAN: GB82WEST12345698765432"
        r1 = refine_opf_span(text, 5, 16, "account_number")
        self.assertEqual(r1["label"], "US_SSN")
        r2 = refine_opf_span(text, 27, 49, "account_number")
        self.assertEqual(r2["label"], "IBAN_CODE")

    def test_hybrid_combiner(self) -> None:
        text = "Contact Evelyn Vance at evelyn@example.com or 412-58-9034 on 2025-10-14."
        opf_raw = [{"start": 8, "end": 20, "label": "private_person"}]
        pres_raw = []
        merged = build_hybrid_predictions(text, opf_raw, pres_raw)
        labels = {s["label"] for s in merged}
        self.assertEqual(labels, {"PERSON", "EMAIL_ADDRESS", "US_SSN", "DATE_TIME"})

    def test_structured_payload_extraction(self) -> None:
        payload = '{"iban": "GB02UOUQ07345637357362", "device_mac": "74-8f-8e-da-43-df", "Version": "2016-11-15", "oauth_token": "xyz123"}'
        spans = extract_deterministic_spans(payload)
        by_lbl = {s["label"]: payload[s["start"] : s["end"]] for s in spans}
        self.assertEqual(
            by_lbl,
            {
                "IBAN_CODE": "GB02UOUQ07345637357362",
                "MAC_ADDRESS": "74-8f-8e-da-43-df",
            },
        )

    def test_harmonized_scoring_mode(self) -> None:
        doc = {
            "id": "kiji_sample",
            "text": "Applicant Fiona Thompson resides at 12 Kilcullen Road.",
            "spans": [
                {"start": 10, "end": 15, "label": "PERSON", "text": "Fiona"},
                {"start": 16, "end": 24, "label": "PERSON", "text": "Thompson"},
            ],
        }
        preds = {
            "kiji_sample": [
                {"start": 10, "end": 24, "label": "PERSON", "score": 0.99},
            ]
        }
        res = score_predictions([doc], preds, label_list=GRAVITEE_25_LABELS, required_labels=MVP_REQUIRED_6_LABELS)
        self.assertEqual(res["harmonized"]["per_label"]["PERSON"]["f1"], 1.0)


if __name__ == "__main__":
    unittest.main()
