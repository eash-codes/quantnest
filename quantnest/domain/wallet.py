"""Wallet - single source of truth for account balance."""


from decimal import Decimal
from typing import List
from .events import DomainEvent, FundsCredited, FundsDebited

class InsufficientFundsError(Exception):
    """Business rule: can't spend what you don't have."""

class Wallet:
    def __init__(self, wallet_id: str):
        self._wallet_id = wallet_id
        self._balance = Decimal("0")
        self._events = []

    @property
    def balance (self) -> Decimal:
        """Current balance  - derived from all events """

        return self._balance
    
    @property
    def events(self) ->List[DomainEvent]:
        """Immutable audit trails"""

        return self._events.copy()
    
    def credit(self, amount: Decimal) -> None:
        """Add Amount - Always Succeed"""
        if amount<=0:
            raise ValueError("Amount can't be negative or Zero")
        
        self._balance += amount
        event = FundsCredited(amount)
        self._events.append(event)

    def debit(self, amount: Decimal) -> None:
        """Spend or withdraw, Reject only if insufficient balance"""
        if amount <= 0:
            raise ValueError("Amount must be positibe ")
        
        if amount >self._balance:
            raise InsufficientFundsError (f"cannot debit {amount} from {self._balance}")
        
        self._balance -= amount
        event = FundsDebited(amount)
        self._events.append(event)