"""PII Inference Engine for Bilingual Detection (ML-03).

Acceptance Criteria for ML-03:
- Nhận normalized text, trả entity spans, label, score và model version.
- Batch/empty/long text xử lý được mà không lỗi.
- Score không tự coi là probability (giữ nguyên score gốc).
- Model load được ngoài Colab (chạy cục bộ bằng checkpoint và rule engine).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.contracts.pii_taxonomy import map_raw_label, CanonicalGroup

# Detect Vietnamese diacritics
VI_DIACRITICS_REGEX = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđĐ]",
    re.IGNORECASE,
)


@dataclass
class DetectedEntitySpan:
    """A detected PII entity span."""
    entity_id: str
    start: int
    end: int
    text: str
    raw_label: str
    canonical_group: Optional[str]
    score: float
    source: str
    model_version: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PiiInferenceEngine:
    """Engine for running PII inference on normalized text."""

    def __init__(
        self,
        model_version: str = "1.0.0",
        repo_root: Optional[Path | str] = None,
        max_chunk_chars: int = 1500,
        chunk_overlap: int = 200,
    ) -> None:
        if repo_root is None:
            self.repo_root = Path(__file__).resolve().parent.parent.parent
        else:
            self.repo_root = Path(repo_root)

        self.model_version = model_version
        self.max_chunk_chars = max_chunk_chars
        self.chunk_overlap = chunk_overlap
        self._spacy_nlp = None
        self._try_load_spacy_model()

    def _try_load_spacy_model(self) -> None:
        """Attempt to load the spaCy model from checkpoints outside Colab."""
        ckpt_path = self.repo_root / "checkpoints" / "spacy_vn_19_ner"
        if ckpt_path.is_dir():
            try:
                import spacy
                self._spacy_nlp = spacy.load(str(ckpt_path))
            except Exception:
                # spacy not installed or checkpoint format incompatible with host python
                self._spacy_nlp = None

    def detect_language(self, text: str) -> str:
        """Heuristic language detection: 'vi' or 'en'."""
        if VI_DIACRITICS_REGEX.search(text):
            return "vi"
        return "en"

    def _extract_rules(self, text: str, lang: str) -> List[Dict[str, Any]]:
        """Run deterministic rule-based detection."""
        results: List[Dict[str, Any]] = []

        if lang == "vi":
            try:
                from evaluation.vn_rules import extract_vn_deterministic_spans
                raw_spans = extract_vn_deterministic_spans(text)
                for s in raw_spans:
                    results.append({
                        "start": s["start"],
                        "end": s["end"],
                        "raw_label": s["label"],
                        "score": s.get("score", 1.0),
                        "source": "rule",
                    })
            except Exception:
                pass
        else:
            try:
                from evaluation.hybrid_rules import extract_deterministic_spans
                raw_spans = extract_deterministic_spans(text)
                for s in raw_spans:
                    results.append({
                        "start": s["start"],
                        "end": s["end"],
                        "raw_label": s["label"],
                        "score": s.get("score", 1.0),
                        "source": "rule",
                    })
            except Exception:
                pass

        return results

    def _extract_model(self, text: str) -> List[Dict[str, Any]]:
        """Run neural NER model if available."""
        if self._spacy_nlp is None:
            return []

        doc = self._spacy_nlp(text)
        results: List[Dict[str, Any]] = []
        for ent in doc.ents:
            results.append({
                "start": ent.start_char,
                "end": ent.end_char,
                "raw_label": ent.label_,
                "score": 0.85,  # Raw non-probabilistic indicator score
                "source": "model",
            })
        return results

    def _deduplicate_spans(self, spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate overlapping spans: prefer longer match or higher score."""
        if not spans:
            return []

        # Sort by start asc, length desc, score desc
        sorted_spans = sorted(
            spans,
            key=lambda x: (x["start"], -(x["end"] - x["start"]), -x.get("score", 0.0)),
        )

        deduped: List[Dict[str, Any]] = []
        for span in sorted_spans:
            s_start, s_end = span["start"], span["end"]
            overlap = False
            for d in deduped:
                d_start, d_end = d["start"], d["end"]
                # Exact or containment overlap
                if s_start >= d_start and s_end <= d_end:
                    overlap = True
                    break
                if d_start >= s_start and d_end <= s_end:
                    # Current span is strictly wider, replace
                    deduped.remove(d)
                    break
                # Partial intersection
                if not (s_end <= d_start or s_start >= d_end):
                    overlap = True
                    break
            if not overlap:
                deduped.append(span)

        return sorted(deduped, key=lambda x: x["start"])

    def predict_chunk(self, chunk_text: str, offset: int = 0, lang_hint: str = "auto") -> List[DetectedEntitySpan]:
        """Run prediction on a single chunk of text."""
        if not chunk_text or not chunk_text.strip():
            return []

        lang = self.detect_language(chunk_text) if lang_hint == "auto" else lang_hint

        # 1. Run deterministic rules
        rule_spans = self._extract_rules(chunk_text, lang)

        # 2. Run model inference if loaded
        model_spans = self._extract_model(chunk_text)

        # 3. Combine and deduplicate
        combined = self._deduplicate_spans(rule_spans + model_spans)

        entities: List[DetectedEntitySpan] = []
        for s in combined:
            raw_lbl = s["raw_label"]
            group, is_excluded = map_raw_label(raw_lbl)
            if is_excluded:
                continue

            abs_start = s["start"] + offset
            abs_end = s["end"] + offset
            span_text = chunk_text[s["start"]:s["end"]]

            entities.append(
                DetectedEntitySpan(
                    entity_id=str(uuid.uuid4()),
                    start=abs_start,
                    end=abs_end,
                    text=span_text,
                    raw_label=raw_lbl,
                    canonical_group=group.value if group else None,
                    score=float(s.get("score", 1.0)),
                    source=s.get("source", "rule"),
                    model_version=self.model_version,
                )
            )

        return entities

    def predict(self, text: str, lang_hint: str = "auto") -> List[DetectedEntitySpan]:
        """Run PII detection on normalized text of arbitrary length."""
        if not text or not text.strip():
            return []

        # If text is within chunk limit, process directly
        if len(text) <= self.max_chunk_chars:
            return self.predict_chunk(text, offset=0, lang_hint=lang_hint)

        # Long text processing: sliding window
        step = self.max_chunk_chars - self.chunk_overlap
        all_entities: List[DetectedEntitySpan] = []

        for i in range(0, len(text), step):
            chunk = text[i : i + self.max_chunk_chars]
            chunk_entities = self.predict_chunk(chunk, offset=i, lang_hint=lang_hint)
            all_entities.extend(chunk_entities)

        # Deduplicate across chunk boundaries
        entity_dicts = [e.to_dict() for e in all_entities]
        # Adapt for deduplicate_spans
        formatted_for_dedup = [
            {
                "start": e["start"],
                "end": e["end"],
                "score": e["score"],
                "raw_label": e["raw_label"],
                "orig": e,
            }
            for e in entity_dicts
        ]
        deduped = self._deduplicate_spans(formatted_for_dedup)

        return [
            DetectedEntitySpan(
                entity_id=d["orig"]["entity_id"],
                start=d["start"],
                end=d["end"],
                text=d["orig"]["text"],
                raw_label=d["orig"]["raw_label"],
                canonical_group=d["orig"]["canonical_group"],
                score=d["orig"]["score"],
                source=d["orig"]["source"],
                model_version=d["orig"]["model_version"],
            )
            for d in deduped
        ]

    def predict_batch(self, texts: List[str], lang_hint: str = "auto") -> List[List[DetectedEntitySpan]]:
        """Run batch detection on a list of texts."""
        return [self.predict(t, lang_hint=lang_hint) for t in texts]
