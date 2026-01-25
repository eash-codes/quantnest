"""Immutable trade records - future ML dataset."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict
from decimal import Decimal

@dataclass(frozen=True)
class Trade:
    symbol: str
    side: Literal["BUY","SELL"]
    quantity: Decimal
    price: Decimal
    timestamp: datetime = field(default=datetime.now)

    @property
    def total_value(self) -> Decimal:
        """Quantity x Price"""
        return self.quantity * self.price