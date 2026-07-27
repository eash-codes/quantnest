"""Authentication and wallet-authorisation orchestration.

Coordinates the user repository, password hasher and token service. Knows
nothing about HTTP — the API layer translates the exceptions raised here into
status codes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from quantnest.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    EmailAlreadyRegisteredError,
    WalletAlreadyExistsError,
)
from quantnest.domain.ports import (
    PasswordHasher,
    TokenService,
    UserRepository,
    WalletOwnershipRepository,
)
from quantnest.domain.user import User, Wallet as WalletOwnership

logger = logging.getLogger(__name__)


class AuthService:
    """Registration, login, token refresh and wallet access checks."""

    def __init__(
        self,
        users: UserRepository,
        wallets: WalletOwnershipRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
    ) -> None:
        self._users = users
        self._wallets = wallets
        self._hasher = hasher
        self._tokens = tokens

    # ── Registration ─────────────────────────────────────────────────────

    def register(
        self,
        email: str,
        password: str,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an account and provision its first wallet."""
        normalised = User.normalise_email(email)
        User.validate_password(password)

        if self._users.get_by_email(normalised) is not None:
            raise EmailAlreadyRegisteredError("That email is already registered")

        user = User(
            email=normalised,
            password_hash=self._hasher.hash(password),
            display_name=(display_name or "").strip() or None,
        )
        self._users.add(user)

        # Every account starts with exactly one wallet it owns.
        wallet = WalletOwnership(
            wallet_id=user.default_wallet_id(),
            owner_id=user.user_id,
            label="Primary",
        )
        self._wallets.add(wallet)

        logger.info(
            "User registered",
            extra={"user_id": user.user_id, "wallet_id": wallet.wallet_id},
        )

        return self._session_payload(user)

    # ── Login ────────────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Exchange credentials for a token pair."""
        try:
            normalised = User.normalise_email(email)
        except Exception:
            # Never reveal whether the failure was format or lookup.
            raise AuthenticationError("Incorrect email or password")

        user = self._users.get_by_email(normalised)

        # Hash even when the user is missing, so response time does not leak
        # whether an account exists (timing-attack mitigation).
        stored_hash = user.password_hash if user else self._hasher.dummy_hash()
        password_ok = self._hasher.verify(password, stored_hash)

        if user is None or not password_ok:
            logger.info("Failed login attempt", extra={"email": normalised})
            raise AuthenticationError("Incorrect email or password")

        if not user.is_active:
            raise AuthenticationError("This account has been deactivated")

        logger.info("User logged in", extra={"user_id": user.user_id})
        return self._session_payload(user)

    # ── Token refresh ────────────────────────────────────────────────────

    def refresh(self, refresh_token: str) -> Dict[str, Any]:
        """Issue a new token pair from a valid refresh token."""
        user_id = self._tokens.verify_refresh_token(refresh_token)

        user = self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("This session is no longer valid")

        return self._session_payload(user)

    # ── Current user ─────────────────────────────────────────────────────

    def user_from_access_token(self, token: str) -> User:
        """Resolve a bearer token to its user."""
        user_id = self._tokens.verify_access_token(token)

        user = self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("This session is no longer valid")

        return user

    # ── Authorisation ────────────────────────────────────────────────────

    def authorize_wallet(self, user: User, wallet_id: str) -> str:
        """Confirm the user owns this wallet, or refuse.

        This is the check that closes the hole where any caller could read or
        trade any wallet simply by editing the URL.
        """
        ownership = self._wallets.get(wallet_id)

        if ownership is None:
            # Do not disclose whether the wallet exists but belongs to someone
            # else; both cases look identical from outside.
            raise AuthorizationError("You do not have access to this wallet")

        if ownership.owner_id != user.user_id:
            logger.warning(
                "Blocked cross-account wallet access",
                extra={"user_id": user.user_id, "wallet_id": wallet_id},
            )
            raise AuthorizationError("You do not have access to this wallet")

        return wallet_id

    def list_wallets(self, user: User) -> List[Dict[str, Any]]:
        return [
            {
                "wallet_id": wallet.wallet_id,
                "label": wallet.label,
                "created_at": wallet.created_at,
            }
            for wallet in self._wallets.list_for_owner(user.user_id)
        ]

    def create_wallet(self, user: User, wallet_id: str, label: Optional[str] = None):
        """Add another wallet to an existing account."""
        cleaned = WalletOwnership.validate_wallet_id(wallet_id)

        if self._wallets.get(cleaned) is not None:
            raise WalletAlreadyExistsError("That wallet id is already taken")

        wallet = WalletOwnership(
            wallet_id=cleaned,
            owner_id=user.user_id,
            label=(label or "").strip() or None,
        )
        self._wallets.add(wallet)

        logger.info(
            "Wallet created",
            extra={"user_id": user.user_id, "wallet_id": wallet.wallet_id},
        )
        return wallet

    # ── Helpers ──────────────────────────────────────────────────────────

    def _session_payload(self, user: User) -> Dict[str, Any]:
        return {
            "access_token": self._tokens.issue_access_token(user.user_id),
            "refresh_token": self._tokens.issue_refresh_token(user.user_id),
            "token_type": "bearer",
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "display_name": user.display_name,
                "wallets": [w["wallet_id"] for w in self.list_wallets(user)],
            },
        }
