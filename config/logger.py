"""Safe Logging utility for PII Detection & Redaction MVP.

Ensures that logs never contain raw secrets, credentials, tokens, or unmasked sensitive PII,
fulfilling the OPS-01 acceptance criteria ("không ghi secret vào artifact/log").
"""
from __future__ import annotations

import logging
import re
import sys
from typing import Any

# Regex patterns for sensitive credentials and tokens
SECRET_PATTERNS = [
    # Bearer tokens and Authorization headers
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{10,}", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(Authorization:\s*)[^\s]+", re.IGNORECASE), r"\1[REDACTED_AUTH]"),
    # API keys and Passwords
    (
        re.compile(r"((?:password|secret|api_key|access_token|private_key)\s*[:=]\s*['\"])[^'\"]+(['\"])", re.IGNORECASE),
        r"\1[REDACTED_SECRET]\2",
    ),
    # JWT tokens
    (re.compile(r"eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*"), "[REDACTED_JWT]"),
    # Private Key markers
    (re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[^-]+-----END [A-Z ]+ PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
]

# Sensitive PII patterns to sanitize from application logs
PII_LOG_PATTERNS = [
    # Credit Card Numbers (13-19 digits)
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[REDACTED_CARD]"),
    # Vietnamese Citizen ID (CCCD - 12 digits)
    (re.compile(r"\b\d{12}\b"), "[REDACTED_CCCD]"),
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    # Vietnamese Mobile Phone numbers (10 digits starting with 03, 05, 07, 08, 09 or +84)
    (re.compile(r"\b(?:\+84|0)(?:3[2-9]|5[689]|7[06-9]|8[1-9]|9[0-9])\d{7}\b"), "[REDACTED_PHONE]"),
]


class SafeFormatter(logging.Formatter):
    """Custom logging formatter that scrubs secrets and raw PII before writing."""

    def __init__(self, fmt: str | None = None, datefmt: str | None = None, scrub_pii: bool = True) -> None:
        super().__init__(fmt, datefmt)
        self.scrub_pii = scrub_pii

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        sanitized = original

        # Scrub secrets
        for pattern, replacement in SECRET_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)

        # Scrub high-risk PII
        if self.scrub_pii:
            for pattern, replacement in PII_LOG_PATTERNS:
                sanitized = pattern.sub(replacement, sanitized)

        return sanitized


def get_logger(name: str = "pii_masking", level: int = logging.INFO, scrub_pii: bool = True) -> logging.Logger:
    """Create or retrieve a safe logger equipped with SafeFormatter."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers if already configured
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = SafeFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            scrub_pii=scrub_pii,
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    return logger
