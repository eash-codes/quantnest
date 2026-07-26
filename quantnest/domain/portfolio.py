"""Portfolio — manages asset positions and delegates all money to the Wallet.

Persistence and pricing arrive through the ports in :mod:`quantnest.domain.ports`,
so this module imports nothing from the infrastructure or web layers.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

from .exceptions import InsufficientPositionsError, ValidationError
from .market import MarketProvider
from .ports import (
    EventStore,
    InMemoryPositionRepository,
    InMemoryTradeRepository,
    MarketDataProvider,
    PositionRepository,
    TradeRepository,
)
from .trade import Trade
from .wallet import Wallet

MONEY = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    """Round a money-like value to two decimal places."""
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


class Portfolio:
    """Aggregate combining a cash :class:`Wallet` with asset positions."""

    def __init__(
        self,
        wallet_id: str,
        market: Optional[MarketDataProvider] = None,
        *,
        event_store: Optional[EventStore] = None,
        position_repository: Optional[PositionRepository] = None,
        trade_repository: Optional[TradeRepository] = None,
        wallet: Optional[Wallet] = None,
    ) -> None:
        self._wallet_id = wallet_id
        self._market: MarketDataProvider = market or MarketProvider()
        self._positions_repo: PositionRepository = (
            position_repository or InMemoryPositionRepository()
        )
        self._trades_repo: TradeRepository = trade_repository or InMemoryTradeRepository()

        self._wallet = wallet or Wallet(wallet_id, event_store=event_store)

        loaded = self._positions_repo.load_positions(wallet_id)
        self._positions: Dict[str, Decimal] = {
            symbol: Decimal(str(quantity)) for symbol, quantity in loaded.items()
        }
        self._trades: List[Trade] = list(self._trades_repo.load_trades(wallet_id))

    # ── Accessors ────────────────────────────────────────────────────────

    @property
    def wallet(self) -> Wallet:
        return self._wallet

    @property
    def positions(self) -> Dict[str, Decimal]:
        return dict(self._positions)

    @property
    def trades(self) -> List[Trade]:
        return list(self._trades)

    # ── Commands ─────────────────────────────────────────────────────────

    def buy(self, symbol: str, quantity: Decimal, transaction_id: Optional[str] = None) -> Trade:
        """Buy ``quantity`` of ``symbol``, debiting the wallet."""
        quantity = self._validate_quantity(quantity)
        tx_id = transaction_id or str(uuid.uuid4())

        price = self._market.get_price(symbol)
        cost = price * quantity

        # Debit first: it enforces the funds check and is idempotent.
        self._wallet.debit(cost, transaction_id=tx_id)

        self._positions[symbol] = self._positions.get(symbol, Decimal("0")) + quantity
        trade = Trade(symbol, "BUY", quantity, price)
        self._trades.append(trade)

        self._persist(trade)
        return trade

    def sell(self, symbol: str, quantity: Decimal, transaction_id: Optional[str] = None) -> Trade:
        """Sell ``quantity`` of ``symbol``, crediting the wallet."""
        quantity = self._validate_quantity(quantity)

        owned = self._positions.get(symbol, Decimal("0"))
        if quantity > owned:
            raise InsufficientPositionsError(
                f"Cannot sell {quantity} of {symbol}; only {owned} held"
            )

        tx_id = transaction_id or str(uuid.uuid4())

        price = self._market.get_price(symbol)
        proceeds = price * quantity

        self._wallet.credit(proceeds, transaction_id=tx_id)

        remaining = owned - quantity
        if remaining == 0:
            self._positions.pop(symbol, None)
        else:
            self._positions[symbol] = remaining

        trade = Trade(symbol, "SELL", quantity, price)
        self._trades.append(trade)

        self._persist(trade)
        return trade

    # ── Analytics (read-only, no side effects) ───────────────────────────

    def cash(self) -> Decimal:
        return _money(self._wallet.balance)

    def asset_value(self, symbol: str) -> Decimal:
        quantity = self._positions.get(symbol, Decimal("0"))
        return _money(quantity * self._market.get_price(symbol))

    def asset_values(self) -> Dict[str, Decimal]:
        return {symbol: self.asset_value(symbol) for symbol in self._positions}

    def total_asset_value(self) -> Decimal:
        return _money(sum(self.asset_values().values(), start=Decimal("0")))

    def total_value(self) -> Decimal:
        return _money(self.cash() + self.total_asset_value())

    def avg_cost(self, symbol: str) -> Decimal:
        """Quantity-weighted average price across all BUY trades."""
        bought_quantity = Decimal("0")
        bought_cost = Decimal("0")

        for trade in self._trades:
            if trade.symbol == symbol and trade.side == "BUY":
                bought_quantity += trade.quantity
                bought_cost += trade.quantity * trade.price

        if bought_quantity == 0:
            return Decimal("0.00")
        return _money(bought_cost / bought_quantity)

    def unrealized_pnl(self, symbol: str) -> Decimal:
        quantity = self._positions.get(symbol, Decimal("0"))
        if quantity == 0:
            return Decimal("0.00")
        price = self._market.get_price(symbol)
        return _money((price - self.avg_cost(symbol)) * quantity)

    def unrealized_pnl_all(self) -> Dict[str, Decimal]:
        return {symbol: self.unrealized_pnl(symbol) for symbol in self._positions}

    def allocations(self) -> Dict[str, Decimal]:
        """Each asset's share of total portfolio value, plus cash."""
        total = self.total_value()
        if total == 0:
            return {"cash": Decimal("0.00")}

        allocations: Dict[str, Decimal] = {"cash": _money(self.cash() / total)}
        for symbol, value in self.asset_values().items():
            allocations[symbol] = _money(value / total)
        return allocations

    def health_signals(
        self,
        max_asset_pct: Decimal = Decimal("0.40"),
        min_cash_pct: Decimal = Decimal("0.10"),
    ) -> List[str]:
        """Rule-based risk warnings for the dashboard."""
        signals: List[str] = []

        try:
            allocations = self.allocations()
        except Exception:
            return ["Could not compute allocations; price data is unavailable for some symbols"]

        for symbol, pct in allocations.items():
            if symbol != "cash" and pct > max_asset_pct:
                signals.append(f"High concentration in {symbol}: {pct:.1%}")

        cash_pct = allocations.get("cash", Decimal("0.00"))
        if cash_pct < min_cash_pct:
            signals.append(f"Low cash buffer: {cash_pct:.1%}")

        return signals

    # ── internals ────────────────────────────────────────────────────────

    @staticmethod
    def _validate_quantity(quantity: Decimal) -> Decimal:
        value = quantity if isinstance(quantity, Decimal) else Decimal(str(quantity))
        if value <= 0:
            raise ValidationError("Quantity must be positive")
        return value

    def _persist(self, trade: Trade) -> None:
        """Write positions and the newly executed trade through the ports."""
        positions = {
            symbol: quantity for symbol, quantity in self._positions.items() if quantity > 0
        }
        self._positions_repo.save_positions(self._wallet_id, positions)
        self._trades_repo.save_trade(self._wallet_id, trade)
