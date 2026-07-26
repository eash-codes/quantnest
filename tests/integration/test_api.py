"""API integration tests.

Exercise the whole stack — routing, validation, dependency injection, the
domain and SQL persistence — against an in-memory database and a deterministic
market provider.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from quantnest.api.deps import get_db_session, get_market
from quantnest.api.main import create_app
from quantnest.domain.ports import StaticMarketDataProvider
from quantnest.infra.db.models import Base


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

    market = StaticMarketDataProvider(
        {
            "RELIANCE": Decimal("2500.00"),
            "TCS": Decimal("3800.00"),
            "INFY": Decimal("1650.00"),
        }
    )

    def override_session():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_market] = lambda: market

    with TestClient(app) as test_client:
        test_client.market = market
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


# ── Meta ─────────────────────────────────────────────────────────────────


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_every_response_carries_a_request_id(client):
    response = client.get("/health")
    assert response.headers.get("X-Request-ID")


# ── Core loop ────────────────────────────────────────────────────────────


def test_full_trading_loop(client):
    """Credit -> quote -> buy -> verify portfolio -> sell -> verify again."""
    wallet = "loop-user"

    credit = client.post(f"/portfolio/{wallet}/credit", json={"amount": 100000})
    assert credit.status_code == 200
    assert credit.json()["new_balance"] == 100000.0

    quote = client.get("/market/quote/INFY")
    assert quote.status_code == 200
    assert quote.json()["ltp"] == 1650.0

    buy = client.post(f"/portfolio/{wallet}/buy", json={"symbol": "INFY", "quantity": 10})
    assert buy.status_code == 200
    body = buy.json()
    assert body["success"] is True
    assert body["order_status"] == "FILLED"
    assert body["portfolio_summary"]["cash"] == 83500.0  # 100000 - 16500

    summary = client.get(f"/portfolio/{wallet}/summary").json()
    assert summary["positions"] == {"INFY": 10.0}
    assert summary["avg_cost"]["INFY"] == 1650.0
    assert summary["cash"] == 83500.0

    sell = client.post(f"/portfolio/{wallet}/sell", json={"symbol": "INFY", "quantity": 4})
    assert sell.status_code == 200
    assert sell.json()["success"] is True

    final = client.get(f"/portfolio/{wallet}/summary").json()
    assert final["positions"] == {"INFY": 6.0}
    assert final["cash"] == 90100.0  # 83500 + 4 × 1650


def test_trade_appears_in_history(client):
    wallet = "history-user"
    client.post(f"/portfolio/{wallet}/credit", json={"amount": 50000})
    client.post(f"/portfolio/{wallet}/buy", json={"symbol": "INFY", "quantity": 2})

    trades = client.get(f"/history/portfolio/{wallet}/trades").json()
    assert trades["total"] == 1
    assert trades["items"][0]["symbol"] == "INFY"
    assert trades["items"][0]["side"] == "BUY"

    orders = client.get(f"/history/portfolio/{wallet}/orders").json()
    assert orders["total"] == 1
    assert orders["items"][0]["status"] == "FILLED"

    events = client.get(f"/history/wallet/{wallet}/events").json()
    assert events["total"] == 2  # the credit plus the buy's debit


def test_batch_quotes(client):
    response = client.get("/market/quotes", params={"symbols": "INFY,RELIANCE"})
    assert response.status_code == 200

    body = response.json()
    assert body["INFY"]["ltp"] == 1650.0
    assert body["RELIANCE"]["ltp"] == 2500.0


def test_batch_quotes_report_unknown_symbols_inline(client):
    body = client.get("/market/quotes", params={"symbols": "INFY,NOPE"}).json()

    assert body["INFY"]["ltp"] == 1650.0
    assert body["NOPE"]["ltp"] is None
    assert "error" in body["NOPE"]


# ── Business rules ───────────────────────────────────────────────────────


def test_buy_without_funds_returns_a_rejection(client):
    wallet = "poor-user"
    client.post(f"/portfolio/{wallet}/credit", json={"amount": 1000})

    response = client.post(f"/portfolio/{wallet}/buy", json={"symbol": "RELIANCE", "quantity": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["order_status"] == "REJECTED"
    assert "Insufficient funds" in body["message"]


def test_overdrawing_the_wallet_returns_409(client):
    wallet = "overdraw"
    client.post(f"/portfolio/{wallet}/credit", json={"amount": 100})

    response = client.post(f"/portfolio/{wallet}/debit", json={"amount": 500})

    assert response.status_code == 409
    problem = response.json()
    assert problem["title"] == "Insufficient funds"
    assert problem["type"] == "insufficient_funds"
    assert problem["status"] == 409


def test_unknown_symbol_quote_returns_404(client):
    response = client.get("/market/quote/NOSUCHTICKER")

    assert response.status_code == 404
    assert response.json()["type"] == "unknown_symbol"


# ── Validation ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "payload",
    [
        {"symbol": "INFY", "quantity": 0},
        {"symbol": "INFY", "quantity": -5},
        {"symbol": "", "quantity": 1},
        {"symbol": "IN FY", "quantity": 1},
        {"symbol": "INFY"},
        {"quantity": 1},
        {"symbol": "INFY", "quantity": 1, "unexpected": "field"},
    ],
)
def test_invalid_trade_payloads_are_rejected(client, payload):
    response = client.post("/portfolio/val-user/buy", json=payload)

    assert response.status_code == 422
    assert response.json()["type"] == "validation_error"


@pytest.mark.parametrize("amount", [0, -100])
def test_non_positive_amounts_are_rejected(client, amount):
    response = client.post("/portfolio/val-user/credit", json={"amount": amount})
    assert response.status_code == 422


def test_symbols_are_normalised_to_uppercase(client):
    wallet = "case-user"
    client.post(f"/portfolio/{wallet}/credit", json={"amount": 50000})

    response = client.post(f"/portfolio/{wallet}/buy", json={"symbol": "infy", "quantity": 1})

    assert response.status_code == 200
    assert client.get(f"/portfolio/{wallet}/summary").json()["positions"] == {"INFY": 1.0}


# ── Idempotency ──────────────────────────────────────────────────────────


def test_credit_is_idempotent_across_requests(client):
    wallet = "idem-user"
    headers = {"X-Transaction-ID": "fixed-tx-001"}

    first = client.post(f"/portfolio/{wallet}/credit", json={"amount": 5000}, headers=headers)
    second = client.post(f"/portfolio/{wallet}/credit", json={"amount": 5000}, headers=headers)

    assert first.json()["new_balance"] == 5000.0
    assert second.json()["new_balance"] == 5000.0
    assert client.get(f"/portfolio/{wallet}/summary").json()["cash"] == 5000.0


# ── Error contract ───────────────────────────────────────────────────────


def test_errors_never_leak_internals(client):
    """Error bodies must be problem+json and free of tracebacks."""
    response = client.get("/portfolio/unknown-wallet/summary")
    assert response.status_code == 200  # an unknown wallet is simply empty

    bad = client.post("/portfolio/x/credit", json={"amount": "not-a-number"})
    assert bad.status_code == 422

    body = bad.json()
    assert set(body) >= {"type", "title", "status", "detail"}

    serialised = str(body).lower()
    assert "traceback" not in serialised
    assert "file \"/" not in serialised


def test_unknown_route_returns_problem_json(client):
    response = client.get("/does/not/exist")
    assert response.status_code == 404
    assert response.json()["title"] == "Not found"


# ── Orders API ───────────────────────────────────────────────────────────


def test_place_order_via_orders_endpoint(client):
    wallet = "oms-user"
    client.post(f"/portfolio/{wallet}/credit", json={"amount": 100000})

    response = client.post(
        "/orders",
        json={"wallet_id": wallet, "symbol": "TCS", "side": "BUY", "quantity": 2},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "FILLED"
    assert body["symbol"] == "TCS"

    fetched = client.get(f"/orders/{wallet}/{body['order_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["order_id"] == body["order_id"]


def test_fetching_a_missing_order_returns_404(client):
    response = client.get("/orders/oms-user/no-such-order")

    assert response.status_code == 404
    assert response.json()["type"] == "order_not_found"
