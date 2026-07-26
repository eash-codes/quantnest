"""Ports (interfaces) the domain depends on.

The domain layer must not know how data is stored or where prices come from.
It declares the capabilities it needs here as ``typing.Protocol`` classes, and
the infrastructure layer provides implementations.

Nothing in this module imports from ``quantnest.infra``, ``quantnest.api`` or
any third-party framework — only the standard library. That is what keeps the
dependency arrow pointing inwards.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, Optional, Protocol, runtime_checkable

from .exceptions import UnknownSymbolError

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .events import DomainEvent
    from .order import Order
    from .trade import Trade

__all__ = [
    "UnknownSymbolError",
    "MarketDataProvider",
    "EventStore",
    "PositionRepository",
    "TradeRepository",
    "OrderRepository",
    "InMemoryEventStore",
    "InMemoryPositionRepository",
    "InMemoryTradeRepository",
    "InMemoryOrderRepository",
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
