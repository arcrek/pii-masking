"""Versioned Canonical 6-Group PII Taxonomy and Mapping Contracts (CORE-01).

Defines the 6 canonical UI groups:
  - PERSON
  - EMAIL
  - PHONE
  - ADDRESS
  - DATE
  - ID_NUMBER

Exhaustively maps raw labels from Vietnamese 19-label OpenPII (opf_vn_19_label_space.json),
English Gravitee 25-label benchmark, Presidio, and OpenPII-Filter.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Set, Tuple, Optional

TAXONOMY_VERSION = "1.0.0"


class CanonicalGroup(str, Enum):
    """The 6 canonical target UI groups for human review and redaction."""
    PERSON = "PERSON"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    ADDRESS = "ADDRESS"
    DATE = "DATE"
    ID_NUMBER = "ID_NUMBER"


# Excluded labels by default policy (audited default - secondary / contextual attributes)
EXCLUDED_LABELS: Set[str] = {
    # Vietnamese secondary
    "AGE",
    "GENDER",
    "SEX",
    "TITLE",
    # English secondary / orgs
    "HONORIFIC",
    "NRP",
    "ORGANIZATION",
    "URL",
    "private_url",
    "IP_ADDRESS",
    "MAC_ADDRESS",
    "IMEI",
    "FINANCIAL",
}

# Vietnamese 19-label mapping
VIETNAMESE_19_TO_CANONICAL: Dict[str, CanonicalGroup] = {
    "GIVENNAME": CanonicalGroup.PERSON,
    "SURNAME": CanonicalGroup.PERSON,
    "EMAIL": CanonicalGroup.EMAIL,
    "TELEPHONENUM": CanonicalGroup.PHONE,
    "BUILDINGNUM": CanonicalGroup.ADDRESS,
    "STREET": CanonicalGroup.ADDRESS,
    "CITY": CanonicalGroup.ADDRESS,
    "ZIPCODE": CanonicalGroup.ADDRESS,
    "DATE": CanonicalGroup.DATE,
    "IDCARDNUM": CanonicalGroup.ID_NUMBER,
    "TAXNUM": CanonicalGroup.ID_NUMBER,
    "SOCIALNUM": CanonicalGroup.ID_NUMBER,
    "PASSPORTNUM": CanonicalGroup.ID_NUMBER,
    "DRIVERLICENSENUM": CanonicalGroup.ID_NUMBER,
    "CREDITCARDNUMBER": CanonicalGroup.ID_NUMBER,
}

# English 25-label / Presidio / OPF mapping
ENGLISH_25_TO_CANONICAL: Dict[str, CanonicalGroup] = {
    # Person
    "PERSON": CanonicalGroup.PERSON,
    "private_person": CanonicalGroup.PERSON,
    # Email
    "EMAIL_ADDRESS": CanonicalGroup.EMAIL,
    "private_email": CanonicalGroup.EMAIL,
    # Phone
    "PHONE_NUMBER": CanonicalGroup.PHONE,
    "private_phone": CanonicalGroup.PHONE,
    # Address
    "LOCATION": CanonicalGroup.ADDRESS,
    "COORDINATE": CanonicalGroup.ADDRESS,
    "private_address": CanonicalGroup.ADDRESS,
    # Date
    "DATE_TIME": CanonicalGroup.DATE,
    "private_date": CanonicalGroup.DATE,
    # IDs / Financial identifiers / Secrets
    "US_SSN": CanonicalGroup.ID_NUMBER,
    "US_PASSPORT": CanonicalGroup.ID_NUMBER,
    "US_DRIVER_LICENSE": CanonicalGroup.ID_NUMBER,
    "US_ITIN": CanonicalGroup.ID_NUMBER,
    "CREDIT_CARD": CanonicalGroup.ID_NUMBER,
    "IBAN_CODE": CanonicalGroup.ID_NUMBER,
    "US_BANK_NUMBER": CanonicalGroup.ID_NUMBER,
    "US_LICENSE_PLATE": CanonicalGroup.ID_NUMBER,
    "PASSWORD": CanonicalGroup.ID_NUMBER,
    "account_number": CanonicalGroup.ID_NUMBER,
    "secret": CanonicalGroup.ID_NUMBER,
}

# Unified combined dictionary
ALL_CANONICAL_MAPPINGS: Dict[str, CanonicalGroup] = {
    **VIETNAMESE_19_TO_CANONICAL,
    **ENGLISH_25_TO_CANONICAL,
}


def map_raw_label(raw_label: str, strict: bool = False) -> Tuple[Optional[CanonicalGroup], bool]:
    """Map a raw model or rule label to its CanonicalGroup.

    Args:
        raw_label: The raw label string from NER or regex.
        strict: If True, raise ValueError for unknown labels.

    Returns:
        tuple (canonical_group, is_excluded)
        - If mapped to a canonical group: (CanonicalGroup, False)
        - If explicitly excluded by policy: (None, True)
        - If unknown: (None, False) or raises ValueError if strict=True.
    """
    clean_label = raw_label.strip()
    if clean_label in EXCLUDED_LABELS:
        return None, True

    if clean_label in ALL_CANONICAL_MAPPINGS:
        return ALL_CANONICAL_MAPPINGS[clean_label], False

    if strict:
        raise ValueError(f"Unknown or unmapped PII raw label: '{clean_label}'")

    return None, False
