"""Session and Token Management (BE-02).

Implements:
- JWT token issuance with unique JTI
- Token expiration verification
- Server-side token revocation on logout
- Strict rejection of revoked, tampered, or expired sessions
- Safe config loading via get_config() with security validation
"""

from __future__ import annotations

import time
import uuid
import threading
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Tuple, Any
import jwt

from config.system_config import SystemConfig, get_config


@dataclass
class SessionRecord:
    session_id: str
    user_id: str
    username: str
    role: str
    token_jti: str
    ip_address: str
    user_agent: str
    expires_at: float
    created_at: float
    is_revoked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SessionManager:
    """Manages active sessions, tokens, and server-side revocation list."""

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        self.config = config or get_config()
        # Security validation (Finding 4)
        sec_violations = self.config.validate_security()
        if sec_violations:
            raise ValueError(f"Security validation failed for session manager: {sec_violations}")

        self.secret_key = self.config.jwt_secret_key
        if not self.secret_key or len(self.secret_key.strip()) < 16:
            raise ValueError("JWT secret key must be non-empty and at least 16 bytes.")
        if self.config.app_env in ("production", "staging") and "change-this" in self.secret_key:
            raise ValueError(f"Insecure default JWT secret cannot be used in {self.config.app_env} environment.")
        self.algorithm = self.config.jwt_algorithm
        self.expire_minutes = self.config.access_token_expire_minutes

        self._lock = threading.Lock()
        # jti -> SessionRecord
        self._sessions: Dict[str, SessionRecord] = {}

    def create_session(
        self,
        user_id: str,
        username: str,
        role: str = "reviewer",
        ip_address: str = "127.0.0.1",
        user_agent: str = "",
        custom_expire_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Issue an access token and register an active session."""
        now = time.time()
        mins = custom_expire_minutes if custom_expire_minutes is not None else self.expire_minutes
        expires_at = now + (mins * 60)
        jti = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        payload = {
            "sub": user_id,
            "username": username,
            "role": role,
            "jti": jti,
            "iat": int(now),
            "exp": int(expires_at),
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        record = SessionRecord(
            session_id=session_id,
            user_id=user_id,
            username=username,
            role=role,
            token_jti=jti,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
            created_at=now,
            is_revoked=False,
        )

        with self._lock:
            self._sessions[jti] = record

        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": int(mins * 60),
            "session_id": session_id,
            "jti": jti,
        }

    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Validate an access token and check revocation status.

        Returns:
            (is_valid, payload, error_message)
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"require": ["exp", "sub", "jti"]},
            )
        except jwt.ExpiredSignatureError:
            return False, None, "TOKEN_EXPIRED"
        except jwt.InvalidTokenError:
            return False, None, "INVALID_TOKEN"

        jti = payload.get("jti")
        if not jti:
            return False, None, "MISSING_JTI"

        with self._lock:
            record = self._sessions.get(jti)
            if not record:
                return False, None, "SESSION_NOT_FOUND"

            if record.is_revoked:
                return False, None, "SESSION_REVOKED"

        return True, payload, None

    def revoke_session(self, jti: str) -> bool:
        """Revoke a session by JTI (e.g. on logout)."""
        with self._lock:
            if jti in self._sessions:
                self._sessions[jti].is_revoked = True
                return True
            return False

    def revoke_user_sessions(self, user_id: str) -> int:
        """Revoke all active sessions for a given user."""
        count = 0
        with self._lock:
            for s in self._sessions.values():
                if s.user_id == user_id and not s.is_revoked:
                    s.is_revoked = True
                    count += 1
        return count

    def purge_expired_sessions(self) -> int:
        """Remove old expired sessions to prevent memory bloat."""
        now = time.time()
        purged = 0
        with self._lock:
            expired_jtis = [jti for jti, s in self._sessions.items() if s.expires_at <= now]
            for jti in expired_jtis:
                del self._sessions[jti]
                purged += 1
        return purged
