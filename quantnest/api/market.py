"""Market data API - Live quotes and stock search using yfinance."""

from fastapi import APIRouter, HTTPException
from typing import Optional
import yfinance as yf
from decimal import Decimal

router = APIRouter(prefix="/market", tags=["market"])

# Periods to try in order — wider periods survive weekends, holidays, and data gaps
_FETCH_PERIODS = ["5d", "1mo", "3mo"]


def _fetch_history(ns_symbol: str):
    """
    Fetch ticker history with progressive period escalation.
    Tries 5d first; if empty (weekend/holiday gap) escalates to 1mo then 3mo.
    Returns (ticker, hist, today_row, prev_close_row) or raises ValueError.
    """
    ticker = yf.Ticker(ns_symbol)
    for period in _FETCH_PERIODS:
        hist = ticker.history(period=period, interval="1d")
        if not hist.empty and len(hist) >= 1:
            # Use last two rows for LTP and prev_close
            today = hist.iloc[-1]
            prev_close = hist.iloc[-2]["Close"] if len(hist) > 1 else hist.iloc[-1]["Close"]
            return ticker, hist, today, prev_close
    raise ValueError(f"No price data available for {ns_symbol} across all periods")


def _get_ticker_info(symbol: str) -> dict:
    """
    Fetch full ticker info for a symbol.
    Tries SYMBOL.NS (NSE India) first; falls back to bare SYMBOL (US/global).
    Uses escalating fetch periods to handle weekends and market holidays.
    """
    symbol = symbol.upper().strip()
    last_error = None

    for ns_symbol in [symbol + ".NS", symbol]:
        try:
            ticker, hist, today, prev_close = _fetch_history(ns_symbol)

            ltp        = round(float(today["Close"]),  2)
            open_price = round(float(today["Open"]),   2)
            high       = round(float(today["High"]),   2)
            low        = round(float(today["Low"]),    2)
            volume     = int(today["Volume"])
            prev       = round(float(prev_close),      2)
            change     = round(ltp - prev,             2)
            change_pct = round((change / prev) * 100, 2) if prev else 0.0

            # Optional extended info (fast_info can fail on some tickers)
            try:
                fast = ticker.fast_info
                week52_high = round(float(fast.year_high),  2)
                week52_low  = round(float(fast.year_low),   2)
                market_cap  = fast.market_cap
            except Exception:
                week52_high = None
                week52_low  = None
                market_cap  = None

            return {
                "symbol":      symbol,
                "yf_symbol":   ns_symbol,          # shows RELIANCE.NS or MSFT for debug
                "exchange":    "NSE" if ".NS" in ns_symbol else "GLOBAL",
                "ltp":         ltp,
                "open":        open_price,
                "high":        high,
                "low":         low,
                "prev_close":  prev,
                "change":      change,
                "change_pct":  change_pct,
                "volume":      volume,
                "week52_high": week52_high,
                "week52_low":  week52_low,
                "market_cap":  market_cap,
            }

        except ValueError as e:
            last_error = str(e)
            print(f"⚠️  market.py: {ns_symbol} → {e}, trying next suffix...")
            continue
        except Exception as e:
            last_error = str(e)
            print(f"⚠️  market.py: {ns_symbol} unexpected error → {e}")
            continue

    raise ValueError(f"Could not fetch data for '{symbol}': {last_error}")


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """
    Get live market quote for an NSE/global symbol.
    Example: GET /market/quote/RELIANCE
    Handles weekends and holidays by escalating fetch period (5d → 1mo → 3mo).
    """
    try:
        return _get_ticker_info(symbol)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch quote: {str(e)}")


@router.get("/chart/{symbol}")
async def get_chart_data(symbol: str, period: str = "6mo", interval: str = "1d"):
    """
    Get historical OHLCV data for charting.
    Returns array of dicts with: time, open, high, low, close, value (volume).
    """
    try:
        ns_symbol = symbol.upper().strip()
        ticker = yf.Ticker(ns_symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty and ".NS" not in ns_symbol:
            ns_symbol = ns_symbol + ".NS"
            ticker = yf.Ticker(ns_symbol)
            hist = ticker.history(period=period, interval=interval)
            
        if hist.empty:
             raise ValueError(f"No historical data available for {symbol}")

        data = []
        for index, row in hist.iterrows():
            dt = index.strftime("%Y-%m-%d") if interval == "1d" else int(index.timestamp())
            data.append({
                "time": dt,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "value": int(row["Volume"])
            })
        return {"symbol": symbol, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chart data: {str(e)}")


@router.get("/quotes")
async def get_batch_quotes(symbols: str):
    """
    Get live quotes for multiple symbols at once.
    Example: GET /market/quotes?symbols=RELIANCE,TCS,INFY
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    results = {}
    for symbol in symbol_list:
        try:
            results[symbol] = _get_ticker_info(symbol)
        except Exception as e:
            results[symbol] = {"symbol": symbol, "error": str(e), "ltp": None}
    return results


@router.get("/search")
async def search_stocks(q: str):
    """
    Live stock search via Yahoo Finance (yfinance.Search).
    Covers ALL NSE-listed stocks + global equities — no hardcoded list.
    Falls back to a curated list only if Yahoo Finance is unreachable.

    Exchange codes returned by Yahoo Finance:
      NSI  = National Stock Exchange of India (NSE)
      BOM  = Bombay Stock Exchange (BSE)
      NMS  = NASDAQ (US)
      NYQ  = NYSE (US)
    """
    q = q.strip()
    if not q:
        return {"results": [], "query": q, "source": "none"}

    # ── 1. Live Yahoo Finance search ──────────────────────────────────────────
    try:
        search = yf.Search(q, news_count=0, max_results=20)
        raw = search.quotes  # list[dict]

        results = []
        for item in raw:
            sym:      str = item.get("symbol", "")
            name:     str = item.get("shortname") or item.get("longname") or sym
            exchange: str = item.get("exchange", "")
            qtype:    str = item.get("quoteType", "")

            # Only show equities (skip ETFs, mutual funds, indices, etc.)
            # NSI = NSE India, BOM = BSE India, NMS = Nasdaq, NYQ = NYSE
            if qtype not in ("EQUITY", "ETF"):
                continue

            # Strip .NS / .BO suffix for display; store clean symbol
            display_sym = sym.replace(".NS", "").replace(".BO", "")

            # Tag with exchange for user clarity
            if exchange in ("NSI",):
                exch_label = "NSE"
            elif exchange in ("BOM",):
                exch_label = "BSE"
            elif exchange in ("NMS", "NGM", "NCM"):
                exch_label = "NASDAQ"
            elif exchange in ("NYQ", "NYB"):
                exch_label = "NYSE"
            else:
                exch_label = exchange

            results.append({
                "symbol":   display_sym,
                "yf_symbol": sym,          # full yfinance symbol e.g. RELIANCE.NS
                "name":     name,
                "exchange": exch_label,
                "type":     qtype,
            })

        if results:
            return {"results": results[:12], "query": q, "source": "yahoo_finance"}

    except Exception as e:
        print(f"⚠️  Search: yfinance.Search failed for '{q}': {e}")

    # ── 2. Fallback: curated popular symbols (offline safety net) ─────────────
    FALLBACK = [
        {"symbol": "RELIANCE",   "name": "Reliance Industries Ltd",              "exchange": "NSE"},
        {"symbol": "TCS",        "name": "Tata Consultancy Services Ltd",        "exchange": "NSE"},
        {"symbol": "INFY",       "name": "Infosys Ltd",                          "exchange": "NSE"},
        {"symbol": "HDFCBANK",   "name": "HDFC Bank Ltd",                        "exchange": "NSE"},
        {"symbol": "ICICIBANK",  "name": "ICICI Bank Ltd",                       "exchange": "NSE"},
        {"symbol": "SBIN",       "name": "State Bank of India",                  "exchange": "NSE"},
        {"symbol": "LT",         "name": "Larsen & Toubro Ltd",                  "exchange": "NSE"},
        {"symbol": "WIPRO",      "name": "Wipro Ltd",                            "exchange": "NSE"},
        {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd",                   "exchange": "NSE"},
        {"symbol": "AXISBANK",   "name": "Axis Bank Ltd",                        "exchange": "NSE"},
        {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd",                    "exchange": "NSE"},
        {"symbol": "MARUTI",     "name": "Maruti Suzuki India Ltd",              "exchange": "NSE"},
        {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd",                      "exchange": "NSE"},
        {"symbol": "ZOMATO",     "name": "Zomato Ltd",                           "exchange": "NSE"},
        {"symbol": "AAPL",       "name": "Apple Inc",                            "exchange": "NASDAQ"},
        {"symbol": "MSFT",       "name": "Microsoft Corporation",                "exchange": "NASDAQ"},
        {"symbol": "GOOGL",      "name": "Alphabet Inc",                         "exchange": "NASDAQ"},
        {"symbol": "NVDA",       "name": "NVIDIA Corporation",                   "exchange": "NASDAQ"},
        {"symbol": "TSLA",       "name": "Tesla Inc",                            "exchange": "NASDAQ"},
        {"symbol": "META",       "name": "Meta Platforms Inc",                   "exchange": "NASDAQ"},
    ]
    q_up = q.upper()
    filtered = [s for s in FALLBACK if q_up in s["symbol"] or q_up in s["name"].upper()]
    return {"results": filtered[:12], "query": q, "source": "fallback_list"}
