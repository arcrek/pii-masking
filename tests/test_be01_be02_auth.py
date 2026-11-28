"""Unit tests for Authentication (BE-01) and Session Management (BE-02)."""

from __future__ import annotations

import unittest
import time
from app.security.auth import (
    hash_password,
    verify_password,
    LoginRateLimiter,
)
from app.security.session import (
    SessionManager,
)


class TestAuthAndSession(unittest.TestCase):
    """Test suite for BE-01 and BE-02."""

    def test_be01_password_hashing_and_verification(self) -> None:
        raw_pw = "DemoUser2026@Secret!"
        hashed = hash_password(raw_pw)

        self.assertNotEqual(raw_pw, hashed)
        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))
        self.assertTrue(verify_password(raw_pw, hashed))
        self.assertFalse(verify_password("WrongPassword123", hashed))
        self.assertFalse(verify_password("", hashed))
        self.assertFalse(verify_password(raw_pw, ""))

    def test_be01_login_rate_limiter_lockout(self) -> None:
        limiter = LoginRateLimiter(max_attempts=3, window_seconds=10, lockout_seconds=30)
        username = "test_user"
        ip = "192.168.1.100"

        # Attempts 1 and 2: not locked
        is_locked, count = limiter.record_failure(username, ip)
        self.assertFalse(is_locked)
        self.assertEqual(count, 1)

        is_locked, count = limiter.record_failure(username, ip)
        self.assertFalse(is_locked)
        self.assertEqual(count, 2)

        # Attempt 3: reached threshold, must lock
        is_locked, count = limiter.record_failure(username, ip)
        self.assertTrue(is_locked)
        self.assertEqual(count, 3)

        locked, remaining = limiter.is_locked(username, ip)
        self.assertTrue(locked)
        self.assertGreater(remaining, 0)

        # Different IP or user is NOT locked
        other_locked, _ = limiter.is_locked("other_user", ip)
        self.assertFalse(other_locked)

        # Reset on success
        limiter.record_success(username, ip)
        locked_after_success, _ = limiter.is_locked(username, ip)
        self.assertFalse(locked_after_success)

    def test_be02_session_creation_and_validation(self) -> None:
        session_mgr = SessionManager()
        session_data = session_mgr.create_session(
            user_id="u-001",
            username="vinh_lead",
            role="lead",
            ip_address="10.0.0.1",
        )

        token = session_data["access_token"]
        self.assertIsInstance(token, str)

        # Validate token
        is_valid, payload, err = session_mgr.validate_token(token)
        self.assertTrue(is_valid)
        self.assertIsNone(err)
        self.assertEqual(payload["sub"], "u-001")
        self.assertEqual(payload["username"], "vinh_lead")
        self.assertEqual(payload["role"], "lead")

    def test_be02_session_revocation_on_logout(self) -> None:
        session_mgr = SessionManager()
        session_data = session_mgr.create_session(user_id="u-002", username="reviewer")
        token = session_data["access_token"]
        jti = session_data["jti"]

        # Valid initially
        is_valid, _, _ = session_mgr.validate_token(token)
        self.assertTrue(is_valid)

        # Logout / Revoke
        revoked = session_mgr.revoke_session(jti)
        self.assertTrue(revoked)

        # Now validation MUST fail with SESSION_REVOKED
        is_valid_after, payload, err = session_mgr.validate_token(token)
        self.assertFalse(is_valid_after)
        self.assertIsNone(payload)
        self.assertEqual(err, "SESSION_REVOKED")

    def test_be02_tampered_or_invalid_token(self) -> None:
        session_mgr = SessionManager()
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.tampered"

        is_valid, payload, err = session_mgr.validate_token(fake_token)
        self.assertFalse(is_valid)
        self.assertIsNone(payload)
        self.assertEqual(err, "INVALID_TOKEN")
