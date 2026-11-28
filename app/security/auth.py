"""Authentication and password hashing utilities (BE-01).

Implements:
- Argon2id password hashing with bcrypt fallback
- Monotonic clock rate-limiting for failed login attempts
- Constant-time password verification
- Memory-bounded eviction to prevent DoS
"""

from __future__ import annotations

import time
import threading
from typing import Tuple, Optional, Dict

# Prefer Argon2id per System Architecture (system-architecture.md §6 & R2.3)
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    _ARGON2_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
except ImportError:
    _ARGON2_HASHER = None
    VerifyMismatchError = Exception  # type: ignore[assignment, misc]

# Optionalize bcrypt import consistently
try:
    import bcrypt
except ImportError:
    bcrypt = None


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id if available, falling back to bcrypt."""
    if not password:
        raise ValueError("Password cannot be empty.")
    encoded = password.encode("utf-8")
    if len(encoded) > 1024:
        raise ValueError("Password exceeds maximum allowed length.")

    if _ARGON2_HASHER is not None:
        return _ARGON2_HASHER.hash(password)

    if bcrypt is None:
        raise RuntimeError("No secure password hashing library available (argon2-cffi or bcrypt required).")

    if len(encoded) > 72:
        raise ValueError("Password exceeds maximum bcrypt length of 72 bytes.")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(encoded, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored Argon2id or bcrypt hash."""
    if not plain_password or not hashed_password:
        return False

    is_argon2 = hashed_password.startswith("$argon2id$") or hashed_password.startswith("$argon2i$")

    if is_argon2:
        if _ARGON2_HASHER is None:
            raise RuntimeError("argon2-cffi is required to verify Argon2 password hashes.")
        try:
            return _ARGON2_HASHER.verify(hashed_password, plain_password)
        except VerifyMismatchError:
            return False
        except (ValueError, TypeError):
            return False

    # Otherwise assume bcrypt hash
    if bcrypt is None:
        raise RuntimeError("bcrypt is required to verify bcrypt password hashes.")
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


class LoginRateLimiter:
    """In-memory rate limiter for failed login attempts by (username, client_ip).

    Rules:
    - Lockout occurs after max_attempts within window_seconds.
    - Active lockout lasts lockout_seconds and cannot be cleared by window expiration.
    - Memory is strictly bounded to max_tracked_keys via LRU/FIFO eviction.
    """

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: float = 300.0,
        lockout_seconds: float = 900.0,
        max_tracked_keys: int = 10000,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self.max_tracked_keys = max_tracked_keys
        self._lock = threading.Lock()
        # key -> (failure_count, first_failure_time, locked_until_time)
        self._records: Dict[str, Tuple[int, float, float]] = {}

    def _make_key(self, username: str, client_ip: str) -> str:
        return f"{username.strip().lower()}::{client_ip.strip()}"

    def _prune_expired_locked(self, now: float) -> None:
        """Remove old records where lockout and window have both expired.

        If still over max_tracked_keys, evict oldest entries by first_time
        to strictly bound memory and O(N) scan time under distributed spray.
        """
        if len(self._records) < self.max_tracked_keys:
            return

        keys_to_delete = []
        for key, (_, first_time, locked_until) in self._records.items():
            if locked_until <= now and (now - first_time > self.window_seconds):
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del self._records[key]

        # Worst-case bound: if still exceeding max_tracked_keys, evict oldest entries
        if len(self._records) >= self.max_tracked_keys:
            sorted_keys = sorted(self._records.keys(), key=lambda k: self._records[k][1])
            # Evict excess plus 10% headroom
            excess = len(self._records) - int(self.max_tracked_keys * 0.9)
            for k in sorted_keys[:excess]:
                del self._records[k]

    def is_locked(self, username: str, client_ip: str) -> Tuple[bool, Optional[int]]:
        """Check if account is currently locked out.

        Returns:
            (is_locked, remaining_seconds)
        """
        key = self._make_key(username, client_ip)
        now = time.monotonic()

        with self._lock:
            record = self._records.get(key)
            if not record:
                return False, None

            count, first_time, locked_until = record
            if locked_until > now:
                remaining = int(locked_until - now)
                return True, max(1, remaining)

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
        now = time.monotonic()

        with self._lock:
            self._prune_expired_locked(now)
            record = self._records.get(key)
            if not record:
                self._records[key] = (1, now, 0.0)
                return False, 1

            count, first_time, locked_until = record

            # Critical Fix: Active lockout must NEVER be reset early by window_seconds expiration
            if locked_until > now:
                return True, count

            # If previously locked and lockout has elapsed, start fresh window
            if locked_until > 0 and locked_until <= now:
                self._records[key] = (1, now, 0.0)
                return False, 1

            # If window expired without lockout, reset window
            if now - first_time > self.window_seconds:
                self._records[key] = (1, now, 0.0)
                return False, 1

            new_count = count + 1
            if new_count >= self.max_attempts:
                new_locked_until = now + self.lockout_seconds
                self._records[key] = (new_count, first_time, new_locked_until)
                return True, new_count

            self._records[key] = (new_count, first_time, 0.0)
            return False, new_count

    def record_success(self, username: str, client_ip: str) -> None:
        """Reset failed login attempts on successful login."""
        key = self._make_key(username, client_ip)
        with self._lock:
            self._records.pop(key, None)
