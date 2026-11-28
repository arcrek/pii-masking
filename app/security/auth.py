"""Authentication and Demo Account Management (BE-01).

Implements:
- Password hashing with bcrypt
- Constant-time password verification
- Brute-force login rate limiting by (username, client_ip)
- Seeding of standard demo accounts (admin, reviewer, demo_user)
"""

from __future__ import annotations

import time
import threading
from typing import Dict, Tuple, Optional
import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with salt."""
    if not password:
        raise ValueError("Password cannot be empty.")
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("Password exceeds maximum bcrypt length of 72 bytes.")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(encoded, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash in constant time."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


class LoginRateLimiter:
    """Thread-safe login rate limiter keyed by (username, client_ip).

    Rules:
    - Max 5 consecutive failed attempts per 5-minute window.
    - If exceeded, locks out the combination for 15 minutes.
    """

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 300,
        lockout_seconds: int = 900,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._lock = threading.Lock()
        # key -> (failure_count, first_failure_time, locked_until_time)
        self._records: Dict[str, Tuple[int, float, float]] = {}

    def _make_key(self, username: str, client_ip: str) -> str:
        return f"{username.strip().lower()}::{client_ip.strip()}"

    def is_locked(self, username: str, client_ip: str) -> Tuple[bool, Optional[int]]:
        """Check if account is currently locked out.

        Returns:
            (is_locked, remaining_seconds)
        """
        key = self._make_key(username, client_ip)
        now = time.time()

        with self._lock:
            record = self._records.get(key)
            if not record:
                return False, None

            count, first_time, locked_until = record
            if locked_until > now:
                remaining = int(locked_until - now)
                return True, remaining

            # If window expired and not locked, clean up
            if now - first_time > self.window_seconds:
                del self._records[key]
                return False, None

            return False, None

    def record_failure(self, username: str, client_ip: str) -> Tuple[bool, int]:
        """Record a failed login attempt.

        Returns:
            (is_now_locked, attempts_count)
        """
        key = self._make_key(username, client_ip)
        now = time.time()

        with self._lock:
            record = self._records.get(key)
            if not record:
                self._records[key] = (1, now, 0.0)
                return False, 1

            count, first_time, locked_until = record

            # If previously locked and lock expired, reset
            if locked_until > 0 and locked_until <= now:
                self._records[key] = (1, now, 0.0)
                return False, 1

            # If outside window, reset
            if now - first_time > self.window_seconds:
                self._records[key] = (1, now, 0.0)
                return False, 1

            new_count = count + 1
            if new_count >= self.max_attempts:
                locked_until = now + self.lockout_seconds
                self._records[key] = (new_count, first_time, locked_until)
                return True, new_count

            self._records[key] = (new_count, first_time, 0.0)
            return False, new_count

    def record_success(self, username: str, client_ip: str) -> None:
        """Clear failed attempts upon successful login."""
        key = self._make_key(username, client_ip)
        with self._lock:
            self._records.pop(key, None)
