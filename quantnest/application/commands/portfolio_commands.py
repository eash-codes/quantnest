"""Command DTOs for portfolio operations."""

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class BuyAssetCommand(BaseModel):
    """Command to buy an asset."""
    
    wallet_id: str
    symbol: str
    quantity: Decimal = Field(..., gt=0, description="Quantity to buy (positive)")
    transaction_id: Optional[str] = None


class SellAssetCommand(BaseModel):
    """Command to sell an asset."""
    
    wallet_id: str
    symbol: str
    quantity: Decimal = Field(..., gt=0, description="Quantity to sell (positive)")
    transaction_id: Optional[str] = None