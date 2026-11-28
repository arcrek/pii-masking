"""Unit tests for Authentication (BE-01) and Session Management (BE-02)."""

from __future__ import annotations

import time
import unittest

from app.security.auth import (
    hash_password,
    verify_password,
    LoginRateLimiter,
)
from app.security.session import (
    SessionManager,
)
from config.system_config import SystemConfig


class TestAuthAndSession(unittest.TestCase):
    """Test suite for BE-01 and BE-02."""

    def test_be01_password_hashing_and_verification(self) -> None:
        raw_pw = "DemoUser2026@Secret!"
        hashed = hash_password(raw_pw)

        self.assertNotEqual(raw_pw, hashed)
        # Supports Argon2id ($argon2id$) or bcrypt ($2b$ / $2a$)
        self.assertTrue(
            hashed.startswith("$argon2id$") or hashed.startswith("$2b$") or hashed.startswith("$2a$"),
            f"Expected Argon2id or bcrypt hash prefix, got {hashed[:15]}",
        )
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

    def test_be01_lockout_persists_past_window_seconds(self) -> None:
        """Lockout must NOT be cleared early when time exceeds window_seconds (Critical Finding 5)."""
        limiter = LoginRateLimiter(max_attempts=2, window_seconds=0.1, lockout_seconds=1.0)
        username = "brute_force_user"
        ip = "10.10.10.10"

        limiter.record_failure(username, ip)
        is_locked, count = limiter.record_failure(username, ip)
        self.assertTrue(is_locked)
        self.assertEqual(count, 2)

        # Wait for window_seconds to elapse, but stay inside lockout_seconds
        time.sleep(0.15)

        # Calling record_failure again MUST keep the account locked and not reset count
        is_still_locked, attempts = limiter.record_failure(username, ip)
        self.assertTrue(is_still_locked)
        self.assertEqual(attempts, 2)

        # is_locked must also still report locked
        locked, rem = limiter.is_locked(username, ip)
        self.assertTrue(locked)
        self.assertIsNotNone(rem)
        self.assertGreater(rem, 0)

    def test_be01_rate_limiter_worst_case_eviction(self) -> None:
        """Rate limiter strictly caps tracked keys under distributed spray (Suggestion 3)."""
        max_keys = 20
        limiter = LoginRateLimiter(max_attempts=5, window_seconds=300.0, lockout_seconds=900.0, max_tracked_keys=max_keys)

        # Insert 30 distinct keys within window (none are expired)
        for i in range(30):
            limiter.record_failure(f"user_{i}", f"10.0.0.{i}")

        # Eviction must keep tracked keys under max_tracked_keys
        self.assertLessEqual(len(limiter._records), max_keys)

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

    def test_be02_session_manager_rejects_placeholder_secret_in_prod_and_staging(self) -> None:
        """SessionManager must fail closed on default placeholder dev secrets in prod and staging."""
        # Production with dev secret -> ValueError
        prod_cfg = SystemConfig(app_env="production", jwt_secret_key="change-this-insecure-secret-key-for-local-dev-only-32bytes")
        with self.assertRaises(ValueError):
            SessionManager(config=prod_cfg)

        # Staging with dev secret -> ValueError
        staging_cfg = SystemConfig(app_env="staging", jwt_secret_key="change-this-insecure-secret-key-for-local-dev-only-32bytes")
        with self.assertRaises(ValueError):
            SessionManager(config=staging_cfg)

        # Dev with dev secret -> Allowed
        dev_cfg = SystemConfig(app_env="development", jwt_secret_key="change-this-insecure-secret-key-for-local-dev-only-32bytes")
        mgr = SessionManager(config=dev_cfg)
        self.assertIsNotNone(mgr)

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

    def test_be02_revoke_user_sessions(self) -> None:
        """Revoking all sessions for a specific user invalidates all their active tokens."""
        session_mgr = SessionManager()
        s1 = session_mgr.create_session(user_id="u-bulk-01", username="user1")
        s2 = session_mgr.create_session(user_id="u-bulk-01", username="user1")
        s3 = session_mgr.create_session(user_id="u-other-02", username="user2")

        revoked_count = session_mgr.revoke_user_sessions("u-bulk-01")
        self.assertEqual(revoked_count, 2)

        # Both user1 tokens are revoked
        v1, _, err1 = session_mgr.validate_token(s1["access_token"])
        v2, _, err2 = session_mgr.validate_token(s2["access_token"])
        self.assertFalse(v1)
        self.assertEqual(err1, "SESSION_REVOKED")
        self.assertFalse(v2)
        self.assertEqual(err2, "SESSION_REVOKED")

        # user2 token remains valid
        v3, _, err3 = session_mgr.validate_token(s3["access_token"])
        self.assertTrue(v3)
        self.assertIsNone(err3)

    def test_be02_token_expiration(self) -> None:
        """Expired tokens must fail validation with TOKEN_EXPIRED."""
        session_mgr = SessionManager()
        session_mgr.expire_minutes = -1
        session_data = session_mgr.create_session(user_id="u-exp", username="expired_user")
        token = session_data["access_token"]

        is_valid, payload, err = session_mgr.validate_token(token)
        self.assertFalse(is_valid)
        self.assertIsNone(payload)
        self.assertEqual(err, "TOKEN_EXPIRED")

    def test_be02_purge_expired_sessions(self) -> None:
        """Purging expired sessions removes them from in-memory storage."""
        session_mgr = SessionManager()
        session_mgr.expire_minutes = -5
        s1 = session_mgr.create_session(user_id="u-p1", username="purge1")
        session_mgr.expire_minutes = 60
        s2 = session_mgr.create_session(user_id="u-p2", username="active2")

        purged = session_mgr.purge_expired_sessions()
        self.assertGreaterEqual(purged, 1)
        self.assertNotIn(s1["jti"], session_mgr._sessions)
        self.assertIn(s2["jti"], session_mgr._sessions)

    def test_be02_tampered_or_invalid_token(self) -> None:
        session_mgr = SessionManager()
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.tampered"

        is_valid, payload, err = session_mgr.validate_token(fake_token)
        self.assertFalse(is_valid)
        self.assertIsNone(payload)
        self.assertEqual(err, "INVALID_TOKEN")
