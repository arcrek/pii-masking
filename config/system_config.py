"""System and Environment Configuration module for PII Detection & Redaction MVP.

Provides centralized, version-pinned settings with environment variable overrides
and security constraints aligned with OPS-01.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

SYSTEM_VERSION = "0.1.0"
API_VERSION = "v1"
PIPELINE_VERSION = "1.0.0"


def _parse_dotenv(path: Path) -> dict[str, str]:
    """Parse a simple .env file without external dependencies."""
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                result[k] = v
    except Exception:
        pass
    return result


@dataclass
class SystemConfig:
    """Central configuration for application runtime, security, and storage."""

    # Application & Versioning
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    system_version: str = SYSTEM_VERSION
    api_version: str = API_VERSION
    pipeline_version: str = PIPELINE_VERSION

    # Security & Authentication
    jwt_secret_key: str = "change-this-insecure-secret-key-for-local-dev-only-32bytes"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Storage Paths & Resource Isolation
    storage_root: Path = field(default_factory=lambda: Path("./storage/private"))
    temp_storage_dir: Path = field(default_factory=lambda: Path("./storage/temp"))
    checkpoints_dir: Path = field(default_factory=lambda: Path("./checkpoints"))

    # Processing Limits (OPS-01 & OPS-03 alignment)
    max_file_size_mb: int = 25
    max_pdf_pages: int = 100
    allowed_mime_types: List[str] = field(default_factory=lambda: ["application/pdf"])
    job_timeout_seconds: int = 300
    worker_concurrency: int = 2
    safe_logging: bool = True

    # Default Models
    default_ner_model: str = "spacy_vn_19_ner"
    default_ner_version: str = "1.0.0"

    @classmethod
    def from_env(cls, env_dict: dict[str, str] | None = None) -> SystemConfig:
        """Instantiate configuration from environment variables, .env file, or custom dict."""
        if env_dict is not None:
            source = env_dict
        else:
            # Merge .env file if present, overridden by os.environ
            dotenv_path = Path(__file__).resolve().parent.parent / ".env"
            if not dotenv_path.is_file():
                dotenv_path = Path(".env")
            file_env = _parse_dotenv(dotenv_path)
            source = {**file_env, **os.environ}

        storage_root_str = source.get("STORAGE_ROOT", "./storage/private")
        temp_storage_str = source.get("TEMP_STORAGE_DIR", "./storage/temp")
        checkpoints_str = source.get("CHECKPOINTS_DIR", "./checkpoints")

        raw_port = source.get("APP_PORT", "8000")
        raw_token_expire = source.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        raw_max_size = source.get("MAX_FILE_SIZE_MB", "25")
        raw_max_pages = source.get("MAX_PDF_PAGES", "100")
        raw_timeout = source.get("JOB_TIMEOUT_SECONDS", "300")
        raw_concurrency = source.get("WORKER_CONCURRENCY", "2")
        raw_safe_logging = source.get("SAFE_LOGGING", "true").lower() in ("true", "1", "yes")

        return cls(
            app_env=source.get("APP_ENV", "development"),
            app_host=source.get("APP_HOST", "0.0.0.0"),
            app_port=int(raw_port),
            system_version=source.get("SYSTEM_VERSION", SYSTEM_VERSION),
            api_version=source.get("API_VERSION", API_VERSION),
            pipeline_version=source.get("PIPELINE_VERSION", PIPELINE_VERSION),
            jwt_secret_key=source.get(
                "JWT_SECRET_KEY", "change-this-insecure-secret-key-for-local-dev-only-32bytes"
            ),
            jwt_algorithm=source.get("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(raw_token_expire),
            storage_root=Path(storage_root_str),
            temp_storage_dir=Path(temp_storage_str),
            checkpoints_dir=Path(checkpoints_str),
            max_file_size_mb=int(raw_max_size),
            max_pdf_pages=int(raw_max_pages),
            job_timeout_seconds=int(raw_timeout),
            worker_concurrency=int(raw_concurrency),
            safe_logging=raw_safe_logging,
            default_ner_model=source.get("DEFAULT_NER_MODEL", "spacy_vn_19_ner"),
            default_ner_version=source.get("DEFAULT_NER_VERSION", "1.0.0"),
        )

    def validate_security(self) -> List[str]:
        """Validate security posture; returns list of violation messages."""
        violations = []
        if self.app_env == "production":
            if "change-this" in self.jwt_secret_key or len(self.jwt_secret_key) < 32:
                violations.append(
                    "Production requires a robust, non-default JWT_SECRET_KEY of at least 32 characters."
                )
        if self.max_file_size_mb <= 0 or self.max_file_size_mb > 100:
            violations.append("MAX_FILE_SIZE_MB must be between 1 and 100 MB.")
        if self.max_pdf_pages <= 0 or self.max_pdf_pages > 500:
            violations.append("MAX_PDF_PAGES must be between 1 and 500 pages.")
        return violations

    def ensure_directories(self) -> None:
        """Create necessary storage directories if they do not exist."""
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.temp_storage_dir.mkdir(parents=True, exist_ok=True)


# Global singleton instance
_CONFIG_INSTANCE: SystemConfig | None = None


def get_config(reload: bool = False) -> SystemConfig:
    """Retrieve global cached SystemConfig instance."""
    global _CONFIG_INSTANCE
    if _CONFIG_INSTANCE is None or reload:
        _CONFIG_INSTANCE = SystemConfig.from_env()
    return _CONFIG_INSTANCE


if __name__ == "__main__":
    cfg = get_config()
    print(f"System Version: {cfg.system_version}")
    print(f"API Version: {cfg.api_version}")
    print(f"Environment: {cfg.app_env}")
    print(f"Storage Root: {cfg.storage_root}")
    print("Configuration loaded successfully.")
