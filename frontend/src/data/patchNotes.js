/**
 * Release history for the About page.
 *
 * Extracted from AboutPage.jsx so the page component stays presentational.
 *
 * To add an entry, prepend an object to this array:
 *   { version, date, title, changes: [{ category: 'FEAT'|'FIX'|'ARCH', items: [...] }] }
 */

export const PATCH_NOTES = [
  {
    version: 'v11.3.0',
    date: '2026-07-28',
    title: 'Security Audit — Closed an Authorisation Bypass',
    changes: [
      {
        category: 'FIX',
        items: [
          'CRITICAL: POST /orders accepted unauthenticated requests and let any signed-in user trade on any wallet. It takes wallet_id in the request body, so it never passed through the path-based dependency that secures every other wallet route',
          'The endpoint now requires a bearer token and verifies ownership explicitly before placing the order',
          'The frontend now signs you out when a token refresh fails, instead of leaving you on a dashboard where every request silently errors — this is what you would hit after signing out from another device',
        ],
      },
      {
        category: 'ARCH',
        items: [
          'Added a route-table security audit: it walks every documented endpoint and fails the build if any accepts a caller-supplied wallet id without checking ownership. Thirty-three auth tests passed while the bypass was live, because each only covered a route someone had remembered to secure',
          'The audit parses each handler AST and strips docstrings, after an earlier version was fooled by a docstring merely mentioning authorize_wallet. Verified by reintroducing the vulnerability and confirming the test fails',
          'Removed infra/storage.py — dead code at 0% coverage with no remaining references after the SQL migration',
          'Tests grew from 146 to 169 (134 backend, 35 frontend)',
        ],
      },
    ],
  },
  {
    version: 'v11.2.0',
    date: '2026-07-28',
    title: 'Token Revocation, Rate Limiting & CI',
    changes: [
      {
        category: 'FEAT',
        items: [
          'Sign-out now genuinely revokes the token server-side. Previously a stateless JWT stayed valid until it expired, so signing out was cosmetic',
          'Sign out everywhere: one per-user cutoff invalidates every session at once, rather than one record per token',
          'Refresh-token rotation: redeeming a refresh token revokes it, so a leaked token is useless once the real client has used it',
          'Rate limiting on the auth endpoints — 10 login attempts per 5 minutes, 5 registrations per hour, answered with 429 and a Retry-After header',
          'A successful login clears the throttle, so one user fumbling a password cannot lock out everyone behind the same NAT address',
          'GitHub Actions CI: backend tests on Python 3.11 and 3.12, frontend lint/test/build, and a Docker job that boots the image and exercises it',
        ],
      },
      {
        category: 'FIX',
        items: [
          'Signing back in immediately after "sign out everywhere" was locked out: JWT iat is integer epoch seconds while the cutoff had microsecond precision, so a newer token compared as older. A successful password login now clears the cutoff',
        ],
      },
      {
        category: 'ARCH',
        items: [
          'TokenBlocklist added as a domain port with SQL and in-memory adapters; a Redis implementation would satisfy the same interface',
          'scripts/check_architecture.py parses the AST to enforce the DDD boundary in CI, allowing deliberate lazy imports inside function bodies while rejecting module-level ones',
          'Tests grew from 128 to 146 (118 backend, 28 frontend)',
        ],
      },
    ],
  },
  {
    version: 'v11.1.0',
    date: '2026-07-27',
    title: 'Authentication, Wallet Ownership & Docker',
    changes: [
      {
        category: 'FEAT',
        items: [
          'JWT authentication: register and sign in for a 30-minute access token plus a 7-day refresh token, refreshed transparently by the API client',
          'Per-user wallet ownership: a wallet_ownership table binds every wallet to an account, and each user can hold several wallets',
          'Sign-in and registration screen; the dashboard is gated until a session exists, and signing out clears the query cache',
          'Docker: multi-stage API and frontend images plus a compose file, with PostgreSQL behind an optional profile',
        ],
      },
      {
        category: 'FIX',
        items: [
          'Closed a real vulnerability: any caller could previously read or trade ANY wallet by editing the URL. Every wallet-scoped route now verifies ownership and returns 403 otherwise',
          'Failed logins hash a dummy password so response time cannot reveal whether an account exists',
          'Unknown email and wrong password return identical 401s, preventing account enumeration',
          'A wallet you do not own and one that does not exist both return 403, preventing wallet enumeration',
          'pyjwt, passlib, bcrypt and pydantic[email] were missing from pyproject.toml — a clean install crashed on import, so the container would have failed at startup',
        ],
      },
      {
        category: 'ARCH',
        items: [
          'UserRepository, WalletOwnershipRepository, PasswordHasher and TokenService added as domain ports, so the domain still imports no crypto or ORM library',
          'JWT_SECRET_KEY is mandatory when ENVIRONMENT=production and must be at least 32 characters; development falls back to an ephemeral per-process key',
          'docs/PROJECT_WALKTHROUGH.md: a full guide to the architecture, request lifecycles, security design and trade-offs',
          'Tests grew from 87 to 128 (100 backend, 28 frontend), including cross-account isolation coverage',
        ],
      },
    ],
  },
  {
    version: 'v11.0.0',
    date: '2026-07-26',
    title: 'Production Overhaul — Design System, Modularisation & Robustness',
    changes: [
      {
        category: 'ARCH',
        items: [
          'Design tokens: single tokens.css defines the full palette, type scale, 4px spacing grid, radii, elevation and motion curves — replacing 637 lines of global CSS and 25 ad-hoc padding values',
          'CSS Modules throughout: every component owns a scoped *.module.css, eliminating the flat global class namespace (.badge, .up, .empty) that risked collisions',
          'PortfolioPage reduced from 603 lines to layout composition; split into SummaryCards, HoldingsTable, HoldingRow, HistoryPanel, OrderTicket, SymbolSearch, QuoteCard and OrderEntry',
          'Portfolio maths extracted to lib/portfolioMath.js as pure, testable functions — previously recomputed inline on every keystroke',
          'TanStack Query owns all server state: caching, market-hours-aware polling, request de-duplication and automatic cancellation',
          'Zustand session store replaces the 15-useState chain and prop-drilled walletId',
        ],
      },
      {
        category: 'FEAT',
        items: [
          'Sophisticated dark palette: deep charcoal surfaces, three text levels, one accent hue, muted #3fb950 / #f85149 reserved strictly for P&L',
          'Inter with tabular figures — numeric columns align perfectly without monospace; every price, quantity and percentage is right-aligned',
          'Loading skeletons sized to match real content replace the "⟳ loading…" text indicators, so the layout never reflows',
          'Toast notification system with an error-normalising fromError() helper, replacing alert() and inline error strings',
          'React error boundaries around each dashboard section so one failure cannot blank the app',
          'Developer inspector rebuilt on an event bus and hidden behind a top-bar toggle; tracing strings no longer live inside components',
          'Keyboard-navigable symbol search (arrow keys, Enter, Escape) with debounced, cancellable queries',
        ],
      },
      {
        category: 'FIX',
        items: [
          'Race condition: switching wallets mid-flight could let a stale response overwrite fresh state — queries are now keyed and cancelled',
          'Search dropdown could be repopulated by a slow response for an earlier term',
          'Quote polling could register duplicate 60s intervals when the selected stock changed',
          'API base URL was hardcoded in three files; now a single VITE_API_URL-driven client',
          'TradingChart hardcoded its own palette (#151515, #2B2B2B, #26a69a) and clashed with the UI; it now reads the theme tokens at runtime',
        ],
      },
    ],
  },
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
