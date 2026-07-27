"""Security adapters: password hashing and JWT tokens.

Implements the :class:`~quantnest.domain.ports.PasswordHasher` and
:class:`~quantnest.domain.ports.TokenService` ports. All cryptography lives
here so the domain stays free of third-party dependencies.
"""

from __future__ import annotations

import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from passlib.context import CryptContext

from quantnest.domain.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

ACCESS_TOKEN_TTL_MINUTES = int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "30"))
REFRESH_TOKEN_TTL_DAYS = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "7"))
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "quantnest"


def get_secret_key() -> str:
    """Return the signing key from ``JWT_SECRET_KEY``.

    Refuses to start in production without an explicit key. In development a
    random key is generated per process, which simply invalidates tokens on
    restart rather than shipping a guessable default.
    """
    secret = os.getenv("JWT_SECRET_KEY", "").strip()

    if secret:
        if len(secret) < 32:
            raise RuntimeError(
                "JWT_SECRET_KEY must be at least 32 characters. "
                "Generate one with: openssl rand -hex 32"
            )
        return secret

    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    if environment in {"production", "prod", "staging"}:
        raise RuntimeError(
            "JWT_SECRET_KEY is required when ENVIRONMENT=production. "
            "Generate one with: openssl rand -hex 32"
        )

    logger.warning(
        "JWT_SECRET_KEY is unset; using an ephemeral development key. "
        "Tokens will be invalidated on restart."
    )
    return secrets.token_hex(32)


class BcryptPasswordHasher:
    """bcrypt-backed :class:`~quantnest.domain.ports.PasswordHasher`."""

    def __init__(self, rounds: int = 12) -> None:
        self._context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=rounds,
        )
        # Precomputed so failed logins do the same work as successful ones.
        self._dummy_hash = self._context.hash("not-a-real-password")

    def hash(self, password: str) -> str:
        return self._context.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return self._context.verify(password, password_hash)
        except Exception:
            # Malformed stored hash: treat as a failed match, never a 500.
            return False

    def dummy_hash(self) -> str:
        """A valid hash that never matches, for constant-time failed logins."""
        return self._dummy_hash


class JwtTokenService:
    """PyJWT-backed :class:`~quantnest.domain.ports.TokenService`.

    Access tokens are short-lived and sent on every request; refresh tokens
    are long-lived and only presented to ``/auth/refresh``. The ``type`` claim
    prevents a refresh token being replayed as an access token.
    """

    def __init__(
        self,
        secret_key: str | None = None,
        access_ttl_minutes: int = ACCESS_TOKEN_TTL_MINUTES,
        refresh_ttl_days: int = REFRESH_TOKEN_TTL_DAYS,
    ) -> None:
        self._secret = secret_key or get_secret_key()
        self._access_ttl = timedelta(minutes=access_ttl_minutes)
        self._refresh_ttl = timedelta(days=refresh_ttl_days)

    # ── Issuing ──────────────────────────────────────────────────────────

    def issue_access_token(self, user_id: str) -> str:
        return self._encode(user_id, "access", self._access_ttl)

    def issue_refresh_token(self, user_id: str) -> str:
        return self._encode(user_id, "refresh", self._refresh_ttl)

    # ── Verifying ────────────────────────────────────────────────────────

    def verify_access_token(self, token: str) -> str:
        return self._decode(token, expected_type="access")

    def verify_refresh_token(self, token: str) -> str:
        return self._decode(token, expected_type="refresh")

    @property
    def access_ttl_seconds(self) -> int:
        return int(self._access_ttl.total_seconds())

    # ── internals ────────────────────────────────────────────────────────

    def _encode(self, user_id: str, token_type: str, ttl: timedelta) -> str:
        now = datetime.now(timezone.utc)
        payload: Dict[str, Any] = {
            "sub": user_id,
            "type": token_type,
            "iss": JWT_ISSUER,
            "iat": now,
            "exp": now + ttl,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self._secret, algorithm=JWT_ALGORITHM)

    def _decode(self, token: str, expected_type: str) -> str:
        if not token:
            raise AuthenticationError("Authentication token is missing")

        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[JWT_ALGORITHM],
                issuer=JWT_ISSUER,
                options={"require": ["exp", "sub", "iss"]},
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Your session has expired; please sign in again")
        except jwt.InvalidTokenError:
            # Covers bad signature, wrong issuer, malformed token.
            raise AuthenticationError("Invalid authentication token")

        if payload.get("type") != expected_type:
            # Blocks presenting a refresh token where an access token is required.
            raise AuthenticationError("Invalid authentication token")

        subject = payload.get("sub")
        if not subject:
            raise AuthenticationError("Invalid authentication token")

        return str(subject)


_hasher_singleton: BcryptPasswordHasher | None = None
_token_service_singleton: JwtTokenService | None = None


def get_password_hasher() -> BcryptPasswordHasher:
    """Shared hasher. Reused so the dummy hash is computed only once."""
    global _hasher_singleton
    if _hasher_singleton is None:
        _hasher_singleton = BcryptPasswordHasher()
    return _hasher_singleton


def get_token_service() -> JwtTokenService:
    global _token_service_singleton
    if _token_service_singleton is None:
        _token_service_singleton = JwtTokenService()
    return _token_service_singleton


def reset_security_singletons() -> None:
    """Clear cached instances. Used by tests."""
    global _hasher_singleton, _token_service_singleton
    _hasher_singleton = None
    _token_service_singleton = None
