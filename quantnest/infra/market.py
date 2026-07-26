"""Market data providers (infrastructure).

Implements the :class:`quantnest.domain.ports.MarketDataProvider` port.

Two modes, selected by ``QUANTNEST_MARKET_PROVIDER``:

* ``yfinance`` (default) — live prices with a short-lived cache
* ``fake``               — deterministic prices, for offline dev, CI and tests
"""

from __future__ import annotations

import logging
import math
import os
import threading
import time
from decimal import Decimal
from typing import Dict, Optional

from quantnest.domain.exceptions import UnknownSymbolError
from quantnest.domain.ports import StaticMarketDataProvider

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60
_FETCH_PERIODS = ("5d", "1mo", "3mo")

#: Used when a live lookup fails, so the simulator stays usable offline.
FALLBACK_PRICES: Dict[str, Decimal] = {
    "RELIANCE": Decimal("2500.00"),
    "TCS": Decimal("3800.00"),
    "INFY": Decimal("1650.00"),
    "HDFCBANK": Decimal("1550.00"),
    "AAPL": Decimal("170.00"),
    "MSFT": Decimal("400.00"),
}


class YFinanceMarketDataProvider:
    """Live prices from Yahoo Finance, cached for :data:`CACHE_TTL_SECONDS`."""

    def __init__(
        self,
        cache_ttl: int = CACHE_TTL_SECONDS,
        fallback_prices: Optional[Dict[str, Decimal]] = None,
    ) -> None:
        self._cache: Dict[str, tuple[Decimal, float]] = {}
        self._lock = threading.Lock()
        self._cache_ttl = cache_ttl
        self._fallback = dict(fallback_prices if fallback_prices is not None else FALLBACK_PRICES)

    def get_price(self, symbol: str) -> Decimal:
        key = symbol.upper().strip()
        if not key:
            raise UnknownSymbolError("Symbol must not be empty")

        cached = self._read_cache(key)
        if cached is not None:
            return cached

        price = self._fetch_live(key)
        if price is not None:
            self._write_cache(key, price)
            return price

        if key in self._fallback:
            logger.warning(
                "Live price lookup failed; using fallback price",
                extra={"symbol": key, "price": str(self._fallback[key])},
            )
            return self._fallback[key]

        raise UnknownSymbolError(f"Unknown symbol or unavailable market data: {symbol}")

    # ── internals ────────────────────────────────────────────────────────

    def _read_cache(self, symbol: str) -> Optional[Decimal]:
        with self._lock:
            entry = self._cache.get(symbol)
            if entry and (time.time() - entry[1]) < self._cache_ttl:
                return entry[0]
        return None

    def _write_cache(self, symbol: str, price: Decimal) -> None:
        with self._lock:
            self._cache[symbol] = (price, time.time())

    def _fetch_live(self, symbol: str) -> Optional[Decimal]:
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance is not installed; live prices unavailable")
            return None

        # Try the NSE listing first, then the bare (global) symbol.
        for candidate in (f"{symbol}.NS", symbol):
            for period in _FETCH_PERIODS:
                try:
                    history = yf.Ticker(candidate).history(period=period, interval="1d")
                except Exception as exc:
                    logger.debug(
                        "Price fetch failed",
                        extra={"symbol": candidate, "period": period, "error": str(exc)},
                    )
                    continue

                if history.empty:
                    continue

                closes = history["Close"].dropna()
                if closes.empty:
                    continue

                raw = float(closes.iloc[-1])
                if math.isnan(raw) or math.isinf(raw) or raw <= 0:
                    continue

                logger.debug(
                    "Resolved live price",
                    extra={"symbol": symbol, "resolved_as": candidate, "price": raw},
                )
                return Decimal(str(round(raw, 2)))

        return None


class FakeMarketDataProvider(StaticMarketDataProvider):
    """Deterministic provider for offline development and tests."""


_provider_singleton: Optional[object] = None
_provider_lock = threading.Lock()


def get_market_provider(*_args, **_kwargs):
    """Return the process-wide market data provider.

    Mode is controlled by ``QUANTNEST_MARKET_PROVIDER``:
    ``yfinance`` (default) or ``fake``.
    """
    global _provider_singleton

    if _provider_singleton is None:
        with _provider_lock:
            if _provider_singleton is None:
                mode = os.getenv("QUANTNEST_MARKET_PROVIDER", "yfinance").strip().lower()
                if mode == "fake":
                    logger.info("Using deterministic market data provider")
                    _provider_singleton = FakeMarketDataProvider()
                else:
                    logger.info("Using yfinance market data provider")
                    _provider_singleton = YFinanceMarketDataProvider()

    return _provider_singleton


def reset_market_provider() -> None:
    """Clear the cached provider. Used by tests."""
    global _provider_singleton
    with _provider_lock:
        _provider_singleton = None
