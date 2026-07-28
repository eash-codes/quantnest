"""Average cost basis: the running weighted average.

Cost basis must reflect the *currently held* position, not every BUY the
wallet has ever made. Averaging over all historical buys leaks the cost of
shares that were already sold into the price of shares still held, which
corrupts unrealised P&L for anyone who round-trips a stock.
"""

from decimal import Decimal


def test_simple_average_over_two_buys(make_portfolio, market):
    portfolio = make_portfolio("avg-simple")
    portfolio.wallet.credit(Decimal("100000"))

    portfolio.buy("INFY", Decimal("10"))            # 10 @ 1650
    market.set_price("INFY", Decimal("1750.00"))
    portfolio.buy("INFY", Decimal("10"))            # 10 @ 1750

    # (10×1650 + 10×1750) / 20
    assert portfolio.avg_cost("INFY") == Decimal("1700.00")


def test_selling_does_not_change_the_average(make_portfolio, market):
    """A partial sale realises profit; it must not move the cost basis."""
    portfolio = make_portfolio("avg-partial")
    portfolio.wallet.credit(Decimal("100000"))

    portfolio.buy("INFY", Decimal("10"))            # avg 1650
    market.set_price("INFY", Decimal("2000.00"))
    portfolio.sell("INFY", Decimal("5"))            # sell half at a profit

    assert portfolio.avg_cost("INFY") == Decimal("1650.00")
    assert portfolio.positions["INFY"] == Decimal("5")


def test_closing_a_position_resets_the_basis(make_portfolio, market):
    """The regression this file exists for.

    Sell everything, then buy again at a different price. The new average
    must be the new purchase price alone — the closed round-trip is history.
    """
    portfolio = make_portfolio("avg-reset")
    portfolio.wallet.credit(Decimal("100000"))

    portfolio.buy("INFY", Decimal("10"))            # 10 @ 1650
    portfolio.sell("INFY", Decimal("10"))           # flat: no shares held

    market.set_price("INFY", Decimal("2000.00"))
    portfolio.buy("INFY", Decimal("1"))             # 1 @ 2000

    assert portfolio.avg_cost("INFY") == Decimal("2000.00"), (
        "cost basis must reset once the position is fully closed"
    )


def test_pnl_is_zero_immediately_after_a_rebuy(make_portfolio, market):
    """P&L must be zero the instant you buy at the current market price."""
    portfolio = make_portfolio("avg-pnl")
    portfolio.wallet.credit(Decimal("100000"))

    portfolio.buy("INFY", Decimal("10"))
    portfolio.sell("INFY", Decimal("10"))

    market.set_price("INFY", Decimal("2000.00"))
    portfolio.buy("INFY", Decimal("2"))

    assert portfolio.unrealized_pnl("INFY") == Decimal("0.00")


def test_average_after_a_partial_sale_then_a_new_buy(make_portfolio, market):
    """Remaining shares keep their basis; the new tranche blends in."""
    portfolio = make_portfolio("avg-blend")
    portfolio.wallet.credit(Decimal("100000"))

    portfolio.buy("INFY", Decimal("10"))            # 10 @ 1650
    portfolio.sell("INFY", Decimal("6"))            # 4 left, still @ 1650

    market.set_price("INFY", Decimal("1900.00"))
    portfolio.buy("INFY", Decimal("6"))             # +6 @ 1900

    # (4×1650 + 6×1900) / 10 = 1800
    assert portfolio.avg_cost("INFY") == Decimal("1800.00")


def test_average_is_zero_when_nothing_was_ever_bought(make_portfolio):
    assert make_portfolio("avg-empty").avg_cost("INFY") == Decimal("0.00")


def test_each_symbol_keeps_its_own_basis(make_portfolio, market):
    portfolio = make_portfolio("avg-multi")
    portfolio.wallet.credit(Decimal("200000"))

    portfolio.buy("INFY", Decimal("10"))            # @ 1650
    portfolio.buy("TCS", Decimal("2"))              # @ 3800

    assert portfolio.avg_cost("INFY") == Decimal("1650.00")
    assert portfolio.avg_cost("TCS") == Decimal("3800.00")


def test_basis_survives_a_reload(make_portfolio, market):
    """The running average must be reconstructable from stored trades."""
    portfolio = make_portfolio("avg-reload")
    portfolio.wallet.credit(Decimal("100000"))

    portfolio.buy("INFY", Decimal("10"))
    portfolio.sell("INFY", Decimal("10"))
    market.set_price("INFY", Decimal("2000.00"))
    portfolio.buy("INFY", Decimal("3"))

    reloaded = make_portfolio("avg-reload")
    assert reloaded.avg_cost("INFY") == Decimal("2000.00")
