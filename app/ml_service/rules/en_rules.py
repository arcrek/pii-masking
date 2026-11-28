"""Production deterministic rules for English PII extraction (ML-03).

Free of benchmark-overfitted heuristics.
"""

from __future__ import annotations

import re
from typing import List, Dict, Any

# Email
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# US / International Phone Numbers
EN_PHONE_RE = re.compile(r"(?:\+?1[-. ]?)?\(?\b[2-9]\d{2}\)?[-. ]?\d{3}[-. ]?\d{4}\b")

# US Social Security Number (SSN: 3-2-4 digits)
US_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# Credit Card Numbers
CREDIT_CARD_RE = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")

# Date time pattern
DATE_TIME_RE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})\b",
    re.IGNORECASE,
)

# IBAN Code (standard 15-34 characters, handles space formatting e.g. DE89 3704 0044 0532 0130 00 without ReDoS)
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){3,7}(?:[ ]?[A-Z0-9]{1,4})?\b")


def extract_en_production_rules(text: str) -> List[Dict[str, Any]]:
    """Extract deterministic English PII spans from text."""
    if not text:
        return []

    spans: List[Dict[str, Any]] = []

    # 1. Email
    for m in EMAIL_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "EMAIL_ADDRESS",
            "score": 1.0,
            "source": "rule",
        })

    # 2. Phone
    for m in EN_PHONE_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "PHONE_NUMBER",
            "score": 0.99,
            "source": "rule",
        })

    # 3. US SSN
    for m in US_SSN_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "US_SSN",
            "score": 0.99,
            "source": "rule",
        })

    # 4. IBAN Code (extracted before credit card so longer IBAN spans take precedence)
    for m in IBAN_RE.finditer(text):
        raw_iban = m.group(0).replace(" ", "")
        if 15 <= len(raw_iban) <= 34:
            spans.append({
                "start": m.start(),
                "end": m.end(),
                "raw_label": "IBAN_CODE",
                "score": 0.99,
                "source": "rule",
            })

    # 5. Credit Card
    for m in CREDIT_CARD_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "CREDIT_CARD",
            "score": 0.99,
            "source": "rule",
        })

    # 6. Date Time
    for m in DATE_TIME_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "DATE_TIME",
            "score": 0.95,
            "source": "rule",
        })

    return spans
