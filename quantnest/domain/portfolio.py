"""Portfolio manages asset positions, delegates money to Wallet."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List

from .wallet import Wallet
from .market import MarketProvider
from .trade import Trade

# Money formatting (2 decimal places, round half up)
MONEY = Decimal("0.01")


def _money(x: Decimal) -> Decimal:
    """Round money-like values to 2 decimal places."""
    return x.quantize(MONEY, rounding=ROUND_HALF_UP)


class Portfolio:
    def __init__(self, wallet_id: str, market: MarketProvider):
        self._wallet = Wallet(wallet_id)
        self._market = market
        self._positions: Dict[str, Decimal] = {}
        self._trades: List[Trade] = []

    @property
    def wallet(self) -> Wallet:
        """Public access to wallet (read-only reference)."""
        return self._wallet

    @property
    def positions(self) -> Dict[str, Decimal]:
        return self._positions.copy()

    @property
    def trades(self) -> List[Trade]:
        return self._trades.copy()

    def buy(self, symbol: str, quantity: Decimal) -> None:
        """Buy quantity of symbol if sufficient funds exist."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        price = self._market.get_price(symbol)
        cost = price * quantity

        self.wallet.debit(cost)
        self._positions[symbol] = self._positions.get(symbol, Decimal("0")) + quantity
        self._trades.append(Trade(symbol, "BUY", quantity, price))

    def sell(self, symbol: str, quantity: Decimal) -> None:
        """Sell quantity of symbol if owned."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        owned = self._positions.get(symbol, Decimal("0"))
        if quantity > owned:
            raise ValueError(f"Cannot sell {quantity}, own only {owned}")

        price = self._market.get_price(symbol)
        proceeds = price * quantity

        self.wallet.credit(proceeds)
        self._positions[symbol] = owned - quantity
        if self._positions[symbol] == 0:
            del self._positions[symbol]
        self._trades.append(Trade(symbol, "SELL", quantity, price))

    # ==================================================
    # DAY 4: READ-ONLY ANALYTICS (No side effects)
    # ==================================================

    def cash(self) -> Decimal:
        """Cash balance (wallet.balance rounded)."""
        return _money(self.wallet.balance)

    def asset_value(self, symbol: str) -> Decimal:
        """Market value of single asset position."""
        qty = self._positions.get(symbol, Decimal("0"))
        price = self._market.get_price(symbol)
        return _money(qty * price)

    def asset_values(self) -> Dict[str, Decimal]:
        """Market value of all asset positions."""
        return {sym: self.asset_value(sym) for sym in self._positions}

    def total_asset_value(self) -> Decimal:
        """Sum of all asset market values."""
        return _money(sum(self.asset_values().values(), start=Decimal("0")))

    def total_value(self) -> Decimal:
        """Cash + total asset value."""
        return _money(self.cash() + self.total_asset_value())

    def avg_cost(self, symbol: str) -> Decimal:
        """Average purchase price (weighted by quantity)."""
        bought_qty = Decimal("0")
        bought_cost = Decimal("0")
        for t in self._trades:
            if t.symbol == symbol and t.side == "BUY":
                bought_qty += t.quantity
                bought_cost += t.quantity * t.price
        return Decimal("0.00") if bought_qty == 0 else _money(bought_cost / bought_qty)

    def unrealized_pnl(self, symbol: str) -> Decimal:
        """Unrealized P&L = (current_price - avg_cost) * current_qty."""
        qty = self._positions.get(symbol, Decimal("0"))
        if qty == 0:
            return Decimal("0.00")
        price = self._market.get_price(symbol)
        cost = self.avg_cost(symbol)
        return _money((price - cost) * qty)

    def unrealized_pnl_all(self) -> Dict[str, Decimal]:
        """Unrealized P&L for all positions."""
        return {sym: self.unrealized_pnl(sym) for sym in self._positions}

    def allocations(self) -> Dict[str, Decimal]:
        """Asset allocation as % of total portfolio value."""
        total = self.total_value()
        if total == 0:
            return {"cash": Decimal("0.00")}
        
        alloc: Dict[str, Decimal] = {"cash": _money(self.cash() / total)}
        for sym, val in self.asset_values().items():
            alloc[sym] = _money(val / total)
        return alloc

    def health_signals(
        self,
        max_asset_pct: Decimal = Decimal("0.40"),
        min_cash_pct: Decimal = Decimal("0.10"),
    ) -> List[str]:
        """Rule-based portfolio health warnings."""
        signals: List[str] = []
        alloc = self.allocations()

        # Concentration risk
        for sym, pct in alloc.items():
            if sym != "cash" and pct > max_asset_pct:
                signals.append(f"⚠️ High concentration in {sym}: {pct:.1%}")

        # Liquidity risk
        cash_pct = alloc.get("cash", Decimal("0.00"))
        if cash_pct < min_cash_pct:
            signals.append(f"⚠️ Low cash buffer: {cash_pct:.1%}")

        return signals
