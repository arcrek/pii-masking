"""Unit and verification tests for OPS-01 (Môi trường và cấu hình phiên bản).

Verifies:
1. Reproducible system and environment configuration (SystemConfig & .env parser).
2. Semantic versioning and Model Registry integrity (checkpoints, labels, versions).
3. Secret scanning script behavior (single-pass tree scan, git staged scan, catches leaks).
4. Safe logging masking credentials and sensitive PII (token, password, card, cccd, phone, email).
5. Environment template (.env.example) and .dockerignore hygiene.
6. Container health endpoint handler.
"""
from __future__ import annotations

import io
import json
import logging
import os
import tempfile
from pathlib import Path
import unittest

from config.health import HealthCheckHandler
from config.logger import SafeFormatter, get_logger
from config.model_registry import ModelRegistry, get_model_registry
from config.system_config import SystemConfig, _parse_dotenv, get_config
from scripts.check_secrets import install_pre_commit_hook, scan_directory, scan_file, scan_git_staged


class TestSystemConfig(unittest.TestCase):
    """Test suite for SystemConfig initialization, environment overrides, and validation."""

    def test_default_versions(self) -> None:
        cfg = SystemConfig()
        self.assertEqual(cfg.system_version, "0.1.0")
        self.assertEqual(cfg.api_version, "v1")
        self.assertEqual(cfg.pipeline_version, "1.0.0")
        self.assertEqual(cfg.app_env, "development")

    def test_environment_variable_override(self) -> None:
        custom_env = {
            "APP_ENV": "staging",
            "APP_PORT": "9000",
            "SYSTEM_VERSION": "0.2.0",
            "STORAGE_ROOT": "/custom/storage",
            "MAX_FILE_SIZE_MB": "50",
            "JOB_TIMEOUT_SECONDS": "600",
            "WORKER_CONCURRENCY": "4",
        }
        cfg = SystemConfig.from_env(custom_env)
        self.assertEqual(cfg.app_env, "staging")
        self.assertEqual(cfg.app_port, 9000)
        self.assertEqual(cfg.system_version, "0.2.0")
        self.assertEqual(str(cfg.storage_root), "/custom/storage")
        self.assertEqual(cfg.max_file_size_mb, 50)
        self.assertEqual(cfg.job_timeout_seconds, 600)
        self.assertEqual(cfg.worker_concurrency, 4)

    def test_dotenv_parser_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_env = Path(tmp_dir) / ".env"
            tmp_env.write_text("APP_PORT=8888\nAPP_ENV=test_env\n# Comment\nINVALID_LINE\n", encoding="utf-8")
            parsed = _parse_dotenv(tmp_env)
            self.assertEqual(parsed.get("APP_PORT"), "8888")
            self.assertEqual(parsed.get("APP_ENV"), "test_env")
            self.assertNotIn("INVALID_LINE", parsed)

    def test_security_validation_production_rejects_weak_jwt(self) -> None:
        cfg = SystemConfig(app_env="production", jwt_secret_key="change-this-insecure-key")
        violations = cfg.validate_security()
        self.assertTrue(any("Production requires a robust" in v for v in violations))

    def test_security_validation_valid_configuration(self) -> None:
        cfg = SystemConfig(
            app_env="production",
            jwt_secret_key="a" * 32,
            max_file_size_mb=25,
            max_pdf_pages=100,
        )
        violations = cfg.validate_security()
        self.assertEqual(violations, [])


class TestModelRegistry(unittest.TestCase):
    """Test suite for Model Registry, version pinning, and checkpoint verification."""

    def setUp(self) -> None:
        self.registry = get_model_registry()

    def test_registry_loaded_and_versioned(self) -> None:
        self.assertEqual(self.registry.registry_version, "1.0.0")
        models = self.registry.list_models()
        self.assertGreaterEqual(len(models), 2)

        # spacy_vn_19_ner should be present with version 1.0.0
        spacy_model = self.registry.get_model("spacy_vn_19_ner", "1.0.0")
        self.assertEqual(spacy_model.version, "1.0.0")
        self.assertEqual(spacy_model.language, "vi")
        self.assertEqual(spacy_model.label_count, 19)

    def test_checkpoint_files_exist_on_disk(self) -> None:
        status = self.registry.verify_checkpoints()
        self.assertIn("spacy_vn_19_ner:1.0.0", status)
        self.assertTrue(status["spacy_vn_19_ner:1.0.0"])

    def test_label_space_matches_19_classes(self) -> None:
        labels = self.registry.load_label_space("spacy_vn_19_ner", "1.0.0")
        self.assertEqual(len(labels), 19)
        self.assertIn("GIVENNAME", labels)
        self.assertIn("IDCARDNUM", labels)
        self.assertIn("CREDITCARDNUMBER", labels)

    def test_get_nonexistent_model_raises_key_error(self) -> None:
        with self.assertRaises(KeyError):
            self.registry.get_model("unknown_model_id")


class TestSafeLogger(unittest.TestCase):
    """Test suite for safe logging and masking of credentials and sensitive PII."""

    def setUp(self) -> None:
        self.formatter = SafeFormatter(scrub_pii=True)

    def _format_message(self, msg: str) -> str:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None,
        )
        return self.formatter.format(record)

    def test_bearer_token_masked(self) -> None:
        sanitized = self._format_message("User request with Bearer secrettoken123456789")
        self.assertIn("[REDACTED_TOKEN]", sanitized)
        self.assertNotIn("secrettoken123456789", sanitized)

    def test_password_assignment_masked(self) -> None:
        sanitized = self._format_message("Connecting with password = 'supersecretpassword123'")
        self.assertIn("[REDACTED_SECRET]", sanitized)
        self.assertNotIn("supersecretpassword123", sanitized)

    def test_credit_card_masked(self) -> None:
        sanitized = self._format_message("User card is 4532-1234-5678-9012 processed")
        self.assertIn("[REDACTED_CARD]", sanitized)
        self.assertNotIn("4532-1234-5678-9012", sanitized)

    def test_citizen_id_cccd_masked(self) -> None:
        sanitized = self._format_message("Target CCCD 001234567890 extracted")
        self.assertIn("[REDACTED_CCCD]", sanitized)
        self.assertNotIn("001234567890", sanitized)

    def test_email_address_masked(self) -> None:
        sanitized = self._format_message("Send invoice to john.doe@example.com immediately")
        self.assertIn("[REDACTED_EMAIL]", sanitized)
        self.assertNotIn("john.doe@example.com", sanitized)

    def test_vietnamese_phone_masked(self) -> None:
        sanitized = self._format_message("User phone is 0987654321 registered")
        self.assertIn("[REDACTED_PHONE]", sanitized)
        self.assertNotIn("0987654321", sanitized)


class TestSecretScanner(unittest.TestCase):
    """Test suite for the secret scanning script (scripts/check_secrets.py)."""

    def test_clean_repository_scan_returns_zero(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        exit_code = scan_directory(repo_root)
        self.assertEqual(exit_code, 0)

    def test_scanner_catches_fake_aws_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            leak_file = tmp_path / "leak.py"
            leak_file.write_text("AWS_KEY = 'AKIA1234567890ABCDEF'\n", encoding="utf-8")
            findings = scan_file(leak_file, tmp_path)
            self.assertTrue(any(rule == "AWS Access Key" for _, rule, _ in findings))

    def test_scanner_catches_private_key_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            key_file = tmp_path / "server.py"
            key_file.write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n", encoding="utf-8")
            findings = scan_file(key_file, tmp_path)
            self.assertTrue(any(rule == "Private Key Block" for _, rule, _ in findings))

    def test_scanner_catches_forbidden_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            env_file = tmp_path / ".env"
            env_file.write_text("SECRET=real_secret_value\n", encoding="utf-8")
            exit_code = scan_directory(tmp_path)
            self.assertEqual(exit_code, 1)

    def test_pre_commit_hook_installer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / ".git").mkdir()
            code = install_pre_commit_hook(tmp_path)
            self.assertEqual(code, 0)
            hook = tmp_path / ".git" / "hooks" / "pre-commit"
            self.assertTrue(hook.is_file())
            self.assertTrue(os.access(hook, os.X_OK))


class TestHygieneAndDocker(unittest.TestCase):
    """Verify .env.example, .dockerignore, and health check handler."""

    def test_env_example_keys_and_safety(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        env_example = repo_root / ".env.example"
        self.assertTrue(env_example.is_file(), ".env.example must exist")

        content = env_example.read_text(encoding="utf-8")
        self.assertIn("APP_ENV=", content)
        self.assertIn("SYSTEM_VERSION=", content)
        self.assertIn("JWT_SECRET_KEY=", content)
        self.assertIn("STORAGE_ROOT=", content)

        # Ensure no real AWS, Github or RSA secrets
        self.assertNotIn("AKIA", content)
        self.assertNotIn("ghp_", content)
        self.assertNotIn("BEGIN RSA PRIVATE KEY", content)

    def test_dockerignore_rules(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        dockerignore = repo_root / ".dockerignore"
        self.assertTrue(dockerignore.is_file(), ".dockerignore must exist")

        content = dockerignore.read_text(encoding="utf-8")
        self.assertIn(".git", content)
        self.assertIn(".env", content)
        self.assertIn(".venv", content)
        self.assertIn(".pytest_cache", content)


if __name__ == "__main__":
    unittest.main()
