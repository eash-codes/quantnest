"""Domain exception hierarchy.

The API layer maps these onto HTTP status codes, so route handlers never need
to inspect exception *names* as strings — which is what the previous
``"InsufficientFundsError" in str(type(e))`` checks were doing.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for every business-rule violation."""

    #: Short machine-readable code surfaced in API error responses.
    code: str = "domain_error"


class ValidationError(DomainError):
    """The request is structurally invalid (bad quantity, bad symbol format)."""

    code = "validation_error"


class InsufficientFundsError(DomainError):
    """The wallet does not hold enough cash for this operation."""

    code = "insufficient_funds"


class InsufficientPositionsError(DomainError):
    """The portfolio does not hold enough shares to sell."""

    code = "insufficient_positions"


class UnknownSymbolError(DomainError):
    """The symbol could not be priced."""

    code = "unknown_symbol"


class OrderExecutionError(DomainError):
    """The order could not be executed."""

    code = "order_execution_error"


class OrderNotFoundError(DomainError):
    """No order exists with the requested identifier."""

    code = "order_not_found"


class OrderStateError(DomainError):
    """The order is in a state that forbids the requested transition."""

    code = "invalid_order_state"


# ── Authentication and authorisation ─────────────────────────────────────


class AuthenticationError(DomainError):
    """Credentials are missing, malformed or incorrect. Maps to HTTP 401."""

    code = "authentication_failed"


class AuthorizationError(DomainError):
    """The caller is authenticated but not permitted. Maps to HTTP 403."""

    code = "not_authorized"


class EmailAlreadyRegisteredError(DomainError):
    """Registration attempted with an email that already exists. HTTP 409."""

    code = "email_already_registered"


class UserNotFoundError(DomainError):
    """No user exists for the given identifier. HTTP 404."""

    code = "user_not_found"


class RateLimitExceededError(DomainError):
    """Too many attempts in the current window. Maps to HTTP 429."""

    code = "rate_limit_exceeded"

    def __init__(self, message: str, retry_after: int = 60) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class WalletAlreadyExistsError(DomainError):
    """A wallet with that id is already taken. HTTP 409."""

    code = "wallet_already_exists"
