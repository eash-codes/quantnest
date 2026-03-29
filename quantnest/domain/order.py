"""Order entity for Order Management System - Day 8."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal
from dataclasses import dataclass, field


class OrderStatus:
    """Order status constants."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    PARTIAL = "PARTIAL"


class OrderSide:
    """Order side constants."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType:
    """Order type constants."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"


@dataclass
class Order:
    """
    Represents a trading order - user's intent to buy/sell.
    
    Separates user intent (Order) from execution result (Trade).
    """
    
    wallet_id: str
    symbol: str
    side: str  # BUY or SELL
    quantity: Decimal
    order_type: str = OrderType.MARKET  # MARKET, LIMIT, STOP_LOSS
    status: str = OrderStatus.PENDING
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    
    # For LIMIT and STOP_LOSS orders
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    
    # Execution details (populated after filling)
    filled_quantity: Decimal = Decimal("0")
    average_fill_price: Optional[Decimal] = None
    rejection_reason: Optional[str] = None
    
    # Idempotency
    transaction_id: Optional[str] = None
    
    @property
    def is_pending(self) -> bool:
        """Check if order is still pending."""
        return self.status == OrderStatus.PENDING
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_rejected(self) -> bool:
        """Check if order was rejected."""
        return self.status == OrderStatus.REJECTED
    
    @property
    def is_partial(self) -> bool:
        """Check if order is partially filled."""
        return self.status == OrderStatus.PARTIAL
    
    @property
    def total_value(self) -> Decimal:
        """Calculate total order value."""
        if self.average_fill_price:
            return self.filled_quantity * self.average_fill_price
        return Decimal("0")
    
    def reject(self, reason: str) -> None:
        """Mark order as rejected with reason."""
        self.status = OrderStatus.REJECTED
        self.rejection_reason = reason
    
    def fill(self, quantity: Decimal, price: Decimal) -> None:
        """
        Mark order as filled.
        
        For partial fills, update filled_quantity and average price.
        For complete fills, set status to FILLED.
        """
        if quantity <= 0:
            raise ValueError("Fill quantity must be positive")
        
        old_filled = self.filled_quantity
        new_filled = old_filled + quantity
        
        # Calculate new average fill price
        old_value = old_filled * (self.average_fill_price or Decimal("0"))
        new_value = old_value + (quantity * price)
        new_avg_price = new_value / new_filled if new_filled > 0 else Decimal("0")
        
        self.filled_quantity = new_filled
        self.average_fill_price = new_avg_price
        
        # Update status based on fill completion
        if new_filled >= self.quantity:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIAL
    
    def to_dict(self) -> dict:
        """Convert order to dictionary for serialization."""
        return {
            "order_id": self.order_id,
            "wallet_id": self.wallet_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": str(self.quantity),
            "order_type": self.order_type,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "limit_price": str(self.limit_price) if self.limit_price else None,
            "stop_price": str(self.stop_price) if self.stop_price else None,
            "filled_quantity": str(self.filled_quantity),
            "average_fill_price": str(self.average_fill_price) if self.average_fill_price else None,
            "rejection_reason": self.rejection_reason,
            "transaction_id": self.transaction_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Order':
        """Create order from dictionary."""
        return cls(
            order_id=data["order_id"],
            wallet_id=data["wallet_id"],
            symbol=data["symbol"],
            side=data["side"],
            quantity=Decimal(data["quantity"]),
            order_type=data["order_type"],
            status=data["status"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            limit_price=Decimal(data["limit_price"]) if data.get("limit_price") else None,
            stop_price=Decimal(data["stop_price"]) if data.get("stop_price") else None,
            filled_quantity=Decimal(data.get("filled_quantity", "0")),
            average_fill_price=Decimal(data["average_fill_price"]) if data.get("average_fill_price") else None,
            rejection_reason=data.get("rejection_reason"),
            transaction_id=data.get("transaction_id")
        )
