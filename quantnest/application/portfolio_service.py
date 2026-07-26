"""Application service orchestrating portfolio reads.

Knows nothing about HTTP. Receives its collaborators by injection so the API
layer can supply request-scoped, transaction-bound repositories.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quantnest.domain.portfolio import Portfolio
from quantnest.domain.ports import (
    EventStore,
    MarketDataProvider,
    PositionRepository,
    TradeRepository,
)

logger = logging.getLogger(__name__)


class PortfolioService:
    """Read-only portfolio queries."""

    def __init__(
        self,
        market: Optional[MarketDataProvider] = None,
        *,
        event_store: Optional[EventStore] = None,
        position_repository: Optional[PositionRepository] = None,
        trade_repository: Optional[TradeRepository] = None,
    ) -> None:
        if market is None:
            from quantnest.infra.market import get_market_provider

            market = get_market_provider()

        self._market = market
        self._event_store = event_store
        self._position_repository = position_repository
        self._trade_repository = trade_repository

    def build_portfolio(self, wallet_id: str) -> Portfolio:
        """Materialise the portfolio aggregate for a wallet."""
        return Portfolio(
            wallet_id,
            self._market,
            event_store=self._event_store,
            position_repository=self._position_repository,
            trade_repository=self._trade_repository,
        )

    def get_summary(self, wallet_id: str) -> Dict[str, Any]:
        """Full analytics snapshot for the dashboard."""
        portfolio = self.build_portfolio(wallet_id)

        summary = {
            "wallet_id": wallet_id,
            "cash": float(portfolio.cash()),
            "total_asset_value": float(portfolio.total_asset_value()),
            "total_value": float(portfolio.total_value()),
            "positions": {
                symbol: float(quantity) for symbol, quantity in portfolio.positions.items()
            },
            "asset_values": {
                symbol: float(value) for symbol, value in portfolio.asset_values().items()
            },
            "avg_cost": {
                symbol: float(portfolio.avg_cost(symbol)) for symbol in portfolio.positions
            },
            "unrealized_pnl": {
                symbol: float(pnl) for symbol, pnl in portfolio.unrealized_pnl_all().items()
            },
            "allocations": {
                asset: float(pct) for asset, pct in portfolio.allocations().items()
            },
            "health_signals": portfolio.health_signals(),
            "event_count": len(portfolio.wallet.events),
        }

        logger.debug(
            "Built portfolio summary",
            extra={
                "wallet_id": wallet_id,
                "position_count": len(summary["positions"]),
                "total_value": summary["total_value"],
            },
        )

        return summary
