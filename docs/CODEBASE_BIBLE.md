# QuantNest — The Codebase Bible

> Everything in this project: every technology, every decision, every trade-off.
> Written to be **learned from**, not just referenced. Where a concept appears
> (event sourcing, JWT, tabular figures, dependency injection) it is explained
> from first principles before the code is shown.
>
> **Version 11.4.0** · 42 Python files (5,561 lines) · 78 frontend files
> (8,704 lines) · **177 tests** (142 backend, 35 frontend) · 29 API endpoints

---

## How to read this

| If you want to… | Start at |
|---|---|
| Understand the product | [Part I](#part-i--the-product) |
| Learn the technologies and *why* each was chosen | [Part II](#part-ii--the-technology-stack) |
| Understand the architecture | [Part III](#part-iii--architecture) |
| Read the backend in depth | [Part IV](#part-iv--the-backend) |
| Read the frontend in depth | [Part V](#part-v--the-frontend) |
| See how a request flows end to end | [Part VI](#part-vi--request-lifecycles) |
| Learn the testing approach | [Part VII](#part-vii--testing) |
| Deploy it | [Part VIII](#part-viii--operations) |
| Read the code review findings | [Part IX](#part-ix--code-review) |
| Prepare to be interviewed on it | [Part X](#part-x--mastery) |

---

# Table of contents

**Part I — The product**
1. [What QuantNest is](#1-what-quantnest-is)
2. [Domain glossary](#2-domain-glossary-finance-for-engineers)

**Part II — The technology stack**
3. [Backend technologies](#3-backend-technologies)
4. [Frontend technologies](#4-frontend-technologies)
5. [Why not the alternatives](#5-why-not-the-alternatives)

**Part III — Architecture**
6. [Hexagonal architecture explained](#6-hexagonal-architecture-explained)
7. [The ports and adapters in this codebase](#7-the-ports-and-adapters-in-this-codebase)
8. [CQRS](#8-cqrs-command-query-responsibility-segregation)
9. [Event sourcing](#9-event-sourcing)

**Part IV — The backend**
10. [Domain layer](#10-domain-layer)
11. [Application layer](#11-application-layer)
12. [Infrastructure layer](#12-infrastructure-layer)
13. [API layer](#13-api-layer)
14. [Authentication and authorisation](#14-authentication-and-authorisation)
15. [The database](#15-the-database)

**Part V — The frontend**
16. [Structure and state ownership](#16-structure-and-state-ownership)
17. [The design system](#17-the-design-system)
18. [Data fetching](#18-data-fetching)
19. [Components](#19-components)

**Part VI — Request lifecycles**
20. [Anatomy of a market buy](#20-anatomy-of-a-market-buy)
21. [Anatomy of a blocked attack](#21-anatomy-of-a-blocked-attack)
22. [Anatomy of a token refresh](#22-anatomy-of-a-token-refresh)

**Part VII — Testing**
23. [Strategy](#23-testing-strategy)
24. [The 177 tests](#24-the-177-tests)

**Part VIII — Operations**
25. [Configuration](#25-configuration)
26. [Docker](#26-docker)
27. [CI](#27-continuous-integration)
28. [Running it](#28-running-it)

**Part IX — Code review**
29. [Findings](#29-code-review-findings)
30. [Bugs found and fixed](#30-bugs-found-and-fixed)
31. [Known limitations](#31-known-limitations)

**Part X — Mastery**
32. [Interview question bank](#32-interview-question-bank)
33. [File-by-file reference](#33-file-by-file-reference)
34. [Glossary](#34-glossary)

---

# Part I — The product

## 1. What QuantNest is

A **paper-trading simulator** for Indian equities. A user registers, gets a
wallet, credits virtual funds, searches for a stock, sees a live quote and a
candlestick chart, and places market buy or sell orders. The portfolio tracks
positions, average cost, unrealised P&L, day P&L and allocation, with a full
audit trail of every order, trade and cash movement.

Prices are real (Yahoo Finance). Execution is simulated. No real money moves.

### Why it is technically interesting

Most portfolio projects are CRUD with a chart. These properties are what make
this one worth reading:

| Property | Where it shows up | Why it matters |
|---|---|---|
| **Event sourcing** | Wallet balance is never stored — it is replayed from an immutable log | Standard for financial ledgers; gives a free audit trail |
| **Idempotency** | Retrying a trade with the same transaction id cannot double-charge | Enforced by a DB constraint, not just application logic |
| **Hexagonal architecture** | `domain/` imports only the standard library | Business rules testable without a database |
| **Exact arithmetic** | `Decimal` in Python, `Numeric` in SQL — never `float` | `0.1 + 0.2 != 0.3` in binary floating point |
| **Ownership authorisation** | One dependency secures 15 wallet routes | And a route-table audit proves none was missed |
| **Moving-average cost basis** | Cost resets when a position closes | The naive version reports phantom profit |

---

## 2. Domain glossary (finance for engineers)

You cannot review this code without these terms. Each is defined the way the
code uses it.

**Instrument / Ticker / Symbol** — a tradable security, identified by a short
code. `INFY` is Infosys on the NSE. Yahoo Finance suffixes the exchange:
`INFY.NS` for NSE, `INFY.BO` for BSE.

**LTP (Last Traded Price)** — the price of the most recent transaction. Not a
quote *offer*; it is a historical fact about the last trade that occurred.

**Position** — how many shares of one symbol you currently hold. Ten shares of
INFY is a position; zero shares is *flat*.

**Cost basis / Average cost** — the average price you paid for the shares you
*currently* hold. Critical subtlety: if you buy 10 at ₹1,650, sell all 10, then
buy 1 at ₹2,000, your basis is ₹2,000 — **not** the blend of both purchases.
The first round-trip is closed history. Getting this wrong was a real bug in
this codebase; see [§30](#30-bugs-found-and-fixed).

**Unrealised P&L** — profit you would make if you sold right now:
`(current price − average cost) × quantity`. Unrealised because you still hold
the shares.

**Realised P&L** — profit actually locked in by selling. This codebase tracks
unrealised P&L; realised P&L is derivable from the trade log.

**Day change** — movement since yesterday's closing price. When the market is
closed, LTP *equals* the previous close, so day change is legitimately 0.00% —
a common source of "is this broken?" confusion.

**Market order** — buy or sell immediately at whatever the current price is.
Guaranteed execution, unguaranteed price. The default here.

**Limit order** — execute only at your price or better. Guaranteed price,
unguaranteed execution.

**Stop-loss order** — becomes a market order once price crosses a trigger.
Used to cap losses.

**Order vs Trade** — an **Order** is your *intent* ("buy 10 INFY"). A **Trade**
is the resulting *execution* ("bought 10 INFY at ₹1,650 at 14:32:07"). One
order can produce several trades (partial fills), or none (rejection). This
codebase models both separately, which is why a rejected order still leaves an
auditable record.

**Wallet / Ledger** — the cash account. A **ledger** records every movement
rather than just the balance.

**NSE trading sessions (IST)** — Pre-open 09:00–09:15, Normal 09:15–15:30,
Post-close 15:30–16:00, closed at weekends. The frontend polls prices every 30
seconds while open and every 5 minutes when closed.

---

# Part II — The technology stack

## 3. Backend technologies

### Python 3.11+

**What.** The backend language.

**Why this version.** 3.11 brought `Self` types, exception groups and a
10–60% speed improvement. More practically, this project uses `X | None` union
syntax (3.10+) and `datetime.UTC` idioms throughout.

**What you should understand.** Python's `Decimal` type is the whole reason
this project is financially correct:

```python
>>> 0.1 + 0.2
0.30000000000000004          # float: binary approximation
>>> Decimal("0.1") + Decimal("0.2")
Decimal('0.3')               # exact decimal arithmetic
```

Floats store base-2 fractions. `0.1` has no exact base-2 representation, the
same way `1/3` has no exact base-10 one. Over thousands of ledger entries the
error accumulates into real money. `Decimal` stores digits and an exponent, so
decimal fractions are exact.

**Rule:** any value denominated in currency uses `Decimal` in Python and
`Numeric` in SQL. Never `float`.

---

### FastAPI

**What.** The web framework — routing, validation, serialisation, OpenAPI docs.

**Why.** Three reasons, in order of importance:

1. **Validation is the type system.** Declare a Pydantic model and FastAPI
   validates, coerces and documents it. No hand-written checking.
2. **Dependency injection is first-class.** `Depends()` gives request-scoped
   resources with automatic cleanup, and — crucially — lets tests substitute
   any collaborator.
3. **OpenAPI for free.** `/docs` is generated from the code, so it cannot
   drift from reality. This project's route-security audit *reads* that schema
   to verify every endpoint.

**Concepts you must understand:**

**Dependency injection.** Instead of a function creating what it needs, it
*declares* what it needs and the framework supplies it:

```python
# Without DI — untestable, opens its own connection, unclear dependencies
async def get_summary(wallet_id: str):
    service = PortfolioService()        # what database? what config?
    return service.get_summary(wallet_id)

# With DI — dependencies are visible, injected, and overridable in tests
async def get_summary(wallet_id: WalletIdDep, service: PortfolioServiceDep):
    return service.get_summary(wallet_id)
```

The payoff is not aesthetic. `WalletIdDep` performs the *ownership check*, so
securing 15 endpoints was a one-line change to that single dependency.

**Dependencies with cleanup.** A `yield` dependency runs teardown after the
response — this is how one transaction wraps one request:

```python
def get_db_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session          # handler runs here
        session.commit()       # success
    except Exception:
        session.rollback()     # any failure rolls back everything
        raise
    finally:
        session.close()
```

**`async def` in this codebase.** Handlers are `async`, but the work inside is
synchronous (SQLAlchemy sync API, `yfinance`). FastAPI runs sync work in a
thread pool, so this is correct but not maximally concurrent. Truly async
would need `asyncpg` and an async HTTP client — a deliberate trade for
simplicity. **This is a real limitation, not an oversight.**

---

### Pydantic v2

**What.** Data validation and serialisation via type annotations.

**Why v2 specifically.** The core was rewritten in Rust — 5–50× faster than
v1. It also replaced `class Config` with `model_config` and `.dict()` with
`.model_dump()`; this codebase uses the v2 idioms throughout.

**How validation is layered here:**

```python
Ticker = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9&._\-]{0,19}$")]
Quantity = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=4)]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
```

`extra="forbid"` is the underrated one. Without it, `{"quantiy": 10}` (typo)
is silently ignored and the real field defaults. With it, the request is
rejected with a clear error. **Fail loudly on malformed input.**

---

### SQLAlchemy 2.0

**What.** The ORM and query builder.

**Why an ORM at all.** Raw SQL would work, but the ORM buys three things:
database portability (SQLite → PostgreSQL with no query changes), typed models
that document the schema, and identity mapping.

**Why 2.0.** The `Mapped[...]` / `mapped_column()` style is fully typed, so a
type checker catches column mistakes:

```python
class UserRow(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

**Sessions, explained.** A `Session` is a unit of work — an in-memory staging
area. Objects added to it are not written until `flush()` (sends SQL) or
`commit()` (sends SQL *and* ends the transaction). This project flushes inside
repositories so constraint violations surface immediately, and commits once
per request in the dependency.

**Why `Numeric`, not `Float`:**

```python
MONEY    = Numeric(20, 4)   # 20 significant digits, 4 after the point
QUANTITY = Numeric(20, 8)   # fractional shares
```

`Numeric` maps to Python `Decimal`, preserving exactness end to end.

---

### PyJWT

**What.** Encodes and verifies JSON Web Tokens.

**What a JWT actually is.** Three base64url segments joined by dots:

```
eyJhbGciOiJIUzI1NiJ9  .  eyJzdWIiOiJ1LTEyMyIsImV4cCI6MTc4NX0  .  3f9dK2...
    header                     payload (claims)                   signature
```

- **Header** — the algorithm (`HS256` here).
- **Payload** — the claims. **Readable by anyone.** Base64 is encoding, not
  encryption. Never put secrets in a JWT.
- **Signature** — `HMAC-SHA256(header.payload, secret)`. Anyone can *read* the
  token; only the holder of the secret can *produce a valid one*.

**Claims used here:**

| Claim | Meaning | Purpose |
|---|---|---|
| `sub` | subject | the user id |
| `exp` | expiry | rejected after this instant |
| `iat` | issued at | compared against the revocation cutoff |
| `iss` | issuer | `quantnest`; rejects foreign tokens |
| `jti` | JWT id | the handle used for revocation |
| `type` | custom | `access` or `refresh` |

**Why `type` matters.** Without it, a stolen refresh token — which lives 7 days
— could be presented as an access token. There is a test for exactly this.

**The fundamental JWT trade-off.** A JWT is *stateless*: the server verifies it
by signature alone, no database lookup. That is what makes it scale. It is also
why you **cannot revoke one** — which is why this project adds a blocklist, see
[§14](#14-authentication-and-authorisation).

---

### bcrypt (via passlib)

**What.** The password hashing function.

**Why not SHA-256.** SHA-256 is designed to be *fast* — billions of hashes per
second on a GPU. That is exactly wrong for passwords. bcrypt is deliberately
*slow* and its cost is tunable:

```python
CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)   # ≈250 ms per hash
```

Cost 12 means 2¹² iterations. Slow enough to make brute force impractical,
fast enough that a user does not notice.

**Salting is automatic.** Every hash embeds a random salt, so two users with
the same password get different hashes and rainbow tables are useless.

**Version pin explained.** `bcrypt<4.1` is pinned because passlib 1.7.4 reads
`bcrypt.__about__`, which bcrypt 4.1 removed. Without the pin the app raises on
import. This is documented in `pyproject.toml`.

---

### yfinance

**What.** Unofficial Yahoo Finance client for quotes and OHLCV history.

**Why.** Free, no API key, covers NSE and global equities. Sufficient for a
simulator.

**Its risks, and how they are handled:**

| Risk | Mitigation |
|---|---|
| Unofficial, can break | Isolated behind the `MarketDataProvider` port |
| Slow (network) | 60-second in-process cache |
| Returns nothing over long weekends | Escalates `5d → 1mo → 3mo` |
| Unavailable offline / in CI | `QUANTNEST_MARKET_PROVIDER=fake` |

The port is the important part. `yfinance` appears in exactly one module. If it
breaks, one file changes.

---

### uvicorn

**What.** The ASGI server that actually runs FastAPI.

**Why you need it.** FastAPI is a framework, not a server. ASGI is the async
successor to WSGI, supporting long-lived connections. `uvicorn[standard]` adds
`uvloop` (a faster event loop) and `httptools` (a faster parser).

---

## 4. Frontend technologies

### React 19

**What.** The UI library.

**The mental model.** UI is a function of state: `UI = f(state)`. You describe
what the screen should look like for the current state; React works out the
minimal DOM changes.

**Hooks used here, and what each is for:**

| Hook | Purpose | Example in this codebase |
|---|---|---|
| `useState` | Local component state | Which history tab is open |
| `useEffect` | Synchronise with something outside React | Creating the chart instance |
| `useMemo` | Cache an expensive computation | Deriving holdings from quotes |
| `useCallback` | Stable function identity across renders | Handlers passed to memoised rows |
| `useRef` | A mutable box that does not trigger re-render | The chart DOM node |
| `useContext` | Read a value from an ancestor provider | Toast API |
| `useSyncExternalStore` | Subscribe to a non-React store | The dev inspector event bus |

**The single most useful rule:** `useEffect` is for synchronising with
*external systems* — the DOM, a chart library, a subscription. It is **not**
for deriving state from other state. Deriving in an effect causes a second
render pass. This codebase had exactly that bug in `SymbolSearch`; the fix was
to compute during render:

```javascript
// Before: setState in an effect -> cascading render
useEffect(() => { setHighlightedIndex(0); }, [results]);

// After: derive it, clamped
const activeIndex = highlightedIndex < results.length ? highlightedIndex : 0;
```

---

### Vite

**What.** The build tool and dev server.

**Why it is fast.** In development it serves native ES modules — no bundling,
so startup is near-instant regardless of project size. For production it
bundles with Rollup, which tree-shakes and code-splits.

**What you must know:** `import.meta.env.VITE_*` variables are **inlined at
build time**, not read at runtime. That is why the Docker frontend image takes
`VITE_API_URL` as a *build argument*, and why it must be the URL the **browser**
will use — not an internal Docker service name.

---

### TanStack Query v5

**What.** Server-state management: caching, background refetching, deduplication,
cancellation.

**The insight it encodes.** *Server state is not application state.* It is a
**cache** of data owned elsewhere. That means it can go stale, needs refetching,
can arrive out of order, and may be shared by many components. `useState` models
none of that.

**Concepts:**

- **Query key** — the cache identity, e.g. `['portfolio', walletId, 'summary']`.
  Change the key and Query fetches fresh data *and cancels the old request*.
  This single mechanism eliminated three race conditions in this codebase.
- **`staleTime`** — how long data is considered fresh (30s here).
- **`gcTime`** — how long unused data stays cached (5 min).
- **`refetchInterval`** — polling. Set per-query and market-hours aware here.
- **Mutations** — writes, with `invalidateQueries` to refresh affected reads.

**Race conditions it solved.** The original hand-rolled code had three:
switching wallets let a stale response overwrite fresh state; a slow search for
`"IN"` could land after `"INFY"`; and quote polling registered duplicate
intervals. All three vanish because the query key *is* the cancellation
mechanism.

---

### Zustand

**What.** A minimal global state store (~1 KB).

**Why not Context.** Context re-renders *every* consumer when the value
changes. Zustand uses selectors, so a component re-renders only when its slice
changes:

```javascript
const walletId = useSessionStore((s) => s.walletId);   // only walletId changes matter
```

**Why not Redux.** Redux needs actions, reducers and dispatch for what is here
a handful of values. Zustand is a hook with a setter.

**`persist` middleware** writes to `localStorage` automatically, which is how a
session survives a page refresh.

---

### CSS Modules

**What.** CSS files whose class names are scoped to one component at build
time. `.row` becomes `._row_1a2b3`.

**Why not plain CSS.** The original stylesheet had 637 lines of *global*
classes — `.badge`, `.up`, `.empty`. Any new component risked collision.

**Why not Tailwind.** Three reasons: zero new dependencies (Vite supports CSS
Modules natively); real scoping; and a token layer the chart can read at
*runtime* via `getComputedStyle`, which utility classes cannot provide.

**Why not CSS-in-JS.** Runtime cost and a larger bundle for no benefit here.

---

### Lightweight Charts v5

**What.** TradingView's open-source charting library (~45 KB).

**Why.** Purpose-built for financial data — candlesticks, volume histograms and
time-scale handling are native rather than bolted onto a general chart library.

**v5 API note.** v5 replaced `chart.addCandlestickSeries()` with
`chart.addSeries(CandlestickSeries, {...})`. This project uses v5 syntax.

---

## 5. Why not the alternatives

Being able to defend a choice *against its alternatives* is what turns a stack
list into engineering judgement.

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Backend framework | FastAPI | Django | Django brings an ORM, admin and templates — heavy for a JSON API. Its ORM also resists the ports pattern. |
| | | Flask | Would need extensions for validation, docs and DI that FastAPI has built in. |
| Frontend state | TanStack Query | Redux Toolkit Query | Comparable; Query is lighter and framework-agnostic. |
| | | Plain `useState` | What the original did. Caused the three race conditions. |
| UI state | Zustand | Context | Context re-renders all consumers. |
| Styling | CSS Modules | Tailwind | Adds a build dependency; tokens must be readable at runtime by the chart. |
| Auth | JWT | Server sessions | Sessions need shared storage to scale; JWTs are stateless. Trade-off: revocation, addressed with a blocklist. |
| Password hash | bcrypt | Argon2id | Argon2id is arguably better; bcrypt has broader library maturity. Both are correct. |
| | | SHA-256 | **Wrong.** Too fast — designed for speed, not password storage. |
| Database | SQLite → Postgres | Postgres only | SQLite means a reviewer clones and runs with zero setup. |
| | | MongoDB | A ledger is inherently relational and needs transactions. |
| Money type | `Decimal` | `float` | **Wrong.** Binary floating point cannot represent decimal fractions exactly. |
| | | integer paise | Valid and used in production systems. `Decimal` is more readable and handles fractional shares. |
| Realtime | Polling | WebSockets | Prices move every few seconds; polling survives reconnects free and needs no sticky sessions. |

---

# Part III — Architecture

## 6. Hexagonal architecture explained

Also called **ports and adapters**, or the practical core of domain-driven
design.

### The problem it solves

In a typical layered app, business logic imports the database:

```python
class Wallet:
    def credit(self, amount):
        ...
        db.execute("INSERT INTO events ...")   # business logic knows about SQL
```

Consequences: you cannot test the rule without a database; changing storage
means editing business logic; and the rules get lost among the plumbing.

### The rule

> **Dependencies point inwards. The domain depends on nothing.**

```
        ┌──────────────────────────────────────────┐
        │                  API                     │  HTTP, JSON, status codes
        │   ┌──────────────────────────────────┐   │
        │   │          APPLICATION             │   │  orchestration, use cases
        │   │   ┌──────────────────────────┐   │   │
        │   │   │        DOMAIN            │   │   │  business rules — pure
        │   │   │  imports stdlib only     │   │   │
        │   │   └──────────────────────────┘   │   │
        │   └──────────────────────────────────┘   │
        └──────────────────────────────────────────┘
                          ▲
                          │ implements the ports
                  ┌───────┴────────┐
                  │ INFRASTRUCTURE │  SQL, bcrypt, JWT, HTTP clients
                  └────────────────┘
```

Infrastructure depends on the domain, never the reverse. That inversion is the
whole idea.

### How the domain stays pure

It declares what it needs as `typing.Protocol` classes:

```python
@runtime_checkable
class EventStore(Protocol):
    def load_events(self, wallet_id: str) -> List["DomainEvent"]: ...
    def append_event(self, wallet_id: str, event: "DomainEvent") -> None: ...
```

**`Protocol` gives structural typing.** Any class with matching methods
satisfies it — no inheritance, and crucially no import from the domain. This is
static duck typing: `SqlEventStore` never mentions `EventStore`, yet satisfies
it, and a type checker verifies that.

### Verify it yourself

```bash
python scripts/check_architecture.py
# Domain layer is clean: 11 files, no forbidden module-level imports.
```

That script parses the **AST** rather than grepping, so a deliberate lazy
import inside a function body is allowed while a module-level one fails. CI
runs it on every push, because this boundary is the property most likely to
erode quietly.

### This was fixed, not inherited

The original code violated the boundary in four places — `wallet.py`,
`portfolio.py` and `order_engine.py` imported `infra.storage`, and `market.py`
imported `yfinance`. Entities persisted *themselves* by calling module-level
functions that wrote JSON files. **Three tests were failing on `main` because
of it**, assuming an injectable price table that no longer existed. Introducing
the ports fixed the architecture and those tests together.

---

## 7. The ports and adapters in this codebase

Eight ports, each with a production and a test implementation:

| Port | Production adapter | Test adapter |
|---|---|---|
| `EventStore` | `SqlEventStore` | `InMemoryEventStore` |
| `PositionRepository` | `SqlPositionRepository` | `InMemoryPositionRepository` |
| `TradeRepository` | `SqlTradeRepository` | `InMemoryTradeRepository` |
| `OrderRepository` | `SqlOrderRepository` | `InMemoryOrderRepository` |
| `UserRepository` | `SqlUserRepository` | `InMemoryUserRepository` |
| `WalletOwnershipRepository` | `SqlWalletOwnershipRepository` | `InMemoryWalletOwnershipRepository` |
| `TokenBlocklist` | `SqlTokenBlocklist` | `InMemoryTokenBlocklist` |
| `MarketDataProvider` | `YFinanceMarketDataProvider` | `StaticMarketDataProvider` |
| `PasswordHasher` | `BcryptPasswordHasher` | (real, low cost) |
| `TokenService` | `JwtTokenService` | (real, short TTL) |

That second column is why the entire test suite runs with **no network and no
database file** — and why tests can move the market:

```python
market.set_price("RELIANCE", Decimal("3000.00"))
assert portfolio.total_value() == Decimal("105000.00")
```

Asserting on P&L against a live feed would be impossible.

---

## 8. CQRS (Command Query Responsibility Segregation)

**The idea.** Separate the path that *changes* state from the path that *reads*
it, because they have different needs. Writes need validation, business rules
and transactions. Reads need projection, pagination and speed.

```
Write:  API → Command DTO → Handler → Domain → Repository → DB
Read:   API → Query Service → Repository → DTO → API
```

**Note the asymmetry.** Reads skip the domain entirely. Listing trades does not
need business rules — it needs rows shaped for display. That is why
`HistoryService` talks to repositories directly and never constructs a
`Portfolio`.

**What a handler looks like** — coordination only, no rules of its own:

```python
class TradeCommandHandler:
    def _execute(self, command, side):
        order = self._engine.place_order(...)          # the domain decides
        if order.is_rejected:
            return {"success": False, "message": order.rejection_reason}
        return {"success": True, "portfolio_summary": {...}}
```

**A design decision worth defending.** A rejected order returns **HTTP 200 with
`success: false`**, not a 4xx. The request was well-formed and produced a
persisted, auditable `Order` record; the business answer was "no". HTTP 4xx
means the *request* was wrong. Reasonable engineers disagree — 422 is also
defensible — but the reasoning must be explicit.

---

## 9. Event sourcing

**The idea.** Do not store current state. Store the sequence of events that
produced it, and derive state by replaying them.

```
Traditional:  balance = 83,500                      ← a fact with no history
Event source: [+100,000, −16,500] → replay → 83,500 ← history that yields the fact
```

### The implementation

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

### Why, for money specifically

1. **Audit trail.** Every movement is permanently recorded. For a financial
   system this is the point, not a bonus feature.
2. **Time travel.** Replay a prefix of the log to get the balance at any past
   instant.
3. **No drift.** A stored balance can disagree with its transaction history —
   through a bug, a partial write, a race. A derived balance *cannot*.
4. **Debuggable.** "Why is the balance 83,500?" is answered by reading the log.

### The costs — stated honestly

- Replaying every event is O(n). At millions of events you need **snapshots**
  (store the balance at event 10,000 and replay only from there). Not
  implemented here; noted as a limitation.
- More storage.
- Events are immutable, so a bug in event *shape* needs a versioned migration.

**This is why only the wallet is event-sourced.** Positions and orders use
plain state — they are derivable from trades and do not need the guarantee.
Applying the pattern everywhere would be cargo-culting.

### Idempotency

Every credit and debit carries a `transaction_id`:

```python
def credit(self, amount, transaction_id=None):
    amount = self._validate_amount(amount)
    tx_id = transaction_id or str(uuid.uuid4())
    if self._already_processed(tx_id):
        return                                    # idempotent — no double credit
    self._record(FundsCredited(amount=amount, transaction_id=tx_id))
```

Backed by a database constraint so it holds under concurrency:

```python
UniqueConstraint("wallet_id", "transaction_id", name="uq_wallet_transaction")
```

**Why this matters.** The client sends `X-Transaction-ID: <uuid>` on every
mutating request. If the network drops *after* the server commits but *before*
the response arrives, the client's retry is safely absorbed. Without this, a
flaky connection could double-charge a user.

### Ordering matters

```python
def debit(self, amount, transaction_id=None):
    amount = self._validate_amount(amount)
    if amount > self._balance:                    # check BEFORE emitting
        raise InsufficientFundsError(...)
```

The funds check happens **before** the event is appended. Since events are
never deleted, emitting first and validating after would leave a permanent bad
record in an immutable log.

---

# Part IV — The backend

## 10. Domain layer

`quantnest/domain/` — 11 files, stdlib imports only.

| File | Lines | Responsibility |
|---|---|---|
| `ports.py` | 392 | Protocol definitions + in-memory fakes |
| `order_engine.py` | 276 | Validation and execution |
| `portfolio.py` | 250 | Positions, valuation, P&L |
| `order.py` | 157 | Order entity and lifecycle |
| `user.py` | 114 | User and wallet-ownership entities |
| `wallet.py` | 101 | Event-sourced ledger |
| `exceptions.py` | 100 | Error hierarchy |
| `events.py` | 75 | `FundsCredited` / `FundsDebited` |
| `trade.py` | 20 | Immutable executed-trade record |
| `market.py` | 32 | Lazy compatibility shim |

### Portfolio analytics

Every figure on the dashboard originates here.

```python
def unrealized_pnl(self, symbol):
    """(current price − average cost) × quantity held."""
    qty = self._positions.get(symbol, Decimal("0"))
    if qty == 0:
        return Decimal("0.00")
    return _money((self._market.get_price(symbol) - self.avg_cost(symbol)) * qty)
```

`_money()` quantises to two decimals with `ROUND_HALF_UP` — banker's rounding
(`ROUND_HALF_EVEN`, Python's default) would surprise users expecting 0.5 to
round up.

### Average cost: the subtle one

This is the function a code review should scrutinise hardest, because the naive
implementation is wrong in a way that looks right.

```python
def avg_cost(self, symbol: str) -> Decimal:
    """Weighted average cost of the shares *currently held*."""
    held = Decimal("0")
    cost_pool = Decimal("0")

    for trade in sorted((t for t in self._trades if t.symbol == symbol),
                        key=lambda t: t.timestamp):
        if trade.side == "BUY":
            held += trade.quantity
            cost_pool += trade.quantity * trade.price
            continue

        if held <= 0:
            continue

        sold = min(trade.quantity, held)
        cost_pool -= (cost_pool / held) * sold      # retire cost proportionally
        held -= sold

        if held <= 0:                                # position closed
            held = Decimal("0")
            cost_pool = Decimal("0")                 # basis resets

    return Decimal("0.00") if held <= 0 else _money(cost_pool / held)
```

**Three properties, each deliberate:**

1. A **BUY** adds its full cost to the pool.
2. A **SELL** removes cost *proportionally*, leaving the average unchanged. The
   gap between sale price and basis is *realised* profit, which is not part of
   cost basis.
3. **Closing** the position empties the pool, so a re-entry starts fresh.

Property 3 is what the original code got wrong. See
[§30](#30-bugs-found-and-fixed) for the full reproduction.

### The exception hierarchy

```python
class DomainError(Exception):
    code: str = "domain_error"

class InsufficientFundsError(DomainError):
    code = "insufficient_funds"
```

Every domain error carries a machine-readable `code`. The API maps exception
*types* to status codes through a table — replacing the original code's
string-sniffing (`"InsufficientFundsError" in str(type(e))`), which was fragile
and silently broke on rename.

---

## 11. Application layer

`quantnest/application/` — orchestration with no HTTP awareness.

| File | Lines | Responsibility |
|---|---|---|
| `auth_service.py` | 335 | Register, login, refresh, revoke, authorise |
| `history_service.py` | 307 | Paginated history and timeline |
| `handlers/__init__.py` | 147 | Command handlers |
| `portfolio_service.py` | 91 | Portfolio snapshot |
| `queries/history_dtos.py` | 73 | Read-side DTOs |

**Why services exist at all.** A route handler should not orchestrate. It
should translate HTTP into a call and back. The service owns the *use case*:
"register a user" means validate, hash, persist, provision a wallet, and issue
tokens — five steps that belong together and are testable without HTTP.

---

## 12. Infrastructure layer

`quantnest/infra/` — every external dependency lives here.

| File | Lines | Responsibility |
|---|---|---|
| `db/repositories.py` | 403 | Port implementations |
| `db/models.py` | 185 | SQLAlchemy tables |
| `db/session.py` | 117 | Engine, sessions, SQLite pragmas |
| `security.py` | 204 | bcrypt + PyJWT |
| `market.py` | 162 | yfinance + fake providers |
| `rate_limit.py` | 148 | Fixed-window throttling |
| `logging.py` | 104 | JSON / console formatters |

### Market data caching

```python
def get_price(self, symbol: str) -> Decimal:
    cached = self._read_cache(key)          # 60-second TTL
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

Thread-locked, because FastAPI serves requests from a thread pool. Escalates
`5d → 1mo → 3mo` because a 5-day window returns nothing across a long weekend.

### Structured logging

```python
class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": ..., "level": record.levelname,
            "logger": record.name, "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
```

**Why JSON.** Machine-parseable. A log aggregator can query
`request_id = "abc"` and return every line for that request. Grepping
free-text logs does not scale.

**How `request_id` propagates.** A `ContextVar` — like a thread-local, but
async-aware. Set once in middleware, read automatically by every log call
during that request, with no parameter threading.

### Rate limiting

Fixed-window counters guarding the auth endpoints:

| Endpoint | Budget | Window |
|---|---|---|
| `POST /auth/login` | 10 | 5 minutes |
| `POST /auth/register` | 5 | 1 hour |

**Why fixed-window over a sliding log.** Constant memory per key. Its known
weakness — up to 2× the limit across a window boundary — is an acceptable trade
for guarding a login form.

**A detail that matters:** a *successful* login clears the counter, so one user
fumbling their password cannot lock out everyone behind the same NAT address.

---

## 13. API layer

### 29 endpoints

| Group | Endpoint | Protection |
|---|---|---|
| **auth** | `POST /auth/register` | public (rate-limited 5/hr) |
| | `POST /auth/login` | public (rate-limited 10/5min) |
| | `POST /auth/refresh` | public |
| | `POST /auth/logout` | bearer |
| | `POST /auth/logout-all` | bearer |
| | `GET /auth/me` | bearer |
| | `GET /auth/wallets` | bearer |
| | `POST /auth/wallets` | bearer |
| **portfolio** | `GET /portfolio/{wallet_id}/summary` | **owner** |
| | `POST /portfolio/{wallet_id}/credit` | **owner** |
| | `POST /portfolio/{wallet_id}/debit` | **owner** |
| | `POST /portfolio/{wallet_id}/buy` | **owner** |
| | `POST /portfolio/{wallet_id}/sell` | **owner** |
| | `GET /portfolio/health` | public |
| **orders** | `POST /orders` | **owner** (body-supplied id) |
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

Market data is public because it is not wallet-scoped — a quote reveals nothing
about any user.

### Error contract: RFC 9457

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

**Why a standard.** Clients can branch on `type` programmatically instead of
string-matching prose. `request_id` links the response to the server logs.

**The mapping:**

| Exception | Status |
|---|---|
| `ValidationError` | 400 |
| `AuthenticationError` | 401 |
| `AuthorizationError` | 403 |
| `UnknownSymbolError`, `OrderNotFoundError`, `UserNotFoundError` | 404 |
| `InsufficientFundsError`, `InsufficientPositionsError` | 409 |
| `EmailAlreadyRegisteredError`, `WalletAlreadyExistsError` | 409 |
| `OrderExecutionError` | 422 |
| `RateLimitExceededError` | 429 (+ `Retry-After`) |
| anything else | 500 — generic body, full traceback logged |

**The catch-all is the important one:**

```python
@app.exception_handler(Exception)
async def handle_unexpected_error(request, exc):
    logger.exception("Unhandled exception", extra={...})   # full detail, server-side
    return _problem(request, status_code=500, title="Internal server error",
                    detail="An unexpected error occurred. Please try again.")
```

A traceback can never reach a client. Tracebacks reveal file paths, library
versions and sometimes secrets — a genuine security concern, not just untidy.

---

## 14. Authentication and authorisation

### Authentication vs authorisation

- **Authentication** — *who are you?* Verified by password, answered with a token.
- **Authorisation** — *are you allowed to do this?* Answered by ownership.

Confusing them is a classic source of vulnerabilities. This project had one:
`POST /orders` authenticated correctly for a while but never authorised.

### The flow

```
Registration  email + password ──▶ bcrypt(cost 12) ──▶ users table
                                └─▶ auto-provision wallet ──▶ wallet_ownership

Login         credentials ──▶ verify ──▶ access token  (30 min)
                                     └─▶ refresh token (7 days)

Request       Authorization: Bearer <access>
                 ├─ verify signature, expiry, issuer, type
                 ├─ check the revocation blocklist
                 ├─ resolve → User
                 └─ wallet route? → wallet_ownership.owner_id == user_id
```

### Why two tokens

| | Access | Refresh |
|---|---|---|
| Lifetime | 30 minutes | 7 days |
| Sent | every request | only to `/auth/refresh` |
| Claim | `type: "access"` | `type: "refresh"` |
| Revocable | yes, by `jti` | yes, and rotated on use |

A short-lived access token bounds the damage from theft. A long-lived refresh
token means the user is not forced to sign in every 30 minutes. The refresh
token is exposed on exactly one endpoint, shrinking its attack surface.

### Token revocation

A stateless JWT stays valid until it expires — so "sign out" would be
cosmetic without a server-side record.

**Two granularities:**

- **`POST /auth/logout`** — revoke this session's tokens, keyed on `jti`. The
  record is purged once the token would have expired anyway.
- **`POST /auth/logout-all`** — write **one** per-user cutoff instant; every
  token issued before it is rejected. One row invalidates a whole fleet.

**Refresh-token rotation.** Redeeming a refresh token revokes it and issues a
new pair. A leaked refresh token is useless once the legitimate client has
used it — and if the attacker gets there first, the real user's next refresh
fails, which is a *detectable signal*.

### Four deliberate security details

**1. Timing-attack mitigation.** A login for a non-existent user still performs
a bcrypt verification against a dummy hash:

```python
stored_hash = user.password_hash if user else self._hasher.dummy_hash()
password_ok = self._hasher.verify(password, stored_hash)
if user is None or not password_ok:
    raise AuthenticationError("Incorrect email or password")
```

Without it, a missing user returns in ~1 ms and a real user in ~250 ms —
enough to enumerate accounts with a stopwatch.

**2. No user enumeration.** Unknown email and wrong password return an
*identical* 401 with identical text.

**3. No wallet enumeration.** A wallet you do not own and one that does not
exist both return **403**. Returning 404 for the latter would let an attacker
map which wallet ids are real.

**4. Fail-closed secrets.**

```python
if environment in {"production", "prod", "staging"} and not secret:
    raise RuntimeError("JWT_SECRET_KEY is required when ENVIRONMENT=production")
if secret and len(secret) < 32:
    raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters")
```

No hardcoded default. A guessable default key is a catastrophic and
depressingly common vulnerability — with it, anyone can forge a token for any
user.

### One dependency secures fifteen routes

```python
def authorized_wallet_id(auth: AuthServiceDep, current_user: CurrentUserDep,
                         wallet_id: str = Path(pattern=r"^[A-Za-z0-9._\-]{1,64}$")) -> str:
    return auth.authorize_wallet(current_user, wallet_id)

WalletIdDep = Annotated[str, Depends(authorized_wallet_id)]
```

Because every wallet-scoped route already declared `WalletIdDep`, swapping that
single dependency for an ownership-checked version secured all of them at once.
**This is the concrete payoff of consistent dependency injection** — a security
property enforced in one place rather than fifteen.

**But it only covers path parameters.** `POST /orders` takes `wallet_id` in the
*body*, so it bypassed this entirely and shipped unprotected. See
[§30](#30-bugs-found-and-fixed).

### Frontend token storage — the honest trade-off

Tokens live in `localStorage` via a persisted Zustand store.

| | `localStorage` | `httpOnly` cookie |
|---|---|---|
| XSS readable | **yes** | no |
| CSRF vulnerable | no | yes, needs tokens |
| Cross-origin dev | simple | fiddly |

`localStorage` is readable by any injected script. Given a 30-minute token
lifetime, revocation support and no real money, it is the reasonable choice
here. **A production system holding real assets should use `httpOnly` cookies
with CSRF tokens.** Stating this clearly is more valuable than pretending the
choice is free.

---

## 15. The database

### Schema — 8 tables

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
├── quantity Numeric(20,8)   ├── symbol, side          ├── symbol, side, quantity
└── updated_at               ├── quantity, price       ├── order_type, status
UNIQUE (wallet_id, symbol)   └── timestamp             ├── filled_quantity
                                                       ├── average_fill_price
revoked_tokens               user_token_cutoffs        └── rejection_reason
├── jti (unique, indexed)    ├── user_id (unique)
├── user_id                  ├── issued_before
├── expires_at (indexed)     └── updated_at
└── revoked_at
```

### Indexes, and why each exists

| Index | Query it serves |
|---|---|
| `users.email` unique | Login lookup — the hot path |
| `wallet_ownership.wallet_id` unique | Every authorisation check |
| `wallet_events (wallet_id, timestamp)` | Replaying a wallet's ledger in order |
| `wallet_events (wallet_id, transaction_id)` unique | Idempotency enforcement |
| `positions (wallet_id, symbol)` unique | One row per holding; upsert target |
| `revoked_tokens.jti` unique | Checked on every authenticated request |

An index is a trade: faster reads, slower writes, more disk. Each one here
serves a query on a hot path.

### SQLite pragmas

```python
cursor.execute("PRAGMA journal_mode=WAL")    # readers proceed during writes
cursor.execute("PRAGMA foreign_keys=ON")     # OFF by default in SQLite
cursor.execute("PRAGMA busy_timeout=5000")   # wait rather than fail instantly
```

**`foreign_keys=ON` is the surprising one.** SQLite ignores foreign key
constraints unless explicitly enabled — a default that silently permits orphan
rows.

### Portability

```bash
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/quantnest
```

One environment variable. No model or query changes, because nothing uses
SQLite-specific SQL and money columns are `Numeric` rather than a dialect type.

### Migration from JSON

The original app stored everything in `data/*.json`.
`scripts/migrate_json_to_db.py` moves it and is **idempotent**:

```
Run 1:  events=126  positions=19  trades=46  orders=64
Run 2:  events=0    positions=0   trades=0   orders=0
```

Getting that right required a fix. Three legacy trades had no `trade_id`, so
the first version minted a random UUID each run and re-inserted them every
time. The fix derives a deterministic id from the trade's natural key:

```python
return str(uuid.uuid5(uuid.NAMESPACE_URL, f"quantnest:trade:{natural_key}"))
```

`uuid5` is a *hash*, so the same input always yields the same id.

---

# Part V — The frontend

## 16. Structure and state ownership

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

### Who owns what

| State | Owner | Why |
|---|---|---|
| Portfolio, quotes, history | TanStack Query | Server state: caching, polling, cancellation |
| `walletId`, selected symbol | Zustand | Global UI state, no provider tree |
| Tokens, user | Zustand (persisted) | Must survive a refresh |
| Toasts | React Context | Tied to the component tree |
| `collapsed`, `activeTab` | `useState` | Purely local |

**Getting this taxonomy right is most of frontend architecture.** The original
put everything in `useState`, which is why it had race conditions.

### The refactor

`PortfolioPage.jsx` went from **603 lines to 108**. The original held 15
`useState` calls, 47 inline `style={{…}}` objects, four `useEffect`s, all P&L
arithmetic inside the render body, and ~46 lines of debug-narration strings.

**Three real bugs surfaced:**

1. **Wallet-switch race** — three requests fired, then a fourth from inside
   `.then()`. Nothing was cancelled, so a stale response could overwrite fresh
   state.
2. **Search race** — the debounce timer was cleared per keystroke but the
   in-flight request was never aborted; a slow `"IN"` could land after `"INFY"`.
3. **Duplicate polling** — a 60s `setInterval` was recreated whenever
   `selectedStock` changed identity, so timers stacked.

All three vanish with TanStack Query, because the query key *is* the
cancellation mechanism.

---

## 17. The design system

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

**Why one accent.** The original used four competing hues (blue, purple, cyan,
yellow) as decoration. When everything is highlighted, nothing is. Profit/loss
colour is never spent on anything that is not a number.

### Tabular figures — the most important typographic decision

```css
.numeric {
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum' 1, 'case' 1;
  text-align: right;
}
```

In proportional type, `1` is narrower than `8`. In a price column that updates
live, the digits jitter as values change. Tabular figures give every digit the
same advance width — perfect alignment **without** monospace, so the UI still
reads as a product rather than a terminal.

Right-alignment matters for the same reason: decimal points line up, making
magnitudes scannable.

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

### Theme-aware charting

Because tokens are CSS custom properties, the chart reads them at runtime:

```javascript
function readChartTheme(element) {
  const styleOf = getComputedStyle(element);
  return {
    background: styleOf.getPropertyValue('--chart-bg').trim(),
    up: styleOf.getPropertyValue('--chart-up').trim(),
  };
}
```

Previously the chart hardcoded `#151515`, `#2B2B2B`, `#26a69a` and visibly
clashed with the panel around it. **This is what a token layer buys that
utility classes cannot.**

---

## 18. Data fetching

### The API client

`lib/apiClient.js` is the only module that knows where the backend lives.
Previously `http://localhost:8000` was hardcoded in three files.

**`ApiError`** normalises every failure shape the backend can produce — RFC
9457 problem+json, FastAPI's `{detail}`, validation error arrays, and network
failures — into one object with `status`, `detail` and a human message.

### Automatic token refresh

```javascript
try {
  return await apiFetch(normalisedPath, withAuth);
} catch (error) {
  if (!(error instanceof ApiError) || error.status !== 401) throw error;

  const freshToken = await refreshSession();
  if (!freshToken) {
    useAuthStore.getState().clearSession();   // fall back to the login screen
    throw error;
  }
  // retry once with the new token
}
```

**Three details worth noting:**

1. **Only 401 triggers a refresh.** A 403 means "authenticated but not
   allowed" — refreshing cannot help, so retrying would waste a round trip.
2. **Concurrent 401s share one refresh** (`refreshInFlight`), so a page firing
   several requests does not trigger several refreshes and race.
3. **An unrecoverable 401 signs the user out**, rather than leaving them on a
   dashboard where every request silently fails. This is what you hit after
   signing out from another device.

### Market-hours-aware polling

```javascript
const interval = getMarketState().isOpen ? 30_000 : 300_000;
```

30 seconds while NSE is open, 5 minutes when closed, and paused entirely in
background tabs (`refetchIntervalInBackground: false`). Polling a closed market
every 30 seconds is pure waste — of battery, bandwidth and API quota.

### Pure calculations

All P&L maths lives in `lib/portfolioMath.js` — no React, no fetch, no side
effects, fully unit-tested. Its most important property is **null-safety**:

```javascript
// WRONG: (h.invested ?? 0) treats "still loading" as zero and understates totals.
// RIGHT: sum only real values, and report whether the set is complete.
const hasAllInvested = holdings.every((h) => h.invested !== null);
```

The original coerced missing values to `0`, silently showing a *wrong total*
while quotes were still arriving. Now every total carries a `has*` flag and the
UI renders a skeleton until data is complete.

**Note it reads `avg_cost` from the API rather than recomputing it** — which is
why fixing the backend cost-basis bug corrected the entire dashboard with no
frontend change.

---

## 19. Components

### The UI primitives

| Component | Notable detail |
|---|---|
| `Button` | 6 variants; `buy`/`sell` are the only place P&L colour fills a control |
| `DataTable` | `numeric` prop right-aligns and enables tabular figures |
| `Skeleton` | Sized to match real content so nothing reflows |
| `Badge` | `tone` maps to semantic colour |
| `ErrorBoundary` | Class component — the only React feature with no hook equivalent |
| `Toast` | Context provider with a `fromError()` helper that never shows a raw stack |

### Error boundaries

The one place a class component is still required:

```javascript
static getDerivedStateFromError(error) { return { error }; }
componentDidCatch(error, errorInfo) { console.error(...); }
```

**Why they matter.** Without one, a render error in any component unmounts the
*entire* React tree — a blank white page. Each dashboard section is wrapped
separately, so a failure in the chart leaves the holdings table working.

---

# Part VI — Request lifecycles

## 20. Anatomy of a market buy

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
            get_current_user    → verify JWT → check blocklist → User
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
            │    │    ├─ balance check      (before emitting!)
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

**The critical property:** the event, the position update and the trade record
commit **together or not at all**. Without that atomicity you could debit a
wallet and fail to record the shares.

---

## 21. Anatomy of a blocked attack

```
Alice authenticates, then requests Bob's wallet:
  GET /portfolio/u-4c318855/summary
  Authorization: Bearer <alice's token>

  → get_current_user       ✓ valid, not revoked → Alice
  → authorized_wallet_id
       wallet_ownership.get("u-4c318855") → owner_id = bob
       bob != alice → AuthorizationError

  → 403 {"type": "not_authorized", "detail": "You do not have access to this wallet"}

  Logged: "Blocked cross-account wallet access" {user_id: alice, wallet_id: ...}
  Bob's balance and positions: unchanged.
```

Verified against a running server, not merely asserted in a unit test.

---

## 22. Anatomy of a token refresh

```
1. Access token expires (30 min).
2. Next request → 401.
3. authFetch catches it, calls refreshSession().
4. Concurrent 401s await the SAME in-flight promise (refreshInFlight).
5. POST /auth/refresh { refresh_token }
     ├─ verify signature, expiry, type == "refresh"
     ├─ check blocklist                       ✗ revoked → 401
     ├─ REVOKE the presented token (rotation)
     └─ issue a new pair
6. Store the new tokens; retry the original request.
7. If the refresh itself fails → clearSession() → login screen.
```

**Why rotation.** Without it, a refresh token stolen on day 1 works for 7 days.
With it, the token dies on first use — and if the attacker redeems it first,
the real user's next refresh fails, which is a detectable anomaly.

---

# Part VII — Testing

## 23. Testing strategy

### The pyramid, as applied here

```
        ╱ Integration (91) ╲     Full stack via HTTP: routing, DI, domain, SQL
      ╱────────────────────╲
    ╱     Unit (86)          ╲   Pure logic: domain rules, P&L maths
  ╱──────────────────────────╲
```

Inverted relative to the classic pyramid, and deliberately so: the *integration*
between layers is where this application's risk concentrates — authorisation,
transactions, error mapping. Unit tests cover the arithmetic.

### Hermetic by construction

```bash
QUANTNEST_MARKET_PROVIDER=fake pytest -q     # 142 passed, no network, no DB file
```

In-memory SQLite plus a deterministic market provider. No fixtures to clean up,
no flakes from a slow API, and **tests can move the market**.

### What is actually tested

Not coverage theatre. Each test targets a property that would hurt if broken:

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
```

### The audit-style test

`test_route_security.py` is the most valuable file in the suite. Rather than
testing one endpoint, it walks the **entire OpenAPI route table** and asserts
that anything touching a caller-supplied `wallet_id` verifies ownership.

**Why this exists.** 33 auth tests passed while `POST /orders` was wide open,
because each covered a route someone had remembered to secure. A per-endpoint
test cannot catch a *forgotten* endpoint. Only an audit over all routes can.

It parses each handler's AST and strips docstrings first — an earlier version
matched raw source and was fooled by a docstring merely *mentioning*
`authorize_wallet`. Verified by reintroducing the vulnerability and confirming
the test fails.

---

## 24. The 177 tests

| Suite | Count | Scope |
|---|---|---|
| `tests/unit/domain/test_wallet.py` | 11 | Ledger, idempotency, replay, overdraft |
| `tests/unit/domain/test_portfolio.py` | 16 | Trading rules, analytics, persistence |
| `tests/unit/domain/test_order_engine.py` | 16 | Fills, rejections, limits, cancellation |
| `tests/unit/domain/test_avg_cost.py` | 8 | Cost basis, including the reset bug |
| `tests/integration/test_api.py` | 24 | Full stack via HTTP |
| `tests/integration/test_auth.py` | 33 | Auth, authorisation, isolation |
| `tests/integration/test_revocation.py` | 18 | Sign-out, rotation, rate limiting |
| `tests/integration/test_route_security.py` | 12 | Whole-route-table audit |
| `tests/integration/test_orders_authz.py` | 4 | Body-supplied wallet ownership |
| **Backend total** | **142** | |
| `frontend/src/lib/portfolioMath.test.js` | 13 | Pure P&L maths |
| `frontend/src/pages/AuthPage.test.jsx` | 8 | Auth gate |
| `frontend/src/lib/apiClient.test.js` | 7 | Token refresh paths |
| `frontend/src/App.test.jsx` | 7 | Real component tree render |
| **Frontend total** | **35** | |
| **Grand total** | **177** | |

---

# Part VIII — Operations

## 25. Configuration

Every setting is an environment variable. See `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | — | **Required in production**, min 32 chars |
| `ACCESS_TOKEN_TTL_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_TTL_DAYS` | `7` | Refresh token lifetime |
| `ENVIRONMENT` | `development` | `production` makes the secret mandatory |
| `DATABASE_URL` | `sqlite:///./quantnest.db` | Postgres-swappable |
| `SQL_ECHO` | `false` | Log every SQL statement |
| `QUANTNEST_MARKET_PROVIDER` | `yfinance` | `fake` for offline/CI |
| `LOG_FORMAT` | `json` | `console` for local development |
| `LOG_LEVEL` | `INFO` | Standard Python levels |
| `CORS_ORIGINS` | `localhost:5173` | Comma-separated allowlist |
| `RATE_LIMIT_ENABLED` | `true` | Disable throttling |
| `LOGIN_MAX_ATTEMPTS` | `10` | Per window |
| `LOGIN_WINDOW_SECONDS` | `300` | Window length |
| `VITE_API_URL` | `localhost:8000` | Frontend **build-time** |

**Why environment variables.** The twelve-factor principle: config that varies
between deployments lives in the environment, not in code. It also keeps
secrets out of version control.

---

## 26. Docker

### Multi-stage builds

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

**Why multi-stage.** Compilers are needed to *build* some Python wheels but not
to *run* them. Discarding the builder halves the image and removes a toolchain
an attacker could use.

**Why non-root.** If the process is compromised, it has no root. Defence in
depth — cheap to do, valuable when it matters.

**Why a healthcheck.** Orchestrators use it to know when the container is ready
and to restart it when it wedges.

### The frontend image

```dockerfile
ARG VITE_API_URL                            # inlined at BUILD time by Vite
RUN npm ci && npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
```

`npm ci` (not `npm install`) installs exactly the lockfile — reproducible
builds.

nginx handles the SPA correctly:

```nginx
location /assets/ { expires 1y; add_header Cache-Control "public, immutable"; }
location = /index.html { add_header Cache-Control "no-cache, no-store, must-revalidate"; }
location / { try_files $uri $uri/ /index.html; }
```

Hashed assets cache for a year (the hash changes when content does).
`index.html` never caches, or clients pin to a stale bundle. Unknown paths fall
through to the client router.

### Compose

```bash
cp .env.example .env
# set JWT_SECRET_KEY — generate with: openssl rand -hex 32
docker compose up --build
```

```yaml
JWT_SECRET_KEY: "${JWT_SECRET_KEY:?JWT_SECRET_KEY must be set in .env}"
```

Compose refuses to start without a key rather than defaulting to something
guessable. Postgres sits behind an optional profile:

```bash
docker compose --profile postgres up --build
```

> **Two bugs caught while building this.** First, `pyjwt`, `passlib`, `bcrypt`
> and `pydantic[email]` were missing from `pyproject.toml` — the container
> would have crashed on import at startup. Found by installing into a clean
> venv to simulate the image build. Second, the unquoted `${VAR:?message}` in
> compose broke YAML parsing because the message contained a colon. Found by
> parsing the file with PyYAML.

---

## 27. Continuous integration

The pipeline lives at **`docs/ci/github-actions-ci.yml`**, activated with one
copy into `.github/workflows/` (see `docs/ci/README.md`). It ships there
because the token used for these commits lacks GitHub's `workflows` permission.

| Job | Steps |
|---|---|
| **backend** | Python 3.11 + 3.12 · architecture check · `print()` check · route security audit · pytest with coverage |
| **frontend** | `npm ci` · lint · tests · production build · upload bundle |
| **docker** | build both images · boot the API container · register a user · assert an unauthenticated request is refused |

**The architecture check is the interesting one.** It fails the build on a
module-level import of infrastructure into the domain — the property most
likely to erode quietly under future edits.

**The Docker job does more than `docker build`.** It boots the image and
exercises it, because a build can succeed and still crash on startup — which is
exactly what happened in v11.1.0.

---

## 28. Running it

### Without Docker

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# set JWT_SECRET_KEY:  openssl rand -hex 32

python scripts/migrate_json_to_db.py    # optional: import legacy JSON
python -m quantnest.main                # http://localhost:8000/docs
```

```bash
cd frontend && npm install && npm run dev    # http://localhost:5173
```

### Offline

```bash
QUANTNEST_MARKET_PROVIDER=fake python -m quantnest.main
```

### Verification commands

```bash
python scripts/check_architecture.py                    # DDD boundary
QUANTNEST_MARKET_PROVIDER=fake pytest -q                # 142 backend tests
cd frontend && npm run lint && npm test && npm run build
```

---

# Part IX — Code review

## 29. Code review findings

A full review was performed over the codebase. Method and results:

| Area | Method | Result |
|---|---|---|
| Concurrency | Two parallel buys against a wallet funded for exactly one share | ✅ One FILLED, one REJECTED, no overdraw |
| Money arithmetic | Fractional quantities, sub-rupee prices, rounding | ✅ Exact |
| Cost basis | Buy → sell-all → re-buy at a new price | ❌ **Bug found** — see §30 |
| Secret leakage | Scanned every OpenAPI response schema for password fields | ✅ None |
| Traceback leakage | Grepped for `detail=str(e)` | ✅ None |
| Bare excepts | Grepped `except:` | ✅ None |
| Frontend logging | Grepped `console.log` outside tests | ✅ None |
| Dead code | Coverage report + reference search | ❌ `infra/storage.py` — removed |
| Route authorisation | Walked the whole OpenAPI table | ❌ **Bug found** — `POST /orders` |
| Stale docs | Grepped documented counts against reality | ❌ Fixed |

---

## 30. Bugs found and fixed

### Bug 1 — Authorisation bypass on `POST /orders` (critical)

**Found by:** auditing the entire route table rather than testing endpoints
individually.

Unlike every other wallet route, `POST /orders` takes `wallet_id` in the
request **body**, so it never passed through the path-based `WalletIdDep`:

```bash
# No token at all. Someone else's wallet.
curl -X POST /orders -d '{"wallet_id":"<victims>","symbol":"INFY","side":"BUY","quantity":10}'
→ HTTP 201 FILLED
```

**Fix:**

```python
wallet_id = auth.authorize_wallet(current_user, request.wallet_id)
```

**Verified:** 401 unauthenticated, 403 cross-account, victim's balance
untouched, legitimate trading unaffected.

**The lesson.** 33 auth tests passed while this was live. The gap was
*structural*, so the fix is too: `test_route_security.py` now makes it
impossible to add an unprotected endpoint without failing the build.

---

### Bug 2 — Cost basis did not reset on position close

**Found by:** probing domain arithmetic with edge cases during this review.

`avg_cost()` averaged over every historical BUY and ignored SELLs entirely:

```python
# Buy 10 @ 1650 → sell all 10 → buy 1 @ 2000
avg_cost  = 1109.09      # WRONG: blends the closed round-trip
pnl       = +890.91      # phantom profit on a position opened seconds ago
```

Anyone who round-tripped a stock saw wrong Invested, P&L and Net Chg. figures.

**Fix.** A running weighted average, replayed chronologically. A SELL retires
cost proportionally; closing the position empties the pool so a re-entry starts
fresh. This is the standard **moving-average cost method** used by brokers.

```python
avg_cost  = 2000.00      # correct
pnl       = 0.00         # correct — you just bought at the market price
```

**Blast radius.** The frontend reads `avg_cost` from the API rather than
recomputing it, so the correction propagated to the whole dashboard with no
client change. **8 new tests**, four of which failed before the fix.

---

### Bug 3 — Frontend stranded on an unrecoverable 401

When a token refresh failed — for instance after signing out from another
device — the user was left on a dashboard where every request silently errored.
Now `authFetch` clears the session and falls back to the login screen. 7 new
tests cover the refresh paths.

---

### Bug 4 — `logout-all` locked users out of signing back in

JWT `iat` is **integer epoch seconds**, but the revocation cutoff was stored
with microsecond precision — so a token issued microseconds *after* the cutoff
compared as *older* and was rejected.

Truncating the cutoff fixed that but broke the opposite case: sessions created
in the same second survived revocation. The two requirements genuinely conflict
at one-second resolution.

**Resolution.** A successful password login clears the cutoff — proving the
password re-establishes exactly the trust `logout-all` withdrew. Both
directions are now tested.

---

### Bug 5 — Non-idempotent migration

Three legacy trades had no `trade_id`, so each run minted a fresh UUID and
re-inserted them. Fixed with a deterministic `uuid5` derived from the trade's
natural key. Caught only by running the migration three times and diffing the
counts rather than trusting the first "success".

---

### Bug 6 — Missing runtime dependencies

`pyjwt`, `passlib`, `bcrypt` and `pydantic[email]` were absent from
`pyproject.toml`. Local development worked because they were in the venv; a
clean install crashed on import, so the Docker image would have failed at
startup. Caught by simulating the image build in a fresh virtualenv.

---

## 31. Known limitations

Knowing what you have *not* built matters as much as what you have.

| Limitation | Impact | Fix |
|---|---|---|
| **In-process rate limiting** | N replicas allow N× the budget | Redis `INCR`/`EXPIRE` |
| **In-process market cache** | Each replica fetches separately | Redis with a shared TTL |
| **Blocklist grows until purged** | `purge_expired()` exists but is unscheduled | Cron or startup task |
| **No refresh-reuse alarm** | A replayed token 401s but raises no alert | Detect reuse, revoke the family |
| **`localStorage` tokens** | XSS-readable | `httpOnly` cookies + CSRF |
| **No email verification** | Anyone can register any address | Verification link flow |
| **No password reset** | Locked out permanently | Time-limited reset token |
| **Unbounded history queries** | `load_trades()` fetches all rows, paginates in Python | Push `LIMIT`/`OFFSET` into SQL |
| **No event snapshots** | Replay is O(n) in wallet events | Snapshot every N events |
| **Sync DB driver** | Handlers are `async` but I/O is sync (thread pool) | `asyncpg` + async SQLAlchemy |
| **Not deployed** | No public URL | Fly.io / Railway / Render |
| **yfinance untested live** | Sandbox blocks outbound TLS | Verify on first real run |
| **Docker unbuilt** | No Docker in the sandbox | `docker compose up` locally |

The last three are environmental, not design gaps.

---

# Part X — Mastery

## 32. Interview question bank

**"Walk me through the architecture."**
> Hexagonal, four layers. The domain holds business rules and imports only the
> standard library — no FastAPI, no SQLAlchemy. It declares what it needs as
> `typing.Protocol` ports; infrastructure implements them; the API injects them
> per request. That is why the test suite runs with no database and no network:
> every port has an in-memory implementation. CI enforces the boundary with an
> AST check, because it is the property most likely to erode quietly.

**"Why is the wallet event-sourced but not the positions?"**
> The balance is replayed from an immutable log, which for money is the point:
> a permanent audit trail, and a balance that cannot drift from its history.
> Positions are derivable from trades and do not need that guarantee, so they
> use plain state. Applying the pattern everywhere would be cargo-culting — and
> replay is O(n), which is a real cost.

**"How do you prevent a double charge on a retry?"**
> Every mutating request carries an `X-Transaction-ID`. The wallet checks
> whether that id already exists before appending an event, and the database
> enforces `UNIQUE(wallet_id, transaction_id)` so it holds under concurrency.
> If the network drops after the server commits, the client's retry is a no-op.
> There is a test that fires the same buy twice and asserts the balance moved
> once.

**"How do you revoke a stateless JWT?"**
> You cannot revoke the token itself, so you keep a server-side record of the
> ones you have withdrawn. Individual sign-out stores the `jti` until natural
> expiry; sign-out-everywhere writes a single per-user cutoff rather than one
> row per token. Refresh tokens also rotate, so redeeming one revokes it. The
> subtle part was that `iat` is integer seconds while my cutoff had microsecond
> precision — signing back in within the same second locked the user out.
> Clearing the cutoff on a successful password login fixed it.

**"Why `Decimal` instead of `float`?"**
> Binary floating point cannot represent `0.1` exactly, so `0.1 + 0.2` gives
> `0.30000000000000004`. In a ledger those errors accumulate. Money is
> `Decimal` in Python and `Numeric(20,4)` in the database, all the way through.

**"Tell me about a bug you found in your own code."**
> Two worth telling. `POST /orders` shipped with no authorisation at all — it
> takes `wallet_id` in the body, so it bypassed the path dependency that
> secures every other route. Thirty-three auth tests passed because each
> covered a route I had remembered to secure. The fix was structural: an audit
> test that walks the whole route table.
>
> The other was cost basis. It averaged over all historical buys, so after
> selling out and re-entering at a new price it reported phantom profit. Fixed
> with a running weighted average that resets when the position closes.

**"How would you scale this?"**
> Three bottlenecks in order. The rate limiter and token blocklist are
> in-process, so they break with more than one replica — Redis fixes both.
> History queries fetch all rows and paginate in Python; that needs `LIMIT`
> pushed into SQL. And event replay is O(n), so at millions of events you need
> snapshots. The database itself is already Postgres-ready via one env var.

**"What would you do differently?"**
> Introduce the ports on day one. The original had entities persisting
> themselves by writing JSON files, and three tests were already failing
> because of it. Retrofitting the boundary was more work than designing it in —
> and the failing tests were a symptom nobody had traced back to the
> architecture.

**"What is the weakest part of this codebase?"**
> Single-process state. The rate limiter and blocklist both assume one
> instance, which quietly becomes wrong the moment you scale horizontally —
> and it fails *open* (more requests allowed), which is the bad direction. It
> is documented rather than hidden, but it is the thing I would fix first.

---

## 33. File-by-file reference

### Backend (42 files, 5,561 lines)

| File | Lines | Purpose |
|---|---|---|
| `domain/ports.py` | 392 | Protocols + in-memory fakes |
| `domain/order_engine.py` | 276 | Validation and execution |
| `domain/portfolio.py` | 250 | Positions, valuation, P&L |
| `domain/order.py` | 157 | Order entity and lifecycle |
| `domain/user.py` | 114 | User and ownership entities |
| `domain/wallet.py` | 101 | Event-sourced ledger |
| `domain/exceptions.py` | 100 | Error hierarchy |
| `domain/events.py` | 75 | Ledger events |
| `domain/market.py` | 32 | Lazy compatibility shim |
| `domain/trade.py` | 20 | Immutable trade record |
| `application/auth_service.py` | 335 | Auth use cases |
| `application/history_service.py` | 307 | Paginated history |
| `application/handlers/__init__.py` | 147 | Command handlers |
| `application/portfolio_service.py` | 91 | Portfolio snapshot |
| `application/queries/history_dtos.py` | 73 | Read DTOs |
| `infra/db/repositories.py` | 403 | Port implementations |
| `infra/db/models.py` | 185 | SQLAlchemy tables |
| `infra/db/session.py` | 117 | Engine and sessions |
| `infra/security.py` | 204 | bcrypt + JWT |
| `infra/market.py` | 162 | Market data providers |
| `infra/rate_limit.py` | 148 | Fixed-window throttling |
| `infra/logging.py` | 104 | Structured logging |
| `api/deps.py` | 282 | Dependency injection |
| `api/market.py` | 275 | Market endpoints |
| `api/auth.py` | 206 | Auth endpoints |
| `api/schemas.py` | 200 | Request/response models |
| `api/errors.py` | 184 | RFC 9457 handlers |
| `api/portfolio.py` | 154 | Portfolio endpoints |
| `api/main.py` | 124 | App factory, middleware |
| `api/orders.py` | 124 | Order endpoints |
| `api/history.py` | 82 | History endpoints |
| `scripts/migrate_json_to_db.py` | 267 | Idempotent JSON → SQL |
| `scripts/check_architecture.py` | 88 | AST boundary check |

### Frontend (78 files, 8,704 lines)

| File | Purpose |
|---|---|
| `App.jsx` | Providers, auth gate, page routing |
| `styles/tokens.css` | The entire design system |
| `lib/apiClient.js` | Fetch wrapper, `ApiError`, token refresh |
| `lib/portfolioMath.js` | Pure P&L calculations |
| `lib/queryClient.js` | Query keys and cache policy |
| `lib/format.js` | Currency, percent, date formatting |
| `lib/devBus.js` | Developer inspector event bus |
| `stores/useAuthStore.js` | Tokens and user (persisted) |
| `stores/useSessionStore.js` | Wallet and ticket state |
| `hooks/useAuth.js` | Register, login, logout |
| `hooks/usePortfolio.js` | Summary, quotes, history |
| `hooks/useMarket.js` | Search, quote, chart |
| `hooks/useMarketHours.js` | NSE sessions and poll cadence |
| `pages/AuthPage.jsx` | Sign-in and registration |
| `pages/PortfolioPage.jsx` | Dashboard (108 lines of composition) |
| `components/trade/OrderTicket.jsx` | Search → quote → chart → entry |
| `components/portfolio/HoldingsTable.jsx` | Holdings with totals |
| `components/chart/TradingChart.jsx` | Lightweight Charts, theme-aware |
| `components/ui/*` | 10 design-system primitives |

---

## 34. Glossary

**Adapter** — a concrete implementation of a port. `SqlEventStore` adapts SQL
to the `EventStore` interface.

**Aggregate** — a cluster of objects treated as one unit for data changes, with
a root that guards invariants. `Portfolio` is an aggregate; you cannot modify
its positions except through its methods.

**ASGI** — Asynchronous Server Gateway Interface. The async successor to WSGI.

**AST** — Abstract Syntax Tree. The parsed structure of source code. Used here
to check imports reliably rather than by grepping text.

**bcrypt** — a deliberately slow, salted password hashing function.

**CQRS** — Command Query Responsibility Segregation. Separate read and write
paths.

**CSRF** — Cross-Site Request Forgery. An attack where another site makes
authenticated requests using your cookies. Relevant only to cookie auth.

**Dependency injection** — supplying a component's collaborators from outside
rather than having it construct them.

**DTO** — Data Transfer Object. A plain shape for moving data across a
boundary.

**Event sourcing** — storing state as a sequence of events and deriving current
state by replaying them.

**Hexagonal architecture** — ports and adapters. Business logic at the centre,
I/O at the edges.

**Idempotency** — performing an operation twice has the same effect as once.

**JWT** — JSON Web Token. A signed, self-contained token.

**`jti`** — JWT ID claim. A unique token identifier, used for revocation.

**Port** — an interface the domain declares, describing a capability it needs.

**Problem+JSON** — RFC 9457. A standard error-response format.

**Protocol** — Python's structural typing mechanism. Satisfied by shape, not
inheritance.

**Rainbow table** — a precomputed hash lookup table. Defeated by salting.

**Tabular figures** — a font feature giving every digit the same width.

**XSS** — Cross-Site Scripting. Injected JavaScript running in your page.
Relevant to `localStorage` token storage.

---

## Quick reference

```bash
# Run
python -m quantnest.main                                  # API :8000
cd frontend && npm run dev                                # UI  :5173
docker compose up --build                                 # both

# Test
QUANTNEST_MARKET_PROVIDER=fake pytest -q                  # 142 backend
cd frontend && npm test                                   # 35 frontend
cd frontend && npm run lint

# Verify invariants
python scripts/check_architecture.py                      # DDD boundary
QUANTNEST_MARKET_PROVIDER=fake pytest tests/integration/test_route_security.py -q

# Data
python scripts/migrate_json_to_db.py --dry-run
openssl rand -hex 32                                      # JWT_SECRET_KEY
```

| Metric | Value |
|---|---|
| Backend | 42 files, 5,561 lines |
| Frontend | 78 files, 8,704 lines |
| Tests | 177 (142 backend, 35 frontend) |
| Endpoints | 29 |
| Tables | 8 |
| Runtime dependencies | 6 frontend, 9 backend |
