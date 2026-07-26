# QuantNest Overhaul — Audit & Proposal

**Status:** Proposal — awaiting sign-off before implementation
**Branch:** `arena/019f9e13-quantnest`
**Baseline commit:** `6ea5ead`

---

## 1. Audit: current state

### 1.1 `frontend/src/PortfolioPage.jsx` — 603 lines

| Metric | Count | Note |
|---|---|---|
| Lines | 603 | Single default-export component |
| `useState` calls | 15 | No grouping, no reducer, no derived-state memoisation |
| Inline `style={{…}}` | 47 | Colours, spacing, font sizes hardcoded at call sites |
| Lines of `devLog` tracing | ~46 | Narration strings interleaved with business logic |
| `useEffect` | 4 | One is a raw `setInterval` polling loop with a stale-closure risk |

**Concrete problems found:**

1. **Data fetching is hand-rolled and racy.** `fetchPortfolio` fires three `fetch`es via `Promise.all`, then conditionally kicks off a *fourth* (`fetchBatchQuotes`) from inside the `.then`. Nothing is cancelled on unmount or on `walletId` change. Switching wallets mid-flight lets a stale response overwrite fresh state.
2. **The search debounce leaks.** `searchTimer` is cleared on the next keystroke but never in a cleanup function, and the in-flight `fetch` is never aborted — a slow response for `"IN"` can land after `"INFY"` and repopulate the dropdown.
3. **A 60s `setInterval` re-creates itself** on every `selectedStock`/`loadQuote` identity change (lines 168–172), so quote polling can double up.
4. **Business math lives in the render body.** `holdings`, `totalInvested`, `totalCurVal`, `totalPnL`, `totalDayPnL`, `hasAllInvested`… (lines 233–276) recompute on every keystroke in the qty box. None of it is unit-testable.
5. **Errors are strings in a banner.** `showAlert('err', String(e))` renders raw `Error: …` text. `quote.error` is stuffed into the quote object itself, so an error is modelled as data.
6. **Loading states are jarring text.** `⟳ loading…`, `⟳ fetching INFY.NS…`, `Loading chart data...` — no skeletons; layout jumps when data lands.
7. **No error boundary anywhere.** One thrown render error blanks the whole app.

### 1.2 `frontend/src/App.css` — 637 lines

The stylesheet is a flat, **fully global** namespace — `.badge`, `.up`, `.down`, `.empty`, `.alert`, `.sym`, `.chg`, `.ltp` are all top-level classes with no scoping. Any new component risks a collision.

**What makes it read as "tacky":**

- **Terminal cosplay over a finance product.** `// market_terminal`, `// wallet_actions`, `// add_funds [ credit ]`, tab labels `[01] portfolio` / `[02] wallet`, `> search NSE stock above`, `↺ refresh`, `[+]` / `[−]`, `⟳`, `✕`, `※ market closed`, `ⓘ`, `⚠`, and arrow glyphs `→ ← ✗` used as UI chrome. Table headers are `snake_case`: `avg_cost`, `cur_val`, `p&l`, `net_chg%`, `day_chg%`.
- **Monospace everywhere.** `JetBrains Mono` is applied to nav tabs, labels, buttons, badges, table cells and body copy. Monospace is right for *numbers* and *logs*; on labels and prose it reads as a dev tool, not a product.
- **Base font is 13px** with `line-height: 1.5` and cramped padding — everything feels dense and small.
- **No spacing system.** 25 distinct `padding` values (`3px 7px`, `2px 6px`, `4px 14px`, `7px 10px`, `6px 12px`, `10px 16px`, `2rem 1rem`…). Nothing sits on a grid.
- **Saturated GitHub-dark palette used at full strength.** `--blue: #58a6ff` on symbols, `--purple: #bc8cff`, `--cyan: #39d353`, `--yellow: #d29922` — four accent hues competing in one table. Buttons invert to solid `--green`/`--red` on hover, which is loud.
- **Transitions are `0.1s` linear or absent.** No easing curve, no hover elevation, no focus-visible ring.
- **`TradingChart.jsx` ignores the theme entirely** — it hardcodes `#151515`, `#2B2B2B`, `#333`, `#26a69a`, `#ef5350`, `#4caf50`, so the chart is visibly a different product from the panel around it.

### 1.3 Backend

**The DDD boundary is already broken.** This is the most important finding, because the brief says the domain must stay pure:

```
quantnest/domain/wallet.py:8       from quantnest.infra.storage import load_events, append_event
quantnest/domain/portfolio.py:10   from quantnest.infra.storage import load_positions, save_positions, …
quantnest/domain/order_engine.py:12 from quantnest.infra.storage import load_orders, save_order, append_order
quantnest/domain/market.py:7       import yfinance as yf          ← network I/O inside the domain
```

Entities persist *themselves* by calling module-level functions that do `Path("data/…").write_text()`. There is no seam to swap in a database.

**Other issues:**

| Issue | Count / location |
|---|---|
| `raise HTTPException(500, detail=str(e))` — leaks internals | 13 across `api/` |
| Exception classification by string-sniffing the type name (`"InsufficientFundsError" in str(type(e))`) | 3 in `api/portfolio.py` |
| `print()` used as logging | 21 across `api/market.py`, `domain/market.py`, `main.py`, `domain_demo.py` |
| Pydantic v1 idioms (`.dict()`, `class Config`) on Pydantic v2 | 5 + 5 |
| Services instantiated inside route handlers (`PortfolioService()`, `HistoryService()`, `OrderExecutionEngine()`) | every endpoint |
| `MarketProvider` is a process-wide mutable singleton (`__new__` + `_cache`) | `domain/market.py` |
| `POST /orders/` takes `symbol`, `side`, `quantity` as **query params**, not a body | `api/orders.py` |
| No validation on ticker format; `quantity: float` allows `0.0001` shares | `api/portfolio.py` |

**Tests: 18 pass, 3 fail — already red on `main`.**

```
FAILED tests/unit/domain/test_portfolio.py::test_portfolio_unknown_symbol
FAILED tests/unit/domain/test_portfolio_analytics.py::test_total_value_and_allocations_change_with_price
FAILED tests/unit/domain/test_portfolio_analytics.py::test_unrealized_pnl_average_cost
```

All three fail for the *same root cause* as the DDD violation: the tests assume a deterministic in-memory market (`market._prices["RELIANCE"] = …`), but `MarketProvider` was rewritten to call yfinance with a hardcoded fallback dict named `_fallback_prices`. Introducing a `MarketDataProvider` port fixes the architecture **and** turns these three green.

> **Sandbox note:** outbound TLS to `query1.finance.yahoo.com` is blocked in this environment, so live quotes cannot be exercised here. I will add a `QUANTNEST_MARKET_PROVIDER=fake|yfinance` switch so the core loop (search → quote → trade → portfolio) is verifiable offline and in CI. This is also what makes the three failing tests deterministic.

---

## 2. Proposed design system

### 2.1 Approach

**Design tokens in one global `tokens.css` + per-component CSS Modules (`*.module.css`).**

Vite supports CSS Modules with zero configuration, so this adds **no new dependency** and gives real scoping — `HoldingsTable.module.css` can define `.row` without any risk of colliding with `OrderEntry.module.css`. Tokens stay global so theming is one file. (Tailwind is a viable alternative — see the questions at the end.)

### 2.2 Colour — "deep charcoal", layered neutrals, muted semantics

```css
/* Neutral ramp — elevation by lightness, not by border */
--surface-canvas:  #0e0f11;   /* app background        */
--surface-raised:  #141517;   /* cards, panels         */
--surface-overlay: #1a1c1f;   /* table header, dropdown*/
--surface-hover:   #212428;   /* row hover             */
--border-subtle:   #212427;   /* row dividers          */
--border-default:  #2b2f34;   /* card outlines         */
--border-strong:   #3a3f45;   /* inputs, focus         */

/* Text — 3 levels only */
--text-primary:    #e8eaed;
--text-secondary:  #9aa0a6;
--text-tertiary:   #6b7178;

/* Semantic — muted, exactly as briefed */
--profit:          #3fb950;
--profit-surface:  rgba(63,185,80,0.10);
--loss:            #f85149;
--loss-surface:    rgba(248,81,73,0.10);
--warning:         #d29922;
--warning-surface: rgba(210,153,34,0.10);

/* ONE accent — used only for focus, active nav, primary CTA */
--accent:          #4f7fff;
--accent-surface:  rgba(79,127,255,0.12);
```

Key changes from today: **one** accent hue instead of four (blue + purple + cyan + yellow all retired as decoration); profit/loss reserved strictly for P&L numbers, never for buttons or symbols; elevation communicated by surface lightness rather than by drawing a border on everything.

### 2.3 Typography

| Token | Value | Used for |
|---|---|---|
| `--font-sans` | `Inter, -apple-system, "Segoe UI", sans-serif` | All UI, labels, prose |
| `--font-mono` | `"JetBrains Mono", ui-monospace, monospace` | **Dev Console only** |
| `--text-xs` | 11px / 1.45 | Overline labels (uppercase, `letter-spacing: .06em`) |
| `--text-sm` | 12.5px / 1.5 | Table cells, secondary text |
| `--text-base` | 14px / 1.55 | Body (**up from 13px**) |
| `--text-md` | 16px / 1.4 | Card values, section titles |
| `--text-lg` | 20px / 1.3 | KPI values |
| `--text-xl` | 30px / 1.15 | Quote LTP hero |

**The single most important typographic rule for this app:**

```css
.numeric {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1, "case" 1;
  text-align: right;
  font-family: var(--font-sans);   /* Inter has excellent tabular figures */
}
```

Inter's tabular figures give perfect column alignment **without** monospace, so numbers line up while the UI still reads as a product. Every price, quantity, percentage and currency cell right-aligns; every label and symbol left-aligns. Columns get a `min-width` so digits don't jitter as live prices poll.

Table headers move from `avg_cost` / `p&l` / `net_chg%` → `Avg Cost` / `P&L` / `Net Chg.` — sentence case, no snake_case, no `%` in the header (it goes on the value).

### 2.4 Spacing, radius, elevation, motion

```css
--space-1: 4px;   --space-2: 8px;   --space-3: 12px;  --space-4: 16px;
--space-5: 20px;  --space-6: 24px;  --space-8: 32px;  --space-10: 40px;

--radius-sm: 6px; --radius-md: 8px; --radius-lg: 12px; --radius-full: 999px;

--shadow-sm: 0 1px 2px rgba(0,0,0,.30);
--shadow-md: 0 4px 12px rgba(0,0,0,.35);
--shadow-lg: 0 12px 32px rgba(0,0,0,.45);

--ease:        cubic-bezier(.22,.61,.36,1);
--duration-1:  120ms;   /* hover, colour   */
--duration-2:  180ms;   /* elevation, tabs */
--duration-3:  240ms;   /* toasts, panels  */
```

Everything lands on a 4px grid — replacing the 25 ad-hoc padding values. Card padding standardises at `--space-5`; table cell padding at `--space-3 --space-4`; page gutter at `--space-6`.

### 2.5 Micro-interactions

- **Rows:** background → `--surface-hover` over `--duration-1`; a 2px `--accent` left rail slides in on the active row.
- **Buttons:** `translateY(-1px)` + `--shadow-md` on hover; `translateY(0)` on `:active`; `:focus-visible` ring `0 0 0 3px var(--accent-surface)`. No colour inversion.
- **Live prices:** brief `--profit-surface` / `--loss-surface` background flash on tick change, fading over 600ms (the standard broker "price flash"), respecting `prefers-reduced-motion`.
- **Skeletons:** `<Skeleton />` primitive with a 1.6s shimmer, replacing every `⟳ loading…`. Skeleton rows match real row height so nothing reflows.
- **Toasts:** slide-in from bottom-right, auto-dismiss 5s, stacked, `role="status"`.

### 2.6 Iconography

`lucide-react` is **already a dependency but almost unused**. Replace the glyph soup (`↺ ✕ ⟳ ▲ ▼ ⚠ ⓘ ※ [+] [−] → ← ✗`) with `RefreshCw`, `X`, `TrendingUp`, `TrendingDown`, `AlertTriangle`, `Info`, `ChevronDown`, `Search`, `Maximize2` at a consistent `16px` / `1.5px` stroke.

---

## 3. Proposed component breakdown

`PortfolioPage.jsx` goes from **603 lines → ~110 lines** of pure layout composition.

```
frontend/src/
├── main.jsx
├── App.jsx                              ← shell + page switch only
├── styles/
│   ├── tokens.css                       ← §2.2–2.4, the whole theme
│   └── base.css                         ← reset, body, scrollbars, focus-visible
│
├── components/ui/                       ← design-system primitives
│   ├── Button.jsx        + .module.css  ← variant: primary|secondary|ghost|buy|sell
│   ├── Card.jsx          + .module.css
│   ├── Badge.jsx         + .module.css  ← tone: profit|loss|neutral|warning|info
│   ├── Skeleton.jsx      + .module.css  ← text | row | card
│   ├── DataTable.jsx     + .module.css  ← <Table><Th numeric><Td numeric>
│   ├── Tabs.jsx          + .module.css
│   ├── Input.jsx         + .module.css
│   ├── EmptyState.jsx    + .module.css
│   ├── Toast.jsx         + .module.css
│   └── ErrorBoundary.jsx
│
├── components/layout/
│   ├── AppShell.jsx                     ← topbar + sidebar + content grid
│   ├── TopBar.jsx                       ← brand, nav, wallet picker, status
│   └── MarketClock.jsx                  ← moved from src/, styles → tokens
│
├── components/portfolio/
│   ├── SummaryCards.jsx                 ← 5 KPI cards (Invested/Current/P&L/Day P&L/Cash)
│   ├── HoldingsTable.jsx                ← table + skeleton + empty state
│   ├── HoldingRow.jsx                   ← one row, memoised
│   ├── HoldingsTotalsRow.jsx            ← the null-safe totals footer
│   └── HistoryPanel.jsx                 ← Tabs → TradesTable | OrdersTable
│       ├── TradesTable.jsx
│       └── OrdersTable.jsx
│
├── components/trade/
│   ├── OrderTicket.jsx                  ← container: Search + Quote + Chart + Entry
│   ├── SymbolSearch.jsx                 ← debounced + abortable + keyboard nav
│   ├── QuoteCard.jsx                    ← LTP hero, change pill, OHLC/52w meta grid
│   └── OrderEntry.jsx                   ← Buy/Sell tabs, qty, presets, cost, submit
│
├── components/chart/
│   └── TradingChart.jsx                 ← KEPT; colours read from CSS custom properties
│
├── components/dev/
│   └── DevConsole.jsx                   ← see question 4
│
├── hooks/
│   ├── usePortfolioSummary.js           ← useQuery
│   ├── useBatchQuotes.js                ← useQuery + refetchInterval, market-hours aware
│   ├── useQuote.js
│   ├── useSymbolSearch.js               ← debounced query key, auto-cancelling
│   ├── useTradeHistory.js
│   └── useTradeMutation.js              ← useMutation + invalidate + toast
│
├── lib/
│   ├── apiClient.js                     ← base URL from env, ApiError class, timeout
│   ├── format.js                        ← inr(), pct(), qty(), compactCr(), signed()
│   └── portfolioMath.js                 ← PURE: buildHoldings(), computeTotals()
│
└── stores/
    └── useSessionStore.js               ← zustand: walletId, selectedSymbol, tradeSide
```

**Why this split:** each file has one reason to change. `portfolioMath.js` is pure and unit-testable (it currently lives in a render body). `apiClient.js` is the only place that knows the backend URL — today `http://localhost:8000` is hardcoded in three separate files (`PortfolioPage.jsx`, `WalletPage.jsx`, `TradingChart.jsx`), which is why it must move to `VITE_API_URL`.

### State ownership

| State | Owner |
|---|---|
| `walletId`, `selectedSymbol`, `tradeSide`, qty draft | **Zustand** (`useSessionStore`) |
| portfolio summary, quotes, search, trades, orders | **TanStack Query** (cache + polling + dedup + cancellation) |
| toasts | **Context** (`ToastProvider`) |
| purely local UI (`collapsed`, `historyTab`) | `useState` in the leaf component |

This replaces the 15-`useState` chain and removes the manual polling, debouncing and race handling entirely — TanStack Query's `refetchInterval` + query-key cancellation solve all three correctly.

---

## 4. Proposed backend plan

Sequenced after the frontend, per the brief.

**Phase B1 — Ports (restores DDD purity, fixes the 3 red tests)**
`domain/ports.py` defines `typing.Protocol` interfaces: `EventStore`, `PositionRepository`, `TradeRepository`, `OrderRepository`, `MarketDataProvider`. `Wallet`, `Portfolio` and `OrderExecutionEngine` receive them via constructor injection instead of importing `infra.storage`. Domain imports drop to stdlib only.

**Phase B2 — SQLAlchemy 2.0 persistence**
`infra/db/models.py` (`wallet_events`, `positions`, `trades`, `orders` — `Numeric(20,4)` for money, not float), `infra/db/session.py` (engine factory driven by `DATABASE_URL`, defaulting to `sqlite:///./quantnest.db`), `infra/db/repositories/*.py` implementing the ports, plus a Unit-of-Work wrapping one transaction per command so a buy is atomic. PostgreSQL becomes a `DATABASE_URL` change.

**Phase B3 — Data migration**
`scripts/migrate_json_to_db.py` — idempotent, reads the existing `data/*.json` (9 wallets), writes to SQLite, leaves the JSON untouched as a backup.

**Phase B4 — DI**
`api/deps.py`: `get_session`, `get_market_provider`, `get_portfolio_service`, `get_order_engine` as FastAPI `Depends`. Route handlers stop calling `PortfolioService()`. Overridable in tests via `app.dependency_overrides`.

**Phase B5 — Errors**
`domain/exceptions.py` hierarchy → registered `@app.exception_handler`s → RFC 9457 `application/problem+json` with `type`, `title`, `status`, `detail`, `request_id`. A catch-all handler logs the traceback server-side and returns a generic 500 body. The 13 `detail=str(e)` sites and the 3 `str(type(e))` sniffs are deleted.

**Phase B6 — Logging**
`infra/logging.py`: JSON formatter (`timestamp`, `level`, `logger`, `message`, `request_id`, extras), `LOG_LEVEL`/`LOG_FORMAT` env-driven (`json` in prod, pretty in dev). Middleware assigns a `request_id`, logs method/path/status/duration_ms. All 21 `print()` calls replaced.

**Phase B7 — Validation**
Ticker `constr(pattern=r"^[A-Z][A-Z0-9&.\-]{0,19}$")` with an uppercasing validator; quantity `condecimal(gt=0, max_digits=18, decimal_places=4)`; amounts `gt=0` with a sane cap; `X-Transaction-ID` validated as a UUID; `POST /orders/` moved from query params to a request body model.

---

## 5. Verification strategy

The core loop — **search → quote → trade → updated portfolio** — is re-checked after every phase:

- **Backend:** `pytest` (the 3 red tests must go green and stay green) + new repository/API integration tests against an in-memory SQLite and the fake market provider.
- **Frontend:** `npm run build` + `npm run lint` after each phase; a smoke script drives the real API loop end-to-end against `QUANTNEST_MARKET_PROVIDER=fake`.
- Each phase is a separate commit, so any step can be reverted independently.

---

## 6. Open questions

See the four questions posed alongside this document.
