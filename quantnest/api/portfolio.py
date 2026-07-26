"""Portfolio API with commands and queries."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from quantnest.application.portfolio_service import PortfolioService
from quantnest.application.commands.wallet_commands import CreditWalletCommand, DebitWalletCommand
from quantnest.application.commands.portfolio_commands import BuyAssetCommand, SellAssetCommand
from quantnest.application.handlers import (
    CreditWalletHandler, 
    DebitWalletHandler, 
    BuyAssetHandler, 
    SellAssetHandler
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

class PortfolioSummary(BaseModel):
    wallet_id: str
    cash: float
    total_asset_value: float
    total_value: float
    positions: Dict[str, float]
    asset_values: Optional[Dict[str, float]] = None
    avg_cost: Optional[Dict[str, float]] = None
    unrealized_pnl: Dict[str, float]
    allocations: Dict[str, float]
    health_signals: List[str]
    event_count: int

    class Config:
        extra = "allow"

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
    return {"status": "healthy", "ledger_version": "Day7"}

# POST endpoints for commands
class CreditRequest(BaseModel):
    amount: float

class DebitRequest(BaseModel):
    amount: float

class BuyRequest(BaseModel):
    symbol: str
    quantity: float

class SellRequest(BaseModel):
    symbol: str
    quantity: float

@router.post("/{wallet_id}/credit")
async def credit_wallet(
    wallet_id: str, 
    request: CreditRequest,
    x_transaction_id: Optional[str] = Header(None)
):
    """Credit funds to wallet."""
    try:
        command = CreditWalletCommand(
            wallet_id=wallet_id, 
            amount=request.amount,
            transaction_id=x_transaction_id
        )
        handler = CreditWalletHandler()
        return handler.handle(command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{wallet_id}/debit")
async def debit_wallet(
    wallet_id: str, 
    request: DebitRequest,
    x_transaction_id: Optional[str] = Header(None)
):
    """Debit funds from wallet."""
    try:
        command = DebitWalletCommand(
            wallet_id=wallet_id, 
            amount=request.amount,
            transaction_id=x_transaction_id
        )
        handler = DebitWalletHandler()
        return handler.handle(command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "InsufficientFundsError" in str(type(e)):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{wallet_id}/buy")
async def buy_asset(
    wallet_id: str, 
    request: BuyRequest,
    x_transaction_id: Optional[str] = Header(None)
):
    """Buy asset."""
    try:
        command = BuyAssetCommand(
            wallet_id=wallet_id, 
            symbol=request.symbol,
            quantity=request.quantity,
            transaction_id=x_transaction_id
        )
        handler = BuyAssetHandler()
        return handler.handle(command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "InsufficientFundsError" in str(type(e)) or "UnknownSymbolError" in str(type(e)):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{wallet_id}/sell")
async def sell_asset(
    wallet_id: str, 
    request: SellRequest,
    x_transaction_id: Optional[str] = Header(None)
):
    """Sell asset."""
    try:
        command = SellAssetCommand(
            wallet_id=wallet_id, 
            symbol=request.symbol,
            quantity=request.quantity,
            transaction_id=x_transaction_id
        )
        handler = SellAssetHandler()
        return handler.handle(command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "InsufficientFundsError" in str(type(e)) or "UnknownSymbolError" in str(type(e)):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))
