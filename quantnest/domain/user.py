"""User entity and wallet ownership rules.

Pure domain logic: no hashing library, no ORM, no framework. The *policy*
(what makes a user valid, who may touch a wallet) lives here; the *mechanism*
(bcrypt, JWT, SQL) lives in the infrastructure layer behind ports.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .exceptions import ValidationError

#: Deliberately permissive but safe: blocks header injection and control chars.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]{2,}$")

#: Wallet ids are used in URLs, so restrict them to URL-safe characters.
WALLET_ID_PATTERN = re.compile(r"^[A-Za-z0-9._\-]{1,64}$")

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class User:
    """A registered account that owns one or more wallets."""

    email: str
    password_hash: str
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    display_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        self.email = self.normalise_email(self.email)
        if not self.password_hash:
            raise ValidationError("A password hash is required")

    # ── Validation policy ────────────────────────────────────────────────

    @staticmethod
    def normalise_email(email: str) -> str:
        """Lowercase and trim so lookups are case-insensitive."""
        cleaned = (email or "").strip().lower()
        if not cleaned:
            raise ValidationError("Email is required")
        if len(cleaned) > 254:
            raise ValidationError("Email is too long")
        if not EMAIL_PATTERN.match(cleaned):
            raise ValidationError("Enter a valid email address")
        return cleaned

    @staticmethod
    def validate_password(password: str) -> str:
        """Enforce the password policy before it is ever hashed."""
        if not password:
            raise ValidationError("Password is required")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValidationError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
            )
        # bcrypt silently truncates beyond 72 bytes; reject rather than mislead.
        if len(password.encode("utf-8")) > MAX_PASSWORD_LENGTH:
            raise ValidationError(
                f"Password must be at most {MAX_PASSWORD_LENGTH} bytes"
            )
        return password

    # ── Ownership policy ─────────────────────────────────────────────────

    def default_wallet_id(self) -> str:
        """Every user gets one wallet automatically at registration."""
        return f"u-{self.user_id[:8]}"

    def owns(self, wallet: "Wallet") -> bool:
        return wallet.owner_id == self.user_id


@dataclass
class Wallet:
    """Ownership record binding a wallet id to a user.

    Distinct from :class:`quantnest.domain.wallet.Wallet`, which is the
    event-sourced *balance* aggregate. This is purely the ownership edge.
    """

    wallet_id: str
    owner_id: str
    label: Optional[str] = None
    created_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        self.wallet_id = self.validate_wallet_id(self.wallet_id)
        if not self.owner_id:
            raise ValidationError("A wallet must have an owner")

    @staticmethod
    def validate_wallet_id(wallet_id: str) -> str:
        cleaned = (wallet_id or "").strip()
        if not WALLET_ID_PATTERN.match(cleaned):
            raise ValidationError(
                "Wallet id may only contain letters, digits, dots, hyphens "
                "and underscores (max 64 characters)"
            )
        return cleaned
