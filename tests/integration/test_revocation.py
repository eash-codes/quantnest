"""Token revocation and rate limiting.

These cover the two gaps documented as known limitations in v11.1.0:
a stateless JWT stayed valid until expiry, and the login form was
brute-forceable.
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
from quantnest.infra.rate_limit import (
    get_login_limiter,
    get_register_limiter,
    reset_limiters,
)


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


def register(client, email="trader@example.com", password="s3cret-passphrase"):
    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    return response.json()


def headers(session):
    return {"Authorization": f"Bearer {session['access_token']}"}


# ── Sign out ─────────────────────────────────────────────────────────────


def test_token_works_before_logout(client):
    session = register(client)
    wallet = session["user"]["wallets"][0]

    assert client.get(f"/portfolio/{wallet}/summary", headers=headers(session)).status_code == 200


def test_logout_revokes_the_access_token(client):
    """The core fix: a signed-out token must stop working immediately."""
    session = register(client)
    wallet = session["user"]["wallets"][0]

    assert client.post("/auth/logout", json={}, headers=headers(session)).status_code == 204

    response = client.get(f"/portfolio/{wallet}/summary", headers=headers(session))
    assert response.status_code == 401
    assert "signed out" in response.json()["detail"].lower()


def test_logout_also_revokes_the_refresh_token_when_supplied(client):
    session = register(client)

    client.post(
        "/auth/logout",
        json={"refresh_token": session["refresh_token"]},
        headers=headers(session),
    )

    refreshed = client.post(
        "/auth/refresh", json={"refresh_token": session["refresh_token"]}
    )
    assert refreshed.status_code == 401


def test_logout_requires_authentication(client):
    assert client.post("/auth/logout", json={}).status_code == 401


def test_logout_is_idempotent(client):
    """Signing out twice must succeed, not error.

    /auth/logout only needs the raw token, not a revocation check, so a repeat
    call is absorbed: re-revoking the same jti is a no-op at the storage layer.
    A client retrying after a dropped response therefore sees success.
    """
    session = register(client)
    wallet = session["user"]["wallets"][0]

    assert client.post("/auth/logout", json={}, headers=headers(session)).status_code == 204
    assert client.post("/auth/logout", json={}, headers=headers(session)).status_code == 204

    # The token is genuinely dead for everything that matters.
    assert client.get(f"/portfolio/{wallet}/summary", headers=headers(session)).status_code == 401


def test_logout_does_not_affect_other_sessions(client):
    """Signing out one device must leave the others alone."""
    register(client)

    first = client.post(
        "/auth/login",
        json={"email": "trader@example.com", "password": "s3cret-passphrase"},
    ).json()
    second = client.post(
        "/auth/login",
        json={"email": "trader@example.com", "password": "s3cret-passphrase"},
    ).json()

    wallet = first["user"]["wallets"][0]

    client.post("/auth/logout", json={}, headers=headers(first))

    assert client.get(f"/portfolio/{wallet}/summary", headers=headers(first)).status_code == 401
    assert client.get(f"/portfolio/{wallet}/summary", headers=headers(second)).status_code == 200


def test_logout_does_not_affect_other_users(client):
    alice = register(client, email="alice@example.com")
    bob = register(client, email="bob@example.com")

    client.post("/auth/logout", json={}, headers=headers(alice))

    bob_wallet = bob["user"]["wallets"][0]
    assert client.get(f"/portfolio/{bob_wallet}/summary", headers=headers(bob)).status_code == 200


# ── Sign out everywhere ──────────────────────────────────────────────────


def test_logout_all_revokes_every_session(client):
    register(client)

    sessions = [
        client.post(
            "/auth/login",
            json={"email": "trader@example.com", "password": "s3cret-passphrase"},
        ).json()
        for _ in range(3)
    ]
    wallet = sessions[0]["user"]["wallets"][0]

    for session in sessions:
        assert client.get(f"/portfolio/{wallet}/summary", headers=headers(session)).status_code == 200

    assert client.post("/auth/logout-all", headers=headers(sessions[0])).status_code == 204

    for index, session in enumerate(sessions):
        response = client.get(f"/portfolio/{wallet}/summary", headers=headers(session))
        assert response.status_code == 401, f"session {index} survived logout-all"


def test_a_new_login_works_after_logout_all(client):
    """The cutoff must not lock the account out permanently."""
    session = register(client)
    client.post("/auth/logout-all", headers=headers(session))

    fresh = client.post(
        "/auth/login",
        json={"email": "trader@example.com", "password": "s3cret-passphrase"},
    )
    assert fresh.status_code == 200

    wallet = fresh.json()["user"]["wallets"][0]
    assert client.get(f"/portfolio/{wallet}/summary", headers=headers(fresh.json())).status_code == 200


def test_logout_all_does_not_affect_other_users(client):
    alice = register(client, email="alice@example.com")
    bob = register(client, email="bob@example.com")

    client.post("/auth/logout-all", headers=headers(alice))

    bob_wallet = bob["user"]["wallets"][0]
    assert client.get(f"/portfolio/{bob_wallet}/summary", headers=headers(bob)).status_code == 200


# ── Refresh-token rotation ───────────────────────────────────────────────


def test_refresh_rotates_the_token(client):
    """A redeemed refresh token must not be reusable."""
    session = register(client)

    first = client.post("/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert first.status_code == 200

    replay = client.post("/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert replay.status_code == 401


def test_the_rotated_token_works(client):
    session = register(client)

    rotated = client.post(
        "/auth/refresh", json={"refresh_token": session["refresh_token"]}
    ).json()

    again = client.post("/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert again.status_code == 200


# ── Rate limiting ────────────────────────────────────────────────────────


def test_repeated_failed_logins_are_throttled(client):
    register(client)
    limit = get_login_limiter()._max

    statuses = [
        client.post(
            "/auth/login",
            json={"email": "trader@example.com", "password": "wrong-password"},
        ).status_code
        for _ in range(limit + 3)
    ]

    assert 401 in statuses, "early attempts should be plain auth failures"
    assert 429 in statuses, "the limiter should eventually reject"
    assert statuses[-1] == 429


def test_a_throttled_response_says_when_to_retry(client):
    register(client)
    limit = get_login_limiter()._max

    response = None
    for _ in range(limit + 2):
        response = client.post(
            "/auth/login",
            json={"email": "trader@example.com", "password": "wrong-password"},
        )

    assert response.status_code == 429
    assert response.json()["type"] == "rate_limit_exceeded"
    assert int(response.headers["Retry-After"]) > 0


def test_a_successful_login_clears_the_throttle(client):
    """One user's failures must not lock out another behind the same NAT."""
    register(client)
    limit = get_login_limiter()._max

    for _ in range(limit - 1):
        client.post(
            "/auth/login",
            json={"email": "trader@example.com", "password": "wrong-password"},
        )

    good = client.post(
        "/auth/login",
        json={"email": "trader@example.com", "password": "s3cret-passphrase"},
    )
    assert good.status_code == 200

    # Budget reset, so the next wrong attempt is a 401 rather than a 429.
    assert (
        client.post(
            "/auth/login",
            json={"email": "trader@example.com", "password": "wrong-password"},
        ).status_code
        == 401
    )


def test_registration_is_rate_limited(client):
    limit = get_register_limiter()._max

    statuses = [
        client.post(
            "/auth/register",
            json={"email": f"user{i}@example.com", "password": "s3cret-passphrase"},
        ).status_code
        for i in range(limit + 2)
    ]

    assert 201 in statuses
    assert statuses[-1] == 429


def test_rate_limiting_leaves_other_endpoints_alone(client):
    session = register(client)
    wallet = session["user"]["wallets"][0]

    for _ in range(30):
        assert client.get(f"/portfolio/{wallet}/summary", headers=headers(session)).status_code == 200


# ── Blocklist hygiene ────────────────────────────────────────────────────


def test_expired_entries_can_be_purged(client):
    """Revocation records are only needed until the token expires anyway."""
    from datetime import datetime, timedelta, timezone

    from quantnest.infra.db.repositories import SqlTokenBlocklist
    from quantnest.infra.db.session import get_session_factory  # noqa: F401

    session = register(client)
    client.post("/auth/logout", json={}, headers=headers(session))

    # Purging with a far-future clock should remove the entry we just made.
    from sqlalchemy.orm import Session as SASession

    engine = client.app.dependency_overrides[get_db_session]
    generator = engine()
    db: SASession = next(generator)
    try:
        blocklist = SqlTokenBlocklist(db)
        purged = blocklist.purge_expired(datetime.now(timezone.utc) + timedelta(days=365))
        assert purged >= 1
    finally:
        generator.close()
