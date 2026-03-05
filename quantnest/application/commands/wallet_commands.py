"""Command DTOs for wallet operations."""

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class CreditWalletCommand(BaseModel):
    """Command to credit funds to a wallet."""
    
    wallet_id: str
    amount: Decimal = Field(..., gt=0, description="Amount to credit (positive)")
    transaction_id: Optional[str] = None


class DebitWalletCommand(BaseModel):
    """Command to debit funds from a wallet."""
    
    wallet_id: str
    amount: Decimal = Field(..., gt=0, description="Amount to debit (positive)")
    transaction_id: Optional[str] = None