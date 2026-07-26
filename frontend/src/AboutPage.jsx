import React, { useState } from 'react';

const PATCH_NOTES = [
  // ─────────────────────────────────────────────────────────────────────────
  // HOW TO ADD A NEW PATCH NOTE (for your own reference):
  //
  // 1. Copy the block below and paste it at the TOP of this array (newest first)
  // 2. Bump version:  v10.4.0 → v10.5.0  (patch = bug fix, minor = new feature)
  // 3. Set today's date in YYYY-MM-DD format
  // 4. Pick a category: 'FEAT' (green), 'FIX' (red), 'ARCH' (purple)
  // 5. Save the file — Vite hot-reloads, no restart needed
  //
  // {
  //   version: 'v10.5.0',
  //   date: '2026-MM-DD',
  //   title: 'Day XX — Short description of what changed',
  //   changes: [
  //     { category: 'FEAT', items: ['Added XYZ feature'] },
  //     { category: 'FIX',  items: ['Fixed ABC bug'] },
  //   ]
  // },
  // ─────────────────────────────────────────────────────────────────────────
  {
    version: 'v10.4.0',
    date: '2026-04-16',
    title: 'Day 10.4 — Market Clock, Kite Import & Day P&L Totals',
    changes: [
      {
        category: 'FEAT',
        items: [
          'NSE Market Clock in topbar: shows real-time IST, market status (CLOSED / PRE-OPEN / OPEN / POST-CLOSE), and live countdown to next state transition',
          'Market sessions: Pre-Open 09:00–09:15 (yellow), Normal Trading 09:15–15:30 (green), Post-Close 15:30–16:00 (yellow), Closed (red). Weekend-aware — counts down to Monday open',
          'Kite/Zerodha portfolio import: seed_kite_portfolio.py — seeds any real portfolio with exact avg_costs, quantities, wallet events, and FILLED orders into a new user kite-portfolio',
          'kite-portfolio added to the topbar user dropdown for instant switching',
          'Day P&L total in summary bar: OVERALL_P&L + DAY_P&L side-by-side, matching Kite\'s dashboard layout',
          'Day P&L in holdings totals row: Σ(change × qty) computed from live yfinance change field — shows ₹ amount + %',
        ]
      },
      {
        category: 'FIX',
        items: [
          'Totals row silently dropped positions with null liveQuotes: (h.curVal ?? 0) treated null as 0, understating totals. Fixed with hasAllCurVal / hasAllInvested guards — shows "loading…" until all 13 LTPs are fetched',
          'Day Chg% totals column showed hardcoded "—": now computes totalDayPnL = Σ(q.change × qty) per holding',
          'Summary bar CURRENT_VALUE fell back to total_asset_value (backend computed) instead of live frontend LTP × qty sum',
        ]
      }
    ]
  },
  {
    version: 'v10.3.0',
    date: '2026-04-16',
    title: 'Day 10.3 — Live Search API & Weekend Price Fix',
    changes: [
      {
        category: 'FEAT',
        items: [
          'Live stock search: replaced hardcoded 80-symbol list with yfinance.Search() — queries Yahoo Finance\'s full database covering all NSE, BSE, NASDAQ, NYSE stocks',
          'Search dropdown now shows color-coded exchange badges: 🟢 NSE · 🔵 BSE · 🟣 NASDAQ/NYSE (from live Yahoo Finance response)',
          'Search result now includes yf_symbol field (e.g. RELIANCE.NS) for accurate quote loading',
          'Fallback: if Yahoo search API is unreachable, gracefully falls back to curated 20-symbol offline list',
          'source field in search response indicates whether data came from yahoo_finance or fallback_list',
        ]
      },
      {
        category: 'FIX',
        items: [
          'Weekend/Holiday 404 Bug: period="2d" passed to yfinance returned empty DataFrame on weekends and market holidays (no trading sessions). Fixed with progressive period escalation: 5d → 1mo → 3mo',
          'Fix applies to BOTH api/market.py (quote endpoint) and domain/market.py (buy/sell price engine)',
          'Both SYMBOL.NS (NSE) and bare SYMBOL (US) are tried for each period before declaring failure',
          'Previously could not search for small-cap, mid-cap, or any stock not in the hardcoded list',
        ]
      }
    ]
  },
  {
    version: 'v10.2.0',
    date: '2026-04-14',
    title: 'Day 10.2 — Calculation Fixes & UX Improvements',
    changes: [
      {
        category: 'FIX',
        items: [
          'TOTAL_INVESTMENT showed ₹0.00: PortfolioSummary Pydantic model was missing avg_cost and asset_values fields — FastAPI\'s response_model silently stripped them. Added both fields with Optional typing and Config(extra="allow")',
          'P&L = Current Value (wrong): was computing P&L = curVal - 0 because avg_cost was None. Fixed by correctly passing avg_cost from backend.',
          'Qty input backspace bug: value={qty} with Number() conversion snapped empty string back to 0. Changed to qtyStr (string state) — user types freely, validation only on submit',
          'No validation on empty qty: was silently sending qty=1. Now shows inline error and blocks submission',
          'Wallet timestamps all same: FundsCredited/FundsDebited.from_dict() called cls() which triggered default_factory=datetime.now. Fixed by reading data["timestamp"] and assigning instance.timestamp = timestamp after construction',
          'Duplicate trade dedup was blocking multi-buy: old logic matched by symbol+side+price+qty, which meant buying the same stock twice at the same price was silently dropped. Fixed: dedup now uses trade_id UUID exclusively',
        ]
      },
      {
        category: 'FEAT',
        items: [
          'Click holdings row → immediately opens Buy/Sell panel pre-filled with SELL for that instrument',
          'Market-closed annotation: when day_chg=0.00%, shows "※ market closed" note below prev_close',
          'Info note below holdings: explains that day_chg=0 is correct behavior when market is closed',
          'Holdings totals row shows — instead of ₹0 when avg_cost data is unavailable',
          'Removed redundant activity_timeline from Wallet page — kept only the clean ledger table',
        ]
      }
    ]
  },
  {
    version: 'v10.1.0',
    date: '2026-04-14',
    title: 'Day 10.1 — Zerodha-Style Holdings Table & 4-Tab UI',
    changes: [
      {
        category: 'FEAT',
        items: [
          'Holdings table redesigned to match professional broking UI: Instrument, Qty, Avg Cost, LTP (live), Invested, Cur Val, P&L, Net Chg%, Day Chg%',
          'Totals row at bottom: sum of Invested, Cur Val, P&L, Net Chg% across all positions',
          'Summary bar: TOTAL_INVESTMENT · CURRENT_VALUE · TOTAL_P&L · AVAIL_CASH',
          'Trade history table with correct timestamps and trade_id per row (actual execution time)',
          'Order history table with FILLED/REJECTED/PENDING status badges and fill_price',
          'Batch quote endpoint GET /market/quotes?symbols=... for full portfolio LTP refresh in one call',
          'Notes page [03]: tagged developer notes saved to localStorage (⌘+Enter to save), filter by tag',
          'About page [04]: architecture diagram, version history, patch notes',
          '4-tab navigation in topbar: portfolio · wallet · notes · about',
          'trade_id now generated as UUID, persisted in trades_{id}.json, used for dedup and traceability',
        ]
      }
    ]
  },
  {
    version: 'v10.0.0',
    date: '2026-04-14',
    title: 'Day 10 — Live Market Integration & Developer Terminal UI',
    changes: [
      {
        category: 'FEAT',
        items: [
          'Live price integration via yfinance — all NSE & US stocks fetch real-time LTP from Yahoo Finance',
          'MarketProvider rewritten as a Singleton with 60-second TTL cache to prevent rate-limiting',
          'Developer Two-Page UI: [01] Portfolio Terminal & [02] Wallet Terminal',
          'Step-by-step Dev Inspector on every action: HTTP → API Router → Handler → Domain → Storage → Response',
          'Dev Inspector shows exact command, layer traversal, file written, and idempotency key',
        ]
      },
      {
        category: 'FIX',
        items: [
          'Trade.timestamp bug: field(default=datetime.now) was a method reference, not a call. Fixed to default_factory=datetime.now',
          'Unknown symbol for non-hardcoded NSE stocks (LT, ZOMATO): MarketProvider now tries SYMBOL.NS first, then bare SYMBOL',
          'Portfolio table not updating after buy: frontend wasn\'t marking order_status=REJECTED as an error',
        ]
      },
      {
        category: 'ARCH',
        items: [
          'CQRS fully implemented: Commands (POST write-side) separated from Queries (GET read-side)',
          'Event Sourcing: Wallet balance derived 100% by replaying immutable wallet_events_{id}.json',
          'Idempotency: every command uses X-Transaction-ID — safe to retry without double-processing',
          'All state persisted to data/*.json — survives server restarts',
        ]
      }
    ]
  },
  {
    version: 'v9.0.0',
    date: '2026-03-29',
    title: 'Day 9 — History, Timeline & Observability Layer',
    changes: [
      {
        category: 'FEAT',
        items: [
          'HistoryService: unified chronological timeline merging wallet events + orders + trades',
          'GET /history/portfolio/{id}/trades — trade history with pagination and symbol filter',
          'GET /history/portfolio/{id}/orders — order lifecycle history (PENDING/FILLED/REJECTED)',
          'GET /history/wallet/{id}/events — full ledger audit trail',
          'Trade persistence: save_trade() + load_trades() added to storage.py',
        ]
      }
    ]
  },
  {
    version: 'v8.0.0',
    date: '2026-03-22',
    title: 'Day 8 — Order Management System (OMS)',
    changes: [
      {
        category: 'FEAT',
        items: [
          'OrderExecutionEngine: validates and executes MARKET, LIMIT, STOP_LOSS orders',
          'Full order lifecycle: PENDING → FILLED / REJECTED / CANCELLED',
          'Order persistence: save_order() + load_orders() in storage.py',
          'POST /portfolio/{id}/buy and /sell now go through the engine with rejection messages surfaced to UI',
        ]
      }
    ]
  }
];

const CAT_COLORS = {
  FEAT: 'var(--green)',
  FIX:  'var(--red)',
  ARCH: 'var(--purple)',
};

export default function AboutPage() {
  const [expanded, setExpanded] = useState({
    'v10.4.0': true,
    'v10.3.0': true,
    'v10.2.0': false,
    'v10.1.0': false,
  });

  const toggle = (v) => setExpanded(prev => ({ ...prev, [v]: !prev[v] }));

  return (
    <div className="page-body" style={{ overflowY: 'auto' }}>
      <div className="main-scroll" style={{ padding: '14px' }}>

        {/* Header */}
        <div className="sec-label">
          <span className="sec-label-dot" style={{ background: 'var(--cyan)' }} />
          about_quantnest // version_history &amp; patch_notes
          <span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: '0.67rem', color: 'var(--muted)' }}>
          current: v10.4.0 · 2026-04-16
          </span>
        </div>

        {/* Architecture */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '6px', padding: '14px', marginBottom: '14px' }}>
          <div style={{ color: 'var(--blue)', fontFamily: 'var(--mono)', fontWeight: 700, marginBottom: '10px', fontSize: '0.8rem' }}>// SYSTEM ARCHITECTURE</div>
          <pre style={{ fontFamily: 'var(--mono)', fontSize: '0.72rem', color: 'var(--text)', lineHeight: 1.8, margin: 0, whiteSpace: 'pre-wrap' }}>{`
┌──────────────────────────────────────────────────────────────┐
│  React Frontend (Vite)                                        │
│  PortfolioPage · WalletPage · NotesPage · AboutPage          │
│  DevConsole: full request→response trace on every action     │
├──────────────────────────────────────────────────────────────┤
│  FastAPI Backend                                              │
│  api/portfolio.py  api/history.py  api/market.py             │
├──────────────────────────────────────────────────────────────┤
│  Application Layer (CQRS)                                     │
│  Commands (Write): BuyAsset, SellAsset, Credit, Debit        │
│  Queries  (Read):  PortfolioService, HistoryService          │
├──────────────────────────────────────────────────────────────┤
│  Domain Layer (Pure Business Logic, zero I/O)                 │
│  Wallet · Portfolio · OrderExecutionEngine · Trade           │
│  MarketProvider (Singleton, 60s TTL cache)                   │
├──────────────────────────────────────────────────────────────┤
│  Infrastructure                                               │
│  storage.py → data/*.json          yfinance → Yahoo Finance  │
│  yf.Search() → live symbol search  period escalation: 5d→3mo │
└──────────────────────────────────────────────────────────────┘

Key Patterns:
  Event Sourcing  → Wallet.balance = replay(wallet_events_{id}.json)
  CQRS            → POST commands strictly separate from GET queries
  Idempotency     → X-Transaction-ID prevents double-execution on retry
  Singleton Cache → MarketProvider._cache[symbol] valid for 60 seconds
  Period Escalation → 5d → 1mo → 3mo handles weekends & market holidays
`.trim()}</pre>
        </div>

        {/* Live Data Flow Summary */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--blue)', borderRadius: '6px', padding: '12px', marginBottom: '14px' }}>
          <div style={{ color: 'var(--blue)', fontFamily: 'var(--mono)', fontWeight: 700, marginBottom: '8px', fontSize: '0.75rem' }}>// LIVE DATA FLOW — SEARCH → QUOTE → TRADE</div>
          <pre style={{ fontFamily: 'var(--mono)', fontSize: '0.7rem', color: 'var(--text)', lineHeight: 1.7, margin: 0, whiteSpace: 'pre-wrap' }}>{`
[Search]   User types "reliance"
           → GET /market/search?q=reliance
           → yf.Search("reliance", news_count=0).quotes
           → Filters EQUITY/ETF types, strips .NS/.BO suffix
           → Returns { symbol, name, exchange, yf_symbol }

[Quote]    User clicks RELIANCE (NSE)
           → GET /market/quote/RELIANCE
           → yf.Ticker("RELIANCE.NS").history(period="5d")  ← escalates if empty
           → Extracts: LTP=Close[-1], prev_close=Close[-2], H/L/O/V
           → Returns: ltp, change, change_pct, volume, 52w_high, market_cap

[Buy]      User enters qty=5, clicks BUY
           → POST /portfolio/{id}/buy { symbol, quantity }
           → BuyAssetHandler.handle(cmd)
           → OrderExecutionEngine._validate_buy (checks cash ≥ cost)
           → MarketProvider.get_price() → cache hit or yfinance fetch
           → Wallet.debit(cost, tx_id) → FundsDebited event → wallet_events.json
           → Trade(trade_id, symbol, side, qty, price, timestamp) → trades.json
           → Positions updated → positions.json
           → Order written with FILLED status → orders.json
`.trim()}</pre>
        </div>

        {/* How to add patch notes guide */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--green)', borderRadius: '6px', padding: '12px', marginBottom: '14px' }}>
          <div style={{ color: 'var(--green)', fontFamily: 'var(--mono)', fontWeight: 700, marginBottom: '8px', fontSize: '0.75rem' }}>// HOW TO ADD YOUR OWN PATCH NOTE</div>
          <pre style={{ fontFamily: 'var(--mono)', fontSize: '0.7rem', color: 'var(--text)', lineHeight: 1.8, margin: 0, whiteSpace: 'pre-wrap' }}>{`
File to edit:  frontend/src/AboutPage.jsx

Step 1 — Open the file. The PATCH_NOTES array starts at line 3.

Step 2 — Copy this template and paste it at the TOP of the array
          (newest patches go first):

  {
    version: 'v10.5.0',          ← bump the last number for a bug fix
    date: '2026-04-17',          ← today's date YYYY-MM-DD
    title: 'Day X — What changed',
    changes: [
      {
        category: 'FEAT',        ← FEAT (green) | FIX (red) | ARCH (purple)
        items: [
          'Description of what you added or fixed',
          'Another bullet point if needed',
        ]
      },
    ]
  },

Step 3 — Update the version label in two places:
    · Line ~172:  current: v10.5.0 · 2026-04-17
    · The expanded state object (~line 157): add 'v10.5.0': true

Step 4 — Save the file. Vite hot-reloads — no server restart needed.
          The new patch note appears instantly at the top of the list.

Version numbering guide:
  v10.4.0 → v10.4.1   tiny fix or text change
  v10.4.0 → v10.5.0   new feature
  v10.4.0 → v11.0.0   major architectural change
`.trim()}</pre>
        </div>

        {/* Patch Notes */}
        {PATCH_NOTES.map(patch => (
          <div key={patch.version} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '6px', marginBottom: '10px', overflow: 'hidden' }}>
            {/* Collapsible Header */}
            <div
              onClick={() => toggle(patch.version)}
              style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px', cursor: 'pointer', borderBottom: expanded[patch.version] ? '1px solid var(--border)' : 'none' }}
            >
              <span className="badge badge-b">{patch.version}</span>
              <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, color: 'var(--text)', fontSize: '0.8rem' }}>{patch.title}</span>
              <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontFamily: 'var(--mono)', fontSize: '0.67rem', color: 'var(--muted)' }}>{patch.date}</span>
                <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{expanded[patch.version] ? '▲' : '▼'}</span>
              </span>
            </div>

            {/* Body */}
            {expanded[patch.version] && (
              <div style={{ padding: '10px 14px' }}>
                {patch.changes.map(c => (
                  <div key={c.category} style={{ marginBottom: '10px' }}>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: '0.67rem', color: CAT_COLORS[c.category] || 'var(--muted)', marginBottom: '5px', fontWeight: 700, letterSpacing: '0.5px' }}>
                      [{c.category}]
                    </div>
                    {c.items.map((item, i) => (
                      <div key={i} style={{ fontFamily: 'var(--mono)', fontSize: '0.74rem', color: 'var(--text)', paddingLeft: '12px', marginBottom: '4px', lineHeight: 1.6, borderLeft: `2px solid ${CAT_COLORS[c.category]}22` }}>
                        · {item}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        <div style={{ fontFamily: 'var(--mono)', fontSize: '0.63rem', color: 'var(--muted)', marginTop: '10px', textAlign: 'center' }}>
          QuantNest DevTool v10.4.0 · For development and debugging only · Not for production use
        </div>
      </div>
    </div>
  );
}
