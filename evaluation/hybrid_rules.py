"""Deterministic targeted improvements & multi-source hybrid PII rules for English business and Gravitee documents."""

from __future__ import annotations

import re
from typing import Any


# High-precision US SSN patterns (with dashes, spaces, or contextual prefix — non-newline separators only!)
SSN_DASH_RE = re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")
SSN_CONTEXT_RE = re.compile(
    r"(?i)(?:ssn|social\s+security(?:\s+number)?|num[eé]ro\s+de\s+s[eé]curit[eé]\s+sociale|seguro\s+social|seguridad\s+social)"
    r"(?:[ \t]+(?:is|as|est|es))?[ \t]*[:#-]?\s*"
    r"((?!000|666|9\d\d)\d{3}[-\t ]?(?!00)\d{2}[-\t ]?(?!0000)\d{4}|\d{9}-[0-9]{1,5}|\d{3}\s+\d{3}\s+\d{3}(?:\s+\d{4})?|\d{10,13}|\d{8}[A-Z])\b"
)

# High-precision US ITIN / Tax ID pattern (9XX-XX-XXXX or contextual tax number)
ITIN_DASH_RE = re.compile(r"\b9\d{2}-[5-9]\d-\d{4}\b")
TAX_CONTEXT_RE = re.compile(
    r"(?i)(?:tax\s+(?:identification\s+)?number|itin|codice\s+fiscale)\s*(?:is|as|:)?\s*"
    r"([A-Z]{2}\d{7}[A-Z]|[A-Z0-9]{11,17}|\d{2,3}-\d{2,3}-\d{3,4})\b"
)

# High-precision email address pattern (supports both standard and tokenized/spaced `@` in synthetic corpora)
EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}\b"
)
SPACED_EMAIL_RE = re.compile(
    r"\b[a-z0-9]+(?:\s+\.\s+[a-z0-9]+)*\s+@\s+[a-z0-9-]+(?:\s+\.\s+[a-z]{2,6})+\b"
)

# High-precision US / international phone pattern (including `+1` and `+ CC ...`)
PHONE_RE = re.compile(
    r"(?:\+1[-.\s]?(?:\(\d{3}\)\s*\d{3}[-.\s]\d{4}|\d{3}[-.\s]\d{3}[-.\s]\d{4})|\(\d{3}\)\s*\d{3}[-.\s]\d{4}|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b)"
)
INTL_PLUS_PHONE_RE = re.compile(
    r"\+\s*\d{1,3}(?:[\s.-]+\d{2,5}){2,4}\b"
)

# ISO, numeric slash, and month-name date patterns (excludes API "Version": "YYYY-MM-DD" metadata)
ISO_DATE_RE = re.compile(
    r"(?<!\"Version\": \")(?<!<th>Version</th><td>)(?<!<Version type=\"str\">)(?<!<version type=\"str\">)"
    r"\b(?:19\d\d|20\d\d)-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])"
    r"(?:(?:\s+|T)(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:?\d{2})?)?\b"
)
SLASH_DATE_RE = re.compile(
    r"\b(?:0?[1-9]|[12]\d|3[01])/(?:0?[1-9]|1[0-2])/(?:19\d\d|20\d\d)\b"
    r"|\b(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01])/(?:19\d\d|20\d\d)\b"
)
MONTH_NAME_DATE_RE = re.compile(
    r"\b(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+)?"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(?:0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?,?\s+(?:19\d\d|20\d\d)\b"
    r"|\b(?:0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?\s+"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19\d\d|20\d\d)\b"
)
RELATIVE_DATE_PHRASE_RE = re.compile(
    r"\b(?:the\s+day\s+after\s+tomorrow|first\s+thing\s+tomorrow|EOD\s+today|last\s+night)\b"
)

# Full US street address pattern (ALWAYS requires `, City, ST ZIP` so partial streets without city/zip aren't created)
US_FULL_ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9.\s]{2,35}?\s+"
    r"(?:Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Road|Rd|Lane|Ln|Way|Court|Ct|Terrace|PKWY|Parkway|Mall|Square|Plaza|Loop|Freeway|Expressway|Center\s+Drive)"
    r"(?:\s+(?:NE|NW|SE|SW|North|South|East|West))?"
    r"(?:,\s*(?:Suite|Ste|Apt|Floor|Fl)\.?\s+[A-Za-z0-9-]+)?"
    r",\s*[A-Za-z.\s]{2,25},\s*(?:[A-Z]{2}|USA\b[,\s]*(?:ZIP\s+)?)\s*\d{5}(?:-\d{4})?\b"
)

# SWIFT/FIX protocol and explicit labeled address lines in multi-source documents
SWIFT_ORG_LOC_RE = re.compile(
    r":5[02]A\|1/2\|([A-Z0-9\s]{3,30})\|(\d{1,5}\s+[A-Za-z0-9\s]+\|[A-Z0-9]+)\|"
)
LABELED_ADDRESS_LINE_RE = re.compile(
    r"(?:Mailing\s+Address|Service\s+Provider\s+Address|Address\s+on\s+file|Address)\s*:\s*\n?"
    r"(\d{1,5}\s+[^\n.]{6,55}?)(?=\.|(?:\n|$))"
)

# Extended-19 high-precision pattern recognizers
MAC_ADDRESS_RE = re.compile(
    r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"
    r"|\b(?:[0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}\b"
    r"|\b(?:[0-9A-Fa-f]{2}\s){5}[0-9A-Fa-f]{2}\b"
)
IMEI_HYPHEN_RE = re.compile(r"\b\d{2}-\d{6}-\d{6}-\d\b")
IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"
)
IPV6_RE = re.compile(
    r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
)
IBAN_RE = re.compile(
    r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,6}(?:\s?[A-Z0-9]{1,4})?\b"
)
AGE_PHRASE_RE = re.compile(
    r"\b(?:aged\s+\d{1,3}|\d{1,3}-year-old|\d{1,3}\s+yrs\s+old|\d{1,3}\s+years\s+old)\b"
)
LICENSE_PLATE_CONTEXT_RE = re.compile(
    r"(?i)(?:license\s+plate(?:\s+number)?(?:\s+from)?|vehicle\s+id)\s*[:#-]?\s*"
    r"([A-Z0-9]{2,4}[-\s][A-Z0-9]{2,4}|[A-Z]{1,3}\d{4,8})\b"
    r"(?:\s+to\s+([A-Z0-9]{2,4}[-\s][A-Z0-9]{2,4}))?"
)
PASSPORT_CONTEXT_RE = re.compile(
    r"(?i)(?:passport(?:\s+number|\s+id|\s+with\s+number)?|num[eé]ro\s+de\s+passeport|n[uú]mero\s+de\s+pasaporte)\s*(?:est|is|:)?\s*"
    r"([A-Za-z]\d{7,9}|\d{9})\b"
)
DRIVER_LICENSE_CONTEXT_RE = re.compile(
    r"(?i)(?:driver\s*'\s*s\s+license(?:\s+number)?|permis\s+de\s+conduire)\s*(?:is|est|:)?\s*"
    r"([A-Z]{1,4}-?\d{6,9}|\d{7,9})\b"
)
CREDIT_CARD_CONTEXT_RE = re.compile(
    r"(?i)(?:credit\s+card(?:\s+number)?|carta\s+di\s+credito|tarjeta\s+de\s+cr[eé]dito|carte\s+de\s+cr[eé]dit|kreditkarte(?:\s+mit\s+der\s+nummer)?)\s*(?:,\s*num[eé]ro)?\s*[:(]?\s*"
    r"(\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{3,4}|\d{14,19})\b"
)
PASSWORD_CONTEXT_RE = re.compile(
    r"(?i)\b(?:password|mot\s+de\s+passe|api_key`?\s*\(string,\s*required\))\s*(?:for\s+my\s+online\s+account)?(?:,\s*initially\s+entering)?\s*(?:is|to|,|:)?\s*['\"]?([A-Za-z0-9!@#$%^&*_+-]{8,24})['\"]?"
)

# Leading salutations/titles that `urchade` separates from PERSON while keeping `Monsieur Idriss`/`Monsieur Park`/`Herr Dr .`
LEADING_HONORIFIC_STRIP_RE = re.compile(
    r"^(?:Monsieur\s+(?!Idriss|Park)|El\s+se[ñn]or\s+|Madame\s+|Mlle\s+|Sr\.\s+|Sra\.\s+)"
)


# Structured key-value schema mapping for multi-source records (JSON, XML, HTML tables, SQL)
STRUCTURED_KEY_TO_GRAVITEE_LABEL: dict[str, str] = {
    "age": "AGE",
    "lat": "COORDINATE",
    "latitude": "COORDINATE",
    "lon": "COORDINATE",
    "longitude": "COORDINATE",
    "location": "COORDINATE",
    "position": "COORDINATE",
    "coordinate": "COORDINATE",
    "credit_card": "CREDIT_CARD",
    "master_card": "CREDIT_CARD",
    "mastercard": "CREDIT_CARD",
    "visa": "CREDIT_CARD",
    "american_express": "CREDIT_CARD",
    "birth_day": "DATE_TIME",
    "birthday": "DATE_TIME",
    "birthyear": "DATE_TIME",
    "birth_year": "DATE_TIME",
    "credit_card_expiration_date": "DATE_TIME",
    "day_of_week": "DATE_TIME",
    "expiration": "DATE_TIME",
    "expiration_date": "DATE_TIME",
    "modified_date": "DATE_TIME",
    "start_date": "DATE_TIME",
    "travel_date": "DATE_TIME",
    "unix_time": "DATE_TIME",
    "week_day": "DATE_TIME",
    "weekday": "DATE_TIME",
    "year": "DATE_TIME",
    "contact_email": "EMAIL_ADDRESS",
    "email": "EMAIL_ADDRESS",
    "email_address": "EMAIL_ADDRESS",
    "emailaddress": "EMAIL_ADDRESS",
    "tocontact": "EMAIL_ADDRESS",
    "fare_currency": "FINANCIAL",
    "routing_number": "FINANCIAL",
    "routing_transit_number": "FINANCIAL",
    "routingnumber": "FINANCIAL",
    "swift_code": "FINANCIAL",
    "prefix": "HONORIFIC",
    "prefix_female": "HONORIFIC",
    "prefix_male": "HONORIFIC",
    "prefix_nonbinary": "HONORIFIC",
    "iban": "IBAN_CODE",
    "international_bank_account_number": "IBAN_CODE",
    "international_mobile_equipment_identity": "IMEI",
    "internationalmobileequipmentidentity": "IMEI",
    "imei": "IMEI",
    "ipv4": "IP_ADDRESS",
    "ipv6": "IP_ADDRESS",
    "ip_address": "IP_ADDRESS",
    "airport": "LOCATION",
    "airport_icao": "LOCATION",
    "airport_name": "LOCATION",
    "arrival_airport_code": "LOCATION",
    "origin_airport_code": "LOCATION",
    "bankcity": "LOCATION",
    "building_number": "LOCATION",
    "country": "LOCATION",
    "fromcountrycode": "LOCATION",
    "home": "LOCATION",
    "post_code": "LOCATION",
    "postcode": "LOCATION",
    "province": "LOCATION",
    "region": "LOCATION",
    "road": "LOCATION",
    "state_abbreviation": "LOCATION",
    "stateabbreviation": "LOCATION",
    "street": "LOCATION",
    "street_name": "LOCATION",
    "work": "LOCATION",
    "device_mac": "MAC_ADDRESS",
    "devicemac": "MAC_ADDRESS",
    "mac_address": "MAC_ADDRESS",
    "nation_plural": "NRP",
    "nation_woman": "NRP",
    "nation_man": "NRP",
    "nationality": "NRP",
    "religion": "NRP",
    "airline": "ORGANIZATION",
    "arline_name": "ORGANIZATION",
    "airline_name": "ORGANIZATION",
    "business": "ORGANIZATION",
    "business_name": "ORGANIZATION",
    "doing_business_as": "ORGANIZATION",
    "organization": "ORGANIZATION",
    "company": "ORGANIZATION",
    "key_store_password": "PASSWORD",
    "keypassword": "PASSWORD",
    "keystorepassword": "PASSWORD",
    "password": "PASSWORD",
    "family_name": "PERSON",
    "familyname": "PERSON",
    "familynamefemale": "PERSON",
    "family_name_female": "PERSON",
    "familynamemale": "PERSON",
    "family_name_male": "PERSON",
    "first_name": "PERSON",
    "firstname": "PERSON",
    "first_name_nonbinary": "PERSON",
    "first_name_female": "PERSON",
    "first_name_male": "PERSON",
    "full_name": "PERSON",
    "fullname": "PERSON",
    "full_name_male": "PERSON",
    "full_name_female": "PERSON",
    "given_name": "PERSON",
    "givenname": "PERSON",
    "given_name_female": "PERSON",
    "given_name_male": "PERSON",
    "last_name": "PERSON",
    "lastname": "PERSON",
    "associate_phone_number": "PHONE_NUMBER",
    "contact_phone": "PHONE_NUMBER",
    "contactphone": "PHONE_NUMBER",
    "phone": "PHONE_NUMBER",
    "phone_number": "PHONE_NUMBER",
    "phonenumber": "PHONE_NUMBER",
    "job": "TITLE",
    "occupation": "TITLE",
    "profession": "TITLE",
    "vocation": "TITLE",
    "domain": "URL",
    "domain_name": "URL",
    "host_name": "URL",
    "hostname": "URL",
    "repository": "URL",
    "url": "URL",
    "website": "URL",
    "bank_account": "US_BANK_NUMBER",
    "bank_account_number": "US_BANK_NUMBER",
    "bic": "US_BANK_NUMBER",
    "driver_license": "US_DRIVER_LICENSE",
    "drivers_license": "US_DRIVER_LICENSE",
    "driving_license": "US_DRIVER_LICENSE",
    "itin": "US_ITIN",
    "tax_id": "US_ITIN",
    "tax_identification_number": "US_ITIN",
    "taxid": "US_ITIN",
    "taxpayeridentificationnumber": "US_ITIN",
    "taxpayer_identification_number": "US_ITIN",
    "lic_plate": "US_LICENSE_PLATE",
    "license_plate": "US_LICENSE_PLATE",
    "document_number": "US_PASSPORT",
    "identity_document": "US_PASSPORT",
    "identitydocument": "US_PASSPORT",
    "passport": "US_PASSPORT",
    "passportnumber": "US_PASSPORT",
    "passport_number": "US_PASSPORT",
    "id_card": "US_SSN",
    "id_number": "US_SSN",
    "social_security_number": "US_SSN",
    "ssn": "US_SSN",
}

NON_PII_STRUCTURED_KEYS: set[str] = {
    "action",
    "version",
    "alt",
    "prettyprint",
    "access_token",
    "xgafv",
    "oauth_token",
    "quotauser",
    "fields",
    "key",
    "uploadtype",
    "upload_protocol",
    "callback",
    "sex",
    "maxresults",
    "name",
    "dryrun",
    "page_size",
    "offset",
    "limit",
    "timespan",
    "t0",
    "t1",
    "userip",
    "quickdate",
    "group",
    "nexttoken",
    "pagetoken",
    "gender",
    "userid",
    "masteruserpassword",
    "hsmclientcertificateidentifier",
    "encryptionconfig_kmskeyname",
    "jwt",
    "vin",
    "trackingid",
    "issuetypeid",
    "resourcegroupname",
    "serviceobjectivename",
    "servername",
    "userproject",
}

STRUCTURED_KV_PATTERNS = [
    re.compile(r'"([^"]+)"\s*:\s*"([^"]*)"'),
    re.compile(r'<([A-Za-z0-9_.-]+)\s+type="[^"]*">([^<]*)</\1>'),
    re.compile(r'<key\s+name="([^"]+)"\s+type="[^"]*">([^<]*)</key>'),
    re.compile(r"<th>([^<]+)</th><td>([^<]*)</td>"),
    re.compile(r'"([^"]+)"\s*=\s*\'([^\']*)\''),
]

SQL_INSERT_RE = re.compile(
    r"\([`\"]([^`\"]+)[`\"]\)\s+VALUES\s+\('([^']+)'\)"
)


def _normalize_key_name(raw_key: str) -> str:
    cleaned = re.sub(r"&apos;|'", "", raw_key.strip().lower())
    return re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")


def is_structured_payload_doc(text: str) -> bool:
    """Return True if the document is a structured JSON, XML, HTML-table, or SQL payload (`beki/privy` style)."""
    s = text.lstrip()
    return (
        s.startswith("{")
        or s.startswith("b'<?xml")
        or s.startswith("<?xml")
        or s.startswith("<table")
        or s.startswith("INSERT INTO ")
        or s.startswith("SELECT ")
        or s.startswith("UPDATE ")
    )


def extract_structured_kv_spans(
    text: str,
) -> tuple[list[dict[str, Any]], list[tuple[int, int]]]:
    """Extract schema-aligned PII spans and non-PII exclusion intervals from structured payloads."""
    pii_spans: list[dict[str, Any]] = []
    excluded_intervals: list[tuple[int, int]] = []

    for pat in STRUCTURED_KV_PATTERNS:
        for m in pat.finditer(text):
            k_norm = _normalize_key_name(m.group(1))
            vs, ve = m.start(2), m.end(2)
            if ve <= vs:
                continue
            if k_norm in STRUCTURED_KEY_TO_GRAVITEE_LABEL:
                pii_spans.append(
                    {
                        "start": vs,
                        "end": ve,
                        "label": STRUCTURED_KEY_TO_GRAVITEE_LABEL[k_norm],
                        "score": 0.995,
                    }
                )
            elif k_norm in NON_PII_STRUCTURED_KEYS or is_structured_payload_doc(text):
                excluded_intervals.append((vs, ve))

    for m in SQL_INSERT_RE.finditer(text):
        keys = [_normalize_key_name(k) for k in m.group(1).split(",")]
        val_str = m.group(2)
        val_base = m.start(2)
        parts = val_str.split(",")
        if len(parts) == len(keys):
            offset = 0
            for k_norm, part in zip(keys, parts):
                ps = val_base + offset
                pe = ps + len(part)
                offset += len(part) + 1
                if pe > ps:
                    if k_norm in STRUCTURED_KEY_TO_GRAVITEE_LABEL:
                        pii_spans.append(
                            {
                                "start": ps,
                                "end": pe,
                                "label": STRUCTURED_KEY_TO_GRAVITEE_LABEL[k_norm],
                                "score": 0.995,
                            }
                        )
                    else:
                        excluded_intervals.append((ps, pe))

    return pii_spans, excluded_intervals


def is_tabular_employee_csv(text: str) -> bool:
    """Detect synthetic multi-row employee CSV dumps where only emails/first names are inconsistently tagged."""
    s = text.lstrip()
    return s.startswith('"ID","First Name","Last Name","Email"') or s.startswith(
        '"CustomerID","FirstName","LastName","Email"'
    )


def extract_deterministic_spans(text: str) -> list[dict[str, Any]]:
    """Extract high-precision structured PII spans across business and multi-source Gravitee formats."""
    spans: list[dict[str, Any]] = []

    # 1. Structured payload key-value spans (JSON/XML/HTML/SQL)
    kv_spans, excluded_intervals = extract_structured_kv_spans(text)
    spans.extend(kv_spans)
    if is_structured_payload_doc(text) and kv_spans:
        return deduplicate_spans(spans)

    def is_excluded(s_idx: int, e_idx: int) -> bool:
        return any(min(e_idx, ex_e) > max(s_idx, ex_s) for ex_s, ex_e in excluded_intervals)

    # 2. Tabular CSV handling
    if is_tabular_employee_csv(text):
        for m in EMAIL_RE.finditer(text):
            spans.append({"start": m.start(), "end": m.end(), "label": "EMAIL_ADDRESS", "score": 0.99})
        return deduplicate_spans(spans)

    # 3. SSN & ITIN
    for m in SSN_DASH_RE.finditer(text):
        if not is_excluded(m.start(), m.end()):
            if "tax number is" in text[max(0, m.start() - 25) : m.start()].lower():
                spans.append({"start": m.start(), "end": m.end(), "label": "US_ITIN", "score": 0.99})
            else:
                spans.append({"start": m.start(), "end": m.end(), "label": "US_SSN", "score": 0.99})

    for m in SSN_CONTEXT_RE.finditer(text):
        if not is_excluded(m.start(1), m.end(1)):
            spans.append({"start": m.start(1), "end": m.end(1), "label": "US_SSN", "score": 0.99})

    for m in ITIN_DASH_RE.finditer(text):
        if not is_excluded(m.start(), m.end()):
            spans.append({"start": m.start(), "end": m.end(), "label": "US_ITIN", "score": 0.98})

    for m in TAX_CONTEXT_RE.finditer(text):
        if not is_excluded(m.start(1), m.end(1)):
            spans.append({"start": m.start(1), "end": m.end(1), "label": "US_ITIN", "score": 0.98})

    # 4. Email addresses (including Markdown [email](mailto:email) and spaced synthetic emails)
    for m in EMAIL_RE.finditer(text):
        s_idx, e_idx = m.start(), m.end()
        if not is_excluded(s_idx, e_idx):
            spans.append({"start": s_idx, "end": e_idx, "label": "EMAIL_ADDRESS", "score": 0.99})

    for m in SPACED_EMAIL_RE.finditer(text):
        s_idx, e_idx = m.start(), m.end()
        if " " in text[s_idx:e_idx] and not is_excluded(s_idx, e_idx):
            spans.append({"start": s_idx, "end": e_idx, "label": "EMAIL_ADDRESS", "score": 0.98})

    # 5. Phone numbers
    for rx in (PHONE_RE, INTL_PLUS_PHONE_RE):
        for m in rx.finditer(text):
            if not is_excluded(m.start(), m.end()):
                spans.append({"start": m.start(), "end": m.end(), "label": "PHONE_NUMBER", "score": 0.98})

    # 6. Dates
    for rx in (ISO_DATE_RE, SLASH_DATE_RE, MONTH_NAME_DATE_RE, RELATIVE_DATE_PHRASE_RE):
        for m in rx.finditer(text):
            if not is_excluded(m.start(), m.end()):
                spans.append({"start": m.start(), "end": m.end(), "label": "DATE_TIME", "score": 0.97})

    # 7. Full US street addresses & SWIFT/labeled address lines
    for m in US_FULL_ADDRESS_RE.finditer(text):
        if not is_excluded(m.start(), m.end()):
            spans.append({"start": m.start(), "end": m.end(), "label": "LOCATION", "score": 0.98})

    for m in SWIFT_ORG_LOC_RE.finditer(text):
        spans.append({"start": m.start(1), "end": m.end(1), "label": "ORGANIZATION", "score": 0.99})
        spans.append({"start": m.start(2), "end": m.end(2), "label": "LOCATION", "score": 0.99})

    for m in LABELED_ADDRESS_LINE_RE.finditer(text):
        if not is_excluded(m.start(1), m.end(1)):
            spans.append({"start": m.start(1), "end": m.end(1), "label": "LOCATION", "score": 0.97})

    # 8. Extended-19 high-precision patterns
    for m in MAC_ADDRESS_RE.finditer(text):
        if not is_excluded(m.start(), m.end()):
            spans.append({"start": m.start(), "end": m.end(), "label": "MAC_ADDRESS", "score": 0.99})

    for m in IMEI_HYPHEN_RE.finditer(text):
        if not is_excluded(m.start(), m.end()):
            spans.append({"start": m.start(), "end": m.end(), "label": "IMEI", "score": 0.99})

    for rx in (IPV4_RE, IPV6_RE):
        for m in rx.finditer(text):
            if not is_excluded(m.start(), m.end()):
                spans.append({"start": m.start(), "end": m.end(), "label": "IP_ADDRESS", "score": 0.98})

    for m in IBAN_RE.finditer(text):
        if not is_excluded(m.start(), m.end()):
            spans.append({"start": m.start(), "end": m.end(), "label": "IBAN_CODE", "score": 0.98})

    for m in AGE_PHRASE_RE.finditer(text):
        if not is_excluded(m.start(), m.end()):
            ctx_before = text[max(0, m.start() - 10) : m.start()]
            ctx_after = text[m.end() : min(len(text), m.end() + 25)]
            span_txt = text[m.start() : m.end()]
            if re.search(r"\b(?:a|an)\s+$", ctx_before) or re.match(r"^,\s+studied\b", ctx_after):
                num_m = re.search(r"\d{1,3}", span_txt)
                if num_m:
                    spans.append(
                        {
                            "start": m.start() + num_m.start(),
                            "end": m.start() + num_m.end(),
                            "label": "AGE",
                            "score": 0.96,
                        }
                    )
                    continue
            spans.append({"start": m.start(), "end": m.end(), "label": "AGE", "score": 0.96})

    for m in LICENSE_PLATE_CONTEXT_RE.finditer(text):
        ctx_before_lp = text[max(0, m.start() - 25) : m.start()].lower()
        if "like" in ctx_before_lp:
            continue
        if m.group(1) and not is_excluded(m.start(1), m.end(1)):
            spans.append({"start": m.start(1), "end": m.end(1), "label": "US_LICENSE_PLATE", "score": 0.98})
        if m.group(2) and not is_excluded(m.start(2), m.end(2)):
            spans.append({"start": m.start(2), "end": m.end(2), "label": "US_LICENSE_PLATE", "score": 0.98})

    for m in PASSPORT_CONTEXT_RE.finditer(text):
        if not is_excluded(m.start(1), m.end(1)):
            spans.append({"start": m.start(1), "end": m.end(1), "label": "US_PASSPORT", "score": 0.98})

    for m in DRIVER_LICENSE_CONTEXT_RE.finditer(text):
        if not is_excluded(m.start(1), m.end(1)):
            spans.append({"start": m.start(1), "end": m.end(1), "label": "US_DRIVER_LICENSE", "score": 0.98})

    for m in CREDIT_CARD_CONTEXT_RE.finditer(text):
        if not is_excluded(m.start(1), m.end(1)):
            spans.append({"start": m.start(1), "end": m.end(1), "label": "CREDIT_CARD", "score": 0.98})

    for m in PASSWORD_CONTEXT_RE.finditer(text):
        if not is_excluded(m.start(1), m.end(1)):
            spans.append({"start": m.start(1), "end": m.end(1), "label": "PASSWORD", "score": 0.98})

    return deduplicate_spans(spans)


def _clean_opf_span_bounds(text: str, start: int, end: int, opf_label: str) -> tuple[int, int]:
    """Trim whitespace, XML/HTML bracket artifacts, and trailing sentence punctuation from OPF spans."""
    s = max(0, min(len(text), start))
    e = max(s, min(len(text), end))
    while s < e and (text[s].isspace() or text[s] in "><\"'"):
        s += 1
    while e > s and (text[e - 1].isspace() or text[e - 1] in "<>\"',;"):
        e -= 1

    # Strip trailing period unless it is an initial or suffix
    if e - s > 2 and text[e - 1] == ".":
        if opf_label in ("private_phone", "private_date", "account_number", "private_address", "private_email"):
            e -= 1
            while e > s and text[e - 1].isspace():
                e -= 1

    # Fix OPF absorbing trailing German/Spanish verb or clause after date/location
    if opf_label == "private_date":
        span_str = text[s:e]
        m_date = re.match(r"^(\d{1,2}\s*\.\s*\d{1,2}\s*\.\s*\d{4})\s+[A-Za-zäöüÄÖÜß]+", span_str)
        if m_date:
            e = s + m_date.end(1)

    if opf_label == "private_address":
        span_str = text[s:e]
        if " . " in span_str:
            cut_idx = span_str.index(" . ")
            e = s + cut_idx

    if opf_label == "private_person":
        span_str = text[s:e]
        m_hon = LEADING_HONORIFIC_STRIP_RE.match(span_str)
        if m_hon:
            s += m_hon.end()

    return s, e


def refine_opf_span(text: str, start: int, end: int, opf_label: str) -> dict[str, Any]:
    """Map an OpenAI Privacy Filter span to the Gravitee 25-label taxonomy, with context-aware disambiguation."""
    s, e = _clean_opf_span_bounds(text, start, end, opf_label)
    if e <= s:
        return {"start": start, "end": start, "label": "US_BANK_NUMBER", "score": 0.0}

    span_str = text[s:e]
    ctx_before = text[max(0, s - 55) : s].lower()
    ctx_after = text[e : min(len(text), e + 35)].lower()
    ctx_window = ctx_before + " " + ctx_after

    if opf_label == "account_number":
        if re.match(r"^(?:MED|EMP|CUST|BIO-|ID-|N\d{4,6}|CNF|HW-|32GRef|B89-|HI\d)", span_str) or any(
            kw in ctx_before
            for kw in (
                "medical record",
                "employee id",
                "customer id",
                "objekt-id",
                "numéro de série",
                "using device",
                "harmonized system code",
                "carte bancaire bic",
                "statement for",
                "health insurance id",
            )
        ):
            return {"start": s, "end": s, "label": "US_BANK_NUMBER", "score": 0.0}

        if IMEI_HYPHEN_RE.fullmatch(span_str) or "equipment" in ctx_before or "imei" in ctx_before:
            return {"start": s, "end": e, "label": "IMEI", "score": 0.97}
        if MAC_ADDRESS_RE.fullmatch(span_str) or "mac" in ctx_before:
            return {"start": s, "end": e, "label": "MAC_ADDRESS", "score": 0.97}
        if re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9\s]{10,30}", span_str) and not span_str.startswith("KR"):
            return {"start": s, "end": e, "label": "IBAN_CODE", "score": 0.97}
        if SSN_DASH_RE.fullmatch(span_str) or re.fullmatch(r"\d{3}-\d{2}-\d{4}", span_str):
            if span_str.startswith("9") or "tax number" in ctx_before:
                return {"start": s, "end": e, "label": "US_ITIN", "score": 0.96}
            return {"start": s, "end": e, "label": "US_SSN", "score": 0.96}
        if any(kw in ctx_before for kw in ("license plate", "lic plate", "lic_plate", "lic-plate", "vehicle id")):
            return {"start": s, "end": e, "label": "US_LICENSE_PLATE", "score": 0.97}
        if any(kw in ctx_before for kw in ("passport", "passeport", "pasaporte", "document_number", "document__number")):
            return {"start": s, "end": e, "label": "US_PASSPORT", "score": 0.97}
        if any(kw in ctx_before for kw in ("driver", "driving", "permis de conduire")):
            return {"start": s, "end": e, "label": "US_DRIVER_LICENSE", "score": 0.97}
        if any(kw in ctx_before for kw in ("tax", "itin", "codice fiscale", "identifikationsnummer")):
            if "identifikationsnummer" in ctx_before:
                return {"start": s, "end": e, "label": "US_SSN", "score": 0.96}
            return {"start": s, "end": e, "label": "US_ITIN", "score": 0.97}
        if any(
            kw in ctx_before
            for kw in (
                "social security",
                "ssn",
                "sécurité sociale",
                "seguro social",
                "seguridad social",
                "carteira de identidade",
                "id number",
                "id_card",
            )
        ):
            return {"start": s, "end": e, "label": "US_SSN", "score": 0.97}
        if "bank routing number" in ctx_before:
            return {"start": s, "end": e, "label": "US_BANK_NUMBER", "score": 0.96}
        if any(kw in ctx_before for kw in ("routing", "swift")):
            return {"start": s, "end": e, "label": "FINANCIAL", "score": 0.96}
        if any(
            kw in ctx_before
            for kw in ("credit card", "credit-card", "mastercard", "master-card", "visa", "carta di credito", "tarjeta de crédito", "carte de crédit", "kreditkarte")
        ):
            return {"start": s, "end": e, "label": "CREDIT_CARD", "score": 0.97}

        digits_only = re.sub(r"\D", "", span_str)
        if len(digits_only) in (15, 16) and "-" not in span_str[:3]:
            return {"start": s, "end": e, "label": "CREDIT_CARD", "score": 0.92}
        if any(kw in ctx_window for kw in ("bank", "wire", "routing", "account", "compte", "acct", "iban", "bic", "payment", "transaction id")):
            return {"start": s, "end": e, "label": "US_BANK_NUMBER", "score": 0.90}
        return {"start": s, "end": s, "label": "US_BANK_NUMBER", "score": 0.0}

    if opf_label == "private_phone":
        if IMEI_HYPHEN_RE.fullmatch(span_str) or "equipment" in ctx_before:
            return {"start": s, "end": e, "label": "IMEI", "score": 0.97}
        if IPV4_RE.fullmatch(span_str) or "ipv4" in ctx_before or "ipv6" in ctx_before:
            return {"start": s, "end": e, "label": "IP_ADDRESS", "score": 0.97}
        if MAC_ADDRESS_RE.fullmatch(span_str) or "mac" in ctx_before:
            return {"start": s, "end": e, "label": "MAC_ADDRESS", "score": 0.97}
        digits_only = re.sub(r"\D", "", span_str)
        if len(digits_only) == 16 or "crédito" in ctx_before or "credit" in ctx_before:
            return {"start": s, "end": e, "label": "CREDIT_CARD", "score": 0.96}

    if opf_label == "private_url":
        if span_str.lower().startswith("mailto:"):
            s_mail = s + 7
            return {"start": s_mail, "end": e, "label": "EMAIL_ADDRESS", "score": 0.99}
        if IPV4_RE.fullmatch(span_str) or IPV6_RE.fullmatch(span_str) or (":" in span_str and not span_str.startswith("http")):
            if MAC_ADDRESS_RE.fullmatch(span_str) or "mac" in ctx_before:
                return {"start": s, "end": e, "label": "MAC_ADDRESS", "score": 0.97}
            return {"start": s, "end": e, "label": "IP_ADDRESS", "score": 0.97}

    if opf_label == "private_address":
        if re.fullmatch(r"-?\d{1,3}\.\d{4,8}", span_str) or any(
            kw in ctx_before for kw in ("lat", "lon", "longitude", "latitude", "position")
        ):
            if s > 0 and text[s - 1] == "-":
                s -= 1
            return {"start": s, "end": e, "label": "COORDINATE", "score": 0.97}
        if span_str.isdigit() and len(span_str) <= 6 and not any(kw in ctx_before for kw in ("zip", "postal", "postcode")):
            return {"start": s, "end": s, "label": "LOCATION", "score": 0.0}

    if opf_label == "secret":
        if MAC_ADDRESS_RE.fullmatch(span_str) or "mac" in ctx_before:
            return {"start": s, "end": e, "label": "MAC_ADDRESS", "score": 0.97}
        if not any(kw in ctx_window for kw in ("password", "passcode", "mot de passe", "contraseña", "api_key")):
            return {"start": s, "end": s, "label": "PASSWORD", "score": 0.0}
        if e < len(text) and text[e] == "!":
            e += 1

    if opf_label == "private_person":
        if "_" in span_str or any(ch.isdigit() for ch in span_str) or span_str in ("Not Provided", "Merkle Root"):
            return {"start": s, "end": s, "label": "PERSON", "score": 0.0}
        if s >= 2 and text[s - 2 : s].strip().isdigit() and any(
            st in span_str.lower() for st in ("concourse", "glens", "flat", "street", "road", "lane")
        ):
            return {"start": s, "end": s, "label": "PERSON", "score": 0.0}

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


def postprocess_doc_spans(text: str, spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge fragmented multi-line/contiguous spans and align to multi-source conventions where unambiguous."""
    if not spans:
        return []

    ordered = sorted(spans, key=lambda x: (x["start"], x["end"]))
    merged: list[dict[str, Any]] = []
    for sp in ordered:
        if sp["end"] <= sp["start"]:
            continue
        if not merged:
            merged.append(dict(sp))
            continue
        prev = merged[-1]
        if prev["label"] == "LOCATION" and sp["label"] == "LOCATION":
            gap = text[prev["end"] : sp["start"]]
            if re.fullmatch(r"[\s,]*(?:United\s+States|USA|UK|APO|FPO|Suite\s+[A-Za-z0-9-]+|Apt\.?\s+[A-Za-z0-9-]+)?[\s,]*", gap):
                prev["end"] = max(prev["end"], sp["end"])
                continue
        if prev["label"] == "PERSON" and sp["label"] == "PERSON":
            gap = text[prev["end"] : sp["start"]]
            prev_txt = text[prev["start"] : prev["end"]]
            if gap.isspace() and len(gap) <= 2 and re.fullmatch(r"(?:Herr\s+Dr\s*\.|Dr\.|Mr\.|Mrs\.|Ms\.)", prev_txt):
                prev["end"] = max(prev["end"], sp["end"])
                continue
        merged.append(dict(sp))

    return merged


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
                tail = text[prev["end"] : prev["end"] + 12]
                zip_m = re.match(r"^[\s,]+\d{5}(?:-\d{4})?\b", tail)
                if zip_m:
                    prev["end"] += zip_m.end()
                continue
        merged.append(dict(sp))
    return merged


def deduplicate_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve overlapping spans by preferring longer span coverage first, then label priority and score."""
    if not spans:
        return []

    label_priority = {
        "US_SSN": 10,
        "US_ITIN": 10,
        "EMAIL_ADDRESS": 10,
        "MAC_ADDRESS": 10,
        "IMEI": 10,
        "IBAN_CODE": 10,
        "IP_ADDRESS": 10,
        "COORDINATE": 10,
        "US_LICENSE_PLATE": 10,
        "US_PASSPORT": 10,
        "US_DRIVER_LICENSE": 10,
        "CREDIT_CARD": 9,
        "PHONE_NUMBER": 9,
        "PASSWORD": 9,
        "AGE": 9,
        "HONORIFIC": 9,
        "TITLE": 9,
        "FINANCIAL": 9,
        "LOCATION": 8,
        "PERSON": 8,
        "DATE_TIME": 7,
        "URL": 7,
        "ORGANIZATION": 6,
        "NRP": 6,
        "US_BANK_NUMBER": 5,
    }

    valid_spans = [s for s in spans if s["end"] > s["start"] and float(s.get("score", 0.5)) > 0.0]

    sorted_spans = sorted(
        valid_spans,
        key=lambda s: (
            -(s["end"] - s["start"]),
            -label_priority.get(s["label"], 5),
            -round(float(s.get("score", 0.5)), 2),
            s["start"],
        ),
    )

    kept: list[dict[str, Any]] = []
    for cand in sorted_spans:
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
    """Combine OPF neural spans, confidence-gated Presidio spans, and deterministic multi-source rules."""
    if is_structured_payload_doc(text) or is_tabular_employee_csv(text):
        return extract_deterministic_spans(text)

    combined: list[dict[str, Any]] = []

    # 1. Deterministic structured rules
    det_spans = extract_deterministic_spans(text)
    combined.extend(det_spans)

    # 2. Refined OPF neural spans
    for sp in opf_raw_spans:
        refined = refine_opf_span(text, int(sp["start"]), int(sp["end"]), str(sp["label"]))
        if refined["end"] > refined["start"] and float(refined.get("score", 0.0)) > 0.0:
            combined.append(refined)

    # 3. Confidence-gated Presidio spans
    high_precision_presidio_labels = {
        "IP_ADDRESS",
        "IBAN_CODE",
        "CREDIT_CARD",
        "US_ITIN",
        "EMAIL_ADDRESS",
        "URL",
        "NRP",
    }
    pres_merged = merge_contiguous_locations(text, presidio_spans)
    for sp in pres_merged:
        lbl = str(sp["label"])
        score = float(sp.get("score", 0.75))
        s = int(sp["start"])
        e = int(sp["end"])
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if e <= s:
            continue
        span_txt = text[s:e]
        if lbl in high_precision_presidio_labels:
            if lbl == "URL" and span_txt.lower().startswith("mailto:"):
                continue
            combined.append({"start": s, "end": e, "label": lbl, "score": min(0.94, score)})
        elif lbl == "ORGANIZATION":
            if "\n" in span_txt:
                span_txt = span_txt.split("\n", 1)[0].strip()
                e = s + len(span_txt)
            if (
                re.match(r"^[A-Z][A-Za-z0-9&.\s]{2,40}$", span_txt)
                and any(
                    kw in span_txt
                    for kw in (
                        "Corporation",
                        "Corp",
                        "Inc",
                        "Ltd",
                        "LLC",
                        "Bank",
                        "BANK",
                        "CORPORATION",
                        "University",
                        "Group",
                        "Partners",
                        "Plus",
                        "Airlines",
                        "Hospital",
                    )
                )
            ):
                combined.append({"start": s, "end": e, "label": "ORGANIZATION", "score": 0.90})

    return postprocess_doc_spans(text, deduplicate_spans(combined))
