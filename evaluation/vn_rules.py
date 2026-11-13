"""Deterministic Vietnamese PII recognizer and disambiguation rules for the 19 OpenPII labels.

Supports:
1. Standalone deterministic extraction (`extract_vn_deterministic_spans(text)`) across structured
   and semi-structured Vietnamese patterns (EMAIL, TELEPHONENUM, DATE, CREDITCARDNUMBER, IDCARDNUM,
   PASSPORTNUM, DRIVERLICENSENUM, TAXNUM, SOCIALNUM, ZIPCODE, AGE, GENDER, SEX, TITLE, BUILDINGNUM,
   STREET, CITY).
2. Disambiguation of coarse 8-label Pre-Finetune OPF spans (`refine_pretrained_opf_span_for_vn`)
   so we can measure both strict 1:1 mapping (`OPF_8_TO_OPENPII_19_PRIMARY_MAP`) and
   rule-enhanced pre-finetune OPF (`opf_pretrained_pre_plus_rules`).
3. Post-processing & merging (`combine_model_and_vn_rules`) that augments either `spaCy NER` or
   `OPF` predictions with high-precision Vietnamese regexes while avoiding over-masking on non-PII.
"""

from __future__ import annotations

import re
from typing import Any

# Strict 1:1 primary mapping from out-of-the-box 8-label OPF (`v2`) to OpenPII 19 labels
OPF_8_TO_OPENPII_19_PRIMARY_MAP: dict[str, str] = {
    "private_person": "GIVENNAME",
    "private_email": "EMAIL",
    "private_phone": "TELEPHONENUM",
    "private_address": "STREET",
    "private_date": "DATE",
    "private_url": "EMAIL",
    "account_number": "IDCARDNUM",
    "secret": "PASSPORTNUM",
}

# Coarse family equivalence sets for analyzing Pre-Finetune OPF's 8-label taxonomy vs OpenPII 19 labels
OPF_8_COMPATIBLE_FAMILIES: dict[str, set[str]] = {
    "private_person": {"GIVENNAME", "SURNAME", "TITLE"},
    "private_address": {"BUILDINGNUM", "STREET", "CITY", "ZIPCODE"},
    "private_date": {"DATE", "AGE"},
    "private_email": {"EMAIL"},
    "private_phone": {"TELEPHONENUM"},
    "account_number": {
        "CREDITCARDNUMBER",
        "IDCARDNUM",
        "PASSPORTNUM",
        "DRIVERLICENSENUM",
        "TAXNUM",
        "SOCIALNUM",
    },
    "secret": {
        "IDCARDNUM",
        "PASSPORTNUM",
        "DRIVERLICENSENUM",
        "TAXNUM",
        "SOCIALNUM",
        "CREDITCARDNUMBER",
    },
}

# 1. Email address
VN_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}\b")

# 2. Vietnamese & OpenPII phone formats
VN_PHONE_RE = re.compile(
    r"(?:\+84|0084|0)(?:[\s.-]*\d){8,10}\b"
    r"|\(\d{2,4}\)[\s.-]*\d{3,4}[\s.-]*\d{3,4}\b"
)
VN_PHONE_CTX_RE = re.compile(
    r"(?i)(?:điện\s+thoại(?:\s+di\s+động)?|sđt|đt|số\s+điện\s+thoại|liên\s+hệ(?:\s+qua\s+số)?|qua\s+số|hotline|tel|phone)\s*[:#-]?\s*"
    r"(\+?\d[\d\s.()-]{7,18}\d)"
)

# 3. Date formats (ISO, DD/MM/YYYY, YYYY-MM-DDTHH:MM:SS, Vietnamese "ngày ... tháng ... năm ...")
VN_ISO_DATE_RE = re.compile(
    r"\b(?:19\d\d|20\d\d)-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])"
    r"(?:T[0-2]\d:[0-5]\d(?::[0-5]\d)?(?:Z|[+-]\d{2}:?\d{2})?)?\b"
)
VN_SLASH_DATE_RE = re.compile(
    r"\b(?:0?[1-9]|[12]\d|3[01])[/-](?:0?[1-9]|1[0-2])[/-](?:19\d\d|20\d\d)\b"
)
VN_TEXT_DATE_RE = re.compile(
    r"(?i)\bngày\s+(\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+(?:19|20)\d{2})\b"
)

# 4. Credit card numbers (13-19 digits with spaces/dashes or context)
VN_CC_CTX_RE = re.compile(
    r"(?i)(?:thẻ\s+tín\s+dụng(?:\s+thanh\s+toán)?|số\s+thẻ|credit\s+card|thẻ\s+ngân\s+hàng)\s*[:#-]?\s*"
    r"(\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{3,4}|\d{13,19})\b"
)
VN_CC_FORMATTED_RE = re.compile(
    r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6011)[-\s]\d{4}[-\s]\d{4}[-\s]\d{3,4}\b"
)

# 5. ID Card / CCCD / CMND (`IDCARDNUM`)
VN_IDCARD_CTX_RE = re.compile(
    r"(?i)(?:cccd(?:\s+gắn\s+chip)?|cmnd|chứng\s+minh\s+nhân\s+dân|căn\s+cước(?:\s+công\s+dân)?|số\s+định\s+danh(?:\s+cá\s+nhân)?)\s*(?:số|là)?\s*[:#(-]?\s*"
    r"([A-Z0-9]{8,15})\b"
)

# 6. Passport (`PASSPORTNUM`)
VN_PASSPORT_CTX_RE = re.compile(
    r"(?i)(?<!cmnd/)(?<!cccd/)(?:hộ\s+chiếu|số\s+hộ\s+chiếu|passport)\s*(?:số|là)?\s*[:#(-]?\s*"
    r"([A-Z]{1,2}\d{6,9}|\d{8,10}|[A-Z0-9]{8,12})\b"
)

# 7. Driver's License (`DRIVERLICENSENUM`)
VN_GPLX_CTX_RE = re.compile(
    r"(?i)(?:gplx|giấy\s+phép\s+lái\s+xe|bằng\s+lái(?:\s+xe)?)\s*(?:số|hạng\s+[A-Z0-9]+\s+số|là)?\s*[:#(-]?\s*"
    r"([A-Z0-9-]{8,15})\b"
)

# 8. Tax ID (`TAXNUM`)
VN_TAX_CTX_RE = re.compile(
    r"(?i)(?:mã\s+số\s+thuế(?:\s+cá\s+nhân)?|mst|mã\s+thuế)\s*(?:số|là)?\s*[:#(-]?\s*"
    r"(\d{10}(?:-\d{3})?|[A-Z0-9-]{8,15})\b"
)

# 9. Social Security / BHXH (`SOCIALNUM`)
VN_SOCIAL_CTX_RE = re.compile(
    r"(?i)(?:mã\s+số\s+bhxh|số\s+sổ\s+bhxh|bảo\s+hiểm\s+xã\s+hội|bhxh|an\s+sinh\s+xã\s+hội)\s*(?:số|là)?\s*[:#(-]?\s*"
    r"([A-Z0-9-]{8,15})\b"
)

# 10. Zipcode / Postal code (`ZIPCODE`)
VN_ZIP_CTX_RE = re.compile(
    r"(?i)(?:mã\s+bưu\s+chính|mã\s+bưu\s+điện|zip(?:\s*code)?|postal\s+code)\s*[:#(-]?\s*"
    r"(\d{5,6})\b"
)
VN_CITY_PAREN_ZIP_RE = re.compile(
    r"(?:Thành\s+phố|Tỉnh)\s+[A-ZÀ-Ỹ][A-Za-zÀ-ỹ\s]{2,25}\s*\((\d{5,6})\)"
)

# 11. Age (`AGE`)
VN_AGE_CTX_RE = re.compile(
    r"(?i)(?<![/\w])(\d{1,2})\s+tuổi\b|(?:tuổi|độ\s+tuổi)\s*[:#-]?\s*(\d{1,2})(?![/\d])\b"
)

# 12. Gender & Sex (`GENDER`, `SEX`)
VN_SEX_CTX_RE = re.compile(
    r"(?i)(?:giới\s+tính\s+sinh\s+học|phái\s+sinh\s+học|sex)\s*[:#-]?\s*(Male|Female|Nam\s+giới|Nữ\s+giới|Phái\s+nam|Phái\s+nữ|Nam|Nữ|Đực|Cái)\b"
)
VN_GENDER_CTX_RE = re.compile(
    r"(?i)(?:nhận\s+dạng\s+giới\s+tính|giới\s+tính(?:\s+nhận\s+dạng)?|phái|gender)(?!\s+sinh\s+học)\s*[:#-]?\s*"
    r"(Agender|Bigender|Non-binary|Two-spirit|Male|Female|Nam\s+giới|Nữ\s+giới|Phái\s+nam|Phái\s+nữ|Nam|Nữ)\b"
)

# 13. Structured Person (`TITLE`, `SURNAME`, `GIVENNAME`) in Vietnamese forms/salutations
VN_TITLES_PATTERN = (
    r"Kế\s+toán\s+trưởng|Trưởng\s+phòng|Giám\s+đốc|Tiến\s+sĩ|Thạc\s+sĩ|Bác\s+sĩ|Kỹ\s+sư|Luật\s+sư|"
    r"Giáo\s+sư|Ông|Bà|Anh|Chị|Cô|Chú|Bác|Em"
)
VN_FULLNAME_CTX_RE = re.compile(
    rf"(?:Khách\s+hàng|Họ\s+và\s+tên(?:\s+người\s+lao\s+động)?|Người\s+nhận|Bệnh\s+nhân|Người\s+nộp\s+thuế|Chủ\s+tài\s+khoản|Họ\s+tên)\s*:\s*"
    rf"(?:(?P<title>{VN_TITLES_PATTERN})\s+)?"
    rf"(?P<surname>[A-ZÀ-Ỹ][a-zà-ỹ]+)\s+"
    rf"(?P<given>[A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){{0,3}})"
)

# 14. Structured Address (`BUILDINGNUM`, `STREET`, `CITY`)
VN_ADDRESS_CTX_RE = re.compile(
    r"(?:Địa\s+chỉ(?:\s+thường\s+trú|\s+giao\s+hàng|\s+liên\s+hệ)?|Chỗ\s+ở\s+hiện\s+nay|Tại\s+phòng)\s*(?::\s*)?(?:Nhà\s+số|Số|phòng)?\s*"
    r"(?P<bnum>\d+[A-Za-z]?(?:/\d+[A-Za-z]?)?)\s*,?\s*"
    r"(?P<street>(?:Đường|đường|Phố|phố|Đại\s+lộ|đại\s+lộ)\s+[A-ZÀ-Ỹa-zà-ỹ0-9\s]{3,35}?)\s*,\s*"
    r"(?:thành\s+phố\s+)?"
    r"(?P<city>(?:Thành\s+phố|Tỉnh)\s+[A-ZÀ-Ỹ][A-Za-zÀ-ỹ\s]{2,25}?)(?=[,.(\n]|$)"
)

# Technical / non-PII patterns for false-positive suppression in +VN Rules pipelines
VN_TECH_UNIT_RIGHT_RE = re.compile(
    r"^\s*(?:Gbps|Mbps|kbps|ms|Hz|kHz|MHz|GHz|nits|pixel|triệu\s+tấn|tấn\s+dầu|tấn\b(?=\s*\.|$)|km\s+đường|mét|lít|MB|GB|TB|kVA|U\b|"
    r"bộ\s+lưu\s+điện|tủ\s+rack|dây\s+nhảy|kết\s+nối|phút|giây|giờ|tháng\s+đối\s+với|năm\s*(?=\.|$)|độ\s+C)\b",
    re.IGNORECASE,
)
VN_TECH_PREFIX_LEFT_RE = re.compile(
    r"(?:HTTPS|HTTP|MTU(?:\s+bằng)?|AES-|RSA-|ISO-|QCVN\s*\d*:?|v\d+\.|gió\s+Đông\s+Bắc\s+cấp\s+\d*-?|OSPF\s+vùng\s+|nhiệt\s+độ\s+dao\s+động\s+từ(?:\s+\d+\s+đến)?|mực\s+nước[^\n]{0,30}từ|lưu\s+trữ\s+tối\s+thiểu|chờ\s+tối\s+đa|UTF-|mức\s+tải\s+trọng|sản\s+lượng\s+lúa\s+gạo[^\n]{0,25}|kim\s+ngạch\s+tăng)\s*$",
    re.IGNORECASE,
)
VN_NON_PII_EXACT_TOKENS = {
    "HTTP",
    "HTTPS",
    "JSON",
    "OSPF",
    "LC",
    "42U",
    "120Hz",
    "Nghị",
    "Thùng",
    "Đông Bắc",
    "Đồng bằng sông Cửu Long",
    "Cửu Long",
}


def filter_vn_false_positives(text: str, spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out deterministic non-PII technical measurements, protocol ports, and geographic region
    false alarms from model predictions.
    """
    filtered: list[dict[str, Any]] = []
    for sp in spans:
        s = int(sp["start"])
        e = int(sp["end"])
        lbl = str(sp["label"])
        span_txt = text[s:e].strip()
        if not span_txt:
            continue

        if span_txt in VN_NON_PII_EXACT_TOKENS or span_txt.startswith("#VN-EQ-"):
            continue

        left_ctx = text[max(0, s - 40) : s]
        right_ctx = text[e : min(len(text), e + 30)]

        if lbl in {
            "AGE",
            "BUILDINGNUM",
            "TAXNUM",
            "CREDITCARDNUMBER",
            "ZIPCODE",
            "TELEPHONENUM",
            "IDCARDNUM",
        }:
            if VN_TECH_UNIT_RIGHT_RE.search(right_ctx) or VN_TECH_PREFIX_LEFT_RE.search(left_ctx):
                continue

        filtered.append(sp)
    return filtered


def deduplicate_vn_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate overlapping spans, preferring higher score, then longer span."""
    valid = [
        sp
        for sp in spans
        if int(sp.get("end", 0)) > int(sp.get("start", 0)) and int(sp.get("start", 0)) >= 0
    ]
    valid.sort(
        key=lambda sp: (
            -float(sp.get("score", 1.0)),
            -(int(sp["end"]) - int(sp["start"])),
            int(sp["start"]),
        )
    )
    kept: list[dict[str, Any]] = []
    for cand in valid:
        cs, ce = int(cand["start"]), int(cand["end"])
        if any(min(ce, int(k["end"])) - max(cs, int(k["start"])) > 0 for k in kept):
            continue
        kept.append(cand)
    kept.sort(key=lambda sp: (int(sp["start"]), int(sp["end"])))
    return kept


def extract_vn_deterministic_spans(text: str) -> list[dict[str, Any]]:
    """Extract high-precision deterministic Vietnamese PII spans across the 19 OpenPII labels.
    Scores are tiered into:
    - `0.999`: Unambiguous context-anchored or RFC-structured patterns (`EMAIL`, `DATE`, `IDCARDNUM`,
      `PASSPORTNUM`, `DRIVERLICENSENUM`, `TAXNUM`, `SOCIALNUM`, `ZIPCODE`, `AGE`, `SEX`,
      context-anchored `CREDITCARDNUMBER`).
    - `0.94`: Heuristic/unanchored patterns (`GENDER`, `TELEPHONENUM`, `VN_FULLNAME_CTX_RE`, `VN_ADDRESS_CTX_RE`)
      that fill unpredicted gaps without overwriting fine-tuned model boundaries (`0.995`).
    """
    spans: list[dict[str, Any]] = []

    def add(s: int, e: int, label: str, score: float = 0.99) -> None:
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if 0 <= s < e <= len(text):
            spans.append(
                {
                    "start": s,
                    "end": e,
                    "label": label,
                    "text": text[s:e],
                    "score": score,
                }
            )

    for m in VN_EMAIL_RE.finditer(text):
        add(m.start(), m.end(), "EMAIL", 0.999)

    for m in VN_PHONE_CTX_RE.finditer(text):
        add(m.start(1), m.end(1), "TELEPHONENUM", 0.94)
    for m in VN_PHONE_RE.finditer(text):
        add(m.start(), m.end(), "TELEPHONENUM", 0.93)

    for m in VN_ISO_DATE_RE.finditer(text):
        add(m.start(), m.end(), "DATE", 0.999)
    for m in VN_SLASH_DATE_RE.finditer(text):
        add(m.start(), m.end(), "DATE", 0.999)
    for m in VN_TEXT_DATE_RE.finditer(text):
        add(m.start(1), m.end(1), "DATE", 0.999)

    for m in VN_CC_CTX_RE.finditer(text):
        add(m.start(1), m.end(1), "CREDITCARDNUMBER", 0.999)
    for m in VN_CC_FORMATTED_RE.finditer(text):
        add(m.start(), m.end(), "CREDITCARDNUMBER", 0.94)

    for m in VN_IDCARD_CTX_RE.finditer(text):
        add(m.start(1), m.end(1), "IDCARDNUM", 0.999)

    for m in VN_PASSPORT_CTX_RE.finditer(text):
        add(m.start(1), m.end(1), "PASSPORTNUM", 0.999)

    for m in VN_GPLX_CTX_RE.finditer(text):
        add(m.start(1), m.end(1), "DRIVERLICENSENUM", 0.999)

    for m in VN_TAX_CTX_RE.finditer(text):
        add(m.start(1), m.end(1), "TAXNUM", 0.999)

    for m in VN_SOCIAL_CTX_RE.finditer(text):
        add(m.start(1), m.end(1), "SOCIALNUM", 0.999)

    for m in VN_ZIP_CTX_RE.finditer(text):
        add(m.start(1), m.end(1), "ZIPCODE", 0.999)
    for m in VN_CITY_PAREN_ZIP_RE.finditer(text):
        add(m.start(1), m.end(1), "ZIPCODE", 0.999)

    for m in VN_AGE_CTX_RE.finditer(text):
        grp = 1 if m.group(1) is not None else 2
        add(m.start(grp), m.end(grp), "AGE", 0.999)

    for m in VN_SEX_CTX_RE.finditer(text):
        add(m.start(1), m.end(1), "SEX", 0.999)

    for m in VN_GENDER_CTX_RE.finditer(text):
        ctx_m = m.group(0).lower()
        # Explicit "nhận dạng giới tính" / "giới tính nhận dạng" is unambiguously GENDER (0.999),
        # whereas generic "giới tính" in OpenPII can be SEX or GENDER, so give 0.94 to only fill gaps.
        g_score = 0.999 if "nhận dạng" in ctx_m else 0.94
        add(m.start(1), m.end(1), "GENDER", g_score)

    for m in VN_FULLNAME_CTX_RE.finditer(text):
        if m.group("title"):
            add(m.start("title"), m.end("title"), "TITLE", 0.94)
        add(m.start("surname"), m.end("surname"), "SURNAME", 0.94)
        add(m.start("given"), m.end("given"), "GIVENNAME", 0.94)

    for m in VN_ADDRESS_CTX_RE.finditer(text):
        add(m.start("bnum"), m.end("bnum"), "BUILDINGNUM", 0.94)
        add(m.start("street"), m.end("street"), "STREET", 0.94)
        add(m.start("city"), m.end("city"), "CITY", 0.94)

    return filter_vn_false_positives(text, deduplicate_vn_spans(spans))


def refine_pretrained_opf_span_for_vn(
    text: str,
    start: int,
    end: int,
    opf_label: str,
) -> list[dict[str, Any]]:
    """Refine a coarse 8-label Pre-Finetune OPF prediction (`private_person`, `private_address`,
    `account_number`, etc.) into one or more 19-label OpenPII spans using local Vietnamese context.
    """
    span_text = text[start:end]
    ctx_left = text[max(0, start - 45) : start].lower()

    if opf_label == "private_email":
        return [{"start": start, "end": end, "label": "EMAIL", "score": 0.92}]
    if opf_label == "private_phone":
        return [{"start": start, "end": end, "label": "TELEPHONENUM", "score": 0.92}]
    if opf_label == "private_date":
        if "tuổi" in ctx_left or "tuổi" in text[end : min(len(text), end + 10)].lower():
            return [{"start": start, "end": end, "label": "AGE", "score": 0.90}]
        return [{"start": start, "end": end, "label": "DATE", "score": 0.92}]

    if opf_label in {"account_number", "secret"}:
        if any(k in ctx_left for k in ("thẻ tín dụng", "credit", "số thẻ", "visa", "master")):
            return [{"start": start, "end": end, "label": "CREDITCARDNUMBER", "score": 0.92}]
        if any(k in ctx_left for k in ("hộ chiếu", "passport")):
            return [{"start": start, "end": end, "label": "PASSPORTNUM", "score": 0.92}]
        if any(k in ctx_left for k in ("gplx", "lái xe", "bằng lái")):
            return [{"start": start, "end": end, "label": "DRIVERLICENSENUM", "score": 0.92}]
        if any(k in ctx_left for k in ("thuế", "mst", "tax")):
            return [{"start": start, "end": end, "label": "TAXNUM", "score": 0.92}]
        if any(k in ctx_left for k in ("bhxh", "bảo hiểm", "an sinh")):
            return [{"start": start, "end": end, "label": "SOCIALNUM", "score": 0.92}]
        if any(k in ctx_left for k in ("bưu chính", "bưu điện", "zip")):
            return [{"start": start, "end": end, "label": "ZIPCODE", "score": 0.92}]
        return [{"start": start, "end": end, "label": "IDCARDNUM", "score": 0.88}]

    if opf_label == "private_address":
        if span_text.isdigit() and 5 <= len(span_text) <= 6:
            return [{"start": start, "end": end, "label": "ZIPCODE", "score": 0.90}]
        if re.fullmatch(r"\d+[A-Za-z]?(?:/\d+[A-Za-z]?)?", span_text):
            return [{"start": start, "end": end, "label": "BUILDINGNUM", "score": 0.90}]
        if any(
            span_text.lower().startswith(p)
            for p in ("thành phố", "tỉnh", "hà nội", "đà nẵng", "hồ chí minh", "cần thơ", "hải phòng")
        ):
            return [{"start": start, "end": end, "label": "CITY", "score": 0.90}]
        return [{"start": start, "end": end, "label": "STREET", "score": 0.88}]

    if opf_label == "private_person":
        parts = [m for m in re.finditer(r"\S+", span_text)]
        if len(parts) >= 2:
            s0 = start + parts[0].start()
            e0 = start + parts[0].end()
            s_rest = start + parts[1].start()
            e_rest = start + parts[-1].end()
            return [
                {"start": s0, "end": e0, "label": "SURNAME", "score": 0.88},
                {"start": s_rest, "end": e_rest, "label": "GIVENNAME", "score": 0.88},
            ]
        return [{"start": start, "end": end, "label": "GIVENNAME", "score": 0.88}]

    mapped = OPF_8_TO_OPENPII_19_PRIMARY_MAP.get(opf_label, opf_label)
    return [{"start": start, "end": end, "label": mapped, "score": 0.85}]


def combine_model_and_vn_rules(
    text: str,
    model_spans: list[dict[str, Any]],
    is_pretrained_opf_8: bool = False,
) -> list[dict[str, Any]]:
    """Combine model predictions (`spaCy NER` or `OPF`) with deterministic Vietnamese rules:
    1. Filter out deterministic non-PII technical/measurement false positives (`filter_vn_false_positives`).
    2. For pre-finetune coarse 8-label models (`is_pretrained_opf_8=True`), refine coarse spans (`0.88-0.92`)
       and merge with deterministic rules (`0.93-0.999`).
    3. For fine-tuned 19-label models (`is_pretrained_opf_8=False`), fine-tuned spans receive `score=0.995`
       so unambiguous context-anchored rules (`0.999`) refine/fill exact structured identifiers while
       heuristic rules (`0.93-0.94`) only fill unpredicted gaps without overwriting fine-tuned spans.
    """
    det_spans = extract_vn_deterministic_spans(text)
    cleaned_model = filter_vn_false_positives(text, model_spans)
    processed_model: list[dict[str, Any]] = []
    for sp in cleaned_model:
        s = int(sp["start"])
        e = int(sp["end"])
        lbl = str(sp["label"])
        sc = float(sp.get("score", 0.90))
        if is_pretrained_opf_8:
            processed_model.extend(refine_pretrained_opf_span_for_vn(text, s, e, lbl))
        else:
            processed_model.append(
                {
                    "start": s,
                    "end": e,
                    "label": lbl,
                    "score": max(sc, 0.995),
                }
            )

    return filter_vn_false_positives(text, deduplicate_vn_spans(processed_model + det_spans))

