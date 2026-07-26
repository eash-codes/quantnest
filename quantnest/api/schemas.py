"""Pydantic v2 request and response models.

Validation is strict and happens at the edge, so invalid data never reaches the
domain: tickers must match an exchange-symbol pattern, quantities and amounts
must be positive, and unknown fields are rejected outright.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ── Reusable constrained types ───────────────────────────────────────────

#: Exchange ticker: starts with a letter, then letters, digits, & . - _
Ticker = Annotated[
    str,
    Field(
        min_length=1,
        max_length=20,
        pattern=r"^[A-Za-z][A-Za-z0-9&._\-]{0,19}$",
        description="Exchange ticker, e.g. INFY or RELIANCE",
        examples=["INFY"],
    ),
]

#: Share quantity: strictly positive, at most 4 decimal places.
Quantity = Annotated[
    Decimal,
    Field(
        gt=0,
        le=Decimal("1000000000"),
        max_digits=18,
        decimal_places=4,
        description="Number of shares; must be greater than zero",
        examples=[10],
    ),
]

#: Money amount: strictly positive, 2 decimal places.
Amount = Annotated[
    Decimal,
    Field(
        gt=0,
        le=Decimal("1000000000000"),
        max_digits=18,
        decimal_places=2,
        description="Amount in INR; must be greater than zero",
        examples=[10000.00],
    ),
]


class StrictModel(BaseModel):
    """Base model that rejects unknown fields and strips whitespace."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ── Requests ─────────────────────────────────────────────────────────────


class CreditRequest(StrictModel):
    amount: Amount


class DebitRequest(StrictModel):
    amount: Amount


class TradeRequest(StrictModel):
    """Body for the buy and sell endpoints."""

    symbol: Ticker
    quantity: Quantity

    @field_validator("symbol")
    @classmethod
    def normalise_symbol(cls, value: str) -> str:
        return value.upper().strip()


class PlaceOrderRequest(StrictModel):
    """Body for ``POST /orders``.

    Previously these were query parameters, which meant no schema validation
    and an unusual shape for a state-changing request.
    """

    wallet_id: str = Field(min_length=1, max_length=64)
    symbol: Ticker
    side: Literal["BUY", "SELL"]
    quantity: Quantity
    order_type: Literal["MARKET", "LIMIT", "STOP_LOSS"] = "MARKET"
    limit_price: Optional[Amount] = None
    stop_price: Optional[Amount] = None

    @field_validator("symbol")
    @classmethod
    def normalise_symbol(cls, value: str) -> str:
        return value.upper().strip()

    @field_validator("side", mode="before")
    @classmethod
    def normalise_side(cls, value: Any) -> Any:
        return value.upper().strip() if isinstance(value, str) else value

    @field_validator("order_type", mode="before")
    @classmethod
    def normalise_order_type(cls, value: Any) -> Any:
        return value.upper().strip() if isinstance(value, str) else value


# ── Responses ────────────────────────────────────────────────────────────


class PortfolioSummaryResponse(BaseModel):
    wallet_id: str
    cash: float
    total_asset_value: float
    total_value: float
    positions: Dict[str, float]
    asset_values: Dict[str, float] = Field(default_factory=dict)
    avg_cost: Dict[str, float] = Field(default_factory=dict)
    unrealized_pnl: Dict[str, float] = Field(default_factory=dict)
    allocations: Dict[str, float] = Field(default_factory=dict)
    health_signals: List[str] = Field(default_factory=list)
    event_count: int


class WalletTransactionResponse(BaseModel):
    wallet_id: str
    amount: float
    transaction_id: Optional[str] = None
    new_balance: float
    message: str


class PortfolioSnapshot(BaseModel):
    cash: float
    total_value: float
    positions: Dict[str, float]


class TradeResponse(BaseModel):
    wallet_id: str
    symbol: str
    quantity: float
    transaction_id: Optional[str] = None
    order_id: str
    order_status: str
    success: bool
    message: str
    portfolio_summary: Optional[PortfolioSnapshot] = None


class OrderResponse(BaseModel):
    order_id: str
    wallet_id: str
    symbol: str
    side: str
    quantity: float
    order_type: str
    status: str
    filled_quantity: float
    average_fill_price: Optional[float] = None
    rejection_reason: Optional[str] = None
    transaction_id: Optional[str] = None
    timestamp: datetime


class QuoteResponse(BaseModel):
    symbol: str
    yf_symbol: Optional[str] = None
    exchange: Optional[str] = None
    ltp: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    prev_close: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[int] = None
    week52_high: Optional[float] = None
    week52_low: Optional[float] = None
    market_cap: Optional[float] = None


class ProblemDetail(BaseModel):
    """RFC 9457 problem detail — the shape of every error response."""

    type: str = Field(default="about:blank", description="Error category URI or code")
    title: str = Field(description="Short, human-readable summary")
    status: int = Field(description="HTTP status code")
    detail: Optional[str] = Field(default=None, description="Explanation for this occurrence")
    instance: Optional[str] = Field(default=None, description="Request path")
    request_id: Optional[str] = Field(default=None, description="Correlation ID")
