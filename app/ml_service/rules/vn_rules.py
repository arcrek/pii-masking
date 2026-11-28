"""Production deterministic rules for Vietnamese PII extraction (ML-03).

Free of benchmark-overfitted heuristics (no is_structured_payload_doc shortcut,
no NON_PII_STRUCTURED_KEYS exclusions).
"""

from __future__ import annotations

import re
from typing import List, Dict, Any

# Email
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Vietnamese Phone Numbers (mobile + landline)
VN_PHONE_RE = re.compile(r"(?:\+?84|0)(?:3[2-9]|5[25689]|7[06-9]|8[1-9]|9[0-9]|2[0-9]{2})[0-9]{7}\b")

# Citizen ID: CCCD (12 digits starting with 0), CMND (9 digits)
CCCD_RE = re.compile(r"\b0\d{11}\b")
CMND_RE = re.compile(r"\b\d{9}\b")

# Tax ID (MST: 10 or 10+3 digits)
TAX_ID_RE = re.compile(r"\b\d{10}(?:-\d{3})?\b")

# Vietnamese Passport Number (B, C, G, H, K, L, M + 7 or 8 digits)
VN_PASSPORT_RE = re.compile(r"\b[BCGHIKLM]\d{7,8}\b")

# Common Date Formats
DATE_RE = re.compile(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b")

# Credit Card Numbers
CREDIT_CARD_RE = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")


def extract_vn_production_rules(text: str) -> List[Dict[str, Any]]:
    """Extract deterministic Vietnamese PII spans from text."""
    if not text:
        return []

    spans: List[Dict[str, Any]] = []

    # 1. Email
    for m in EMAIL_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "EMAIL",
            "score": 1.0,
            "source": "rule",
        })

    # 2. Phone
    for m in VN_PHONE_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "TELEPHONENUM",
            "score": 0.99,
            "source": "rule",
        })

    # 3. Credit Card
    for m in CREDIT_CARD_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "CREDITCARDNUMBER",
            "score": 0.99,
            "source": "rule",
        })

    # 4. Passport
    for m in VN_PASSPORT_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "PASSPORTNUM",
            "score": 0.95,
            "source": "rule",
        })

    # 5. CCCD / CMND / Tax ID
    for m in CCCD_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "IDCARDNUM",
            "score": 0.98,
            "source": "rule",
        })

    for m in TAX_ID_RE.finditer(text):
        # Avoid clobbering CCCD
        if len(m.group(0)) == 10 or "-" in m.group(0):
            spans.append({
                "start": m.start(),
                "end": m.end(),
                "raw_label": "TAXNUM",
                "score": 0.92,
                "source": "rule",
            })

    # 6. Date
    for m in DATE_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "DATE",
            "score": 0.95,
            "source": "rule",
        })

    return spans
