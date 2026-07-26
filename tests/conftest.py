"""Shared pytest fixtures.

Every test runs against an isolated in-memory SQLite database and a
deterministic market provider, so the suite is fast, hermetic and requires no
network access.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force deterministic pricing before any application module is imported.
os.environ.setdefault("QUANTNEST_MARKET_PROVIDER", "fake")

from quantnest.domain.ports import StaticMarketDataProvider  # noqa: E402
from quantnest.infra.db.models import Base  # noqa: E402
from quantnest.infra.db.repositories import (  # noqa: E402
    SqlEventStore,
    SqlOrderRepository,
    SqlPositionRepository,
    SqlTradeRepository,
)


@pytest.fixture
def engine():
    """In-memory SQLite engine shared across connections for one test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def session(engine):
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    db = factory()
    try:
        yield db
        db.commit()
    finally:
        db.close()


@pytest.fixture
def market():
    """Deterministic market provider; mutate ``market.prices`` to move it."""
    return StaticMarketDataProvider(
        {
            "RELIANCE": Decimal("2500.00"),
            "TCS": Decimal("3800.00"),
            "INFY": Decimal("1650.00"),
            "HDFCBANK": Decimal("1550.00"),
        }
    )


@pytest.fixture
def event_store(session):
    return SqlEventStore(session)


@pytest.fixture
def position_repository(session):
    return SqlPositionRepository(session)


@pytest.fixture
def trade_repository(session):
    return SqlTradeRepository(session)


@pytest.fixture
def order_repository(session):
    return SqlOrderRepository(session)


@pytest.fixture
def repositories(event_store, position_repository, trade_repository, order_repository):
    """Bundle of every repository, for concise injection into aggregates."""
    return {
        "event_store": event_store,
        "position_repository": position_repository,
        "trade_repository": trade_repository,
        "order_repository": order_repository,
    }


@pytest.fixture
def make_portfolio(market, repositories):
    """Factory returning a Portfolio wired to the test database."""
    from quantnest.domain.portfolio import Portfolio

    def _make(wallet_id: str = "test-wallet"):
        return Portfolio(
            wallet_id,
            market,
            event_store=repositories["event_store"],
            position_repository=repositories["position_repository"],
            trade_repository=repositories["trade_repository"],
        )

    return _make


@pytest.fixture
def make_wallet(event_store):
    """Factory returning a Wallet wired to the test database."""
    from quantnest.domain.wallet import Wallet

    def _make(wallet_id: str = "test-wallet"):
        return Wallet(wallet_id, event_store=event_store)

    return _make
