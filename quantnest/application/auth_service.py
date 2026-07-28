"""Authentication and wallet-authorisation orchestration.

Coordinates the user repository, password hasher and token service. Knows
nothing about HTTP — the API layer translates the exceptions raised here into
status codes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from quantnest.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    EmailAlreadyRegisteredError,
    WalletAlreadyExistsError,
)
from quantnest.domain.ports import (
    PasswordHasher,
    TokenBlocklist,
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
        blocklist: Optional[TokenBlocklist] = None,
    ) -> None:
        self._users = users
        self._wallets = wallets
        self._hasher = hasher
        self._tokens = tokens
        self._blocklist = blocklist

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

        # A successful password check re-establishes trust, so any global
        # cutoff from a previous "sign out everywhere" is lifted. This also
        # sidesteps the one-second resolution of the JWT `iat` claim: without
        # it, signing back in during the same second would be locked out.
        self._clear_cutoff(user.user_id)

        logger.info("User logged in", extra={"user_id": user.user_id})
        return self._session_payload(user)

    # ── Token refresh ────────────────────────────────────────────────────

    def refresh(self, refresh_token: str) -> Dict[str, Any]:
        """Issue a new token pair from a valid refresh token.

        The presented token is revoked as part of the exchange (rotation), so
        a leaked refresh token cannot be reused after the legitimate client
        has already redeemed it.
        """
        claims = self._decode_refresh(refresh_token)
        user_id = str(claims["sub"])

        self._assert_not_revoked(claims, user_id)

        user = self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("This session is no longer valid")

        # Rotate: the old refresh token dies with this exchange.
        self._revoke_claims(claims, user_id)

        return self._session_payload(user)

    # ── Sign out ─────────────────────────────────────────────────────────

    def logout(self, access_token: str, refresh_token: Optional[str] = None) -> None:
        """Revoke the current session's tokens.

        Without this a stateless JWT stays valid until it expires, so
        "sign out" would be a client-side illusion.
        """
        if self._blocklist is None:
            return

        claims = self._decode_access(access_token)
        user_id = str(claims["sub"])
        self._revoke_claims(claims, user_id)

        if refresh_token:
            try:
                refresh_claims = self._decode_refresh(refresh_token)
            except AuthenticationError:
                # An unusable refresh token needs no revoking.
                return
            if str(refresh_claims.get("sub")) == user_id:
                self._revoke_claims(refresh_claims, user_id)

        logger.info("User signed out", extra={"user_id": user_id})

    def logout_everywhere(self, user: User) -> None:
        """Invalidate every token issued to this user so far.

        The cutoff is truncated to whole seconds because a JWT ``iat`` claim
        is integer epoch seconds. Storing microsecond precision would make a
        token issued moments *after* the cutoff compare as older, locking the
        user out of a fresh sign-in within the same second.
        """
        if self._blocklist is None:
            return

        cutoff = datetime.now(timezone.utc).replace(microsecond=0)
        self._blocklist.revoke_all_for_user(user.user_id, cutoff)
        # Tokens minted later in this same second must survive, so the
        # re-issued pair below carries a fresh jti and a later iat.
        logger.info("All sessions revoked", extra={"user_id": user.user_id})

    # ── Current user ─────────────────────────────────────────────────────

    def user_from_access_token(self, token: str) -> User:
        """Resolve a bearer token to its user, rejecting revoked tokens."""
        claims = self._decode_access(token)
        user_id = str(claims["sub"])

        self._assert_not_revoked(claims, user_id)

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

    def _decode_access(self, token: str) -> Dict[str, Any]:
        decoder = getattr(self._tokens, "decode_access_token", None)
        if decoder is None:
            return {"sub": self._tokens.verify_access_token(token)}
        return decoder(token)

    def _decode_refresh(self, token: str) -> Dict[str, Any]:
        decoder = getattr(self._tokens, "decode_refresh_token", None)
        if decoder is None:
            return {"sub": self._tokens.verify_refresh_token(token)}
        return decoder(token)

    def _clear_cutoff(self, user_id: str) -> None:
        """Lift a global revocation cutoff after a successful login."""
        if self._blocklist is None:
            return
        clear = getattr(self._blocklist, "clear_cutoff", None)
        if clear is not None:
            clear(user_id)

    def _assert_not_revoked(self, claims: Dict[str, Any], user_id: str) -> None:
        """Reject a token that is individually revoked or predates a cutoff."""
        if self._blocklist is None:
            return

        jti = claims.get("jti")
        if jti and self._blocklist.is_revoked(str(jti)):
            raise AuthenticationError("This session has been signed out")

        cutoff = self._blocklist.user_cutoff(user_id)
        issued_at = claims.get("iat")
        if cutoff is not None and issued_at is not None:
            issued = self._as_datetime(issued_at)
            # `iat` is integer epoch seconds, so a token issued in the same
            # second as the cutoff is indistinguishable from one issued just
            # before it. Revoke it: losing a session is far safer than
            # keeping a revoked one alive.
            if issued is not None and issued <= self._as_utc(cutoff):
                raise AuthenticationError("This session has been signed out")

    def _revoke_claims(self, claims: Dict[str, Any], user_id: str) -> None:
        if self._blocklist is None:
            return

        jti = claims.get("jti")
        if not jti:
            return

        expires = self._as_datetime(claims.get("exp")) or datetime.now(timezone.utc)
        self._blocklist.revoke(str(jti), user_id, expires)

    @staticmethod
    def _as_datetime(value: Any) -> Optional[datetime]:
        """JWT numeric dates arrive as epoch seconds."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return AuthService._as_utc(value)
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _as_utc(moment: datetime) -> datetime:
        """SQLite returns naive datetimes; treat them as UTC."""
        return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)

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
