"""Market price provider - Single source of truth for all assets"""

import time
from decimal import Decimal, InvalidOperation
from typing import Dict
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

class UnknownSymbolError(ValueError):
    """Raised when a symbol is not found in the market"""

class MarketProvider:
    """Live market provider with 60-second caching."""

    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MarketProvider, cls).__new__(cls)
            cls._instance._cache: Dict[str, dict] = {}
            # Fallbacks in case API is down or yfinance isn't installed
            cls._instance._fallback_prices = {
                "RELIANCE": Decimal("2500.00"),
                "TCS": Decimal("3800.00"),
                "INFY": Decimal("1650.00"),
                "HDFCBANK": Decimal("1550.00"),
                "AAPL": Decimal("170.00"),
                "MSFT": Decimal("400.00")
            }
        return cls._instance
    
    def get_price(self, symbol: str) -> Decimal:
        """Get current live price for symbol from Yahoo Finance or cache."""
        symbol = symbol.upper().strip()
        
        # 1. Check cache (valid for 60 seconds)
        now = time.time()
        if symbol in self._cache:
            entry = self._cache[symbol]
            if now - entry['timestamp'] < 60:
                return entry['price']

        # 2. If no yfinance, fall back to mock data
        if not YFINANCE_AVAILABLE:
            return self._get_fallback(symbol)

        # 3. Try yfinance with progressive period escalation (handles weekends/holidays)
        import math
        for yf_symbol in [symbol + ".NS", symbol]:
            for period in ["5d", "1mo", "3mo"]:
                try:
                    print(f"📡 MarketProvider: Fetching LIVE price for {yf_symbol} (period={period})...")
                    ticker = yf.Ticker(yf_symbol)
                    history = ticker.history(period=period, interval="1d")

                    if not history.empty:
                        # Drop NaN rows — ETFs like GOLDBEES/NIFTYBEES sometimes have NaN closes
                        clean = history['Close'].dropna()
                        if clean.empty:
                            print(f"⚠️  MarketProvider: {yf_symbol}/{period} — all closes NaN, trying next period")
                            continue

                        raw_val = float(clean.iloc[-1])

                        if math.isnan(raw_val) or math.isinf(raw_val) or raw_val <= 0:
                            print(f"⚠️  MarketProvider: {yf_symbol}/{period} — invalid price {raw_val}, trying next")
                            continue

                        price = Decimal(str(round(raw_val, 2)))
                        self._cache[symbol] = {'price': price, 'timestamp': now}
                        print(f"✅ MarketProvider: {symbol} → ₹{price} (via {yf_symbol}, period={period})")
                        return price
                except Exception as e:
                    print(f"⚠️  MarketProvider: {yf_symbol}/{period} failed: {e}")
                    continue
        
        # 4. Fall back to hardcoded mock prices
        print(f"⚠️  MarketProvider: All live fetches failed for {symbol}, using fallback")
        return self._get_fallback(symbol)
            
    def _get_fallback(self, symbol: str) -> Decimal:
        if symbol in self._fallback_prices:
            return self._fallback_prices[symbol]
        raise UnknownSymbolError(f"Unknown symbol or failed to fetch live data: {symbol}")