"""Wallet — an event-sourced financial ledger.

The balance is never stored; it is always derived by replaying the immutable
event log. Credits and debits are idempotent on ``transaction_id``, so a
retried request can never double-apply.

The wallet depends on the :class:`EventStore` *port*, not on any concrete
storage module, which keeps this layer free of infrastructure imports.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional

from .events import DomainEvent, FundsCredited, FundsDebited
from .exceptions import InsufficientFundsError
from .ports import EventStore, InMemoryEventStore


class Wallet:
    """Aggregate root for money movement."""

    def __init__(self, wallet_id: str, event_store: Optional[EventStore] = None) -> None:
        self._wallet_id = wallet_id
        self._event_store: EventStore = event_store or InMemoryEventStore()
        self._events: List[DomainEvent] = list(self._event_store.load_events(wallet_id))
        self._balance = Decimal("0")
        self._replay_events()

    @property
    def wallet_id(self) -> str:
        return self._wallet_id

    @property
    def balance(self) -> Decimal:
        """Current balance, always derived from the event log."""
        return self._balance

    @property
    def events(self) -> List[DomainEvent]:
        """Copy of the immutable audit trail."""
        return list(self._events)

    def credit(self, amount: Decimal, transaction_id: Optional[str] = None) -> None:
        """Add funds. Safe to retry with the same ``transaction_id``."""
        amount = self._validate_amount(amount)
        tx_id = transaction_id or str(uuid.uuid4())

        if self._already_processed(tx_id):
            return

        event = FundsCredited(amount=amount, transaction_id=tx_id)
        self._record(event)

    def debit(self, amount: Decimal, transaction_id: Optional[str] = None) -> None:
        """Remove funds, refusing to overdraw. Idempotent on ``transaction_id``."""
        amount = self._validate_amount(amount)

        # Check funds before emitting an event so the ledger never goes negative.
        if amount > self._balance:
            raise InsufficientFundsError(
                f"Cannot debit {amount} from a balance of {self._balance}"
            )

        tx_id = transaction_id or str(uuid.uuid4())

        if self._already_processed(tx_id):
            return

        event = FundsDebited(amount=amount, transaction_id=tx_id)
        self._record(event)

    # ── internals ────────────────────────────────────────────────────────

    @staticmethod
    def _validate_amount(amount: Decimal) -> Decimal:
        value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
        if value <= 0:
            raise ValueError("Amount must be positive")
        return value

    def _already_processed(self, transaction_id: str) -> bool:
        return any(event.transaction_id == transaction_id for event in self._events)

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)
        self._event_store.append_event(self._wallet_id, event)
        self._replay_events()

    def _replay_events(self) -> None:
        """Rebuild the balance from scratch by folding over every event."""
        balance = Decimal("0")
        for event in self._events:
            amount = Decimal(event.payload["amount"])
            if event.event_type == "FundsCredited":
                balance += amount
            elif event.event_type == "FundsDebited":
                balance -= amount
        self._balance = balance
