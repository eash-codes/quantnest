"""Read-only portfolio API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from quantnest.application.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

class PortfolioSummary(BaseModel):
    wallet_id: str
    cash: float
    total_asset_value: float
    total_value: float
    positions: Dict[str, float]
    unrealized_pnl: Dict[str, float]
    allocations: Dict[str, float]
    health_signals: List[str]
    event_count: int

@router.get("/{wallet_id}/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(wallet_id: str):
    """Get complete portfolio analytics."""
    try:
        service = PortfolioService()
        return service.get_summary(wallet_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check."""
    return {"status": "healthy", "ledger_version": "Day6"}
