"""Market price provider - Single source of truth for all assets"""

from decimal import Decimal
from typing import Dict

class UnknownSymbolError(ValueError):
    """Raised when a symobol is not found in the market"""

class MarketProvider():
    """Mock market with deterministic prices"""

    def __init__(self):
        self._prices: Dict[str, Decimal] = {
            "RELIANCE": Decimal("2500.00"),
            "TCS": Decimal("3800.00"),
            "INFY": Decimal("1650.00"),
            "HDFCBANK": Decimal("1550.00"),
        }
    
    def get_price(self, symbol: str) -> Decimal:
        """Get current price for symbol."""
        symbol = symbol.upper()
        if symbol not in self._prices:
            raise UnknownSymbolError(f"Unknown symbol: {symbol}")
        return self._prices[symbol]