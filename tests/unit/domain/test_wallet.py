"""Wallet ledger: balance derivation, idempotency and replay guarantees."""

from decimal import Decimal

import pytest

from quantnest.domain.events import FundsCredited, FundsDebited
from quantnest.domain.exceptions import InsufficientFundsError
from quantnest.domain.ports import InMemoryEventStore
from quantnest.domain.wallet import Wallet


def test_credit_and_debit_happy_path(make_wallet):
    wallet = make_wallet("W1")

    wallet.credit(Decimal("10000"))
    assert wallet.balance == Decimal("10000")
    assert len(wallet.events) == 1
    assert isinstance(wallet.events[0], FundsCredited)

    wallet.debit(Decimal("4000"))
    assert wallet.balance == Decimal("6000")
    assert len(wallet.events) == 2
    assert isinstance(wallet.events[1], FundsDebited)


def test_debit_beyond_balance_is_refused(make_wallet):
    wallet = make_wallet("W1")
    wallet.credit(Decimal("5000"))

    with pytest.raises(InsufficientFundsError):
        wallet.debit(Decimal("6000"))

    # The failed attempt must leave no trace on the ledger.
    assert wallet.balance == Decimal("5000")
    assert len(wallet.events) == 1


@pytest.mark.parametrize("amount", [Decimal("-100"), Decimal("0")])
def test_non_positive_amounts_are_rejected(make_wallet, amount):
    wallet = make_wallet("W1")

    with pytest.raises(ValueError):
        wallet.credit(amount)
    with pytest.raises(ValueError):
        wallet.debit(amount)


def test_credit_is_idempotent_on_transaction_id(make_wallet):
    wallet = make_wallet("W1")

    wallet.credit(Decimal("100"), "tx-123")
    wallet.credit(Decimal("100"), "tx-123")

    assert wallet.balance == Decimal("100")
    assert len(wallet.events) == 1


def test_debit_is_idempotent_on_transaction_id(make_wallet):
    wallet = make_wallet("W1")
    wallet.credit(Decimal("200"), "funding")

    wallet.debit(Decimal("50"), "tx-456")
    wallet.debit(Decimal("50"), "tx-456")

    assert wallet.balance == Decimal("150")
    assert len(wallet.events) == 2


def test_distinct_transaction_ids_both_apply(make_wallet):
    wallet = make_wallet("W1")

    wallet.credit(Decimal("100"), "tx-a")
    wallet.credit(Decimal("100"), "tx-b")

    assert wallet.balance == Decimal("200")
    assert len(wallet.events) == 2


def test_balance_is_rebuilt_from_the_event_log(event_store):
    """A second Wallet over the same store must replay to the same balance."""
    first = Wallet("W1", event_store=event_store)
    first.credit(Decimal("1000"))
    first.debit(Decimal("250"))
    first.credit(Decimal("75.50"))

    replayed = Wallet("W1", event_store=event_store)

    assert replayed.balance == first.balance == Decimal("825.50")
    assert len(replayed.events) == 3


def test_events_are_append_only(make_wallet):
    wallet = make_wallet("W1")
    wallet.credit(Decimal("100"))

    # The events property hands back a copy, so callers cannot mutate history.
    snapshot = wallet.events
    snapshot.clear()

    assert len(wallet.events) == 1


def test_wallets_are_isolated_by_id():
    store = InMemoryEventStore()

    alice = Wallet("alice", event_store=store)
    bob = Wallet("bob", event_store=store)

    alice.credit(Decimal("500"))

    assert alice.balance == Decimal("500")
    assert bob.balance == Decimal("0")
    assert Wallet("bob", event_store=store).balance == Decimal("0")


def test_wallet_defaults_to_ephemeral_storage():
    """Constructing without a store must not touch the database."""
    wallet = Wallet("scratch")
    wallet.credit(Decimal("42"))

    assert wallet.balance == Decimal("42")
    assert Wallet("scratch").balance == Decimal("0")
