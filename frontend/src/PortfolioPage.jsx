import React, { useState, useEffect, useCallback, useRef } from 'react';
import DevConsole from './DevConsole';
import TradingChart from './components/TradingChart';


const API = 'http://localhost:8000';
const INR = n => n != null ? `₹${Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—';
const PCT = n => n != null ? `${n >= 0 ? '+' : ''}${Number(n).toFixed(2)}%` : '—';

export default function PortfolioPage({ walletId }) {
  const [summary, setSummary] = useState(null);
  const [trades, setTrades] = useState([]);
  const [orders, setOrders] = useState([]);
  const [liveQuotes, setLiveQuotes] = useState({});
  const [quotesLoading, setQuotesLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);
  const [quote, setQuote] = useState(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [tradeTab, setTradeTab] = useState('BUY');
  // qty as string so backspace/delete works cleanly
  const [qtyStr, setQtyStr] = useState('');
  const [alert, setAlert] = useState(null);
  const [devLog, setDevLog] = useState(null);
  const [historyTab, setHistoryTab] = useState('trades');
  const searchTimer = useRef(null);

  const showAlert = (type, msg) => { setAlert({ type, msg }); setTimeout(() => setAlert(null), 5000); };
  const qty = parseInt(qtyStr, 10);
  const qtyValid = !isNaN(qty) && qty >= 1;

  // ── Fetch portfolio summary + history ──────────────
  const fetchPortfolio = useCallback(async () => {
    const steps = [
      { arrow: '→', text: `[1] HTTP GET /portfolio/${walletId}/summary`, cls: 'step-cmd' },
      { arrow: '  ', text: '    PortfolioService.get_summary(wallet_id)', cls: 'step-layer' },
      { arrow: '  ', text: '    └→ Portfolio(wallet_id, MarketProvider()).__init__()', cls: 'step-layer' },
      { arrow: '  ', text: '       ├→ storage.load_positions() → positions_{id}.json', cls: 'step-data' },
      { arrow: '  ', text: '       ├→ storage.load_trades()    → trades_{id}.json (with timestamps)', cls: 'step-data' },
      { arrow: '  ', text: '       └→ Wallet.__init__() → load_events() → _replay_events()', cls: 'step-data' },
      { arrow: '  ', text: '    └→ analytics: avg_cost(), asset_values(), unrealized_pnl_all(), allocations()', cls: 'step-layer' },
      { arrow: '→', text: `[2] HTTP GET /history/portfolio/${walletId}/trades?limit=50`, cls: 'step-cmd' },
      { arrow: '→', text: `[3] HTTP GET /history/portfolio/${walletId}/orders?limit=50`, cls: 'step-cmd' },
    ];
    setDevLog({ steps, request: `GET /portfolio/${walletId}/summary\nGET /history/portfolio/${walletId}/trades?limit=50\nGET /history/portfolio/${walletId}/orders?limit=50`, response: 'Fetching...', status: 'running' });

    try {
      const [sRes, tRes, oRes] = await Promise.all([
        fetch(`${API}/portfolio/${walletId}/summary`),
        fetch(`${API}/history/portfolio/${walletId}/trades?limit=50`),
        fetch(`${API}/history/portfolio/${walletId}/orders?limit=50`),
      ]);
      const s = await sRes.json();
      const t = await tRes.json();
      const o = await oRes.json();
      setSummary(s);
      setTrades(t.items || []);
      setOrders(o.items || []);

      const syms = Object.keys(s.positions || {});
      if (syms.length > 0) {
        fetchBatchQuotes(syms, steps, s);
      } else {
        setDevLog(prev => ({
          ...prev,
          steps: [...steps, { arrow: '←', text: `RESPONSE: cash=₹${s.cash?.toFixed(2)}, positions=${JSON.stringify(Object.keys(s.positions || {}))}`, cls: 'step-resp' }],
          response: JSON.stringify({ cash: s.cash, total_value: s.total_value, avg_cost: s.avg_cost, positions: s.positions }, null, 2),
          status: 'ok'
        }));
      }
    } catch (err) {
      setDevLog(prev => ({ ...prev, steps: [...(prev?.steps || []), { arrow: '✗', text: String(err), cls: 'step-err' }], response: String(err), status: 'error' }));
      showAlert('err', `Backend error: ${err.message}`);
    }
  }, [walletId]);

  // ── Batch live LTPs ────────────────────────────────
  const fetchBatchQuotes = async (symbols, prevSteps, summaryData) => {
    setQuotesLoading(true);
    const symStr = symbols.join(',');
    const batchSteps = [
      ...(prevSteps || []),
      { arrow: '→', text: `[4] HTTP GET /market/quotes?symbols=${symStr}`, cls: 'step-cmd' },
      { arrow: '  ', text: '    MarketProvider: cache (60s TTL) → if miss → yfinance.Ticker.history(period="2d")', cls: 'step-data' },
      { arrow: '  ', text: '    Tries SYMBOL.NS (NSE) first, then SYMBOL (US)', cls: 'step-data' },
    ];
    setDevLog(prev => ({ ...prev, steps: batchSteps, status: 'running' }));

    try {
      const res = await fetch(`${API}/market/quotes?symbols=${symStr}`);
      const data = await res.json();
      setLiveQuotes(data);
      setDevLog(prev => ({
        ...prev,
        steps: [
          ...batchSteps,
          { arrow: '←', text: `LIVE PRICES: ${symbols.map(s => `${s}=₹${data[s]?.ltp ?? 'ERR'}`).join(', ')}`, cls: 'step-resp' },
        ],
        response: JSON.stringify({
          avg_cost: summaryData?.avg_cost,
          positions: summaryData?.positions,
          live_prices: Object.fromEntries(symbols.map(s => [s, data[s]?.ltp]))
        }, null, 2),
        status: 'ok'
      }));
    } catch (e) {
      setDevLog(prev => ({ ...prev, steps: [...(prev?.steps || []), { arrow: '⚠', text: `Live quotes failed: ${e.message}`, cls: 'step-err' }], status: 'error' }));
    } finally {
      setQuotesLoading(false);
    }
  };

  useEffect(() => { fetchPortfolio(); }, [fetchPortfolio]);

  // ── Stock Search ───────────────────────────────────
  useEffect(() => {
    if (!query.trim()) { setSearchResults([]); return; }
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(async () => {
      try {
        const res = await fetch(`${API}/market/search?q=${encodeURIComponent(query)}`);
        const d = await res.json();
        setSearchResults(d.results || []);
      } catch { setSearchResults([]); }
    }, 300);
  }, [query]);

  // ── Load Quote ─────────────────────────────────────
  const loadQuote = useCallback(async (symbol) => {
    setQuoteLoading(true); setQuote(null);
    const steps = [
      { arrow: '→', text: `HTTP GET /market/quote/${symbol}`, cls: 'step-cmd' },
      { arrow: '  ', text: `yfinance.Ticker("${symbol}.NS").history(period="2d", interval="1d")`, cls: 'step-data' },
      { arrow: '  ', text: 'Extracts: ltp=Close[-1], prev_close=Close[-2], volume, H, L, O', cls: 'step-data' },
      { arrow: '  ', text: 'Computes: change=ltp−prev_close, change_pct=(change/prev_close)×100', cls: 'step-data' },
    ];
    setDevLog({ steps, request: `GET /market/quote/${symbol}`, response: 'Fetching live...', status: 'running' });
    try {
      const res = await fetch(`${API}/market/quote/${symbol}`);
      if (!res.ok) throw new Error(`${res.status}: Not found on NSE`);
      const d = await res.json();
      setQuote(d);
      setDevLog(prev => ({
        ...prev,
        steps: [...steps, { arrow: '←', text: `LTP=${INR(d.ltp)}, chg=${d.change?.toFixed(2)} (${PCT(d.change_pct)}), vol=${d.volume?.toLocaleString()}`, cls: 'step-resp' }],
        response: JSON.stringify(d, null, 2),
        status: 'ok'
      }));
    } catch (e) {
      setQuote({ error: e.message });
      setDevLog(prev => ({ ...prev, steps: [...steps, { arrow: '✗', text: String(e), cls: 'step-err' }], response: String(e), status: 'error' }));
    } finally { setQuoteLoading(false); }
  }, []);

  const selectStock = (s) => {
    setSelectedStock(s);
    setSearchResults([]);
    setQuery('');
    loadQuote(s.symbol);
  };

  // Click from holdings table → pre-fill trade form
  const selectFromHoldings = (sym) => {
    setSelectedStock({ symbol: sym, name: sym });
    setTradeTab('SELL');
    loadQuote(sym);
    window.scrollTo({ top: 0 });
  };

  useEffect(() => {
    if (!selectedStock) return;
    const t = setInterval(() => loadQuote(selectedStock.symbol), 60000);
    return () => clearInterval(t);
  }, [selectedStock, loadQuote]);

  // ── Execute Trade ──────────────────────────────────
  const executeTrade = async () => {
    if (!qtyValid) { showAlert('err', 'Enter a valid quantity (minimum 1)'); return; }
    if (!quote || quote.error) { showAlert('err', 'No valid quote loaded'); return; }

    const endpoint = `/portfolio/${walletId}/${tradeTab.toLowerCase()}`;
    const payload = { symbol: quote.symbol, quantity: qty };
    const txId = crypto.randomUUID();
    const cost = (qty * quote.ltp).toFixed(2);

    const steps = [
      { arrow: '→', text: `COMMAND: POST ${endpoint}`, cls: 'step-cmd' },
      { arrow: '  ', text: `${tradeTab === 'BUY' ? 'BuyAssetHandler' : 'SellAssetHandler'}.handle(cmd)`, cls: 'step-layer' },
      { arrow: '  ', text: `OrderExecutionEngine.place_order(symbol="${quote.symbol}", side="${tradeTab}", qty=${qty}, type=MARKET)`, cls: 'step-layer' },
      { arrow: '  ', text: `├→ MarketProvider.get_price("${quote.symbol}") → LTP=${INR(quote.ltp)}`, cls: 'step-data' },
      { arrow: '  ', text: tradeTab === 'BUY'
          ? `├→ _validate_buy: Portfolio.cash()=${INR(summary?.cash)} >= cost=${INR(cost)} ?`
          : `├→ _validate_sell: positions["${quote.symbol}"]=${summary?.positions?.[quote.symbol] ?? 0} >= qty=${qty} ?`,
        cls: 'step-data' },
      { arrow: '  ', text: `└→ Order PENDING → ${tradeTab === 'BUY' ? `Wallet.debit(${INR(cost)}) → FundsDebited` : `Wallet.credit(${INR(cost)}) → FundsCredited`}`, cls: 'step-layer' },
      { arrow: '  ', text: `Trade(trade_id=uuid, symbol, side, qty, price=${INR(quote.ltp)}, timestamp=now) → trades_{id}.json`, cls: 'step-data' },
      { arrow: '  ', text: 'Positions updated → positions_{id}.json', cls: 'step-data' },
      { arrow: '  ', text: `IDEMPOTENCY: X-Tx-ID=${txId.slice(0,12)}... → stored in FundsDebited/Credited event`, cls: 'step-data' },
    ];

    setDevLog({ steps, request: `POST ${endpoint}\nX-Transaction-ID: ${txId}\n\n${JSON.stringify(payload, null, 2)}`, response: 'Executing...', status: 'running' });

    try {
      const res = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Transaction-ID': txId },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      const ok = res.ok && data.success !== false;

      setDevLog(prev => ({
        ...prev,
        steps: [...steps, {
          arrow: '←',
          text: `HTTP ${res.status} | order_status=${data.order_status} | order_id=${data.order_id?.slice(0,12)}... | ${ok ? `new_cash=₹${data.portfolio_summary?.cash?.toFixed(2)}` : `REJECTED: ${data.message}`}`,
          cls: ok ? 'step-resp' : 'step-err'
        }],
        response: JSON.stringify(data, null, 2),
        status: ok ? 'ok' : 'error'
      }));

      if (!ok) throw new Error(data.message || data.detail || 'Order rejected by engine');
      showAlert('ok', data.message);
      fetchPortfolio();
    } catch (e) {
      setDevLog(prev => ({ ...prev, steps: [...(prev?.steps || []), { arrow: '✗', text: String(e), cls: 'step-err' }], response: String(e), status: 'error' }));
      showAlert('err', String(e));
    }
  };

  // ── Compute holdings rows ──────────────────────────
  // NOTE on market-closed behavior:
  // When market is closed, yfinance returns the last close price.
  // avg_cost = weighted avg of all BUY trades (from backend)
  // LTP      = last close from yfinance
  // If you bought AFTER close: LTP ≈ prev close, avg_cost = buy price (same as LTP or close to it)
  // So P&L ≈ 0 and Day Change = 0 is CORRECT when market is closed.
  const holdings = Object.entries(summary?.positions || {}).map(([sym, qty]) => {
    const avgCost = summary?.avg_cost?.[sym] ?? 0;
    const q = liveQuotes[sym];
    // Use live LTP from batch quotes; fallback to asset_value / qty
    const ltp = q?.ltp != null ? q.ltp : (summary?.asset_values?.[sym] ? summary.asset_values[sym] / qty : null);
    // invested = avg_cost × current held qty (what money is currently "in" this position)
    const invested = avgCost > 0 ? avgCost * qty : null;
    // curVal = live LTP × qty
    const curVal = ltp != null ? ltp * qty : (summary?.asset_values?.[sym] ?? null);
    // P&L = cur market value - cost basis
    const pnl = (invested != null && curVal != null) ? curVal - invested : null;
    // Net Chg% = P&L / invested × 100
    const netChgPct = (invested != null && invested > 0 && pnl != null) ? (pnl / invested) * 100 : null;
    // Day Change% from yfinance (0 if market closed)
    const dayChgPct = q?.change_pct ?? null;
    return { sym, qty, avgCost, ltp, invested, curVal, pnl, netChgPct, dayChgPct };
  });

  //  ── Null-safe totals: exclude positions where data is still loading ────────
  // WRONG: (h.invested ?? 0) silently drops nulls → understated totals
  // RIGHT: only sum positions that have a real value; show — if any are still missing
  const hasAllInvested = holdings.every(h => h.invested != null);
  const hasAllCurVal   = holdings.every(h => h.curVal   != null);

  const totalInvested = holdings.reduce((a, h) => a + (h.invested ?? 0), 0);
  const totalCurVal   = holdings.reduce((a, h) => a + (h.curVal   ?? 0), 0);
  const totalPnL      = holdings.reduce((a, h) => a + (h.pnl      ?? 0), 0);
  const totalNetPct   = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

  // Day P&L = sum of (dayChgPct / 100 × prevClose × qty) per holding
  // = sum of (change × qty) since batch quotes include change (LTP - prevClose)
  const dayPnLItems = holdings.map(h => {
    const q = liveQuotes[h.sym];
    if (!q || q.change == null) return null;
    return q.change * h.qty;   // ₹ day gain/loss for this holding
  });
  const hasAllDayPnL = dayPnLItems.every(x => x != null);
  const totalDayPnL  = dayPnLItems.reduce((a, x) => a + (x ?? 0), 0);
  const totalDayPct  = totalCurVal > 0 ? (totalDayPnL / (totalCurVal - totalDayPnL)) * 100 : 0;
  const isUp = quote && quote.change >= 0;

  return (
    <div className="page-body">
      {/* LEFT: Search + Quote + Trade */}
      <div className="left-panel">
        <div className="panel-header">// market_terminal</div>
        <div className="search-wrap">
          <input className="search-input" placeholder="Search NSE symbol (e.g. INFY, LT, ZOMATO)"
            value={query} onChange={e => setQuery(e.target.value)} />
          {searchResults.length > 0 && (
          <div className="dropdown">
              {searchResults.map(r => (
                <div key={r.yf_symbol || r.symbol} className="dropdown-item" onClick={() => selectStock(r)}>
                  <div>
                    <div className="sym">{r.symbol}</div>
                    <div className="sym-name">{r.name}</div>
                  </div>
                  <span className="sym-tag" style={{
                    background: r.exchange === 'NSE' ? 'rgba(63,185,80,0.15)' :
                                r.exchange === 'BSE' ? 'rgba(88,166,255,0.15)' :
                                'rgba(188,140,255,0.15)',
                    color: r.exchange === 'NSE' ? 'var(--green)' :
                           r.exchange === 'BSE' ? 'var(--blue)' : 'var(--purple)',
                    border: `1px solid ${r.exchange === 'NSE' ? 'var(--green)' : r.exchange === 'BSE' ? 'var(--blue)' : 'var(--purple)'}`
                  }}>{r.exchange || 'NSE'}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="quote-scroll">
          {!selectedStock && (
            <div className="placeholder-hint">{'>'} search NSE stock above, or<br/>click any holding row below to trade</div>
          )}
          {selectedStock && quoteLoading && <div className="placeholder-hint">⟳ fetching {selectedStock.symbol}.NS…</div>}
          {quote?.error && <div className="alert alert-err">{quote.error}</div>}

          {quote && !quote.error && (
            <>
              <div className="quote-block">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <span className="quote-sym">{quote.symbol}</span>
                    <span className="quote-exchange" style={{ marginLeft: '6px', display: 'block', fontSize: '0.67rem' }}>NSE · {selectedStock?.name}</span>
                  </div>
                  <button onClick={() => { setSelectedStock(null); setQuote(null); }}
                    style={{ background: 'transparent', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: '0.8rem' }}>✕</button>
                </div>
                <div className="ltp-row">
                  <span className="ltp">{INR(quote.ltp)}</span>
                  <span className={`chg ${isUp ? 'is-up' : 'is-down'}`}>{isUp ? '▲' : '▼'} {Math.abs(quote.change).toFixed(2)} ({PCT(quote.change_pct)})</span>
                </div>
                <div style={{ fontSize: '0.67rem', color: 'var(--muted)', marginBottom: '6px', fontFamily: 'var(--mono)' }}>
                  prev_close: {INR(quote.prev_close)}
                  {quote.change === 0 && <span style={{ color: 'var(--yellow)', marginLeft: '8px' }}>※ market closed</span>}
                </div>
                <div className="meta-grid">
                  {[['LTP',INR(quote.ltp)],['VOL',quote.volume?.toLocaleString()],['DAY H',INR(quote.high),'up'],['DAY L',INR(quote.low),'down'],
                    ['OPEN',INR(quote.open)],['52W H',quote.week52_high?INR(quote.week52_high):'—'],['52W L',quote.week52_low?INR(quote.week52_low):'—'],
                    ['MKT CAP',quote.market_cap?`₹${(quote.market_cap/1e7).toFixed(0)} Cr`:'—']
                  ].map(([k,v,c]) => (
                    <div key={k} className="meta-cell"><div className="meta-k">{k}</div><div className={`meta-v ${c||''}`}>{v}</div></div>
                  ))}
                </div>
                </div>

                {/* Chart Block */}
                <div style={{ marginTop: '1rem', marginBottom: '1rem', width: '100%' }}>
                  <TradingChart symbol={quote.symbol} />
                </div>

              {/* Trade Form */}

              <div className="trade-block">
                <div className="trade-tabs">
                  <button className={`trade-tab ${tradeTab==='BUY'?'buy-active':''}`} onClick={() => setTradeTab('BUY')} title={`POST /portfolio/${walletId}/buy`}>BUY</button>
                  <button className={`trade-tab ${tradeTab==='SELL'?'sell-active':''}`} onClick={() => setTradeTab('SELL')} title={`POST /portfolio/${walletId}/sell`}>SELL</button>
                </div>

                <div className="form-group">
                  <label className="form-label">qty (shares)</label>
                  <input
                    className="form-input"
                    type="number"
                    min="1"
                    placeholder="enter qty"
                    value={qtyStr}
                    onChange={e => setQtyStr(e.target.value)}
                    style={{ borderColor: qtyStr && !qtyValid ? 'var(--red)' : undefined }}
                  />
                  {qtyStr && !qtyValid && (
                    <div style={{ color: 'var(--red)', fontSize: '0.68rem', marginTop: '3px', fontFamily: 'var(--mono)' }}>
                      ⚠ enter a valid quantity ≥ 1
                    </div>
                  )}
                </div>

                <div style={{ marginBottom: '6px' }}>
                  {[1,5,10,20].map(q => (
                    <button key={q} onClick={() => setQtyStr(String(q))}
                      style={{ marginRight:'4px',background:qtyStr===String(q)?'var(--blue-dim)':'var(--surface)',border:`1px solid ${qtyStr===String(q)?'var(--blue)':'var(--border)'}`,color:qtyStr===String(q)?'var(--blue)':'var(--muted)',padding:'3px 7px',borderRadius:'3px',cursor:'pointer',fontFamily:'var(--mono)',fontSize:'0.72rem' }}>
                      {q}
                    </button>
                  ))}
                </div>

                {qtyValid && (
                  <div className="cost-row">
                    <span style={{ color:'var(--muted)' }}>{tradeTab==='BUY'?'est_cost':'est_proceeds'}</span>
                    <span>{INR((qty * quote.ltp).toFixed(2))}</span>
                  </div>
                )}

                <button
                  className={tradeTab==='BUY'?'btn-buy':'btn-sell'}
                  onClick={executeTrade}
                  title={`POST /portfolio/${walletId}/${tradeTab.toLowerCase()}\nBody: { symbol: "${quote.symbol}", quantity: ${qtyValid ? qty : '?'} }`}
                >
                  {qtyValid
                    ? `${tradeTab} ${qty}×${quote.symbol} @ ${INR(quote.ltp)}`
                    : `${tradeTab} ${quote.symbol} — enter qty first`}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* MAIN Panel */}
      <div className="main-area">
        <div className="main-scroll">
          {alert && <div className={`alert alert-${alert.type}`}>{alert.msg}</div>}

          {/* Summary Bar */}
          <div className="summary-bar">
            <div className="summary-item">
              <div className="summary-k">TOTAL_INVESTMENT</div>
              <div className="summary-v">
                {hasAllInvested
                  ? INR(totalInvested)
                  : <span style={{color:'var(--yellow)',fontSize:'0.8rem'}}>⟳ loading…</span>}
              </div>
            </div>
            <div className="summary-sep"/>
            <div className="summary-item">
              <div className="summary-k">CURRENT_VALUE {quotesLoading && <span style={{color:'var(--yellow)',fontSize:'0.65rem'}}> ⟳ live…</span>}</div>
              <div className="summary-v">{hasAllCurVal ? INR(totalCurVal) : <span style={{color:'var(--yellow)',fontSize:'0.8rem'}}>⟳ loading…</span>}</div>
            </div>
            <div className="summary-sep"/>
            <div className="summary-item">
              <div className="summary-k">OVERALL_P&L</div>
              <div className={`summary-v ${totalPnL >= 0 ? 'up' : 'down'}`}>
                {hasAllCurVal && hasAllInvested
                  ? <>{INR(totalPnL)} <span className={`summary-badge ${totalPnL < 0 ? 'neg' : ''}`}>{PCT(totalNetPct)}</span></>
                  : '—'}
              </div>
            </div>
            <div className="summary-sep"/>
            <div className="summary-item">
              <div className="summary-k">DAY_P&L</div>
              <div className={`summary-v ${totalDayPnL >= 0 ? 'up' : 'down'}`}>
                {hasAllDayPnL
                  ? <>{totalDayPnL >= 0 ? '+' : ''}{INR(totalDayPnL)} <span className={`summary-badge ${totalDayPnL < 0 ? 'neg' : ''}`}>{PCT(totalDayPct)}</span></>
                  : '—'}
              </div>
            </div>
            <div className="summary-sep"/>
            <div className="summary-item">
              <div className="summary-k">AVAIL_CASH</div>
              <div className="summary-v up">{INR(summary?.cash)}</div>
            </div>
          </div>

          {/* Holdings Table */}
          <div className="sec-label">
            <span className="sec-label-dot" style={{ background: 'var(--green)' }} />
            holdings — {holdings.length} positions
            <button onClick={fetchPortfolio} className="btn-icon" style={{ marginLeft:'auto' }}
              title={`Refresh: GET /portfolio/${walletId}/summary + GET /market/quotes + GET /history/trades`}>↺ refresh</button>
          </div>

          <table className="data-table">
            <thead>
              <tr>
                <th>instrument</th><th>qty</th><th>avg_cost</th><th>ltp</th>
                <th>invested</th><th>cur_val</th><th>p&l</th><th>net_chg%</th><th>day_chg%</th>
              </tr>
            </thead>
            <tbody>
              {holdings.length === 0 && (
                <tr><td colSpan="9" className="empty">No positions. Search and buy a stock.</td></tr>
              )}
              {holdings.map(h => (
                <tr key={h.sym} style={{ cursor: 'pointer' }} onClick={() => selectFromHoldings(h.sym)}
                  title={`Click to open trade panel for ${h.sym}`}>
                  <td><strong style={{ color: 'var(--blue)' }}>{h.sym}</strong></td>
                  <td>{h.qty}</td>
                  <td style={{fontFamily:'var(--mono)'}}>{h.avgCost > 0 ? INR(h.avgCost) : <span style={{color:'var(--yellow)'}}>—</span>}</td>
                  <td style={{ fontWeight: 600 }}>{h.ltp ? INR(h.ltp) : <span style={{color:'var(--muted)'}}>—</span>}</td>
                  <td>{h.invested != null && h.invested > 0 ? INR(h.invested) : '—'}</td>
                  <td>{h.curVal ? INR(h.curVal) : '—'}</td>
                  <td>
                    {h.pnl != null
                      ? <span className={`badge ${h.pnl >= 0 ? 'badge-g' : 'badge-r'}`}>{h.pnl >= 0 ? '+' : ''}{INR(h.pnl)}</span>
                      : <span style={{color:'var(--muted)'}}>—</span>}
                  </td>
                  <td className={h.netChgPct != null ? (h.netChgPct >= 0 ? 'up' : 'down') : 'neutral'}>
                    {h.netChgPct != null ? PCT(h.netChgPct) : '—'}
                  </td>
                  <td className={h.dayChgPct != null ? (h.dayChgPct >= 0 ? 'up' : 'down') : 'neutral'}>
                    {h.dayChgPct != null ? PCT(h.dayChgPct) : '—'}
                  </td>
                </tr>
              ))}
              {holdings.length > 0 && (
                <tr style={{ background: 'var(--surface2)', fontWeight: 700 }}>
                  <td colSpan="4" style={{ color:'var(--muted)',fontFamily:'var(--mono)',fontSize:'0.67rem' }}>— TOTALS ({holdings.length} positions) —</td>
                  <td style={{ fontFamily:'var(--mono)' }}>
                    {hasAllInvested ? INR(totalInvested) : <span style={{color:'var(--yellow)'}}>loading…</span>}
                  </td>
                  <td style={{ fontFamily:'var(--mono)' }}>
                    {hasAllCurVal ? INR(totalCurVal) : <span style={{color:'var(--yellow)'}}>loading…</span>}
                  </td>
                  <td>
                    {hasAllCurVal && hasAllInvested
                      ? <span className={`badge ${totalPnL >= 0 ? 'badge-g' : 'badge-r'}`}>
                          {totalPnL >= 0 ? '+' : ''}{INR(totalPnL)}
                        </span>
                      : '—'}
                  </td>
                  <td className={totalNetPct >= 0 ? 'up' : 'down'}>
                    {hasAllCurVal && hasAllInvested ? PCT(totalNetPct) : '—'}
                  </td>
                  <td className={totalDayPnL >= 0 ? 'up' : 'down'} style={{ fontWeight: 600 }}>
                    {hasAllDayPnL
                      ? <span title={`Day P&L: ${INR(totalDayPnL)}`}>
                          {totalDayPnL >= 0 ? '+' : ''}{INR(totalDayPnL)}
                          <span style={{ color:'var(--muted)', fontWeight:400, fontSize:'0.7rem', marginLeft:'4px' }}>
                            ({PCT(totalDayPct)})
                          </span>
                        </span>
                      : '—'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {/* Note about market-closed state */}
          {holdings.some(h => h.dayChgPct === 0) && (
            <div style={{ fontSize:'0.7rem', color:'var(--muted)', fontFamily:'var(--mono)', marginBottom:'8px' }}>
              ⓘ day_chg=0.00% indicates market is currently closed — LTP reflects last close price from NSE.
            </div>
          )}

          {summary?.health_signals?.length > 0 && summary.health_signals.map((s, i) => (
            <div key={i} style={{ fontSize:'0.72rem',color:'var(--yellow)',fontFamily:'var(--mono)',marginBottom:'3px' }}>⚠ health: {s}</div>
          ))}

          {/* Trade / Order History */}
          <div className="sec-label" style={{ marginTop:'10px' }}>
            <span className="sec-label-dot" style={{ background:'var(--purple)' }} />
            portfolio_history
            <div style={{ marginLeft:'auto',display:'flex',gap:'4px' }}>
              {['trades','orders'].map(t => (
                <button key={t} onClick={() => setHistoryTab(t)}
                  style={{ padding:'2px 8px',border:`1px solid ${historyTab===t?'var(--blue)':'var(--border)'}`,background:historyTab===t?'var(--blue-dim)':'transparent',color:historyTab===t?'var(--blue)':'var(--muted)',borderRadius:'3px',cursor:'pointer',fontFamily:'var(--mono)',fontSize:'0.72rem',fontWeight:600 }}>
                  {t}
                </button>
              ))}
            </div>
          </div>

          {historyTab === 'trades' && (
            <table className="data-table">
              <thead>
                <tr><th>symbol</th><th>trade_time</th><th>trade_id</th><th>type</th><th>qty</th><th>price</th><th>total_value</th></tr>
              </thead>
              <tbody>
                {trades.length === 0 && <tr><td colSpan="7" className="empty">No trades recorded.</td></tr>}
                {trades.map((t, i) => (
                  <tr key={t.trade_id || i}>
                    <td><strong style={{ color:'var(--blue)' }}>{t.symbol}</strong></td>
                    <td style={{ color:'var(--muted)',fontSize:'0.72rem' }}>{new Date(t.timestamp).toLocaleString('en-IN')}</td>
                    <td style={{ color:'var(--muted)',fontSize:'0.67rem' }}>{t.trade_id?.slice(0,14)}…</td>
                    <td><span className={`badge ${t.side==='BUY'?'badge-b':'badge-r'}`}>{t.side}</span></td>
                    <td>{t.quantity}</td>
                    <td style={{fontFamily:'var(--mono)'}}>{INR(t.price)}</td>
                    <td style={{fontFamily:'var(--mono)',fontWeight:600}}>{INR(t.total_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {historyTab === 'orders' && (
            <table className="data-table">
              <thead>
                <tr><th>symbol</th><th>order_time</th><th>order_id</th><th>type</th><th>qty</th><th>status</th><th>fill_price</th></tr>
              </thead>
              <tbody>
                {orders.length === 0 && <tr><td colSpan="7" className="empty">No orders recorded.</td></tr>}
                {orders.map((o, i) => (
                  <tr key={o.order_id || i}>
                    <td><strong style={{ color:'var(--blue)' }}>{o.symbol}</strong></td>
                    <td style={{ color:'var(--muted)',fontSize:'0.72rem' }}>{new Date(o.timestamp).toLocaleString('en-IN')}</td>
                    <td style={{ color:'var(--muted)',fontSize:'0.67rem' }}>{o.order_id?.slice(0,14)}…</td>
                    <td><span className={`badge ${o.side==='BUY'?'badge-b':'badge-r'}`}>{o.side}</span></td>
                    <td>{o.quantity}</td>
                    <td><span className={`badge ${o.status==='FILLED'?'badge-g':o.status==='REJECTED'?'badge-r':'badge-y'}`}>{o.status}</span></td>
                    <td style={{fontFamily:'var(--mono)'}}>{o.price ? INR(o.price) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <DevConsole log={devLog} />
        </div>
      </div>
    </div>
  );
}
