"""Portfolio: trading rules, persistence and analytics."""

from decimal import Decimal

import pytest

from quantnest.domain.exceptions import (
    InsufficientFundsError,
    InsufficientPositionsError,
    UnknownSymbolError,
    ValidationError,
)


def test_buy_then_sell_full_cycle(make_portfolio):
    portfolio = make_portfolio("cycle")
    portfolio.wallet.credit(Decimal("100000"))

    portfolio.buy("RELIANCE", Decimal("10"))  # 10 × 2500 = 25,000
    assert portfolio.wallet.balance == Decimal("75000")
    assert portfolio.positions["RELIANCE"] == Decimal("10")
    assert len(portfolio.trades) == 1

    portfolio.sell("RELIANCE", Decimal("5"))  # +12,500
    assert portfolio.wallet.balance == Decimal("87500")
    assert portfolio.positions["RELIANCE"] == Decimal("5")
    assert len(portfolio.trades) == 2


def test_cannot_sell_more_than_held(make_portfolio):
    portfolio = make_portfolio("oversell")
    portfolio.wallet.credit(Decimal("100000"))
    portfolio.buy("TCS", Decimal("2"))

    with pytest.raises(InsufficientPositionsError):
        portfolio.sell("TCS", Decimal("3"))


def test_cannot_buy_without_funds(make_portfolio):
    portfolio = make_portfolio("broke")
    portfolio.wallet.credit(Decimal("1000"))

    with pytest.raises(InsufficientFundsError):
        portfolio.buy("RELIANCE", Decimal("10"))


def test_unknown_symbol_is_rejected(make_portfolio):
    portfolio = make_portfolio("unknown")
    portfolio.wallet.credit(Decimal("100000"))

    with pytest.raises(UnknownSymbolError):
        portfolio.buy("NOTREAL", Decimal("1"))


@pytest.mark.parametrize("quantity", [Decimal("0"), Decimal("-5")])
def test_non_positive_quantity_is_rejected(make_portfolio, quantity):
    portfolio = make_portfolio("qty")
    portfolio.wallet.credit(Decimal("100000"))

    with pytest.raises(ValidationError):
        portfolio.buy("INFY", quantity)


def test_selling_the_whole_position_removes_it(make_portfolio):
    portfolio = make_portfolio("flatten")
    portfolio.wallet.credit(Decimal("100000"))

    portfolio.buy("INFY", Decimal("10"))
    portfolio.sell("INFY", Decimal("10"))

    assert "INFY" not in portfolio.positions


def test_positions_and_trades_survive_a_reload(make_portfolio):
    """State must round-trip through the repositories."""
    portfolio = make_portfolio("persist")
    portfolio.wallet.credit(Decimal("100000"))
    portfolio.buy("INFY", Decimal("10"))
    portfolio.buy("TCS", Decimal("2"))

    reloaded = make_portfolio("persist")

    assert reloaded.positions == {"INFY": Decimal("10"), "TCS": Decimal("2")}
    assert len(reloaded.trades) == 2
    assert reloaded.wallet.balance == portfolio.wallet.balance


def test_positions_property_is_a_copy(make_portfolio):
    portfolio = make_portfolio("copy")
    portfolio.wallet.credit(Decimal("100000"))
    portfolio.buy("INFY", Decimal("5"))

    portfolio.positions["INFY"] = Decimal("999")

    assert portfolio.positions["INFY"] == Decimal("5")


# ── Analytics ────────────────────────────────────────────────────────────


def test_valuation_tracks_price_moves(make_portfolio, market):
    portfolio = make_portfolio("valuation")
    portfolio.wallet.credit(Decimal("100000"))
    portfolio.buy("RELIANCE", Decimal("10"))

    assert portfolio.cash() == Decimal("75000.00")
    assert portfolio.asset_values()["RELIANCE"] == Decimal("25000.00")
    assert portfolio.total_value() == Decimal("100000.00")

    market.set_price("RELIANCE", Decimal("3000.00"))

    assert portfolio.asset_values()["RELIANCE"] == Decimal("30000.00")
    assert portfolio.total_value() == Decimal("105000.00")

    allocations = portfolio.allocations()
    assert allocations["cash"] == Decimal("0.71")       # 75000 / 105000
    assert allocations["RELIANCE"] == Decimal("0.29")   # 30000 / 105000


def test_unrealized_pnl_uses_weighted_average_cost(make_portfolio, market):
    portfolio = make_portfolio("pnl")
    portfolio.wallet.credit(Decimal("100000"))

    portfolio.buy("INFY", Decimal("10"))  # at 1650
    market.set_price("INFY", Decimal("1700.00"))

    assert portfolio.avg_cost("INFY") == Decimal("1650.00")
    assert portfolio.unrealized_pnl("INFY") == Decimal("500.00")  # (1700-1650) × 10


def test_average_cost_is_quantity_weighted(make_portfolio, market):
    portfolio = make_portfolio("avg")
    portfolio.wallet.credit(Decimal("100000"))

    portfolio.buy("INFY", Decimal("10"))  # at 1650
    market.set_price("INFY", Decimal("1750.00"))
    portfolio.buy("INFY", Decimal("10"))  # at 1750

    # (10×1650 + 10×1750) / 20 = 1700
    assert portfolio.avg_cost("INFY") == Decimal("1700.00")


def test_average_cost_is_zero_without_buys(make_portfolio):
    portfolio = make_portfolio("nobuys")
    assert portfolio.avg_cost("INFY") == Decimal("0.00")


def test_health_signals_flag_concentration_and_low_cash(make_portfolio):
    portfolio = make_portfolio("health")
    portfolio.wallet.credit(Decimal("100000"))
    portfolio.buy("RELIANCE", Decimal("30"))  # 75k invested, 25k cash

    signals = portfolio.health_signals(
        max_asset_pct=Decimal("0.40"), min_cash_pct=Decimal("0.30")
    )

    assert any("High concentration" in signal for signal in signals)
    assert any("Low cash buffer" in signal for signal in signals)


def test_healthy_portfolio_reports_no_signals(make_portfolio):
    portfolio = make_portfolio("balanced")
    portfolio.wallet.credit(Decimal("100000"))
    portfolio.buy("INFY", Decimal("10"))  # 16.5k of 100k

    assert portfolio.health_signals() == []


def test_empty_portfolio_allocations(make_portfolio):
    portfolio = make_portfolio("empty")
    assert portfolio.allocations() == {"cash": Decimal("0.00")}
    assert portfolio.total_value() == Decimal("0.00")
