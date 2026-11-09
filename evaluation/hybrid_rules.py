"""Deterministic targeted improvements & hybrid PII rules for English business documents."""

from __future__ import annotations

import re
from typing import Any


# High-precision US SSN patterns (with dashes, spaces, or contextual prefix)
SSN_DASH_RE = re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")
SSN_CONTEXT_RE = re.compile(
    r"(?i)(?:ssn|social\s+security(?:\s+number)?|tax\s*id|tin)\s*[:#-]?\s*"
    r"((?!000|666|9\d\d)\d{3}[-\s]?(?!00)\d{2}[-\s]?(?!0000)\d{4})\b"
)

# High-precision email address pattern
EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}\b"
)

# High-precision US / business phone pattern
PHONE_RE = re.compile(
    r"(?:(?:\+1[-.\s]?)?\(\d{3}\)\s*\d{3}[-.\s]\d{4}|\b(?:\+1[-.\s]?)?\d{3}[-.\s]\d{3}[-.\s]\d{4}\b)"
)

# ISO, numeric slash, and month-name date patterns
ISO_DATE_RE = re.compile(
    r"\b(?:19\d\d|20\d\d)-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])"
    r"(?:\s+(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?)?\b"
)
SLASH_DATE_RE = re.compile(
    r"\b(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01])/(?:19\d\d|20\d\d)\b"
)
MONTH_NAME_DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(?:0?[1-9]|[12]\d|3[01]),?\s+(?:19\d\d|20\d\d)\b"
)

# Full US street address pattern (number + street + city + state + zip)
US_FULL_ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9.\s]{2,35}?\s+"
    r"(?:Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Road|Rd|Lane|Ln|Way|Court|Ct|Terrace|PKWY|Parkway|Mall|Square|Plaza|Loop|Freeway|Expressway|Center\s+Drive)"
    r"(?:\s+(?:NE|NW|SE|SW|North|South|East|West))?"
    r"(?:,\s*(?:Suite|Ste|Apt|Floor|Fl)\s+[A-Za-z0-9-]+)?"
    r",\s*[A-Za-z.\s]{2,25},\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?\b"
)

# Honorifics that Gravitee splits from PERSON into HONORIFIC
LEADING_HONORIFIC_RE = re.compile(
    r"^(?:Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.|Rev\.|Hon\.|Monsieur|Herr|Señor)\s+"
)


def extract_deterministic_spans(text: str) -> list[dict[str, Any]]:
    """Extract high-precision structured PII spans (US_SSN, EMAIL_ADDRESS, PHONE_NUMBER, DATE_TIME, full US addresses)."""
    spans: list[dict[str, Any]] = []

    for m in SSN_DASH_RE.finditer(text):
        spans.append({"start": m.start(), "end": m.end(), "label": "US_SSN", "score": 0.99})

    for m in SSN_CONTEXT_RE.finditer(text):
        spans.append({"start": m.start(1), "end": m.end(1), "label": "US_SSN", "score": 0.99})

    for m in EMAIL_RE.finditer(text):
        spans.append({"start": m.start(), "end": m.end(), "label": "EMAIL_ADDRESS", "score": 0.99})

    for m in PHONE_RE.finditer(text):
        spans.append({"start": m.start(), "end": m.end(), "label": "PHONE_NUMBER", "score": 0.98})

    for rx in (ISO_DATE_RE, SLASH_DATE_RE, MONTH_NAME_DATE_RE):
        for m in rx.finditer(text):
            spans.append({"start": m.start(), "end": m.end(), "label": "DATE_TIME", "score": 0.97})

    for m in US_FULL_ADDRESS_RE.finditer(text):
        spans.append({"start": m.start(), "end": m.end(), "label": "LOCATION", "score": 0.98})

    return deduplicate_spans(spans)


def refine_opf_span(text: str, start: int, end: int, opf_label: str) -> dict[str, Any]:
    """Map an OpenAI Privacy Filter span to the Gravitee 25-label taxonomy, with disambiguation for account_number."""
    s = max(0, min(len(text), start))
    e = max(s, min(len(text), end))
    while s < e and text[s].isspace():
        s += 1
    while e > s and text[e - 1].isspace():
        e -= 1

    span_str = text[s:e]

    if opf_label == "account_number":
        if SSN_DASH_RE.fullmatch(span_str) or re.fullmatch(r"\d{3}[-\s]?\d{2}[-\s]?\d{4}", span_str):
            # Check context for ITIN (starts with 9) vs SSN
            if span_str.startswith("9"):
                return {"start": s, "end": e, "label": "US_ITIN", "score": 0.95}
            return {"start": s, "end": e, "label": "US_SSN", "score": 0.95}
        if re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9\s]{10,30}", span_str):
            return {"start": s, "end": e, "label": "IBAN_CODE", "score": 0.95}
        digits_only = re.sub(r"\D", "", span_str)
        if len(digits_only) in (15, 16):
            return {"start": s, "end": e, "label": "CREDIT_CARD", "score": 0.92}
        return {"start": s, "end": e, "label": "US_BANK_NUMBER", "score": 0.85}

    mapping = {
        "private_person": "PERSON",
        "private_email": "EMAIL_ADDRESS",
        "private_phone": "PHONE_NUMBER",
        "private_address": "LOCATION",
        "private_date": "DATE_TIME",
        "private_url": "URL",
        "secret": "PASSWORD",
    }
    return {
        "start": s,
        "end": e,
        "label": mapping.get(opf_label, opf_label),
        "score": 0.95,
    }


def merge_contiguous_locations(text: str, spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge adjacent LOCATION spans separated only by comma/whitespace/ZIP code (fixes spaCy GPE+LOC fragmentation)."""
    if not spans:
        return []
    ordered = sorted(spans, key=lambda x: (x["start"], x["end"]))
    merged: list[dict[str, Any]] = []

    for sp in ordered:
        if not merged:
            merged.append(dict(sp))
            continue
        prev = merged[-1]
        if prev["label"] == "LOCATION" and sp["label"] == "LOCATION":
            gap = text[prev["end"] : sp["start"]]
            if re.fullmatch(r"[\s,]*(?:Suite\s+[A-Za-z0-9-]+[\s,]*)?", gap):
                prev["end"] = max(prev["end"], sp["end"])
                # Also absorb trailing 5-digit ZIP code if immediately following
                tail = text[prev["end"] : prev["end"] + 12]
                zip_m = re.match(r"^[\s,]+\d{5}(?:-\d{4})?\b", tail)
                if zip_m:
                    prev["end"] += zip_m.end()
                continue
        merged.append(dict(sp))
    return merged


def deduplicate_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve overlapping spans by preferring higher priority/score and longer span coverage."""
    if not spans:
        return []

    label_priority = {
        "US_SSN": 10,
        "EMAIL_ADDRESS": 10,
        "PHONE_NUMBER": 9,
        "LOCATION": 8,
        "PERSON": 8,
        "DATE_TIME": 7,
    }

    sorted_spans = sorted(
        spans,
        key=lambda s: (
            -(s["end"] - s["start"]),
            -label_priority.get(s["label"], 5),
            -float(s.get("score", 0.5)),
            s["start"],
        ),
    )

    kept: list[dict[str, Any]] = []
    for cand in sorted_spans:
        if cand["end"] <= cand["start"]:
            continue
        overlaps = False
        for k in kept:
            inter = min(cand["end"], k["end"]) - max(cand["start"], k["start"])
            if inter > 0:
                overlaps = True
                break
        if not overlaps:
            kept.append(cand)

    return sorted(kept, key=lambda s: (s["start"], s["end"]))


def build_hybrid_predictions(
    text: str,
    opf_raw_spans: list[dict[str, Any]],
    presidio_spans: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Combine OPF neural spans, Presidio NER/pattern spans, and deterministic business rules."""
    combined: list[dict[str, Any]] = []

    # 1. Deterministic structured rules (highest precision for SSN, Email, Phone, Full US Address, Dates)
    det_spans = extract_deterministic_spans(text)
    combined.extend(det_spans)

    # 2. Refined OPF neural spans (strong contextual PERSON, LOCATION, secret/account)
    for sp in opf_raw_spans:
        refined = refine_opf_span(text, int(sp["start"]), int(sp["end"]), str(sp["label"]))
        combined.append(refined)

    # 3. Presidio spans (adds broad DATE_TIME, LOCATION, NRP, ORGANIZATION, etc. where OPF is private-only)
    pres_merged = merge_contiguous_locations(text, presidio_spans)
    for sp in pres_merged:
        s = int(sp["start"])
        e = int(sp["end"])
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if e > s:
            combined.append(
                {
                    "start": s,
                    "end": e,
                    "label": str(sp["label"]),
                    "score": float(sp.get("score", 0.75)),
                }
            )

    return deduplicate_spans(combined)
