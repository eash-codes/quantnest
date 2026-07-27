# QuantNest — Complete Project Walkthrough

> The single reference for understanding this codebase: what it does, how it is
> built, why each decision was made, and how to explain it under questioning.

**Version 11.1.0** · FastAPI + React · ~5,000 lines of Python, ~8,400 lines of
frontend · 128 automated tests

---

## Table of contents

1. [What QuantNest is](#1-what-quantnest-is)
2. [System overview](#2-system-overview)
3. [Architecture: DDD and why](#3-architecture-ddd-and-why)
4. [The backend, layer by layer](#4-the-backend-layer-by-layer)
5. [Event sourcing: the wallet ledger](#5-event-sourcing-the-wallet-ledger)
6. [Authentication and authorisation](#6-authentication-and-authorisation)
7. [The database layer](#7-the-database-layer)
8. [The API layer](#8-the-api-layer)
9. [The frontend](#9-the-frontend)
10. [The design system](#10-the-design-system)
11. [Request lifecycles end to end](#11-request-lifecycles-end-to-end)
12. [Testing strategy](#12-testing-strategy)
13. [Docker and deployment](#13-docker-and-deployment)
14. [Running it locally](#14-running-it-locally)
15. [Design decisions and trade-offs](#15-design-decisions-and-trade-offs)
16. [Known limitations](#16-known-limitations)
17. [Interview question bank](#17-interview-question-bank)
18. [File-by-file map](#18-file-by-file-map)

---

## 1. What QuantNest is

QuantNest is a **paper-trading simulator** for Indian equities (NSE). A user
registers, receives a wallet, credits virtual funds, searches for a stock, sees
a live quote and candlestick chart, and places market buy or sell orders. The
portfolio tracks positions, average cost, unrealised P&L, day P&L and
allocation, with a full audit trail of every order, trade and cash movement.

No real money and no real orders are involved. Prices are real (Yahoo Finance);
execution is simulated.

**What makes it interesting technically**, rather than just another CRUD app:

| Property | How it shows up |
|---|---|
| Event sourcing | Wallet balance is never stored — it is replayed from an immutable event log |
| Idempotency | Retrying a trade with the same transaction id cannot double-charge, enforced by a DB constraint |
| Hexagonal architecture | The domain layer imports only the standard library; everything external arrives through ports |
| Exact money arithmetic | `Decimal` end to end, `Numeric` columns — never `float` |
| Ownership authorisation | One dependency secures all 15 wallet-scoped routes |

---

## 2. System overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  BROWSER                                                            │
│  React 19 SPA · TanStack Query (server state) · Zustand (session)   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTPS · JWT bearer token
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FastAPI                                                            │
│  Request-ID middleware → CORS → auth dependency → route handler     │
│  Errors → RFC 9457 problem+json ·  Logs → structured JSON           │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ dependency injection (one txn per request)
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  APPLICATION   AuthService · PortfolioService · HistoryService       │
│                Command handlers (CQRS write side)                    │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ ports (typing.Protocol)
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  DOMAIN        Wallet · Portfolio · Order · Trade · User             │
│                OrderExecutionEngine · business rules                 │
│                ── imports stdlib only ──                             │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ implemented by
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  INFRASTRUCTURE                                                      │
│  SQLAlchemy repositories · bcrypt · PyJWT · yfinance · JSON logging  │
└───────────────────────────┬─────────────────────────────────────────┘
                            ▼
                 SQLite (dev) / PostgreSQL (prod)
```

### Stack

| Layer | Choice | Reason |
|---|---|---|
| Frontend | React 19 + Vite | Fast HMR, modern React features |
| Server state | TanStack Query v5 | Caching, polling, de-duplication, cancellation |
| UI state | Zustand v5 | ~1 KB, no provider tree |
| Styling | CSS Modules + tokens | Real scoping, zero runtime, no new dependency |
| Charts | Lightweight Charts v5 | TradingView's library, purpose-built for finance |
| Backend | FastAPI | Async, Pydantic validation, automatic OpenAPI |
| ORM | SQLAlchemy 2.0 | Mature, typed, database-portable |
| Auth | PyJWT + bcrypt | Stateless tokens, industry-standard KDF |
| Market data | yfinance | Free NSE and global coverage |

---

## 3. Architecture: DDD and why

The codebase follows **hexagonal architecture** (ports and adapters), the
practical form of domain-driven design.

### The one rule

> **Dependencies point inwards. The domain depends on nothing.**

```
   api  ──────▶  application  ──────▶  domain  ◀──────  infra
                                          ▲                │
                                          └── implements ──┘
                                              the ports
```

`quantnest/domain/` imports only the Python standard library. No FastAPI, no
SQLAlchemy, no Pydantic, no bcrypt, no yfinance. Verify it:

```bash
grep -rn "from quantnest.infra\|import yfinance\|fastapi\|sqlalchemy\|pydantic" quantnest/domain/*.py
```

The only match is a deliberate lazy import inside a function body in
`domain/market.py`, a backwards-compatibility shim — not a module-level
dependency.

### Why this matters

The domain layer expresses *business rules*: you cannot sell shares you do not
own; a wallet cannot go negative; average cost is quantity-weighted. Those
rules are true regardless of whether data lives in JSON, SQLite or Postgres, and
regardless of whether the interface is HTTP, a CLI or a message queue.

Mixing infrastructure into that layer means:
- you cannot test rules without a database,
- swapping storage means editing business logic,
- the rules become hard to find among the plumbing.

### Ports: how the domain stays pure

The domain declares what it needs as `typing.Protocol` classes in
`domain/ports.py`:

```python
@runtime_checkable
class EventStore(Protocol):
    def load_events(self, wallet_id: str) -> List["DomainEvent"]: ...
    def append_event(self, wallet_id: str, event: "DomainEvent") -> None: ...
```

`Protocol` gives **structural typing**: any class with matching methods
satisfies it, with no inheritance and no import from the domain. `infra` depends
on `domain`, never the reverse.

Each port has two implementations:

| Port | Production | Test / offline |
|---|---|---|
| `EventStore` | `SqlEventStore` | `InMemoryEventStore` |
| `PositionRepository` | `SqlPositionRepository` | `InMemoryPositionRepository` |
| `TradeRepository` | `SqlTradeRepository` | `InMemoryTradeRepository` |
| `OrderRepository` | `SqlOrderRepository` | `InMemoryOrderRepository` |
| `UserRepository` | `SqlUserRepository` | `InMemoryUserRepository` |
| `MarketDataProvider` | `YFinanceMarketDataProvider` | `StaticMarketDataProvider` |
| `PasswordHasher` | `BcryptPasswordHasher` | (real, low cost) |
| `TokenService` | `JwtTokenService` | (real, short TTL) |

That second column is why the test suite needs no network and no database file.

### This was fixed, not inherited

The original code violated the boundary in four places:

```python
# domain/wallet.py       → from quantnest.infra.storage import load_events
# domain/portfolio.py    → from quantnest.infra.storage import load_positions
# domain/order_engine.py → from quantnest.infra.storage import load_orders
# domain/market.py       → import yfinance
```

Entities persisted *themselves* by calling module-level functions that wrote
`Path("data/…").write_text()`. There was no seam for a database. Three tests
were failing on `main` for exactly this reason: they assumed an injectable price
table that no longer existed. Introducing the ports fixed the architecture and
those tests in one move.

---

## 4. The backend, layer by layer

### 4.1 Domain (`quantnest/domain/`)

| File | Contains |
|---|---|
| `wallet.py` | Event-sourced cash ledger |
| `portfolio.py` | Positions, valuation, P&L, allocations, health signals |
| `order.py` | `Order` entity and its lifecycle |
| `order_engine.py` | Validation and execution |
| `trade.py` | Immutable executed-trade record |
| `events.py` | `FundsCredited` / `FundsDebited` |
| `user.py` | `User` and wallet-ownership entities |
| `exceptions.py` | The `DomainError` hierarchy |
| `ports.py` | Protocol definitions + in-memory fakes |
| `market.py` | Lazy compatibility shim |

**Portfolio analytics** — every figure the dashboard shows:

```python
def avg_cost(self, symbol):
    """Quantity-weighted average across BUY trades only."""
    qty  = sum(t.quantity for t in self._trades if t.symbol == symbol and t.side == "BUY")
    cost = sum(t.quantity * t.price for t in self._trades if t.symbol == symbol and t.side == "BUY")
    return Decimal("0.00") if qty == 0 else _money(cost / qty)

def unrealized_pnl(self, symbol):
    """(current price − average cost) × quantity held."""
    qty = self._positions.get(symbol, Decimal("0"))
    if qty == 0:
        return Decimal("0.00")
    return _money((self._market.get_price(symbol) - self.avg_cost(symbol)) * qty)
```

`_money()` quantises to two decimal places with `ROUND_HALF_UP`. Money is
`Decimal` everywhere: `0.1 + 0.2 != 0.3` in binary floating point, which is
unacceptable in a ledger.

### 4.2 Application (`quantnest/application/`)

Implements **CQRS** — separate paths for writes and reads.

```
Write:  API → Command DTO → Handler → Domain → Repository
Read:   API → Query Service → Repository → DTO
```

Handlers coordinate; they contain no business rules of their own:

```python
class TradeCommandHandler:
    def _execute(self, command, side):
        order = self._engine.place_order(...)          # domain decides
        if order.is_rejected:
            return {"success": False, "message": order.rejection_reason}
        return {"success": True, "portfolio_summary": {...}}
```

A rejected order returns **HTTP 200 with `success: false`**, not an error status.
A rejection is a legitimate business outcome that produces a persisted,
auditable `Order` record — it is not a protocol failure.

### 4.3 Infrastructure (`quantnest/infra/`)

| File | Role |
|---|---|
| `db/models.py` | SQLAlchemy tables |
| `db/session.py` | Engine, session factory, SQLite pragmas |
| `db/repositories.py` | Port implementations |
| `market.py` | yfinance provider with a 60s cache |
| `security.py` | bcrypt + PyJWT |
| `logging.py` | JSON / console formatters |
| `storage.py` | Legacy shim, now DB-backed |

**Market data caching** — a 60-second in-process cache, thread-locked because
FastAPI serves from a thread pool:

```python
def get_price(self, symbol: str) -> Decimal:
    cached = self._read_cache(key)          # 60s TTL
    if cached is not None:
        return cached
    price = self._fetch_live(key)            # tries SYMBOL.NS, then SYMBOL
    if price is not None:
        self._write_cache(key, price)
        return price
    if key in self._fallback:                # keeps the sim usable offline
        return self._fallback[key]
    raise UnknownSymbolError(...)
```

It escalates `5d → 1mo → 3mo` because a 5-day window returns nothing across a
long weekend or holiday.

---

## 5. Event sourcing: the wallet ledger

**The wallet balance is never stored.** It is derived by replaying every event.

```python
def _replay_events(self) -> None:
    balance = Decimal("0")
    for event in self._events:
        amount = Decimal(event.payload["amount"])
        if event.event_type == "FundsCredited":
            balance += amount
        elif event.event_type == "FundsDebited":
            balance -= amount
    self._balance = balance
```

### Why

1. **Audit trail** — every movement is permanently recorded. For anything
   financial this is the point, not a bonus.
2. **Time travel** — replaying a prefix of the log yields the balance at any
   past moment.
3. **No drift** — a stored balance can disagree with its transaction history.
   A derived balance cannot.
4. **Debuggable** — "why is the balance 83,500?" is answered by reading the log.

### Idempotency

Every credit and debit carries a `transaction_id`. Replaying it is a no-op:

```python
def credit(self, amount, transaction_id=None):
    amount = self._validate_amount(amount)
    tx_id = transaction_id or str(uuid.uuid4())
    if self._already_processed(tx_id):
        return                                    # idempotent
    self._record(FundsCredited(amount=amount, transaction_id=tx_id))
```

Backed by a database constraint, so it holds even under concurrency:

```python
UniqueConstraint("wallet_id", "transaction_id", name="uq_wallet_transaction")
```

The frontend sends `X-Transaction-ID: <uuid>` on every mutating request. If the
network drops after the server commits but before the response arrives, the
client's retry is safely absorbed.

### Ordering matters

```python
def debit(self, amount, transaction_id=None):
    amount = self._validate_amount(amount)
    if amount > self._balance:                    # check BEFORE emitting
        raise InsufficientFundsError(...)
    ...
```

The funds check happens *before* the event is appended. Since events are never
deleted, emitting first and validating later would leave a permanent bad record.

---

## 6. Authentication and authorisation

### The vulnerability this closed

Before auth, `wallet_id` was just a path parameter. Any caller could read or
trade **any** wallet by editing the URL:

```bash
curl http://localhost:8000/portfolio/someone-elses-wallet/summary   # 200 OK
```

### Design

```
Registration  email + password ──▶ bcrypt(cost 12) ──▶ users table
                                └─▶ auto-provision wallet ──▶ wallet_ownership

Login         credentials ──▶ verify ──▶ access token  (30 min)
                                     └─▶ refresh token (7 days)

Request       Authorization: Bearer <access>
                 ├─ verify signature, expiry, issuer, type
                 ├─ resolve → User
                 └─ wallet route? → check wallet_ownership.owner_id == user_id
```

### Token strategy

| | Access | Refresh |
|---|---|---|
| Lifetime | 30 minutes | 7 days |
| Sent | every request | only to `/auth/refresh` |
| Claim | `type: "access"` | `type: "refresh"` |

The `type` claim is load-bearing. Without it, a stolen refresh token — which
lives far longer — could be replayed as an access token:

```python
if payload.get("type") != expected_type:
    raise AuthenticationError("Invalid authentication token")
```

There is a test for exactly this
(`test_refresh_token_cannot_be_used_as_an_access_token`).

### One dependency secures fifteen routes

Because every wallet-scoped route already declared `WalletIdDep`, swapping that
single dependency for an ownership-checked version secured all of them at once:

```python
def authorized_wallet_id(
    auth: AuthServiceDep,
    current_user: CurrentUserDep,
    wallet_id: str = Path(pattern=r"^[A-Za-z0-9._\-]{1,64}$"),
) -> str:
    return auth.authorize_wallet(current_user, wallet_id)

WalletIdDep = Annotated[str, Depends(authorized_wallet_id)]
```

This is the payoff of consistent dependency injection: a security property
enforced in one place rather than fifteen, with no route left behind.

### Deliberate security details

**1. Timing-attack mitigation.** A login for a non-existent user still performs
a bcrypt verification against a dummy hash, so response time does not reveal
whether an account exists:

```python
stored_hash = user.password_hash if user else self._hasher.dummy_hash()
password_ok = self._hasher.verify(password, stored_hash)
if user is None or not password_ok:
    raise AuthenticationError("Incorrect email or password")
```

**2. No user enumeration.** Unknown email and wrong password return an identical
401 with identical text. Verified live:

```
wrong password  → 401 {"detail": "Incorrect email or password"}
unknown email   → 401 {"detail": "Incorrect email or password"}
```

**3. No wallet enumeration.** A wallet you do not own and a wallet that does not
exist both return **403**. Returning 404 for the latter would let an attacker
map which wallet ids are real.

**4. Fail-closed secret handling.**

```python
if environment in {"production", "prod", "staging"} and not secret:
    raise RuntimeError("JWT_SECRET_KEY is required when ENVIRONMENT=production")
if secret and len(secret) < 32:
    raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters")
```

There is no hardcoded default. Development generates an ephemeral per-process
key, which merely invalidates tokens on restart.

**5. bcrypt, not SHA.** Cost factor 12 (~250 ms/hash). General-purpose hashes
are billions-per-second on a GPU; bcrypt is deliberately slow and salted.

### Frontend token handling

Tokens live in `localStorage` via a persisted Zustand store, and `authFetch`
refreshes transparently on a 401:

```javascript
try {
  return await apiFetch(path, withAuth);
} catch (error) {
  if (!(error instanceof ApiError) || error.status !== 401) throw error;
  const freshToken = await refreshSession();     // shared in-flight promise
  if (!freshToken) throw error;
  return apiFetch(path, { ...options, headers: { Authorization: `Bearer ${freshToken}` } });
}
```

Concurrent 401s share **one** in-flight refresh (`refreshInFlight`), so a page
firing several requests at once does not trigger several refreshes and race.

**Trade-off, stated honestly:** `localStorage` is readable by XSS. The
alternative — `httpOnly` cookies — resists XSS but needs CSRF protection and
complicates cross-origin dev. Given a token lifetime of 30 minutes and no real
money, `localStorage` is the reasonable choice here. A production system holding
real assets should use `httpOnly` cookies with CSRF tokens.

---

## 7. The database layer

### Schema

```
users                                wallet_ownership
├── user_id       (unique)           ├── wallet_id  (unique)
├── email         (unique, indexed)  ├── owner_id   → users.user_id  CASCADE
├── password_hash (bcrypt)           ├── label
├── display_name                     └── created_at
├── is_active
└── created_at

wallet_events  ← the ledger, append-only
├── event_id       (unique)
├── wallet_id      (indexed)
├── event_type     FundsCredited | FundsDebited
├── transaction_id
├── amount         Numeric(20,4)
├── payload        JSON
└── timestamp
    UNIQUE (wallet_id, transaction_id)   ← idempotency, enforced by the DB

positions                    trades                    orders
├── wallet_id                ├── trade_id (unique)     ├── order_id (unique)
├── symbol                   ├── wallet_id             ├── wallet_id
├── quantity Numeric(20,8)   ├── symbol                ├── symbol, side
└── updated_at               ├── side                  ├── quantity
UNIQUE (wallet_id, symbol)   ├── quantity, price       ├── order_type, status
                             └── timestamp             ├── filled_quantity
                                                       ├── average_fill_price
                                                       └── rejection_reason
```

### Numeric, never Float

```python
MONEY    = Numeric(20, 4)   # cash and prices
QUANTITY = Numeric(20, 8)   # supports fractional shares
```

`Float` is binary floating point: `0.1 + 0.2 = 0.30000000000000004`. Over
thousands of ledger entries those errors accumulate into real discrepancies.
`Numeric` is exact decimal and maps to Python's `Decimal`.

### Portability

```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./quantnest.db")
```

Moving to PostgreSQL is one environment variable — no model or query changes:

```bash
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/quantnest
```

SQLite gets pragmas it needs for correctness under concurrency:

```python
cursor.execute("PRAGMA journal_mode=WAL")    # readers proceed during writes
cursor.execute("PRAGMA foreign_keys=ON")     # off by default in SQLite
cursor.execute("PRAGMA busy_timeout=5000")   # wait rather than fail instantly
```

### Migration from JSON

The original app stored everything in `data/*.json`.
`scripts/migrate_json_to_db.py` moves it across and is **idempotent** — running
it repeatedly inserts nothing new:

```
Run 1:  events=126  positions=19  trades=46  orders=64
Run 2:  events=0    positions=0   trades=0   orders=0
Run 3:  events=0    positions=0   trades=0   orders=0
```

Getting that right required a fix. Three legacy trades had no `trade_id`, so the
first version minted a random UUID each run and re-inserted them every time.
The fix derives a deterministic id from the trade's natural key:

```python
def _stable_trade_id(wallet_id, record, index):
    natural_key = "|".join([wallet_id, str(index), record["symbol"], ...])
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"quantnest:trade:{natural_key}"))
```

Balances were verified to match the JSON source exactly (`293486.6000`, 56
events for `demo-user`).

---

## 8. The API layer

### 27 endpoints

| Group | Endpoint | Auth |
|---|---|---|
| **auth** | `POST /auth/register` | public |
| | `POST /auth/login` | public |
| | `POST /auth/refresh` | public |
| | `GET /auth/me` | bearer |
| | `GET /auth/wallets` | bearer |
| | `POST /auth/wallets` | bearer |
| **portfolio** | `GET /portfolio/{wallet_id}/summary` | **owner** |
| | `POST /portfolio/{wallet_id}/credit` | **owner** |
| | `POST /portfolio/{wallet_id}/debit` | **owner** |
| | `POST /portfolio/{wallet_id}/buy` | **owner** |
| | `POST /portfolio/{wallet_id}/sell` | **owner** |
| | `GET /portfolio/health` | public |
| **orders** | `POST /orders` | bearer |
| | `GET /orders/{wallet_id}` | **owner** |
| | `GET /orders/{wallet_id}/{order_id}` | **owner** |
| | `POST /orders/{wallet_id}/{order_id}/cancel` | **owner** |
| **history** | `GET /history/portfolio/{wallet_id}/trades` | **owner** |
| | `GET /history/portfolio/{wallet_id}/orders` | **owner** |
| | `GET /history/portfolio/{wallet_id}/timeline` | **owner** |
| | `GET /history/portfolio/{wallet_id}/activity-summary` | **owner** |
| | `GET /history/wallet/{wallet_id}/events` | **owner** |
| **market** | `GET /market/quote/{symbol}` | public |
| | `GET /market/quotes` | public |
| | `GET /market/chart/{symbol}` | public |
| | `GET /market/search` | public |
| **meta** | `GET /` · `GET /health` | public |

Market data is public because it is not wallet-scoped — quotes reveal nothing
about any user.

### Dependency injection

`api/deps.py` wires everything. Route handlers never construct services:

```python
def get_db_session() -> Iterator[Session]:
    """One transaction per request: commit on success, roll back on error."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

A handler then reads as a declaration of its needs:

```python
async def buy_asset(
    wallet_id: WalletIdDep,          # validated AND ownership-checked
    request: TradeRequest,           # validated body
    transaction_id: TransactionIdDep,
    engine: OrderEngineDep,          # transaction-bound
    ...
) -> TradeResponse:
```

Tests override any of these via `app.dependency_overrides`.

### Errors: RFC 9457 problem+json

Every error has the same shape:

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

Domain exceptions map to status codes through a table, replacing the original
code's string-sniffing (`"InsufficientFundsError" in str(type(e))`):

| Exception | Status |
|---|---|
| `ValidationError` | 400 |
| `AuthenticationError` | 401 |
| `AuthorizationError` | 403 |
| `UnknownSymbolError`, `OrderNotFoundError` | 404 |
| `InsufficientFundsError`, `InsufficientPositionsError` | 409 |
| `EmailAlreadyRegisteredError`, `WalletAlreadyExistsError` | 409 |
| `OrderExecutionError` | 422 |
| anything else | 500 (generic body, full traceback logged) |

The catch-all is the important one:

```python
@app.exception_handler(Exception)
async def handle_unexpected_error(request, exc):
    logger.exception("Unhandled exception", extra={...})   # full detail server-side
    return _problem(
        request, status_code=500, title="Internal server error",
        detail="An unexpected error occurred. Please try again or contact support.",
    )
```

A traceback can never reach a client. The `request_id` links the sanitised
response to the full log entry.

### Validation

```python
Ticker = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9&._\-]{0,19}$")]
Quantity = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=4)]
Amount   = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
```

`extra="forbid"` rejects unknown fields outright, so a typo like
`{"quantiy": 10}` fails loudly instead of silently defaulting.

### Observability

```python
@app.middleware("http")
async def request_context(request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_var.set(request_id)
    ...
```

The id is stored in a `ContextVar`, so every log line during that request
carries it automatically:

```json
{"timestamp": "2026-07-27T13:24:29Z", "level": "INFO", "logger": "quantnest.api.main",
 "message": "Request completed", "request_id": "5b206466-...", "method": "GET",
 "path": "/portfolio/demo-user/summary", "status_code": 200, "duration_ms": 21.24}
```

> **A bug worth remembering:** the first version reset the `ContextVar` in a
> `finally` block *before* the completion log ran, so every completion line
> showed `request_id: "-"`. The fix was to log inside the `try`, before the
> reset. Caught only by actually reading the log output.

---

## 9. The frontend

### Structure

```
frontend/src/
├── styles/          tokens.css (the whole theme) + base.css
├── components/
│   ├── ui/          Button Card Badge Skeleton DataTable Tabs Input
│   │                EmptyState Toast ErrorBoundary
│   ├── layout/      AppShell TopBar MarketClock
│   ├── portfolio/   SummaryCards HoldingsTable HoldingRow HistoryPanel
│   ├── trade/       OrderTicket SymbolSearch QuoteCard OrderEntry
│   ├── chart/       TradingChart
│   ├── wallet/      WalletActions LedgerTable
│   └── dev/         DevConsole
├── hooks/           useAuth usePortfolio useMarket useWallet useMarketHours
├── lib/             apiClient format portfolioMath queryClient devBus
├── stores/          useAuthStore useSessionStore
└── pages/           AuthPage Portfolio Wallet Notes About
```

### The refactor

`PortfolioPage.jsx` went from **603 lines to 108**. The original held 15
`useState` calls, 47 inline `style={{…}}` objects, four `useEffect`s, all P&L
arithmetic inside the render body, and ~46 lines of debug-narration strings.

Three real bugs came out of it:

**1. Wallet-switch race.** `fetchPortfolio` fired three requests, then a fourth
from inside `.then()`. Nothing was cancelled on unmount or wallet change, so a
stale response could overwrite fresh state.

**2. Search race.** The debounce timer was cleared on each keystroke but the
in-flight request was never aborted. A slow response for `"IN"` could land after
`"INFY"` and repopulate the dropdown.

**3. Duplicate polling.** A 60s `setInterval` was recreated whenever
`selectedStock` or `loadQuote` changed identity, so timers could stack.

All three vanish with TanStack Query: the debounced term is part of the query
key, so superseded requests are cancelled automatically, and one timer exists
per key.

### State ownership

| State | Owner | Why |
|---|---|---|
| Portfolio, quotes, history | TanStack Query | Server state: caching, polling, cancellation |
| `walletId`, selected symbol | Zustand | Global UI state, no provider tree |
| Tokens, user | Zustand (persisted) | Must survive a refresh |
| Toasts | React Context | Tied to the component tree |
| `collapsed`, `activeTab` | `useState` | Purely local |

The distinction that matters: **server state is not application state.** It is a
cache of something owned elsewhere, and needs staleness, refetching and
invalidation — which is exactly what TanStack Query provides.

### Market-hours-aware polling

```javascript
export function useQuoteRefetchInterval() {
  const [interval, setIntervalMs] = useState(
    () => (getMarketState().isOpen ? 30_000 : 300_000)
  );
  ...
}
```

30 seconds while NSE is open, 5 minutes when closed, and paused entirely in
background tabs (`refetchIntervalInBackground: false`). Polling a closed market
every 30 seconds is pure waste.

### Pure calculations

All P&L maths lives in `lib/portfolioMath.js` — no React, no fetch, no side
effects, fully unit-tested. Its most important property is **null-safety**:

```javascript
// WRONG: (h.invested ?? 0) treats "still loading" as zero and understates totals.
// RIGHT: sum only real values, and report whether the set is complete.
const hasAllInvested = holdings.every((h) => h.invested !== null);
```

The original code coerced missing values to `0`, silently showing a wrong total
while quotes were still arriving. Now every total carries a `has*` flag and the
UI renders a skeleton until the data is complete.

---

## 10. The design system

### Tokens

Everything visual comes from `styles/tokens.css`.

```css
/* Surfaces: elevation by lightness, not by drawing borders everywhere */
--surface-canvas:  #0e0f11;
--surface-raised:  #141517;
--surface-overlay: #1a1c1f;
--surface-hover:   #212428;

/* Text: exactly three levels */
--text-primary:   #e8eaed;
--text-secondary: #9aa0a6;
--text-tertiary:  #6b7178;

/* Semantic: reserved strictly for P&L and status */
--profit: #3fb950;
--loss:   #f85149;

/* ONE accent: focus, active nav, primary CTA. Nothing else. */
--accent: #4f7fff;
```

The original used four competing accent hues (blue, purple, cyan, yellow) as
decoration. Now there is one, and profit/loss colour is never spent on anything
that is not a number.

### Tabular figures

The single most important typographic decision:

```css
.numeric {
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum' 1, 'case' 1;
  text-align: right;
}
```

In proportional type, `1` is narrower than `8`, so price columns jitter as live
values update. Tabular figures give every digit identical width — perfect
column alignment **without** resorting to a monospace font, so the UI still
reads as a product rather than a terminal.

### Before and after

| | Before | After |
|---|---|---|
| Table headers | `avg_cost`, `p&l`, `net_chg%` | `Avg cost`, `P&L`, `Net chg.` |
| Nav | `[01] portfolio` | `Portfolio` |
| Panels | `// market_terminal` | `Order ticket` |
| Icons | `↺ ✕ ⟳ ▲ ▼ ⚠ ※ ⓘ` | lucide-react, 16px, 1.5px stroke |
| Loading | `⟳ loading…` | Skeletons sized to real content |
| Padding | 25 ad-hoc values | 4px grid |
| Base font | 13px | 14px |

### CSS Modules over Tailwind

Chosen because it adds **zero dependencies** (Vite supports it natively), gives
real scoping, and keeps the token layer as the single source of truth — which is
what lets `TradingChart` read theme colours at runtime:

```javascript
function readChartTheme(element) {
  const styleOf = getComputedStyle(element);
  return {
    background: styleOf.getPropertyValue('--chart-bg').trim(),
    up: styleOf.getPropertyValue('--chart-up').trim(),
    ...
  };
}
```

Previously the chart hardcoded `#151515`, `#2B2B2B`, `#26a69a` and visibly
clashed with the panel around it.

---

## 11. Request lifecycles end to end

### A market buy

```
1. BROWSER  OrderEntry submit
            validateOrder() → client-side pre-check (instant feedback)

2. HOOK     usePlaceOrder mutation
            POST /portfolio/u-58adf7e1/buy
            Authorization: Bearer <access>
            X-Transaction-ID: <uuid>          ← idempotency key
            { "symbol": "INFY", "quantity": 10 }

3. MIDDLEWARE  assign request_id → CORS → route

4. DEPS     get_db_session      → open transaction
            get_current_user    → verify JWT → User
            authorized_wallet_id→ wallet_ownership.owner_id == user.user_id
                                  ✗ → 403, request ends here
            get_order_engine    → engine with transaction-bound repositories

5. VALIDATION  TradeRequest: ticker pattern, quantity > 0, extra="forbid"

6. HANDLER  TradeCommandHandler.buy(BuyAssetCommand)

7. DOMAIN   OrderExecutionEngine.place_order
            ├─ Order(status=PENDING)
            ├─ validate
            │    ├─ quantity > 0
            │    ├─ market.get_price("INFY") → 1650.00   (cache → yfinance)
            │    └─ portfolio.cash() >= 16500.00
            │         ✗ → order.reject(...) → persisted, HTTP 200 success:false
            ├─ portfolio.buy("INFY", 10, tx_id)
            │    ├─ wallet.debit(16500.00, tx_id)
            │    │    ├─ balance check
            │    │    ├─ idempotency check on tx_id
            │    │    └─ append FundsDebited
            │    ├─ positions["INFY"] += 10
            │    └─ persist positions + Trade
            └─ order.fill(10, 1650.00) → status=FILLED

8. PERSIST  repositories flush; the dependency commits ONE transaction.
            A failure anywhere rolls back everything — no half-applied trade.

9. RESPONSE 200 { order_status: "FILLED", portfolio_summary: {...} }

10. BROWSER onSuccess → invalidate portfolio + history queries
            → refetch → table re-renders → success toast
```

The whole trade is **one database transaction**. The event, the position update
and the trade record commit together or not at all.

### A cross-account attack, blocked

```
Alice authenticates, then requests Bob's wallet:
  GET /portfolio/u-4c318855/summary
  Authorization: Bearer <alice's token>

  → get_current_user       ✓ valid token → Alice
  → authorized_wallet_id
       wallet_ownership.get("u-4c318855") → owner_id = bob
       bob != alice → AuthorizationError

  → 403 {"type": "not_authorized", "detail": "You do not have access to this wallet"}

  Logged: "Blocked cross-account wallet access" {user_id: alice, wallet_id: ...}
  Bob's balance and positions: unchanged.
```

Verified live, not just asserted.

---

## 12. Testing strategy

### 128 tests

| Suite | Count | Scope |
|---|---|---|
| `tests/unit/domain/test_wallet.py` | 10 | Ledger, idempotency, replay, overdraft |
| `tests/unit/domain/test_portfolio.py` | 17 | Trading rules, analytics, persistence |
| `tests/unit/domain/test_order_engine.py` | 16 | Fills, rejections, limits, cancellation |
| `tests/integration/test_api.py` | 24 | Full stack via HTTP |
| `tests/integration/test_auth.py` | 33 | Auth, authorisation, isolation |
| `frontend/src/lib/portfolioMath.test.js` | 13 | Pure P&L maths |
| `frontend/src/App.test.jsx` | 7 | Real component tree render |
| `frontend/src/pages/AuthPage.test.jsx` | 8 | Auth gate |

Hermetic: in-memory SQLite + deterministic market provider. No network, no
database file, no fixtures to clean up.

```bash
QUANTNEST_MARKET_PROVIDER=fake pytest -q     # 100 passed
cd frontend && npm test                      # 28 passed
```

### What is actually tested

Not coverage theatre — the tests target the properties that would hurt if broken:

```python
def test_idempotent_buy_does_not_double_debit(engine, funded_wallet, event_store):
    wallet = funded_wallet("w1")
    starting = wallet.balance
    engine.place_order("w1", "INFY", "BUY", Decimal("2"), transaction_id="tx-1")
    engine.place_order("w1", "INFY", "BUY", Decimal("2"), transaction_id="tx-1")
    assert Wallet("w1", event_store=event_store).balance == starting - Decimal("3300.00")
```

```python
def test_a_user_cannot_trade_on_another_users_wallet(client):
    alice, bob = register(client, "alice@…"), register(client, "bob@…")
    # ... alice attacks bob's funded wallet ...
    assert attack.status_code == 403
    assert summary["cash"] == 100000.0       # untouched
    assert summary["positions"] == {}
```

```javascript
it('flags incomplete data instead of understating totals', () => {
  const holdings = buildHoldings(summary, { INFY: quotes.INFY });  // partial
  expect(computeTotals(holdings, summary).hasAllDayPnl).toBe(false);
});
```

### Deterministic market provider

```python
market.set_price("RELIANCE", Decimal("3000.00"))
assert portfolio.total_value() == Decimal("105000.00")
```

Tests can move the market. With a live feed, asserting on P&L would be
impossible.

---

## 13. Docker and deployment

### Backend image

Multi-stage: compile in a throwaway builder, ship a slim runtime.

```dockerfile
FROM python:3.11-slim AS builder
RUN apt-get install -y build-essential      # discarded with this stage
RUN python -m venv /opt/venv && pip install .

FROM python:3.11-slim AS runtime
COPY --from=builder /opt/venv /opt/venv     # only the venv survives
RUN useradd --create-home --uid 10001 quantnest
USER quantnest                              # never root
HEALTHCHECK CMD curl --fail --silent http://localhost:8000/health
```

Compilers exist only in the builder. The container runs as uid 10001 — if the
process is compromised, it has no root. `/data` is a volume so the SQLite file
survives rebuilds.

### Frontend image

```dockerfile
FROM node:22-alpine AS builder
ARG VITE_API_URL                            # inlined at BUILD time by Vite
RUN npm ci && npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
```

`VITE_API_URL` is a **build argument**, not a runtime variable — Vite bakes env
vars into the bundle. It must be the URL the *browser* uses, not the internal
Docker service name.

nginx handles the SPA correctly:

```nginx
location /assets/ { expires 1y; add_header Cache-Control "public, immutable"; }
location = /index.html { add_header Cache-Control "no-cache, no-store, must-revalidate"; }
location / { try_files $uri $uri/ /index.html; }
```

Hashed assets cache for a year; `index.html` never caches (or clients pin to a
stale bundle); unknown paths fall through to the client router.

### Compose

```bash
cp .env.example .env
# set JWT_SECRET_KEY — generate with: openssl rand -hex 32
docker compose up --build
```

```yaml
JWT_SECRET_KEY: "${JWT_SECRET_KEY:?JWT_SECRET_KEY must be set in .env}"
```

Compose refuses to start without a key, rather than defaulting to something
guessable. Postgres sits behind an optional profile:

```bash
docker compose --profile postgres up --build
```

> **Two bugs caught while building this.** First, `pyjwt`, `passlib`, `bcrypt`
> and `pydantic[email]` were missing from `pyproject.toml` — the container
> would have crashed on import at startup. Found by installing the package into
> a clean venv to simulate the image build. Second, the unquoted
> `${VAR:?message}` in compose broke YAML parsing, because the message contained
> a colon. Found by parsing the file with PyYAML.
>
> **Docker itself is not available in the build sandbox**, so the images have
> been validated by simulation — clean-install boot, YAML parse, dependency
> resolution — but not by an actual `docker build`. That is the one step to run
> on a machine with Docker before relying on it.

---

## 14. Running it locally

### Without Docker

```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# set JWT_SECRET_KEY:  openssl rand -hex 32

python scripts/migrate_json_to_db.py    # optional: import legacy JSON
python -m quantnest.main                # http://localhost:8000/docs
```

```bash
# Frontend
cd frontend && npm install && npm run dev    # http://localhost:5173
```

Offline (no network)? Use deterministic prices:

```bash
QUANTNEST_MARKET_PROVIDER=fake python -m quantnest.main
```

### With Docker

```bash
cp .env.example .env      # set JWT_SECRET_KEY
docker compose up --build
```

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | — | **Required in production**, ≥32 chars |
| `ACCESS_TOKEN_TTL_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_TTL_DAYS` | `7` | Refresh token lifetime |
| `ENVIRONMENT` | `development` | `production` makes the secret mandatory |
| `DATABASE_URL` | `sqlite:///./quantnest.db` | Postgres-swappable |
| `QUANTNEST_MARKET_PROVIDER` | `yfinance` | `fake` for offline/CI |
| `LOG_FORMAT` / `LOG_LEVEL` | `json` / `INFO` | `console` for local |
| `CORS_ORIGINS` | `localhost:5173` | Comma-separated |
| `VITE_API_URL` | `localhost:8000` | Frontend build-time |

---

## 15. Design decisions and trade-offs

### Event sourcing for the wallet only

Positions and orders use plain state. Event sourcing costs complexity and only
pays off where an audit trail is essential — cash movement. Positions are
derivable from trades anyway.

### JWT over server-side sessions

| | JWT | Sessions |
|---|---|---|
| Scaling | Stateless; any instance verifies | Needs shared store (Redis) |
| Revocation | Hard — valid until expiry | Easy — delete the record |
| Size | ~300 bytes per request | Small cookie |

Chosen for statelessness with short access tokens to bound the revocation
window. **The honest weakness:** a stolen access token is valid for up to 30
minutes and cannot be revoked. Fixing that properly needs a token blocklist in
Redis, which is the natural next step.

### Rejections as HTTP 200

A rejected order returns `200 {"success": false}` rather than `4xx`. The request
was well-formed and produced a persisted, auditable `Order` record — the
business outcome was "no". HTTP 4xx means the *request* was wrong.

Reasonable people disagree here; 422 would also be defensible.

### Polling over WebSockets

Prices update every few seconds at best, and one user watches ~10 symbols.
Polling is simpler, survives reconnects for free, and needs no sticky sessions.
WebSockets would win for order-book depth or tick-level data.

### CSS Modules over Tailwind

Zero new dependencies, real scoping, and a token layer the chart can read at
runtime. Tailwind would be faster to iterate but adds a build dependency and
moves styling into long `className` strings.

### SQLite default, Postgres-ready

Zero setup for a reviewer cloning the repo; one env var to move to Postgres.
`Numeric` columns and no SQLite-specific SQL keep it portable.

---

## 16. Known limitations

Stated plainly — knowing what you have *not* built matters as much as what you have.

| Limitation | Impact | Fix |
|---|---|---|
| **No token revocation** | A stolen access token is valid ≤30 min | Redis blocklist keyed on `jti` |
| **No rate limiting** | Login is brute-forceable | slowapi or a gateway rule |
| **`localStorage` tokens** | XSS-readable | `httpOnly` cookies + CSRF |
| **No email verification** | Anyone can register any address | Verification link flow |
| **No password reset** | Locked out permanently | Time-limited reset token |
| **In-process cache** | Doesn't scale past one instance | Redis |
| **Not deployed** | No public URL | Fly.io / Railway / Render |
| **No CI pipeline** | Tests run manually | GitHub Actions |
| **yfinance untested live** | Sandbox blocks outbound TLS | Verify on first real run |
| **Docker unbuilt** | No Docker in sandbox | Run `docker compose up` locally |
| **Single-node only** | No horizontal scaling | Postgres + Redis + stateless instances |

The last three are environmental, not design gaps — they need a machine with
network and Docker access.

---

## 17. Interview question bank

**"Walk me through the architecture."**
> Hexagonal, four layers. The domain holds the business rules and imports only
> the standard library — no FastAPI, no SQLAlchemy. It declares what it needs as
> `typing.Protocol` ports; infrastructure implements them; the API injects them
> per request. That is why the test suite runs with no database and no network:
> every port has an in-memory implementation.

**"Why is the wallet event-sourced?"**
> The balance is never stored — it is replayed from an immutable event log. For
> anything financial the audit trail is the point: every movement is permanently
> recorded, the balance can never drift from its history, and you can reconstruct
> the balance at any past moment. Positions use plain state, because they are
> derivable from trades and do not need the same guarantee.

**"How do you prevent a double charge on a retry?"**
> Every mutating request carries an `X-Transaction-ID`. Before appending an
> event the wallet checks whether that id already exists, and the database
> enforces `UNIQUE(wallet_id, transaction_id)` so it holds under concurrency
> too. If the network drops after the server commits, the client's retry is a
> no-op. There is a test that fires the same buy twice and asserts the balance
> moved once.

**"How does authorisation work?"**
> A `wallet_ownership` table maps wallet ids to user ids. Every wallet-scoped
> route depends on `WalletIdDep`, which validates the id *and* checks ownership.
> Because all fifteen routes already used that dependency, swapping in the
> ownership check secured all of them at once — that is the real payoff of
> consistent dependency injection.

**"What security details did you get right?"**
> Four worth naming. Failed logins hash a dummy password so response time does
> not reveal whether an account exists. Unknown email and wrong password return
> identical 401s. A wallet you do not own and one that does not exist both return
> 403, so the API cannot be used to enumerate wallets. And the JWT secret is
> mandatory in production with a 32-character minimum — there is no hardcoded
> default.

**"Why `Decimal` instead of `float`?"**
> Binary floating point cannot represent `0.1` exactly, so `0.1 + 0.2` gives
> `0.30000000000000004`. In a ledger those errors accumulate. Money is `Decimal`
> in Python and `Numeric(20,4)` in the database, all the way through.

**"What was the hardest bug?"**
> The migration script looked idempotent but re-inserted three trades on every
> run. Three legacy records had no `trade_id`, so it minted a random UUID each
> time. The fix derives a deterministic UUID5 from the trade's natural key. I
> only caught it because I ran the migration three times and diffed the counts
> instead of trusting the first "success".

**"What would you do next?"**
> Three things in order. Redis for a token blocklist — that closes the
> revocation gap, which is the most real weakness. Then rate limiting on
> `/auth/login`, because it is currently brute-forceable. Then a CI pipeline, so
> the 128 tests run on every push rather than when I remember.

**"What would you do differently?"**
> Introduce the ports on day one. The original code had entities persisting
> themselves by calling module-level functions that wrote JSON files — three
> tests were already failing because of it. Retrofitting the boundary was more
> work than designing it in, and the failing tests were a symptom nobody had
> traced back to the architecture.

---

## 18. File-by-file map

### Backend

| File | Lines | Purpose |
|---|---|---|
| `domain/wallet.py` | 105 | Event-sourced ledger |
| `domain/portfolio.py` | 200 | Positions, valuation, P&L |
| `domain/order_engine.py` | 250 | Order validation and execution |
| `domain/order.py` | 157 | Order entity and lifecycle |
| `domain/user.py` | 120 | User and ownership entities |
| `domain/ports.py` | 320 | Protocols + in-memory fakes |
| `domain/exceptions.py` | 90 | Error hierarchy |
| `domain/events.py` | 75 | Ledger events |
| `domain/trade.py` | 20 | Immutable trade record |
| `application/auth_service.py` | 190 | Register, login, refresh, authorise |
| `application/portfolio_service.py` | 90 | Portfolio snapshot |
| `application/history_service.py` | 307 | Paginated history and timeline |
| `application/handlers/__init__.py` | 155 | Command handlers |
| `infra/db/models.py` | 150 | SQLAlchemy tables |
| `infra/db/repositories.py` | 320 | Port implementations |
| `infra/db/session.py` | 117 | Engine and session |
| `infra/security.py` | 195 | bcrypt + JWT |
| `infra/market.py` | 162 | yfinance + fake providers |
| `infra/logging.py` | 104 | JSON / console logging |
| `api/main.py` | 130 | App factory, middleware |
| `api/deps.py` | 230 | Dependency injection |
| `api/errors.py` | 175 | RFC 9457 handlers |
| `api/schemas.py` | 200 | Request/response models |
| `api/auth.py` | 160 | Auth endpoints |
| `api/portfolio.py` | 155 | Portfolio endpoints |
| `api/orders.py` | 110 | Order endpoints |
| `api/history.py` | 85 | History endpoints |
| `api/market.py` | 290 | Market data endpoints |

### Frontend

| File | Purpose |
|---|---|
| `App.jsx` | Providers, auth gate, page routing |
| `styles/tokens.css` | The entire design system |
| `lib/apiClient.js` | Fetch wrapper, `ApiError`, token refresh |
| `lib/portfolioMath.js` | Pure P&L calculations |
| `lib/queryClient.js` | Query keys and cache policy |
| `stores/useAuthStore.js` | Tokens and user (persisted) |
| `stores/useSessionStore.js` | Wallet and ticket state |
| `hooks/useAuth.js` | Register, login, logout |
| `hooks/usePortfolio.js` | Summary, quotes, history, orders |
| `hooks/useMarket.js` | Search, quote, chart |
| `hooks/useMarketHours.js` | NSE sessions and poll cadence |
| `pages/AuthPage.jsx` | Sign-in and registration |
| `pages/PortfolioPage.jsx` | Dashboard (108 lines of composition) |
| `components/trade/OrderTicket.jsx` | Search → quote → chart → entry |
| `components/portfolio/HoldingsTable.jsx` | Holdings with totals |
| `components/chart/TradingChart.jsx` | Lightweight Charts, theme-aware |

---

## Quick reference

```bash
# Run
python -m quantnest.main                                  # API :8000
cd frontend && npm run dev                                # UI  :5173
docker compose up --build                                 # both

# Test
QUANTNEST_MARKET_PROVIDER=fake pytest -q                  # 100 backend
cd frontend && npm test                                   # 28 frontend
cd frontend && npm run lint

# Verify the architecture holds
grep -rn "from quantnest.infra\|fastapi\|sqlalchemy" quantnest/domain/*.py

# Data
python scripts/migrate_json_to_db.py --dry-run
openssl rand -hex 32                                      # JWT_SECRET_KEY
```

| Metric | Value |
|---|---|
| Backend | 42 files, ~5,000 lines |
| Frontend | 77 files, ~8,400 lines |
| Tests | 128 (100 backend, 28 frontend) |
| Endpoints | 27 |
| Tables | 6 |
| Bundle | 482 KB (153 KB gzipped) |
