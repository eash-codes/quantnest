"""History and timeline API endpoints."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from quantnest.api.deps import HistoryServiceDep, WalletIdDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/portfolio/{wallet_id}/trades", summary="Executed trade history")
async def get_trade_history(
    wallet_id: WalletIdDep,
    service: HistoryServiceDep,
    symbol: Optional[str] = Query(None, max_length=20, description="Filter by symbol"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    result = service.get_trades(wallet_id, symbol=symbol, limit=limit, offset=offset)
    return result.model_dump()


@router.get("/portfolio/{wallet_id}/orders", summary="Order history")
async def get_order_history(
    wallet_id: WalletIdDep,
    service: HistoryServiceDep,
    status: Optional[str] = Query(None, max_length=16, description="Filter by order status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    result = service.get_orders(wallet_id, status=status, limit=limit, offset=offset)
    return result.model_dump()


@router.get("/wallet/{wallet_id}/events", summary="Wallet ledger audit trail")
async def get_wallet_events(
    wallet_id: WalletIdDep,
    service: HistoryServiceDep,
    event_type: Optional[str] = Query(
        None, max_length=32, description="FundsCredited or FundsDebited"
    ),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict:
    result = service.get_wallet_events(
        wallet_id, event_type=event_type, limit=limit, offset=offset
    )
    return result.model_dump()


@router.get("/portfolio/{wallet_id}/timeline", summary="Unified chronological timeline")
async def get_timeline(
    wallet_id: WalletIdDep,
    service: HistoryServiceDep,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    result = service.get_timeline(
        wallet_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return result.model_dump()


@router.get("/portfolio/{wallet_id}/activity-summary", summary="Aggregate activity statistics")
async def get_activity_summary(
    wallet_id: WalletIdDep,
    service: HistoryServiceDep,
) -> dict:
    return service.get_activity_summary(wallet_id)
