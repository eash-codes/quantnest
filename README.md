# QuantNest

A trading simulator built with domain-driven design: a FastAPI backend over a
SQL event-sourced ledger, and a React dashboard for research and paper trading.

**JWT authentication**, per-user wallet ownership, and Docker deployment.

> **New here?** [`docs/PROJECT_WALKTHROUGH.md`](docs/PROJECT_WALKTHROUGH.md) is
> the complete guide — architecture, request lifecycles, security design,
> trade-offs and known limitations.

---

## Quick start

### Docker (everything at once)

```bash
cp .env.example .env
# set JWT_SECRET_KEY — generate with: openssl rand -hex 32
docker compose up --build
```

Frontend on `:5173`, API docs on `:8000/docs`.
Postgres instead of SQLite: `docker compose --profile postgres up --build`.

### Backend (local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# set JWT_SECRET_KEY — required in production, optional in development

python scripts/migrate_json_to_db.py       # one-off: data/*.json -> SQLite
python -m quantnest.main                   # http://localhost:8000/docs
```

No network? Use deterministic prices:

```bash
QUANTNEST_MARKET_PROVIDER=fake python -m quantnest.main
```

### Frontend

```bash
cd frontend
npm install
npm run dev                                # http://localhost:5173
```

---

## Configuration

Every setting is an environment variable; see `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | — | **Required in production**, min 32 chars |
| `ACCESS_TOKEN_TTL_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_TTL_DAYS` | `7` | Refresh token lifetime |
| `ENVIRONMENT` | `development` | `production` makes the secret mandatory |
| `DATABASE_URL` | `sqlite:///./quantnest.db` | Swap to `postgresql+psycopg://…` for Postgres |
| `QUANTNEST_MARKET_PROVIDER` | `yfinance` | `fake` for offline/CI deterministic pricing |
| `LOG_FORMAT` | `json` | `console` for readable local logs |
| `LOG_LEVEL` | `INFO` | Standard Python levels |
| `CORS_ORIGINS` | `http://localhost:5173,…` | Comma-separated allowed origins |
| `VITE_API_URL` *(frontend)* | `http://localhost:8000` | Backend base URL |

---

## Architecture

```
quantnest/
├── domain/            Pure business logic — stdlib only, no framework imports
│   ├── ports.py       Protocols: EventStore, *Repository, MarketDataProvider
│   ├── exceptions.py  DomainError hierarchy (mapped to HTTP at the edge)
│   ├── wallet.py      Event-sourced ledger; balance replayed from events
│   ├── portfolio.py   Positions, valuation, P&L, allocations, health signals
│   └── order_engine.py Validation, execution and the order lifecycle
│
├── application/       CQRS orchestration; no HTTP awareness
│   ├── commands/      Command DTOs
│   ├── handlers/      WalletCommandHandler, TradeCommandHandler
│   ├── portfolio_service.py
│   └── history_service.py
│
├── infra/             Adapters implementing the domain ports
│   ├── db/            SQLAlchemy models, session, repositories
│   ├── market.py      yfinance + deterministic providers
│   └── logging.py     JSON / console structured logging
│
└── api/               FastAPI presentation layer
    ├── deps.py        Dependency injection wiring
    ├── errors.py      RFC 9457 problem+json handlers
    └── schemas.py     Strict Pydantic v2 request/response models
```

**The dependency arrow points inwards.** The domain declares the capabilities it
needs as `typing.Protocol` ports; infrastructure supplies implementations; the
API injects them per request. `quantnest/domain/` imports nothing from
`infra`, `api`, SQLAlchemy, FastAPI, Pydantic or yfinance.

### Frontend

```
frontend/src/
├── styles/            tokens.css (the entire theme) + base.css
├── components/
│   ├── ui/            Button, Card, Badge, Skeleton, DataTable, Tabs,
│   │                  Input, EmptyState, Toast, ErrorBoundary
│   ├── layout/        AppShell, TopBar, MarketClock
│   ├── portfolio/     SummaryCards, HoldingsTable, HoldingRow, HistoryPanel
│   ├── trade/         OrderTicket, SymbolSearch, QuoteCard, OrderEntry
│   ├── chart/         TradingChart (Lightweight Charts v5)
│   └── wallet/, dev/
├── hooks/             TanStack Query data hooks + market-hours logic
├── lib/               apiClient, format, portfolioMath (pure), queryClient
├── stores/            Zustand session store
└── pages/             Portfolio, Wallet, Notes, About
```

Server state is owned by **TanStack Query** (caching, market-hours-aware
polling, de-duplication, automatic cancellation). UI session state lives in a
small **Zustand** store. Styling is **CSS Modules over design tokens** — one
`tokens.css` defines the palette, type scale, 4px spacing grid and motion.

---

## Design system

- **Surfaces** — deep charcoal (`#0e0f11` → `#26292e`); elevation by lightness, not borders.
- **Semantics** — muted `#3fb950` / `#f85149`, used *only* for P&L and status.
- **Accent** — a single hue (`#4f7fff`) for focus, active nav and primary actions.
- **Type** — Inter with `tabular-nums`, so numeric columns align without monospace. JetBrains Mono is reserved for the developer inspector.
- **Numbers** — every price, quantity and percentage is right-aligned with fixed-width digits.

---

## Testing

```bash
QUANTNEST_MARKET_PROVIDER=fake pytest -q     # 100 backend tests
cd frontend && npm test                      # 28 frontend tests
cd frontend && npm run lint
```

The suite is hermetic: an in-memory SQLite database and a deterministic market
provider mean no network access is required.

Coverage includes the wallet ledger (idempotency, replay, overdraft refusal),
portfolio analytics, the order engine (fills, rejections, limit orders,
cancellation), API integration across the full stack, authentication and
cross-account isolation, the pure P&L maths, and React render tests that mount
the real component tree.

## Authentication

Register, receive a wallet, and sign in for a JWT pair — a 30-minute access
token and a 7-day refresh token. Every wallet-scoped route checks ownership, so
one user can never read or trade another's wallet.

```bash
curl -X POST localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"at-least-8-chars"}'

curl localhost:8000/portfolio/<wallet_id>/summary \
  -H "Authorization: Bearer <access_token>"
```

See the [walkthrough](docs/PROJECT_WALKTHROUGH.md#6-authentication-and-authorisation)
for the security design and its trade-offs.

---

## Error handling

Every error is RFC 9457 `application/problem+json`:

```json
{
  "type": "insufficient_funds",
  "title": "Insufficient funds",
  "status": 409,
  "detail": "Cannot debit 99999999 from a balance of 285236.60",
  "instance": "/portfolio/demo-user/debit",
  "request_id": "2b12d989-962a-42cc-9e30-dd9db090d392"
}
```

Domain exceptions map to meaningful status codes (`400`, `404`, `409`, `422`);
anything unexpected is logged in full server-side and returned as a generic
`500`. Internal details never reach the client. The `request_id` correlates the
response with the structured logs.

---

## Data migration

`scripts/migrate_json_to_db.py` moves the legacy `data/*.json` files into SQL.
It is idempotent — re-running inserts nothing — and leaves the JSON untouched
as a backup.

```bash
python scripts/migrate_json_to_db.py --dry-run   # preview
python scripts/migrate_json_to_db.py             # apply
```

---

## Moving to PostgreSQL

```bash
pip install -e ".[postgres]"
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/quantnest"
python scripts/migrate_json_to_db.py
```

No model or query changes are required. Money columns are `Numeric`, never
`Float`, so values stay exact.
