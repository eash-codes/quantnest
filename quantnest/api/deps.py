"""FastAPI dependency providers.

Route handlers declare what they need via ``Depends`` instead of constructing
services inline. That makes the wiring explicit, keeps a single transaction per
request, and lets tests swap any collaborator through
``app.dependency_overrides``.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Iterator, Optional

from fastapi import Depends, Header, HTTPException, Path, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from quantnest.application.auth_service import AuthService
from quantnest.application.history_service import HistoryService
from quantnest.application.portfolio_service import PortfolioService
from quantnest.domain.exceptions import AuthenticationError, RateLimitExceededError
from quantnest.domain.user import User
from quantnest.domain.order_engine import OrderExecutionEngine
from quantnest.domain.ports import MarketDataProvider
from quantnest.infra.db.repositories import (
    SqlEventStore,
    SqlTokenBlocklist,
    SqlOrderRepository,
    SqlPositionRepository,
    SqlTradeRepository,
    SqlUserRepository,
    SqlWalletOwnershipRepository,
)
from quantnest.infra.db.session import get_session_factory
from quantnest.infra.market import get_market_provider
from quantnest.infra.security import get_password_hasher, get_token_service
from quantnest.infra.rate_limit import (
    RATE_LIMIT_ENABLED,
    client_key,
    get_login_limiter,
    get_register_limiter,
)


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


# ── Authentication ───────────────────────────────────────────────────────

#: auto_error=False so a missing header raises our AuthenticationError
#: (RFC 9457 problem+json) rather than Starlette's bare 403.
_bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


def get_token_blocklist(session: SessionDep) -> SqlTokenBlocklist:
    return SqlTokenBlocklist(session)


TokenBlocklistDep = Annotated[SqlTokenBlocklist, Depends(get_token_blocklist)]


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(
        users=SqlUserRepository(session),
        wallets=SqlWalletOwnershipRepository(session),
        hasher=get_password_hasher(),
        tokens=get_token_service(),
        blocklist=SqlTokenBlocklist(session),
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_current_user(
    auth: AuthServiceDep,
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(_bearer_scheme)
    ] = None,
) -> User:
    """Resolve the bearer token to the signed-in user.

    Raises ``AuthenticationError`` (HTTP 401) when the token is absent,
    malformed, expired, or of the wrong type.
    """
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Sign in to access this resource")

    return auth.user_from_access_token(credentials.credentials)


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_bearer_token(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(_bearer_scheme)
    ] = None,
) -> str:
    """The raw access token, needed by sign-out so it can be revoked."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Sign in to access this resource")
    return credentials.credentials


BearerTokenDep = Annotated[str, Depends(get_bearer_token)]


# ── Rate limiting ────────────────────────────────────────────────────────


def _enforce(request: Request, limiter, scope: str) -> None:
    if not RATE_LIMIT_ENABLED:
        return

    result = limiter.check(client_key(request, scope))
    if not result.allowed:
        raise RateLimitExceededError(
            "Too many attempts. Please wait before trying again.",
            retry_after=result.retry_after,
        )


def rate_limit_login(request: Request) -> None:
    """Throttle sign-in attempts per client IP."""
    _enforce(request, get_login_limiter(), "login")


def rate_limit_register(request: Request) -> None:
    """Throttle account creation per client IP."""
    _enforce(request, get_register_limiter(), "register")


# ── Authorisation ────────────────────────────────────────────────────────


def authorized_wallet_id(
    auth: AuthServiceDep,
    current_user: CurrentUserDep,
    wallet_id: str = Path(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9._\-]{1,64}$",
        description="Wallet identifier",
    ),
) -> str:
    """Validate the wallet id *and* confirm the caller owns it.

    Every wallet-scoped route depends on this, so ownership is enforced in
    one place rather than repeated per handler. Previously any caller could
    read or trade any wallet by editing the URL.
    """
    return auth.authorize_wallet(current_user, wallet_id)


WalletIdDep = Annotated[str, Depends(authorized_wallet_id)]
