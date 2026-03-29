"""DTOs for history and timeline queries."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class TradeHistoryItem(BaseModel):
    """Single trade history item."""
    
    trade_id: str
    wallet_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    price: float
    total_value: float
    timestamp: datetime
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class OrderHistoryItem(BaseModel):
    """Single order history item."""
    
    order_id: str
    wallet_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    order_type: Literal["MARKET", "LIMIT"]
    status: Literal["PENDING", "FILLED", "REJECTED", "CANCELLED"]
    price: Optional[float] = None
    timestamp: datetime
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class WalletEventItem(BaseModel):
    """Single wallet event item."""
    
    event_id: str
    wallet_id: str
    event_type: Literal["FundsCredited", "FundsDebited"]
    amount: float
    transaction_id: str
    timestamp: datetime
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class TimelineEvent(BaseModel):
    """Unified timeline event."""
    
    event_type: Literal["wallet_credit", "wallet_debit", "trade_executed", "order_placed", "order_filled", "order_rejected"]
    timestamp: datetime
    wallet_id: str
    metadata: Dict[str, Any]
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    
    items: list
    total: int
    limit: int
    offset: int
    has_more: bool
