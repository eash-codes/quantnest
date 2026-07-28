"""Ports (interfaces) the domain depends on.

The domain layer must not know how data is stored or where prices come from.
It declares the capabilities it needs here as ``typing.Protocol`` classes, and
the infrastructure layer provides implementations.

Nothing in this module imports from ``quantnest.infra``, ``quantnest.api`` or
any third-party framework — only the standard library. That is what keeps the
dependency arrow pointing inwards.
"""

from __future__ import annotations

from datetime import datetime  # noqa: F401 - used in Protocol annotations
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Optional, Protocol, runtime_checkable

from .exceptions import UnknownSymbolError

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .events import DomainEvent
    from .order import Order
    from .trade import Trade
    from .user import User, Wallet as WalletOwnership

__all__ = [
    "UnknownSymbolError",
    "MarketDataProvider",
    "EventStore",
    "PositionRepository",
    "TradeRepository",
    "OrderRepository",
    "UserRepository",
    "WalletOwnershipRepository",
    "PasswordHasher",
    "TokenService",
    "TokenBlocklist",
    "InMemoryEventStore",
    "InMemoryPositionRepository",
    "InMemoryTradeRepository",
    "InMemoryOrderRepository",
    "InMemoryUserRepository",
    "InMemoryWalletOwnershipRepository",
    "InMemoryTokenBlocklist",
    "StaticMarketDataProvider",
]


@runtime_checkable
class MarketDataProvider(Protocol):
    """Supplies the current price for a tradable symbol."""

    def get_price(self, symbol: str) -> Decimal:
        """Return the latest price for ``symbol``.

        Raises:
            UnknownSymbolError: if no price can be determined.
        """
        ...


@runtime_checkable
class EventStore(Protocol):
    """Append-only store for wallet ledger events."""

    def load_events(self, wallet_id: str) -> List["DomainEvent"]:
        """Return every event for a wallet, oldest first."""
        ...

    def append_event(self, wallet_id: str, event: "DomainEvent") -> None:
        """Append a single event. Must never mutate or delete existing events."""
        ...


@runtime_checkable
class PositionRepository(Protocol):
    """Persists current holdings per wallet."""

    def load_positions(self, wallet_id: str) -> Dict[str, Decimal]:
        """Return ``{symbol: quantity}`` for all non-zero positions."""
        ...

    def save_positions(self, wallet_id: str, positions: Dict[str, Decimal]) -> None:
        """Replace the stored positions for a wallet."""
        ...


@runtime_checkable
class TradeRepository(Protocol):
    """Persists executed trades."""

    def load_trades(self, wallet_id: str) -> List["Trade"]:
        """Return every trade for a wallet, oldest first."""
        ...

    def save_trade(self, wallet_id: str, trade: "Trade") -> None:
        """Persist a trade. Implementations must be idempotent on ``trade_id``."""
        ...


@runtime_checkable
class OrderRepository(Protocol):
    """Persists orders across their lifecycle."""

    def load_orders(self, wallet_id: str) -> List["Order"]:
        """Return every order for a wallet."""
        ...

    def save_order(self, wallet_id: str, order: "Order") -> None:
        """Insert or update an order, keyed on ``order_id``."""
        ...

    def get_order(self, wallet_id: str, order_id: str) -> Optional["Order"]:
        """Return a single order, or ``None`` when it does not exist."""
        ...


@runtime_checkable
class UserRepository(Protocol):
    """Persists user accounts."""

    def get_by_email(self, email: str) -> Optional["User"]:
        """Return the user with this email, or ``None``."""
        ...

    def get_by_id(self, user_id: str) -> Optional["User"]:
        """Return the user with this id, or ``None``."""
        ...

    def add(self, user: "User") -> None:
        """Persist a new user. Raises if the email is already taken."""
        ...


@runtime_checkable
class WalletOwnershipRepository(Protocol):
    """Records which user owns which wallet."""

    def get(self, wallet_id: str) -> Optional["WalletOwnership"]:
        """Return the ownership record for a wallet, or ``None``."""
        ...

    def list_for_owner(self, owner_id: str) -> List["WalletOwnership"]:
        """Return every wallet belonging to a user."""
        ...

    def add(self, wallet: "WalletOwnership") -> None:
        """Record a new wallet ownership edge."""
        ...


@runtime_checkable
class PasswordHasher(Protocol):
    """Hashes and verifies passwords.

    A port so the domain never imports bcrypt, and tests can substitute a
    fast fake instead of paying the deliberate KDF cost.
    """

    def hash(self, password: str) -> str:
        ...

    def verify(self, password: str, password_hash: str) -> bool:
        ...


@runtime_checkable
class TokenService(Protocol):
    """Issues and verifies bearer tokens."""

    def issue_access_token(self, user_id: str) -> str:
        ...

    def issue_refresh_token(self, user_id: str) -> str:
        ...

    def verify_access_token(self, token: str) -> str:
        """Return the subject (user id). Raises ``AuthenticationError``."""
        ...

    def verify_refresh_token(self, token: str) -> str:
        """Return the subject (user id). Raises ``AuthenticationError``."""
        ...


@runtime_checkable
class TokenBlocklist(Protocol):
    """Revocation list for issued tokens.

    JWTs are stateless, so a token stays valid until it expires unless the
    server keeps a record of the ones it has revoked. This port is that
    record. Two granularities are supported:

    * ``revoke`` — a single token, by its ``jti`` claim (sign out this device)
    * ``revoke_all_for_user`` — every token issued before a cutoff instant
      (sign out everywhere, or force re-auth after a password change)
    """

    def revoke(self, jti: str, user_id: str, expires_at: "datetime") -> None:
        """Block a single token until it would have expired anyway."""
        ...

    def is_revoked(self, jti: str) -> bool:
        """True when this token has been explicitly revoked."""
        ...

    def revoke_all_for_user(self, user_id: str, issued_before: "datetime") -> None:
        """Block every token for a user issued before ``issued_before``."""
        ...

    def user_cutoff(self, user_id: str) -> Optional["datetime"]:
        """The user's global revocation instant, or ``None``."""
        ...

    def clear_cutoff(self, user_id: str) -> None:
        """Lift the global cutoff, after the user proves their password."""
        ...

    def purge_expired(self, now: Optional["datetime"] = None) -> int:
        """Delete entries whose tokens have expired. Returns the count."""
        ...


class InMemoryTokenBlocklist:
    """Ephemeral :class:`TokenBlocklist`."""

    def __init__(self) -> None:
        self._revoked: Dict[str, "datetime"] = {}
        self._cutoffs: Dict[str, "datetime"] = {}

    def revoke(self, jti: str, user_id: str, expires_at: "datetime") -> None:
        self._revoked[jti] = expires_at

    def is_revoked(self, jti: str) -> bool:
        return jti in self._revoked

    def revoke_all_for_user(self, user_id: str, issued_before: "datetime") -> None:
        self._cutoffs[user_id] = issued_before

    def user_cutoff(self, user_id: str) -> Optional["datetime"]:
        return self._cutoffs.get(user_id)

    def clear_cutoff(self, user_id: str) -> None:
        self._cutoffs.pop(user_id, None)

    def purge_expired(self, now: Optional["datetime"] = None) -> int:
        from datetime import datetime as _dt, timezone as _tz

        moment = now or _dt.now(_tz.utc)
        stale = [jti for jti, exp in self._revoked.items() if exp <= moment]
        for jti in stale:
            del self._revoked[jti]
        return len(stale)


class InMemoryUserRepository:
    """Ephemeral :class:`UserRepository`."""

    def __init__(self) -> None:
        self._by_id: Dict[str, "User"] = {}
        self._by_email: Dict[str, str] = {}

    def get_by_email(self, email: str) -> Optional["User"]:
        user_id = self._by_email.get(email.strip().lower())
        return self._by_id.get(user_id) if user_id else None

    def get_by_id(self, user_id: str) -> Optional["User"]:
        return self._by_id.get(user_id)

    def add(self, user: "User") -> None:
        from .exceptions import EmailAlreadyRegisteredError

        if user.email in self._by_email:
            raise EmailAlreadyRegisteredError("That email is already registered")
        self._by_id[user.user_id] = user
        self._by_email[user.email] = user.user_id


class InMemoryWalletOwnershipRepository:
    """Ephemeral :class:`WalletOwnershipRepository`."""

    def __init__(self) -> None:
        self._wallets: Dict[str, "WalletOwnership"] = {}

    def get(self, wallet_id: str) -> Optional["WalletOwnership"]:
        return self._wallets.get(wallet_id)

    def list_for_owner(self, owner_id: str) -> List["WalletOwnership"]:
        return [w for w in self._wallets.values() if w.owner_id == owner_id]

    def add(self, wallet: "WalletOwnership") -> None:
        self._wallets[wallet.wallet_id] = wallet


class InMemoryEventStore:
    """Ephemeral :class:`EventStore`, used by tests and the null wallet."""

    def __init__(self) -> None:
        self._events: Dict[str, List["DomainEvent"]] = {}

    def load_events(self, wallet_id: str) -> List["DomainEvent"]:
        return list(self._events.get(wallet_id, []))

    def append_event(self, wallet_id: str, event: "DomainEvent") -> None:
        self._events.setdefault(wallet_id, []).append(event)


class InMemoryPositionRepository:
    """Ephemeral :class:`PositionRepository`."""

    def __init__(self) -> None:
        self._positions: Dict[str, Dict[str, Decimal]] = {}

    def load_positions(self, wallet_id: str) -> Dict[str, Decimal]:
        return dict(self._positions.get(wallet_id, {}))

    def save_positions(self, wallet_id: str, positions: Dict[str, Decimal]) -> None:
        self._positions[wallet_id] = dict(positions)


class InMemoryTradeRepository:
    """Ephemeral :class:`TradeRepository`."""

    def __init__(self) -> None:
        self._trades: Dict[str, List["Trade"]] = {}

    def load_trades(self, wallet_id: str) -> List["Trade"]:
        return list(self._trades.get(wallet_id, []))

    def save_trade(self, wallet_id: str, trade: "Trade") -> None:
        trades = self._trades.setdefault(wallet_id, [])
        if any(t.trade_id == trade.trade_id for t in trades):
            return
        trades.append(trade)


class InMemoryOrderRepository:
    """Ephemeral :class:`OrderRepository`."""

    def __init__(self) -> None:
        self._orders: Dict[str, List["Order"]] = {}

    def load_orders(self, wallet_id: str) -> List["Order"]:
        return list(self._orders.get(wallet_id, []))

    def save_order(self, wallet_id: str, order: "Order") -> None:
        orders = self._orders.setdefault(wallet_id, [])
        for index, existing in enumerate(orders):
            if existing.order_id == order.order_id:
                orders[index] = order
                return
        orders.append(order)

    def get_order(self, wallet_id: str, order_id: str) -> Optional["Order"]:
        for order in self._orders.get(wallet_id, []):
            if order.order_id == order_id:
                return order
        return None


class StaticMarketDataProvider:
    """Deterministic :class:`MarketDataProvider` backed by a price table.

    Used by unit tests and by the ``fake`` market provider mode so the core
    trading loop can be exercised without network access.
    """

    DEFAULT_PRICES: Dict[str, Decimal] = {
        "RELIANCE": Decimal("2500.00"),
        "TCS": Decimal("3800.00"),
        "INFY": Decimal("1650.00"),
        "HDFCBANK": Decimal("1550.00"),
        "AAPL": Decimal("170.00"),
        "MSFT": Decimal("400.00"),
    }

    def __init__(self, prices: Optional[Dict[str, Decimal]] = None) -> None:
        self._prices: Dict[str, Decimal] = dict(prices or self.DEFAULT_PRICES)

    @property
    def prices(self) -> Dict[str, Decimal]:
        """Mutable price table, so tests can move the market."""
        return self._prices

    def get_price(self, symbol: str) -> Decimal:
        key = symbol.upper().strip()
        if key not in self._prices:
            raise UnknownSymbolError(f"Unknown symbol: {symbol}")
        return self._prices[key]

    def set_price(self, symbol: str, price: Decimal) -> None:
        self._prices[symbol.upper().strip()] = Decimal(str(price))
