"""Domain events for audit trail - NEVER delete events!"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any
from dataclasses import dataclass

@dataclass  # ← ADD THIS LINE
class DomainEvent:
    event_id: uuid.UUID = None
    timestamp: datetime = None
    event_type: str = ""
    payload: dict[str, Any] = None
    
    def __post_init__(self):
        if self.event_id is None:
            self.event_id = uuid.uuid4()
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.payload is None:
            self.payload = {}

class FundsCredited(DomainEvent):
    def __init__(self, amount: Decimal):
        super().__init__(event_id=None, timestamp=None, event_type="FundsCredited", payload={"amount": str(amount)})

class FundsDebited(DomainEvent):
    def __init__(self, amount: Decimal):
        super().__init__(event_id=None, timestamp=None, event_type="FundsDebited", payload={"amount": str(amount)})
