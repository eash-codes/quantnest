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
    
    def to_dict(self) -> dict:
        return {
            "event_id": str(self.event_id),
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "payload": self.payload,
    }

    @staticmethod
    def from_dict(data: dict) -> "DomainEvent":
        import uuid
        from datetime import datetime

        return DomainEvent(
            event_id=uuid.UUID(data["event_id"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=data["event_type"],
            payload=data["payload"],
    )


class FundsCredited(DomainEvent):
    def __init__(self, amount: Decimal):
        super().__init__(event_id=None, timestamp=None, event_type="FundsCredited", payload={"amount": str(amount)})

class FundsDebited(DomainEvent):
    def __init__(self, amount: Decimal):
        super().__init__(event_id=None, timestamp=None, event_type="FundsDebited", payload={"amount": str(amount)})
