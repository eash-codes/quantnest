"""Application service: Orchestrates domain without HTTP awareness."""

from quantnest.domain.portfolio import Portfolio
from quantnest.domain.market import MarketProvider
from typing import Dict, Any

class PortfolioService:
    """Read-only portfolio queries."""
    
    def __init__(self):
        self._market = MarketProvider()
    
    def get_summary(self, wallet_id: str) -> Dict[str, Any]:
        """Full portfolio snapshot."""
        portfolio = Portfolio(wallet_id, self._market)
        return {
            "wallet_id": wallet_id,
            "cash": float(portfolio.cash()),
            "total_asset_value": float(portfolio.total_asset_value()),
            "total_value": float(portfolio.total_value()),
            "positions": portfolio.positions.copy(),
            "unrealized_pnl": {
                sym: float(pnl) for sym, pnl in portfolio.unrealized_pnl_all().items()
            },
            "allocations": {
                asset: float(pct) for asset, pct in portfolio.allocations().items()
            },
            "health_signals": portfolio.health_signals(),
            "event_count": len(portfolio.wallet.events),
        }
