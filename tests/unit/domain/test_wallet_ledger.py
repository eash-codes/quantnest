"""Day 5: Production Ledger Tests - Idempotency & Replay Guarantees."""

import pytest
from decimal import Decimal
import os
import shutil
from quantnest.domain.wallet import Wallet
from quantnest.domain.events import FundsCredited, FundsDebited


@pytest.fixture
def clean_wallet():
    """Clean wallet for isolated tests."""
    wallet_id = "test-ledger-clean"
    # Delete existing data
    event_file = f"data/wallet_events_{wallet_id}.json"
    if os.path.exists(event_file):
        os.remove(event_file)
    return Wallet(wallet_id)


def test_idempotent_credit(clean_wallet):
    """Same transaction_id twice → no double credit!"""
    tx_id = "test-tx-123"
    
    clean_wallet.credit(Decimal("100"), tx_id)
    balance1 = clean_wallet.balance  # Should be 100
    
    clean_wallet.credit(Decimal("100"), tx_id)  # Same tx_id!
    assert clean_wallet.balance == balance1  # Still 100! No double credit!
    assert len(clean_wallet.events) == 1  # Only 1 event!


def test_idempotent_debit(clean_wallet):
    """Same debit tx_id twice → no double debit!"""
    tx_id = "test-debit-456"
    clean_wallet.credit(Decimal("200"), "fund")
    
    clean_wallet.debit(Decimal("50"), tx_id)
    balance1 = clean_wallet.balance  # Should be 150
    
    clean_wallet.debit(Decimal("50"), tx_id)  # Same tx_id!
    assert clean_wallet.balance == balance1  # Still 150!
    assert len([e for e in clean_wallet.events if e.transaction_id == tx_id]) == 1


def test_replay_from_zero(clean_wallet):
    """Delete file → recreate wallet → starts fresh with zero balance."""
    # Step 1: Create transactions
    clean_wallet.credit(Decimal("100"), "tx1")
    clean_wallet.debit(Decimal("30"), "tx2")
    expected_balance = clean_wallet.balance  # 70
    event_count = len(clean_wallet.events)   # 2

    # Step 2: Delete file (simulate crash/data loss)
    event_file = f"data/wallet_events_{clean_wallet._wallet_id}.json"
    os.remove(event_file)

    # Step 3: Recreate wallet → no events to replay, starts fresh
    replayed_wallet = Wallet(clean_wallet._wallet_id)
    assert replayed_wallet.balance == Decimal("0")  # Starts fresh!
    assert len(replayed_wallet.events) == 0


def test_insufficient_funds_stops_debit(clean_wallet):
    """Cannot spend what you don't have."""
    clean_wallet.credit(Decimal("50"), "fund")
    
    with pytest.raises(Exception, match="Cannot debit"):
        clean_wallet.debit(Decimal("100"), "overdraft")


def test_negative_amount_rejected(clean_wallet):
    """Business rule violations."""
    with pytest.raises(ValueError, match="positive"):
        clean_wallet.credit(Decimal("-10"), "negative")
    
    with pytest.raises(ValueError, match="positive"):
        clean_wallet.debit(Decimal("0"), "zero")


def test_event_replay_math_correct():
    """Manual verification of replay math."""
    wallet = Wallet("math-test")
    
    # Known sequence: +100, -30, +50, -20
    wallet.credit(Decimal("100"), "e1")
    wallet.debit(Decimal("30"), "e2")
    wallet.credit(Decimal("50"), "e3")
    wallet.debit(Decimal("20"), "e4")
    
    assert wallet.balance == Decimal("100")  # 100 - 30 + 50 - 20 = 100


def test_uuid_auto_generates():
    """Auto-generate tx_id when None provided."""
    wallet = Wallet("uuid-test")
    
    tx_count_before = len(wallet.events)
    wallet.credit(Decimal("100"))  # No tx_id provided
    assert len(wallet.events) == tx_count_before + 1
    assert wallet.events[-1].transaction_id != ""  # UUID generated
