import pytest
import json
from pathlib import Path
from decimal import Decimal
from quantnest.domain.wallet import Wallet
from quantnest.infra.storage import EVENT_FILE

@pytest.fixture(autouse=True)
def clean_storage():
    """Clean storage before/after each test - isolation."""
    # Create data directory if missing
    EVENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Clean file
    if EVENT_FILE.exists():
        EVENT_FILE.unlink()
    yield
    if EVENT_FILE.exists():
        EVENT_FILE.unlink()


def test_wallet_persistence_end_to_end():
    """Full cycle: create → mutate → restart → replay works."""
    # Arrange: fresh wallet
    wallet1 = Wallet("user-1")
    
    # Act: mutate state
    wallet1.credit(Decimal("1000"))
    wallet1.debit(Decimal("400"))
    assert wallet1.balance == Decimal("600")
    assert len(wallet1.events) == 2
    
    # Assert: events persisted to disk
    assert EVENT_FILE.exists()
    assert EVENT_FILE.read_text().strip() != "[]"
    
    # Act: NEW wallet instance (simulates restart)
    wallet2 = Wallet("user-1")
    
    # Assert: balance replayed from events
    assert wallet2.balance == Decimal("600")
    assert len(wallet2.events) == 2

def test_wallet_replay_from_empty_file():
    """Wallet works when no events exist."""
    wallet = Wallet("user-1")
    assert wallet.balance == Decimal("0")
    assert len(wallet.events) == 0

def test_wallet_replay_from_invalid_json():
    """Graceful handling of corrupt storage."""
    # Create invalid JSON file
    EVENT_FILE.write_text("invalid json")
    
    wallet = Wallet("user-1")
    assert wallet.balance == Decimal("0")  # Should recover gracefully
    assert len(wallet.events) == 0

def test_persistence_is_append_only():
    """Events never get deleted/lost."""
    wallet1 = Wallet("user-1")
    wallet1.credit(Decimal("100"))
    events1_count = len(wallet1.events)
    
    # New instance replays SAME events
    wallet2 = Wallet("user-1") 
    assert len(wallet2.events) == events1_count
    
    # New events get APPENDED
    wallet2.credit(Decimal("200"))
    assert len(wallet2.events) == events1_count + 1
