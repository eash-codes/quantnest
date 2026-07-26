"""Order execution engine: validation, lifecycle and rejection handling."""

from decimal import Decimal

import pytest

from quantnest.domain.exceptions import OrderStateError
from quantnest.domain.order import OrderStatus
from quantnest.domain.order_engine import OrderExecutionEngine
from quantnest.domain.wallet import Wallet


@pytest.fixture
def engine(market, repositories):
    return OrderExecutionEngine(
        market=market,
        order_repository=repositories["order_repository"],
        event_store=repositories["event_store"],
        position_repository=repositories["position_repository"],
        trade_repository=repositories["trade_repository"],
    )


@pytest.fixture
def funded_wallet(event_store):
    def _fund(wallet_id: str, amount: str = "100000"):
        wallet = Wallet(wallet_id, event_store=event_store)
        wallet.credit(Decimal(amount))
        return wallet

    return _fund


def test_market_buy_fills(engine, funded_wallet):
    funded_wallet("w1")

    order = engine.place_order("w1", "INFY", "BUY", Decimal("10"))

    assert order.status == OrderStatus.FILLED
    assert order.filled_quantity == Decimal("10")
    assert order.average_fill_price == Decimal("1650.00")
    assert order.rejection_reason is None


def test_market_sell_fills(engine, funded_wallet):
    funded_wallet("w1")
    engine.place_order("w1", "INFY", "BUY", Decimal("10"))

    order = engine.place_order("w1", "INFY", "SELL", Decimal("4"))

    assert order.status == OrderStatus.FILLED
    assert order.filled_quantity == Decimal("4")


def test_buy_without_funds_is_rejected_not_raised(engine, funded_wallet):
    """A business rejection must return an auditable order, not an exception."""
    funded_wallet("w1", "1000")

    order = engine.place_order("w1", "RELIANCE", "BUY", Decimal("10"))

    assert order.status == OrderStatus.REJECTED
    assert "Insufficient funds" in order.rejection_reason


def test_sell_without_holdings_is_rejected(engine, funded_wallet):
    funded_wallet("w1")

    order = engine.place_order("w1", "INFY", "SELL", Decimal("5"))

    assert order.status == OrderStatus.REJECTED
    assert "Insufficient holdings" in order.rejection_reason


def test_unknown_symbol_is_rejected(engine, funded_wallet):
    funded_wallet("w1")

    order = engine.place_order("w1", "NOTREAL", "BUY", Decimal("1"))

    assert order.status == OrderStatus.REJECTED
    assert "Unknown symbol" in order.rejection_reason


@pytest.mark.parametrize("quantity", [Decimal("0"), Decimal("-1")])
def test_non_positive_quantity_is_rejected(engine, funded_wallet, quantity):
    funded_wallet("w1")

    order = engine.place_order("w1", "INFY", "BUY", quantity)

    assert order.status == OrderStatus.REJECTED
    assert "Quantity must be positive" in order.rejection_reason


def test_invalid_side_is_rejected(engine, funded_wallet):
    funded_wallet("w1")

    order = engine.place_order("w1", "INFY", "HOLD", Decimal("1"))

    assert order.status == OrderStatus.REJECTED
    assert "Invalid order side" in order.rejection_reason


def test_limit_order_requires_a_limit_price(engine, funded_wallet):
    funded_wallet("w1")

    order = engine.place_order("w1", "INFY", "BUY", Decimal("1"), order_type="LIMIT")

    assert order.status == OrderStatus.REJECTED
    assert "limit price" in order.rejection_reason


def test_limit_buy_fills_when_market_is_within_the_limit(engine, funded_wallet):
    funded_wallet("w1")

    order = engine.place_order(
        "w1", "INFY", "BUY", Decimal("5"), order_type="LIMIT", limit_price=Decimal("1700")
    )

    assert order.status == OrderStatus.FILLED


def test_limit_buy_is_rejected_above_the_limit(engine, funded_wallet):
    funded_wallet("w1")

    order = engine.place_order(
        "w1", "INFY", "BUY", Decimal("5"), order_type="LIMIT", limit_price=Decimal("1600")
    )

    assert order.status == OrderStatus.REJECTED
    assert "exceeds the limit price" in order.rejection_reason


def test_orders_are_persisted_and_retrievable(engine, funded_wallet):
    funded_wallet("w1")
    placed = engine.place_order("w1", "INFY", "BUY", Decimal("3"))

    fetched = engine.get_order("w1", placed.order_id)

    assert fetched is not None
    assert fetched.order_id == placed.order_id
    assert fetched.status == OrderStatus.FILLED


def test_get_orders_filters_by_status(engine, funded_wallet):
    funded_wallet("w1", "20000")
    engine.place_order("w1", "INFY", "BUY", Decimal("1"))          # fills
    engine.place_order("w1", "RELIANCE", "BUY", Decimal("100"))    # rejected

    assert len(engine.get_orders("w1")) == 2
    assert len(engine.get_orders("w1", status=OrderStatus.FILLED)) == 1
    assert len(engine.get_orders("w1", status=OrderStatus.REJECTED)) == 1


def test_cancelling_a_filled_order_is_refused(engine, funded_wallet):
    funded_wallet("w1")
    order = engine.place_order("w1", "INFY", "BUY", Decimal("1"))

    with pytest.raises(OrderStateError):
        engine.cancel_order("w1", order.order_id)


def test_cancelling_an_unknown_order_returns_none(engine):
    assert engine.cancel_order("w1", "does-not-exist") is None


def test_idempotent_buy_does_not_double_debit(engine, funded_wallet, event_store):
    """Replaying the same transaction id must not move money twice."""
    wallet = funded_wallet("w1")
    starting = wallet.balance

    engine.place_order("w1", "INFY", "BUY", Decimal("2"), transaction_id="tx-1")
    engine.place_order("w1", "INFY", "BUY", Decimal("2"), transaction_id="tx-1")

    reloaded = Wallet("w1", event_store=event_store)
    assert reloaded.balance == starting - Decimal("3300.00")  # charged exactly once
