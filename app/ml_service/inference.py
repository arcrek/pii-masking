"""PII Inference Engine for Bilingual Detection (ML-03).

Production hardening:
- Uses clean rules from app.ml_service.rules (no benchmark shortcuts)
- Dispatches models based on language (Vietnamese model only runs on Vietnamese/mixed text)
- Excluded labels are filtered BEFORE deduplication to prevent shadowing of valid PII
- Proper chunk overlap validation and boundary-safe sliding window deduplication
- Explicit logging instead of silent exception swallowing
"""

from __future__ import annotations

import re
import uuid
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.contracts.pii_taxonomy import map_raw_label
from app.ml_service.rules.vn_rules import extract_vn_production_rules
from app.ml_service.rules.en_rules import extract_en_production_rules

logger = logging.getLogger(__name__)

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
    canonical_group: str
    score: float
    source: str
    model_version: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PiiInferenceEngine:
    """Production-grade engine for running bilingual PII inference on normalized text."""

    def __init__(
        self,
        model_version: str = "1.0.0",
        repo_root: Optional[Path | str] = None,
        max_chunk_chars: int = 1500,
        chunk_overlap: int = 200,
    ) -> None:
        if chunk_overlap <= 0 or chunk_overlap >= max_chunk_chars:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) must be > 0 and strictly < max_chunk_chars ({max_chunk_chars})."
            )

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
        """Attempt to load the Vietnamese spaCy model from checkpoints."""
        ckpt_path = self.repo_root / "checkpoints" / "spacy_vn_19_ner"
        if ckpt_path.is_dir():
            try:
                import spacy
                self._spacy_nlp = spacy.load(str(ckpt_path))
                logger.info("Successfully loaded spacy_vn_19_ner model from %s", ckpt_path)
            except ImportError:
                logger.info("spaCy package not installed; running in rule-based mode.")
            except Exception as e:
                logger.warning("Could not load spacy_vn_19_ner from %s: %s", ckpt_path, e)

    def detect_language(self, text: str) -> str:
        """Heuristic language detection: 'vi' or 'en'."""
        if VI_DIACRITICS_REGEX.search(text):
            return "vi"
        return "en"

    def _extract_rules(self, text: str, lang: str) -> List[Dict[str, Any]]:
        """Run deterministic rule-based detection using clean production extractors."""
        results: List[Dict[str, Any]] = []

        if lang == "vi":
            try:
                results.extend(extract_vn_production_rules(text))
            except Exception as e:
                logger.error("Error executing Vietnamese production rules: %s", e)
                raise
        elif lang == "en":
            try:
                results.extend(extract_en_production_rules(text))
            except Exception as e:
                logger.error("Error executing English production rules: %s", e)
                raise
        else:
            # Dual pass for mixed text
            try:
                results.extend(extract_vn_production_rules(text))
                results.extend(extract_en_production_rules(text))
            except Exception as e:
                logger.error("Error executing dual-pass rules: %s", e)
                raise

        return results

    def _extract_model(self, text: str, lang: str) -> List[Dict[str, Any]]:
        """Run neural NER model only when language matches model capability."""
        # Never run Vietnamese NER model on pure English text
        if lang == "en":
            return []

        if self._spacy_nlp is None:
            return []

        try:
            doc = self._spacy_nlp(text)
            results: List[Dict[str, Any]] = []
            for ent in doc.ents:
                # Use model-provided score or 1.0 indicator
                score = getattr(ent, "confidence", 1.0)
                results.append({
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "raw_label": ent.label_,
                    "score": float(score),
                    "source": "model",
                })
            return results
        except Exception as e:
            logger.error("Error during spaCy model inference: %s", e)
            raise

    def _deduplicate_spans(self, spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate overlapping spans: prefer longer match or higher score."""
        if not spans:
            return []

        # Sort by start asc, length desc (so longer span is considered first), score desc
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
                # If current span is within or equal to existing span
                if s_start >= d_start and s_end <= d_end:
                    overlap = True
                    break
                # If existing span is strictly within current span, replace existing
                if d_start >= s_start and d_end <= s_end:
                    deduped.remove(d)
                    break
                # Partial intersection: preserve longer match
                if not (s_end <= d_start or s_start >= d_end):
                    curr_len = s_end - s_start
                    prev_len = d_end - d_start
                    if curr_len > prev_len:
                        deduped.remove(d)
                        break
                    else:
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

        # 1. Extract rules and model outputs
        rule_spans = self._extract_rules(chunk_text, lang)
        model_spans = self._extract_model(chunk_text, lang)
        combined_raw = rule_spans + model_spans

        # 2. Critical Fix: Filter EXCLUDED_LABELS BEFORE deduplication
        # This prevents an excluded label (e.g. TITLE, URL) from shadowing valid PII (e.g. PERSON, EMAIL)
        valid_pii_candidates: List[Dict[str, Any]] = []
        for s in combined_raw:
            raw_lbl = s["raw_label"]
            group, is_excluded = map_raw_label(raw_lbl)
            if is_excluded or group is None:
                continue
            s_copy = dict(s)
            s_copy["canonical_group"] = group.value
            valid_pii_candidates.append(s_copy)

        # 3. Deduplicate valid PII candidates
        deduped = self._deduplicate_spans(valid_pii_candidates)

        entities: List[DetectedEntitySpan] = []
        for s in deduped:
            abs_start = s["start"] + offset
            abs_end = s["end"] + offset
            span_text = chunk_text[s["start"]:s["end"]]

            entities.append(
                DetectedEntitySpan(
                    entity_id=str(uuid.uuid4()),
                    start=abs_start,
                    end=abs_end,
                    text=span_text,
                    raw_label=s["raw_label"],
                    canonical_group=s["canonical_group"],
                    score=float(s.get("score", 1.0)),
                    source=s.get("source", "rule"),
                    model_version=self.model_version,
                )
            )

        return entities

    def predict(self, text: str, lang_hint: str = "auto") -> List[DetectedEntitySpan]:
        """Run PII detection on normalized text of arbitrary length with safe windowing."""
        if not text or not text.strip():
            return []

        if len(text) <= self.max_chunk_chars:
            return self.predict_chunk(text, offset=0, lang_hint=lang_hint)

        # Sliding window with overlap
        step = self.max_chunk_chars - self.chunk_overlap
        all_entities: List[DetectedEntitySpan] = []

        for i in range(0, len(text), step):
            chunk = text[i : i + self.max_chunk_chars]
            chunk_entities = self.predict_chunk(chunk, offset=i, lang_hint=lang_hint)
            all_entities.extend(chunk_entities)

        # Deduplicate across sliding window boundaries, preserving longer matches
        formatted_for_dedup = [
            {
                "start": e.start,
                "end": e.end,
                "score": e.score,
                "raw_label": e.raw_label,
                "orig": e,
            }
            for e in all_entities
        ]
        deduped = self._deduplicate_spans(formatted_for_dedup)

        return [d["orig"] for d in deduped]

    def predict_batch(self, texts: List[str], lang_hint: str = "auto") -> List[List[DetectedEntitySpan]]:
        """Run batch detection on a list of texts."""
        return [self.predict(t, lang_hint=lang_hint) for t in texts]
