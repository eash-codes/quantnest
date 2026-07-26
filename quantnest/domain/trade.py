"""Immutable trade records - future ML dataset."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from decimal import Decimal
import uuid

@dataclass(frozen=True)
class Trade:
    symbol: str
    side: Literal["BUY","SELL"]
    quantity: Decimal
    price: Decimal
    timestamp: datetime = field(default_factory=datetime.now)
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def total_value(self) -> Decimal:
        """Quantity x Price"""
        return self.quantity * self.price