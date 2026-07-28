"""Authentication and authorisation tests.

The most important case here is cross-account isolation: before auth existed,
any caller could read or trade any wallet by editing the URL.
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
from quantnest.infra.security import JwtTokenService


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """The limiter is a process-wide singleton; clear it between tests."""
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

    market = StaticMarketDataProvider(
        {"INFY": Decimal("1650.00"), "TCS": Decimal("3800.00")}
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
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def register(client, email="trader@example.com", password="s3cret-passphrase"):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": password, "display_name": "Trader"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(session):
    return {"Authorization": f"Bearer {session['access_token']}"}


# ── Registration ─────────────────────────────────────────────────────────


def test_register_returns_tokens_and_provisions_a_wallet(client):
    body = register(client)

    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["email"] == "trader@example.com"
    # Every new account gets exactly one wallet.
    assert len(body["user"]["wallets"]) == 1


def test_email_is_normalised_to_lowercase(client):
    body = register(client, email="MiXeD@Example.COM")
    assert body["user"]["email"] == "mixed@example.com"


def test_duplicate_email_is_rejected(client):
    register(client)
    response = client.post(
        "/auth/register",
        json={"email": "trader@example.com", "password": "another-password"},
    )

    assert response.status_code == 409
    assert response.json()["type"] == "email_already_registered"


def test_duplicate_email_is_case_insensitive(client):
    register(client, email="user@example.com")
    response = client.post(
        "/auth/register",
        json={"email": "USER@EXAMPLE.COM", "password": "another-password"},
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "s3cret-passphrase"},
        {"email": "a@b.co", "password": "short"},
        {"email": "a@b.co"},
        {"password": "s3cret-passphrase"},
        {"email": "a@b.co", "password": "s3cret-passphrase", "role": "admin"},
    ],
)
def test_invalid_registration_payloads_are_rejected(client, payload):
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 422


def test_password_is_never_returned(client):
    body = register(client)
    serialised = str(body).lower()
    assert "password" not in serialised
    assert "s3cret" not in serialised


# ── Login ────────────────────────────────────────────────────────────────


def test_login_with_correct_credentials(client):
    register(client)
    response = client.post(
        "/auth/login",
        json={"email": "trader@example.com", "password": "s3cret-passphrase"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_with_wrong_password_fails(client):
    register(client)
    response = client.post(
        "/auth/login",
        json={"email": "trader@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["type"] == "authentication_failed"


def test_unknown_email_and_wrong_password_are_indistinguishable(client):
    """The API must not leak which accounts exist."""
    register(client)

    unknown = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever-long"}
    )
    wrong = client.post(
        "/auth/login", json={"email": "trader@example.com", "password": "wrong-password"}
    )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


# ── Protected routes ─────────────────────────────────────────────────────


def test_protected_route_requires_a_token(client):
    response = client.get("/portfolio/some-wallet/summary")

    assert response.status_code == 401
    assert response.json()["type"] == "authentication_failed"


def test_protected_route_rejects_a_garbage_token(client):
    response = client.get(
        "/portfolio/some-wallet/summary",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


def test_protected_route_rejects_an_expired_token(client):
    session = register(client)
    wallet = session["user"]["wallets"][0]

    # Mint a token that expired an hour ago using the same signing key.
    from quantnest.infra.security import get_token_service

    expired_service = JwtTokenService(
        secret_key=get_token_service()._secret, access_ttl_minutes=-60
    )
    expired = expired_service.issue_access_token(session["user"]["user_id"])

    response = client.get(
        f"/portfolio/{wallet}/summary", headers={"Authorization": f"Bearer {expired}"}
    )

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_refresh_token_cannot_be_used_as_an_access_token(client):
    """The ``type`` claim must prevent this substitution."""
    session = register(client)
    wallet = session["user"]["wallets"][0]

    response = client.get(
        f"/portfolio/{wallet}/summary",
        headers={"Authorization": f"Bearer {session['refresh_token']}"},
    )
    assert response.status_code == 401


def test_authenticated_user_can_read_their_own_wallet(client):
    session = register(client)
    wallet = session["user"]["wallets"][0]

    response = client.get(f"/portfolio/{wallet}/summary", headers=auth_headers(session))

    assert response.status_code == 200
    assert response.json()["wallet_id"] == wallet


# ── Cross-account isolation ──────────────────────────────────────────────


def test_a_user_cannot_read_another_users_wallet(client):
    alice = register(client, email="alice@example.com")
    bob = register(client, email="bob@example.com")

    bob_wallet = bob["user"]["wallets"][0]

    response = client.get(
        f"/portfolio/{bob_wallet}/summary", headers=auth_headers(alice)
    )

    assert response.status_code == 403
    assert response.json()["type"] == "not_authorized"


def test_a_user_cannot_trade_on_another_users_wallet(client):
    alice = register(client, email="alice@example.com")
    bob = register(client, email="bob@example.com")

    bob_wallet = bob["user"]["wallets"][0]
    client.post(
        f"/portfolio/{bob_wallet}/credit",
        json={"amount": 100000},
        headers=auth_headers(bob),
    )

    attack = client.post(
        f"/portfolio/{bob_wallet}/buy",
        json={"symbol": "INFY", "quantity": 10},
        headers=auth_headers(alice),
    )

    assert attack.status_code == 403

    # Bob's cash must be untouched.
    summary = client.get(
        f"/portfolio/{bob_wallet}/summary", headers=auth_headers(bob)
    ).json()
    assert summary["cash"] == 100000.0
    assert summary["positions"] == {}


def test_a_user_cannot_credit_another_users_wallet(client):
    alice = register(client, email="alice@example.com")
    bob = register(client, email="bob@example.com")

    response = client.post(
        f"/portfolio/{bob['user']['wallets'][0]}/credit",
        json={"amount": 5000},
        headers=auth_headers(alice),
    )
    assert response.status_code == 403


def test_a_user_cannot_read_another_users_history(client):
    alice = register(client, email="alice@example.com")
    bob = register(client, email="bob@example.com")

    bob_wallet = bob["user"]["wallets"][0]

    for path in (
        f"/history/portfolio/{bob_wallet}/trades",
        f"/history/portfolio/{bob_wallet}/orders",
        f"/history/wallet/{bob_wallet}/events",
    ):
        assert client.get(path, headers=auth_headers(alice)).status_code == 403


def test_nonexistent_wallet_is_indistinguishable_from_a_foreign_one(client):
    """Both must return 403, so the API cannot be used to probe for wallets."""
    alice = register(client, email="alice@example.com")

    response = client.get(
        "/portfolio/some-wallet-that-does-not-exist/summary",
        headers=auth_headers(alice),
    )
    assert response.status_code == 403


# ── Session management ───────────────────────────────────────────────────


def test_refresh_issues_a_working_token_pair(client):
    session = register(client)

    refreshed = client.post(
        "/auth/refresh", json={"refresh_token": session["refresh_token"]}
    )
    assert refreshed.status_code == 200

    new_session = refreshed.json()
    wallet = new_session["user"]["wallets"][0]

    response = client.get(
        f"/portfolio/{wallet}/summary", headers=auth_headers(new_session)
    )
    assert response.status_code == 200


def test_access_token_cannot_be_used_to_refresh(client):
    session = register(client)
    response = client.post(
        "/auth/refresh", json={"refresh_token": session["access_token"]}
    )
    assert response.status_code == 401


def test_me_returns_the_current_profile(client):
    session = register(client)

    response = client.get("/auth/me", headers=auth_headers(session))

    assert response.status_code == 200
    assert response.json()["email"] == "trader@example.com"


def test_me_requires_authentication(client):
    assert client.get("/auth/me").status_code == 401


# ── Multiple wallets ─────────────────────────────────────────────────────


def test_a_user_can_create_and_use_a_second_wallet(client):
    session = register(client)

    created = client.post(
        "/auth/wallets",
        json={"wallet_id": "swing-trades", "label": "Swing"},
        headers=auth_headers(session),
    )
    assert created.status_code == 201

    listed = client.get("/auth/wallets", headers=auth_headers(session)).json()
    assert len(listed) == 2

    response = client.get(
        "/portfolio/swing-trades/summary", headers=auth_headers(session)
    )
    assert response.status_code == 200


def test_wallet_ids_cannot_be_claimed_twice(client):
    alice = register(client, email="alice@example.com")
    bob = register(client, email="bob@example.com")

    client.post(
        "/auth/wallets", json={"wallet_id": "shared-name"}, headers=auth_headers(alice)
    )
    response = client.post(
        "/auth/wallets", json={"wallet_id": "shared-name"}, headers=auth_headers(bob)
    )

    assert response.status_code == 409


# ── Public routes ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    ["/health", "/", "/market/quote/INFY", "/market/search?q=INF"],
)
def test_public_routes_remain_open(client, path):
    """Market data is not wallet-scoped, so it needs no token."""
    assert client.get(path).status_code == 200
