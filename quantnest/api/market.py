"""Market data API — quotes, charts and symbol search."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from quantnest.api.deps import MarketDep
from quantnest.domain.exceptions import UnknownSymbolError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])

_FETCH_PERIODS = ("5d", "1mo", "3mo")

_VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
_VALID_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"}

_FALLBACK_SEARCH = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "exchange": "NSE"},
    {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "exchange": "NSE"},
    {"symbol": "INFY", "name": "Infosys Ltd", "exchange": "NSE"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "exchange": "NSE"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "exchange": "NSE"},
    {"symbol": "SBIN", "name": "State Bank of India", "exchange": "NSE"},
    {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
]

_EXCHANGE_LABELS = {
    "NSI": "NSE",
    "BOM": "BSE",
    "NMS": "NASDAQ",
    "NGM": "NASDAQ",
    "NCM": "NASDAQ",
    "NYQ": "NYSE",
    "NYB": "NYSE",
}


def _using_fake_market() -> bool:
    return os.getenv("QUANTNEST_MARKET_PROVIDER", "yfinance").strip().lower() == "fake"


def _synthetic_quote(symbol: str, market) -> Dict[str, Any]:
    """Build a quote from the injected provider.

    Used in ``fake`` mode and as a fallback when the live feed is unreachable,
    so the trading loop stays exercisable offline.
    """
    price = float(market.get_price(symbol))
    return {
        "symbol": symbol,
        "yf_symbol": f"{symbol}.NS",
        "exchange": "NSE",
        "ltp": price,
        "open": price,
        "high": price,
        "low": price,
        "prev_close": price,
        "change": 0.0,
        "change_pct": 0.0,
        "volume": 0,
        "week52_high": None,
        "week52_low": None,
        "market_cap": None,
    }


def _fetch_live_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch a full quote from Yahoo Finance, or ``None`` if unavailable."""
    try:
        import yfinance as yf
    except ImportError:
        return None

    for candidate in (f"{symbol}.NS", symbol):
        for period in _FETCH_PERIODS:
            try:
                ticker = yf.Ticker(candidate)
                history = ticker.history(period=period, interval="1d")
            except Exception as exc:
                logger.debug(
                    "Quote fetch failed",
                    extra={"symbol": candidate, "period": period, "error": str(exc)},
                )
                continue

            if history.empty:
                continue

            latest = history.iloc[-1]
            prev_close = float(
                history.iloc[-2]["Close"] if len(history) > 1 else history.iloc[-1]["Close"]
            )

            ltp = round(float(latest["Close"]), 2)
            prev = round(prev_close, 2)
            change = round(ltp - prev, 2)

            week52_high = week52_low = market_cap = None
            try:
                fast = ticker.fast_info
                week52_high = round(float(fast.year_high), 2)
                week52_low = round(float(fast.year_low), 2)
                market_cap = fast.market_cap
            except Exception:
                pass

            return {
                "symbol": symbol,
                "yf_symbol": candidate,
                "exchange": "NSE" if candidate.endswith(".NS") else "GLOBAL",
                "ltp": ltp,
                "open": round(float(latest["Open"]), 2),
                "high": round(float(latest["High"]), 2),
                "low": round(float(latest["Low"]), 2),
                "prev_close": prev,
                "change": change,
                "change_pct": round((change / prev) * 100, 2) if prev else 0.0,
                "volume": int(latest["Volume"]),
                "week52_high": week52_high,
                "week52_low": week52_low,
                "market_cap": market_cap,
            }

    return None


def _resolve_quote(symbol: str, market) -> Dict[str, Any]:
    """Return a quote, preferring live data and falling back to the provider."""
    symbol = symbol.upper().strip()

    if not _using_fake_market():
        live = _fetch_live_quote(symbol)
        if live is not None:
            return live

    # Raises UnknownSymbolError if the provider cannot price the symbol.
    return _synthetic_quote(symbol, market)


@router.get("/quote/{symbol}", summary="Live quote for a single symbol")
async def get_quote(symbol: str, market: MarketDep) -> Dict[str, Any]:
    return _resolve_quote(symbol, market)


@router.get("/quotes", summary="Live quotes for several symbols")
async def get_batch_quotes(
    market: MarketDep,
    symbols: str = Query(..., min_length=1, max_length=500, description="Comma-separated tickers"),
) -> Dict[str, Any]:
    requested = [s.strip().upper() for s in symbols.split(",") if s.strip()][:50]

    results: Dict[str, Any] = {}
    for symbol in requested:
        try:
            results[symbol] = _resolve_quote(symbol, market)
        except UnknownSymbolError as exc:
            results[symbol] = {"symbol": symbol, "ltp": None, "error": str(exc)}
        except Exception:
            logger.exception("Batch quote lookup failed", extra={"symbol": symbol})
            results[symbol] = {
                "symbol": symbol,
                "ltp": None,
                "error": "Quote temporarily unavailable",
            }

    return results


@router.get("/chart/{symbol}", summary="Historical OHLCV series")
async def get_chart_data(
    symbol: str,
    market: MarketDep,
    period: str = Query("6mo", description="Look-back window"),
    interval: str = Query("1d", description="Candle interval"),
) -> Dict[str, Any]:
    if period not in _VALID_PERIODS:
        period = "6mo"
    if interval not in _VALID_INTERVALS:
        interval = "1d"

    symbol = symbol.upper().strip()

    if not _using_fake_market():
        try:
            import yfinance as yf

            for candidate in (symbol, f"{symbol}.NS"):
                history = yf.Ticker(candidate).history(period=period, interval=interval)
                if history.empty:
                    continue

                data: List[Dict[str, Any]] = []
                for index, row in history.iterrows():
                    data.append(
                        {
                            "time": (
                                index.strftime("%Y-%m-%d")
                                if interval == "1d"
                                else int(index.timestamp())
                            ),
                            "open": round(float(row["Open"]), 2),
                            "high": round(float(row["High"]), 2),
                            "low": round(float(row["Low"]), 2),
                            "close": round(float(row["Close"]), 2),
                            "value": int(row["Volume"]),
                        }
                    )
                return {"symbol": symbol, "period": period, "interval": interval, "data": data}
        except ImportError:
            pass
        except Exception:
            logger.exception("Chart data fetch failed", extra={"symbol": symbol})

    # Offline / fake mode: confirm the symbol is priceable, return no candles.
    market.get_price(symbol)
    return {"symbol": symbol, "period": period, "interval": interval, "data": []}


@router.get("/search", summary="Search for tradable instruments")
async def search_stocks(
    q: str = Query("", max_length=64, description="Search term"),
) -> Dict[str, Any]:
    query = q.strip()
    if not query:
        return {"results": [], "query": query, "source": "none"}

    if not _using_fake_market():
        try:
            import yfinance as yf

            search = yf.Search(query, news_count=0, max_results=20)
            results = []

            for item in search.quotes:
                quote_type = item.get("quoteType", "")
                if quote_type not in ("EQUITY", "ETF"):
                    continue

                raw_symbol = item.get("symbol", "")
                exchange = item.get("exchange", "")

                results.append(
                    {
                        "symbol": raw_symbol.replace(".NS", "").replace(".BO", ""),
                        "yf_symbol": raw_symbol,
                        "name": item.get("shortname") or item.get("longname") or raw_symbol,
                        "exchange": _EXCHANGE_LABELS.get(exchange, exchange),
                        "type": quote_type,
                    }
                )

            if results:
                return {"results": results[:12], "query": query, "source": "yahoo_finance"}
        except ImportError:
            pass
        except Exception as exc:
            logger.warning(
                "Symbol search failed; using the offline list",
                extra={"query": query, "error": str(exc)},
            )

    needle = query.upper()
    matches = [
        {**entry, "yf_symbol": f"{entry['symbol']}.NS", "type": "EQUITY"}
        for entry in _FALLBACK_SEARCH
        if needle in entry["symbol"] or needle in entry["name"].upper()
    ]
    return {"results": matches[:12], "query": query, "source": "offline"}
