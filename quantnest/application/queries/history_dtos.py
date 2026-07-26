"""DTOs for history and timeline queries (Pydantic v2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TradeHistoryItem(BaseModel):
    """A single executed trade."""

    model_config = ConfigDict(from_attributes=True)

    trade_id: str
    wallet_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    price: float
    total_value: float
    timestamp: datetime


class OrderHistoryItem(BaseModel):
    """A single order and its current status."""

    model_config = ConfigDict(from_attributes=True)

    order_id: str
    wallet_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    order_type: Literal["MARKET", "LIMIT", "STOP_LOSS"]
    status: Literal["PENDING", "FILLED", "REJECTED", "CANCELLED", "PARTIAL"]
    price: Optional[float] = None
    timestamp: datetime


class WalletEventItem(BaseModel):
    """A single ledger entry."""

    model_config = ConfigDict(from_attributes=True)

    event_id: str
    wallet_id: str
    event_type: Literal["FundsCredited", "FundsDebited"]
    amount: float
    transaction_id: str
    timestamp: datetime


class TimelineEvent(BaseModel):
    """A unified activity-feed entry."""

    model_config = ConfigDict(from_attributes=True)

    event_type: str
    timestamp: datetime
    wallet_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaginatedResponse(BaseModel):
    """Envelope for every paginated list endpoint."""

    items: List[Any] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
    has_more: bool
