"""Authorisation on POST /orders.

This endpoint takes ``wallet_id`` in the request *body*, so it never passes
through the path-based ``WalletIdDep`` that secures every other wallet route.
That made it the one hole in the ownership model.
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
from quantnest.infra.rate_limit import reset_limiters


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    reset_limiters()
    yield
    reset_limiters()


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
    market = StaticMarketDataProvider({"INFY": Decimal("1650.00")})

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
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def register(client, email):
    response = client.post(
        "/auth/register", json={"email": email, "password": "s3cret-passphrase"}
    )
    assert response.status_code == 201
    return response.json()


def headers(session):
    return {"Authorization": f"Bearer {session['access_token']}"}


def test_place_order_requires_authentication(client):
    response = client.post(
        "/orders", json={"wallet_id": "anything", "symbol": "INFY", "side": "BUY", "quantity": 1}
    )
    assert response.status_code == 401


def test_cannot_place_an_order_on_someone_elses_wallet(client):
    """The body-supplied wallet_id must still be ownership-checked."""
    alice = register(client, "alice@example.com")
    bob = register(client, "bob@example.com")

    bob_wallet = bob["user"]["wallets"][0]
    client.post(
        f"/portfolio/{bob_wallet}/credit", json={"amount": 100000}, headers=headers(bob)
    )

    attack = client.post(
        "/orders",
        json={"wallet_id": bob_wallet, "symbol": "INFY", "side": "BUY", "quantity": 10},
        headers=headers(alice),
    )

    assert attack.status_code == 403, "a user must not trade on another user's wallet"

    # Bob's money must be untouched.
    summary = client.get(f"/portfolio/{bob_wallet}/summary", headers=headers(bob)).json()
    assert summary["cash"] == 100000.0
    assert summary["positions"] == {}


def test_can_place_an_order_on_your_own_wallet(client):
    alice = register(client, "alice@example.com")
    wallet = alice["user"]["wallets"][0]

    client.post(f"/portfolio/{wallet}/credit", json={"amount": 100000}, headers=headers(alice))

    response = client.post(
        "/orders",
        json={"wallet_id": wallet, "symbol": "INFY", "side": "BUY", "quantity": 5},
        headers=headers(alice),
    )

    assert response.status_code == 201
    assert response.json()["status"] == "FILLED"


def test_ordering_on_an_unknown_wallet_is_refused(client):
    alice = register(client, "alice@example.com")

    response = client.post(
        "/orders",
        json={"wallet_id": "no-such-wallet", "symbol": "INFY", "side": "BUY", "quantity": 1},
        headers=headers(alice),
    )
    assert response.status_code == 403
