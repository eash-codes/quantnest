"""Backwards-compatible market provider alias.

The real implementations now live in the infrastructure layer:

* :class:`quantnest.infra.market.YFinanceMarketDataProvider` — live prices
* :class:`quantnest.domain.ports.StaticMarketDataProvider`   — deterministic

``MarketProvider`` is resolved lazily so importing the domain never pulls in
``yfinance`` or any network dependency. Prefer injecting a
:class:`~quantnest.domain.ports.MarketDataProvider` explicitly in new code.
"""

from __future__ import annotations

from typing import Any

from .exceptions import UnknownSymbolError

__all__ = ["MarketProvider", "UnknownSymbolError"]


def MarketProvider(*args: Any, **kwargs: Any):  # noqa: N802 - kept for compatibility
    """Return the configured market data provider.

    Delegates to :func:`quantnest.infra.market.get_market_provider`, which
    honours the ``QUANTNEST_MARKET_PROVIDER`` environment variable
    (``yfinance`` by default, ``fake`` for offline and test use).
    """
    from quantnest.infra.market import get_market_provider

    return get_market_provider(*args, **kwargs)
