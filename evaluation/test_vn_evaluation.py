"""Automated unit and integration tests for the Vietnamese 19-label OpenPII benchmark,
deterministic rules (`evaluation/vn_rules.py`), data manifest integrity, and Pre vs Post Fine-tune results.
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from evaluation.prepare_vn_data import OPENPII_19_LABELS
from evaluation.vn_rules import (
    combine_model_and_vn_rules,
    extract_vn_deterministic_spans,
    refine_pretrained_opf_span_for_vn,
)


class TestVietnamesePIIEvaluationSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.data_dir = cls.repo_root / "evaluation" / "data"
        cls.results_dir = cls.repo_root / "evaluation" / "results"
        cls.ckpt_dir = cls.repo_root / "checkpoints"

    def test_vn_manifest_and_splits_integrity(self) -> None:
        manifest_path = self.data_dir / "vn_openpii_manifest.json"
        self.assertTrue(manifest_path.exists(), "vn_openpii_manifest.json must exist")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["num_canonical_labels"], 19)
        self.assertEqual(manifest["canonical_19_labels"], OPENPII_19_LABELS)
        self.assertEqual(manifest["opf_num_bieso_classes"], 77)
        self.assertEqual(manifest["curation_audit"]["cross_split_duplicate_texts"], 0)

        for split_name in ("train", "dev", "test", "independent_holdout"):
            split_info = manifest["splits"][split_name]
            split_path = self.repo_root / split_info["path"]
            self.assertTrue(split_path.exists(), f"{split_path} must exist")
            counts = split_info["label_span_counts"]
            for lbl in OPENPII_19_LABELS:
                self.assertGreater(
                    counts.get(lbl, 0),
                    0,
                    f"Label {lbl} must have positive support in {split_name}",
                )

    def test_vn_deterministic_rules_and_zero_false_positives_on_negatives(self) -> None:
        sample = (
            "HỒ SƠ ĐỊNH DANH CÔNG DÂN (eKYC)\n"
            "Khách hàng: Ông Nguyễn Văn Hùng (Giới tính: Nam, Giới tính sinh học: Đực, 34 tuổi, ngày sinh 1992-04-15).\n"
            "Số CCCD: 079080001234 | Số Hộ chiếu: C8102345 | Số GPLX: 7901540210 | Mã số thuế: 0314589012 | Mã số BHXH: 7923410982.\n"
            "Thẻ tín dụng thanh toán: 4532 1400 8821 3012.\n"
            "Địa chỉ thường trú: Số 128A, Đường Nguyễn Thị Minh Khai, Thành phố Hồ Chí Minh, mã bưu chính 700000.\n"
            "Liên hệ: ĐT 0912345670, hộp thư van.hung.10@congtyvn.vn."
        )
        spans = extract_vn_deterministic_spans(sample)
        detected_labels = {sp["label"] for sp in spans}
        expected_labels = set(OPENPII_19_LABELS)
        self.assertEqual(
            detected_labels,
            expected_labels,
            f"Missing labels in deterministic extraction: {expected_labels - detected_labels}",
        )

        # Verify 0 false positives on all 15 negative non-PII holdout documents
        ind_path = self.data_dir / "vn_independent_holdout.jsonl"
        ind_docs = [
            json.loads(line)
            for line in ind_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        neg_docs = [d for d in ind_docs if not d["spans"]]
        self.assertEqual(len(neg_docs), 15)
        for d in neg_docs:
            neg_spans = extract_vn_deterministic_spans(d["text"])
            self.assertEqual(
                len(neg_spans),
                0,
                f"Expected 0 false positives on negative doc {d['id']}, got {neg_spans}",
            )

    def test_pretrained_opf_disambiguation_and_hybrid_combiner(self) -> None:
        text = "Khách hàng: Lê Hoàng Nam, Số CCCD: 079082001308, Mã số thuế: 0314589838, hộ chiếu C8102583."
        s_cccd = text.index("079082001308")
        r_cccd = refine_pretrained_opf_span_for_vn(
            text, s_cccd, s_cccd + 12, "account_number"
        )
        self.assertEqual(r_cccd[0]["label"], "IDCARDNUM")

        s_tax = text.index("0314589838")
        r_tax = refine_pretrained_opf_span_for_vn(
            text, s_tax, s_tax + 10, "account_number"
        )
        self.assertEqual(r_tax[0]["label"], "TAXNUM")

        s_pp = text.index("C8102583")
        r_pp = refine_pretrained_opf_span_for_vn(
            text, s_pp, s_pp + 8, "account_number"
        )
        self.assertEqual(r_pp[0]["label"], "PASSPORTNUM")

        combined = combine_model_and_vn_rules(
            text,
            [{"start": s_cccd, "end": s_cccd + 12, "label": "account_number"}],
            is_pretrained_opf_8=True,
        )
        labels = {c["label"] for c in combined}
        self.assertTrue({"SURNAME", "GIVENNAME", "IDCARDNUM", "TAXNUM", "PASSPORTNUM"}.issubset(labels))

    def test_pre_vs_post_benchmark_results_and_checkpoints(self) -> None:
        res_path = self.results_dir / "vn_benchmark_results.json"
        if not res_path.exists():
            self.skipTest("vn_benchmark_results.json not yet generated")
        res = json.loads(res_path.read_text(encoding="utf-8"))

        # Check that both pre-finetune and post-finetune candidates exist and post > pre
        deltas_test = res["pre_vs_post_deltas"]["vn_test_600"]
        self.assertGreater(
            deltas_test["spacy_model_only_pre_to_post"]["exact_micro_f1_delta"],
            0.50,
            "Fine-tuned spaCy NER must improve Exact F1 by >50 percentage points over untrained pre-finetune baseline",
        )
        self.assertGreater(
            deltas_test["opf_model_only_pre_to_post"]["exact_micro_f1_delta"],
            0.35,
            "Fine-tuned 19-label OPF must improve Exact F1 by >35 percentage points over pre-finetune 8-label OPF",
        )
        self.assertGreater(
            deltas_test["spacy_plus_rules_pre_to_post"]["exact_micro_f1_delta"],
            0.25,
            "Fine-tuned spaCy + Rules must substantially outperform Pre-finetune + Rules",
        )
        self.assertGreater(
            deltas_test["opf_plus_rules_pre_to_post"]["exact_micro_f1_delta"],
            0.25,
            "Fine-tuned OPF + Rules must substantially outperform Pre-finetune OPF + Rules",
        )

        # Verify Post-Finetune (+VN Rules) >= Post-Finetune (Model-Only) on both vn_test_600 and vn_independent_holdout_75
        for split_key in ("vn_test_600", "vn_independent_holdout_75"):
            ev = res["evaluation"][split_key]
            self.assertGreaterEqual(
                ev["spacy_finetuned_post_plus_rules"]["exact"]["overall_micro"]["f1"],
                ev["spacy_finetuned_post_model_only"]["exact"]["overall_micro"]["f1"],
                f"spacy_finetuned_post_plus_rules must be >= model-only on {split_key}",
            )
            self.assertGreaterEqual(
                ev["opf_finetuned_post_plus_rules"]["exact"]["overall_micro"]["f1"],
                ev["opf_finetuned_post_model_only"]["exact"]["overall_micro"]["f1"],
                f"opf_finetuned_post_plus_rules must be >= model-only on {split_key}",
            )

        # Verify all post-finetune +Rules pipelines pass all locked quality gates with 0 negative holdout FPs
        verdicts = res["gate_verdicts_on_test"]
        for cand in (
            "spacy_finetuned_post_plus_rules",
            "opf_finetuned_post_plus_rules",
            "hybrid_finetuned_opf_spacy_rules",
        ):
            self.assertTrue(
                verdicts[cand]["passed_all_locked_gates"],
                f"{cand} must pass all locked quality gates",
            )
            self.assertEqual(
                verdicts[cand]["negative_holdout_fp_spans"],
                0,
                f"{cand} must have 0 false positive spans on negative 0-PII holdout docs",
            )

        # Verify both checkpoints exist and have valid metadata
        spacy_ckpt = self.ckpt_dir / "spacy_vn_19_ner"
        opf_ckpt = self.ckpt_dir / "opf_vn_19"
        self.assertTrue((spacy_ckpt / "meta.json").exists())
        self.assertTrue((spacy_ckpt / "spacy_finetune_summary.json").exists())
        self.assertTrue((opf_ckpt / "config.json").exists())
        self.assertTrue((opf_ckpt / "finetune_summary.json").exists())


if __name__ == "__main__":
    unittest.main()
