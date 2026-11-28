"""Production deterministic rules for Vietnamese PII extraction (ML-03).

Free of benchmark-overfitted heuristics.
"""

from __future__ import annotations

import re
from typing import List, Dict, Any

# Email
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Vietnamese Phone Numbers (mobile + landline with optional separators . - space)
# Mobiles: 10 digits total starting with 03, 05, 07, 08, 09 or +84
VN_MOBILE_RE = re.compile(
    r"(?<!\w)(?:\+?84|0)[-.\s]?(?:3[2-9]|5[25689]|7[06-9]|8[1-9]|9\d)(?:[-.\s]?\d){7}\b"
)
# Landlines: 11 digits total starting with 02x (e.g. 024 Hanoi, 028 HCMC, 02xx provinces)
VN_LANDLINE_RE = re.compile(
    r"(?<!\w)(?:\+?84|0)[-.\s]?2\d{1,2}(?:[-.\s]?\d){7,8}\b"
)

# Citizen ID: CCCD (12 digits starting with 0), CMND (9 digits with context)
CCCD_STANDALONE_RE = re.compile(r"\b0\d{11}\b")
VN_ID_CTX_RE = re.compile(
    r"(?i)(?:căn\s+cước\s+công\s+dân|cccd|chứng\s+minh\s+nhân\s+dân|chứng\s+minh\s+thư|cmnd|cmnd/cccd|số\s+định\s+danh)\s*(?:số|là)?\s*[:#(-]?\s*"
    r"(\d{9}|\d{12})\b"
)

# Tax ID (MST: 10 or 10+3 digits with context anchor)
VN_TAX_CTX_RE = re.compile(
    r"(?i)(?:mã\s+số\s+thuế(?:\s+cá\s+nhân)?|mst|mã\s+thuế|tax\s*(?:id|code)?)\s*(?:số|là)?\s*[:#(-]?\s*"
    r"(\d{10}(?:-\d{3})?)\b"
)

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

    # 2. Phone (Mobile & Landline)
    for m in VN_MOBILE_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "TELEPHONENUM",
            "score": 0.99,
            "source": "rule",
        })
    for m in VN_LANDLINE_RE.finditer(text):
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

    # 5. CCCD / CMND
    for m in CCCD_STANDALONE_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "IDCARDNUM",
            "score": 0.98,
            "source": "rule",
        })
    for m in VN_ID_CTX_RE.finditer(text):
        spans.append({
            "start": m.start(1),
            "end": m.end(1),
            "raw_label": "IDCARDNUM",
            "score": 0.99,
            "source": "rule",
        })

    # 6. Tax ID (Context anchored)
    for m in VN_TAX_CTX_RE.finditer(text):
        spans.append({
            "start": m.start(1),
            "end": m.end(1),
            "raw_label": "TAXNUM",
            "score": 0.95,
            "source": "rule",
        })

    # 7. Date
    for m in DATE_RE.finditer(text):
        spans.append({
            "start": m.start(),
            "end": m.end(),
            "raw_label": "DATE",
            "score": 0.90,
            "source": "rule",
        })

    return spans
