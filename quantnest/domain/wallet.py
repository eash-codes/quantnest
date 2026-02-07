"""Wallet - TRUE FINANCIAL LEDGER (Day 5).
Balance derived 100% from events. Idempotent. Replay-safe."""

import uuid
from decimal import Decimal
from typing import List
from .events import DomainEvent, FundsCredited, FundsDebited
from quantnest.infra.storage import load_events, append_event


class InsufficientFundsError(Exception):
    """Business rule: can't spend what you don't have."""


class Wallet:
    def __init__(self, wallet_id: str):
        self._wallet_id = wallet_id
        self._events = load_events(self._wallet_id)
        self._replay_events()  # Balance derived from events

    @property
    def balance(self) -> Decimal:
        """Current balance - ALWAYS replayed from events."""
        return self._balance

    @property
    def events(self) -> List[DomainEvent]:
        """Immutable audit trail - complete movie of all transactions."""
        return self._events.copy()

    def credit(self, amount: Decimal, transaction_id: str = None) -> None:
        """Add money - idempotent (safe to retry same payment)."""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        tx_id = transaction_id or str(uuid.uuid4())

        # ← DAY 5: Skip if already processed (no double credit!)
        if any(e.transaction_id == tx_id for e in self._events):
            return  # Idempotent!

        event = FundsCredited(amount=amount, transaction_id=tx_id)
        self._events.append(event)
        append_event(event, self._wallet_id)
        self._replay_events()  # Recompute balance from ALL events

    def debit(self, amount: Decimal, transaction_id: str = None) -> None:
        """Spend money - check balance FIRST, then append event."""
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Check balance BEFORE creating event
        if amount > self.balance:
            raise InsufficientFundsError(
                f"Cannot debit ₹{amount} from ₹{self.balance}"
            )

        tx_id = transaction_id or str(uuid.uuid4())

        # ← DAY 5: Skip if already processed (no double debit!)
        if any(e.transaction_id == tx_id for e in self._events):
            return  # Idempotent!

        event = FundsDebited(amount=amount, transaction_id=tx_id)
        self._events.append(event)
        append_event(event, self._wallet_id)
        self._replay_events()  # Recompute balance from ALL events

    def _replay_events(self) -> None:
        """MAGIC: Rebuild balance from events (delete _balance → replay)."""
        self._balance = Decimal("0")
        for event in self._events:
            amount = Decimal(event.payload["amount"])
            if event.event_type == "FundsCredited":
                self._balance += amount
            elif event.event_type == "FundsDebited":
                self._balance -= amount
