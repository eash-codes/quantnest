"""Domain events for audit trail - NEVER delete events!"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict
from dataclasses import dataclass, field

@dataclass(kw_only=True)
class DomainEvent:
    event_type: str
    transaction_id: str              
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "transaction_id": self.transaction_id,  
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainEvent':
        event_type = data["event_type"]
        if event_type == "FundsCredited":
            return FundsCredited.from_dict(data)
        elif event_type == "FundsDebited":
            return FundsDebited.from_dict(data)
        raise ValueError(f"Unknown event type: {event_type}")

@dataclass(kw_only=True)
class FundsCredited(DomainEvent):
    event_type: str = "FundsCredited"
    amount: Decimal = Decimal("0")

    def __post_init__(self):
        self.payload = {"amount": str(self.amount)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FundsCredited':
        transaction_id = data.get("transaction_id") or str(uuid.uuid4())
        # ✅ Restore original timestamp from JSON — do NOT let default_factory run
        ts_str = data.get("timestamp")
        timestamp = datetime.fromisoformat(ts_str) if ts_str else datetime.now()
        instance = cls(
            transaction_id=transaction_id,
            amount=Decimal(data["payload"]["amount"])
        )
        # dataclass is NOT frozen, so we can overwrite the auto-generated timestamp
        instance.timestamp = timestamp
        return instance

@dataclass(kw_only=True)
class FundsDebited(DomainEvent):
    event_type: str = "FundsDebited"
    amount: Decimal = Decimal("0")

    def __post_init__(self):
        self.payload = {"amount": str(self.amount)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FundsDebited':
        transaction_id = data.get("transaction_id") or str(uuid.uuid4())
        # ✅ Restore original timestamp from JSON — do NOT let default_factory run
        ts_str = data.get("timestamp")
        timestamp = datetime.fromisoformat(ts_str) if ts_str else datetime.now()
        instance = cls(
            transaction_id=transaction_id,
            amount=Decimal(data["payload"]["amount"])
        )
        instance.timestamp = timestamp
        return instance