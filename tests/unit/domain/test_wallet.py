import pytest
from decimal import Decimal
from quantnest.domain.wallet import Wallet, InsufficientFundsError
from quantnest.domain.events import FundsCredited, FundsDebited

def test_wallet_credit_debit_happy_path():
    wallet = Wallet("W1")
    
    # Credit
    wallet.credit(Decimal("10000"))
    assert wallet.balance == Decimal("10000")
    assert len(wallet.events) == 1
    assert isinstance(wallet.events[0], FundsCredited)
    
    # Debit (partial)
    wallet.debit(Decimal("4000"))
    assert wallet.balance == Decimal("6000")
    assert len(wallet.events) == 2
    assert isinstance(wallet.events[1], FundsDebited)

def test_wallet_insufficient_funds():
    wallet = Wallet("W1")
    wallet.credit(Decimal("5000"))
    
    with pytest.raises(InsufficientFundsError):
        wallet.debit(Decimal("6000"))

def test_wallet_negative_amounts():
    wallet = Wallet("W1")
    
    with pytest.raises(ValueError):
        wallet.credit(Decimal("-100"))
    with pytest.raises(ValueError): 
        wallet.debit(Decimal("0"))

