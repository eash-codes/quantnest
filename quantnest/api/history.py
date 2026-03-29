"""History and timeline API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional

from quantnest.application.queries import HistoryService

router = APIRouter(prefix="/history", tags=["history"])

@router.get("/portfolio/{wallet_id}/trades")
async def get_trade_history(
    wallet_id: str,
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(50, ge=1, le=500, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip")
):
    """Get trade history for a wallet."""
    try:
        service = HistoryService()
        result = service.get_trades(wallet_id, symbol=symbol, limit=limit, offset=offset)
        return result.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio/{wallet_id}/orders")
async def get_order_history(
    wallet_id: str,
    status: Optional[str] = Query(None, description="Filter by order status"),
    limit: int = Query(50, ge=1, le=500, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip")
):
    """Get order history for a wallet."""
    try:
        service = HistoryService()
        result = service.get_orders(wallet_id, status=status, limit=limit, offset=offset)
        return result.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/wallet/{wallet_id}/events")
async def get_wallet_events(
    wallet_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type (FundsCredited/FundsDebited)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip")
):
    """Get wallet event history (ledger audit trail)."""
    try:
        service = HistoryService()
        result = service.get_wallet_events(wallet_id, event_type=event_type, limit=limit, offset=offset)
        return result.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio/{wallet_id}/timeline")
async def get_timeline(
    wallet_id: str,
    start_date: Optional[datetime] = Query(None, description="Filter events from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter events until this date"),
    limit: int = Query(100, ge=1, le=500, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip")
):
    """Get unified chronological timeline of all events."""
    try:
        service = HistoryService()
        result = service.get_timeline(
            wallet_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        return result.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio/{wallet_id}/activity-summary")
async def get_activity_summary(wallet_id: str):
    """Get summary of portfolio activity."""
    try:
        service = HistoryService()
        result = service.get_activity_summary(wallet_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
