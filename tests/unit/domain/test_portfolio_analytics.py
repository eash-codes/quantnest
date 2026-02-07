from decimal import Decimal
from quantnest.domain.portfolio import Portfolio
from quantnest.domain.market import MarketProvider

def test_total_value_and_allocations_change_with_price():
    market = MarketProvider()
    p = Portfolio("A1", market)
    p.wallet.credit(Decimal("100000"))
    p.buy("RELIANCE", Decimal("10"))  # cost 25k → cash 75k

    # baseline
    assert p.cash() == Decimal("75000.00")
    assert p.asset_values()["RELIANCE"] == Decimal("25000.00")
    assert p.total_value() == Decimal("100000.00")

    # price changes → value changes (read-only analytics)
    market._prices["RELIANCE"] = Decimal("3000.00")
    assert p.asset_values()["RELIANCE"] == Decimal("30000.00")
    assert p.total_value() == Decimal("105000.00")

    alloc = p.allocations()
    assert alloc["cash"] == Decimal("0.71")        # 75000/105000 ≈ 0.714.. → 0.71
    assert alloc["RELIANCE"] == Decimal("0.29")    # 30000/105000 ≈ 0.285.. → 0.29

def test_unrealized_pnl_average_cost():
    market = MarketProvider()
    p = Portfolio("A2", market)
    p.wallet.credit(Decimal("100000"))

    p.buy("INFY", Decimal("10"))  # buy at 1650
    market._prices["INFY"] = Decimal("1700.00")

    assert p.avg_cost("INFY") == Decimal("1650.00")
    assert p.unrealized_pnl("INFY") == Decimal("500.00")  # (1700-1650)*10

def test_health_signals_concentration_and_cash():
    market = MarketProvider()
    p = Portfolio("A3", market)
    p.wallet.credit(Decimal("100000"))
    p.buy("RELIANCE", Decimal("30"))  # 75k invested, 25k cash → heavy concentration

    signals = p.health_signals(max_asset_pct=Decimal("0.40"), min_cash_pct=Decimal("0.30"))
    assert any("High concentration" in s for s in signals)
    assert any("Low cash buffer" in s for s in signals)
