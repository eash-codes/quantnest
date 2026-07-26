"""FastAPI dependency providers.

Route handlers declare what they need via ``Depends`` instead of constructing
services inline. That makes the wiring explicit, keeps a single transaction per
request, and lets tests swap any collaborator through
``app.dependency_overrides``.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Iterator, Optional

from fastapi import Depends, Header, HTTPException, Path, status
from sqlalchemy.orm import Session

from quantnest.application.history_service import HistoryService
from quantnest.application.portfolio_service import PortfolioService
from quantnest.domain.order_engine import OrderExecutionEngine
from quantnest.domain.ports import MarketDataProvider
from quantnest.infra.db.repositories import (
    SqlEventStore,
    SqlOrderRepository,
    SqlPositionRepository,
    SqlTradeRepository,
)
from quantnest.infra.db.session import get_session_factory
from quantnest.infra.market import get_market_provider


def get_db_session() -> Iterator[Session]:
    """Yield a session wrapped in a single transaction per request."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_db_session)]


def get_market() -> MarketDataProvider:
    """Return the configured market data provider."""
    return get_market_provider()


MarketDep = Annotated[MarketDataProvider, Depends(get_market)]


# ── Repositories ─────────────────────────────────────────────────────────


def get_event_store(session: SessionDep) -> SqlEventStore:
    return SqlEventStore(session)


def get_position_repository(session: SessionDep) -> SqlPositionRepository:
    return SqlPositionRepository(session)


def get_trade_repository(session: SessionDep) -> SqlTradeRepository:
    return SqlTradeRepository(session)


def get_order_repository(session: SessionDep) -> SqlOrderRepository:
    return SqlOrderRepository(session)


EventStoreDep = Annotated[SqlEventStore, Depends(get_event_store)]
PositionRepoDep = Annotated[SqlPositionRepository, Depends(get_position_repository)]
TradeRepoDep = Annotated[SqlTradeRepository, Depends(get_trade_repository)]
OrderRepoDep = Annotated[SqlOrderRepository, Depends(get_order_repository)]


# ── Services ─────────────────────────────────────────────────────────────


def get_portfolio_service(
    market: MarketDep,
    event_store: EventStoreDep,
    position_repository: PositionRepoDep,
    trade_repository: TradeRepoDep,
) -> PortfolioService:
    return PortfolioService(
        market=market,
        event_store=event_store,
        position_repository=position_repository,
        trade_repository=trade_repository,
    )


def get_history_service(
    event_store: EventStoreDep,
    trade_repository: TradeRepoDep,
    order_repository: OrderRepoDep,
) -> HistoryService:
    return HistoryService(
        event_store=event_store,
        trade_repository=trade_repository,
        order_repository=order_repository,
    )


def get_order_engine(
    market: MarketDep,
    order_repository: OrderRepoDep,
    event_store: EventStoreDep,
    position_repository: PositionRepoDep,
    trade_repository: TradeRepoDep,
) -> OrderExecutionEngine:
    return OrderExecutionEngine(
        market=market,
        order_repository=order_repository,
        event_store=event_store,
        position_repository=position_repository,
        trade_repository=trade_repository,
    )


PortfolioServiceDep = Annotated[PortfolioService, Depends(get_portfolio_service)]
HistoryServiceDep = Annotated[HistoryService, Depends(get_history_service)]
OrderEngineDep = Annotated[OrderExecutionEngine, Depends(get_order_engine)]


# ── Request-scoped values ────────────────────────────────────────────────


def get_transaction_id(
    x_transaction_id: Optional[str] = Header(
        default=None,
        alias="X-Transaction-ID",
        description="Idempotency key (UUID). Generated automatically when omitted.",
    ),
) -> str:
    """Validate the caller's idempotency key, or mint one."""
    if x_transaction_id is None:
        return str(uuid.uuid4())

    candidate = x_transaction_id.strip()
    if not candidate:
        return str(uuid.uuid4())

    if len(candidate) > 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Transaction-ID must be at most 64 characters.",
        )

    return candidate


TransactionIdDep = Annotated[str, Depends(get_transaction_id)]


def validated_wallet_id(
    wallet_id: str = Path(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9._\-]{1,64}$",
        description="Wallet identifier",
    ),
) -> str:
    return wallet_id


WalletIdDep = Annotated[str, Depends(validated_wallet_id)]
