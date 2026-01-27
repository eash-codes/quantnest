import pytest
from decimal import Decimal
from quantnest.domain.wallet import Wallet
from quantnest.infra.storage import get_event_file

@pytest.fixture(autouse=True)
def clean_storage():
    # We’re already in a temp cwd (via conftest.py), so this is safe.
    event_file = get_event_file("user-1")
    event_file.parent.mkdir(parents=True, exist_ok=True)
    if event_file.exists():
        event_file.unlink()
    yield
    if event_file.exists():
        event_file.unlink()

def test_wallet_persistence_end_to_end():
    wallet1 = Wallet("user-1")

    wallet1.credit(Decimal("1000"))
    wallet1.debit(Decimal("400"))
    assert wallet1.balance == Decimal("600")
    assert len(wallet1.events) == 2

    event_file = get_event_file("user-1")
    assert event_file.exists()
    assert event_file.read_text().strip() != "[]"

    wallet2 = Wallet("user-1")
    assert wallet2.balance == Decimal("600")
    assert len(wallet2.events) == 2

def test_wallet_replay_from_empty_file():
    wallet = Wallet("user-1")
    assert wallet.balance == Decimal("0")
    assert len(wallet.events) == 0

def test_wallet_replay_from_invalid_json():
    event_file = get_event_file("user-1")
    event_file.parent.mkdir(parents=True, exist_ok=True)
    event_file.write_text("invalid json")

    wallet = Wallet("user-1")
    assert wallet.balance == Decimal("0")
    assert len(wallet.events) == 0

def test_persistence_is_append_only():
    wallet1 = Wallet("user-1")
    wallet1.credit(Decimal("100"))
    events1_count = len(wallet1.events)

    wallet2 = Wallet("user-1")
    assert len(wallet2.events) == events1_count

    wallet2.credit(Decimal("200"))
    assert len(wallet2.events) == events1_count + 1
