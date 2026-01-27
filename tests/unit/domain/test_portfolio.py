import pytest
from decimal import Decimal
from quantnest.domain.portfolio import Portfolio
from quantnest.domain.market import MarketProvider, UnknownSymbolError

def test_portfolio_buy_sell_full_cycle():
    """Complete trading cycle works."""
    market = MarketProvider()
    portfolio = Portfolio("test-user", market)
    portfolio.wallet.credit(Decimal("100000"))
    
    # Buy
    portfolio.buy("RELIANCE", Decimal("10"))
    assert portfolio.wallet.balance == Decimal("75000")
    assert portfolio.positions["RELIANCE"] == Decimal("10")
    assert len(portfolio.trades) == 1
    
    # Sell half
    portfolio.sell("RELIANCE", Decimal("5"))
    assert portfolio.wallet.balance == Decimal("87500")
    assert portfolio.positions["RELIANCE"] == Decimal("5")
    assert len(portfolio.trades) == 2

def test_portfolio_cannot_oversell():
    """Business rule: cannot sell more than owned."""
    market = MarketProvider()
    portfolio = Portfolio("test-user", market)
    portfolio.wallet.credit(Decimal("100000"))
    
    portfolio.buy("TCS", Decimal("2"))
    with pytest.raises(ValueError, match="Cannot sell"):
        portfolio.sell("TCS", Decimal("3"))

def test_portfolio_unknown_symbol():
    """Market enforces valid symbols."""
    market = MarketProvider()
    portfolio = Portfolio("test-user", market)
    
    with pytest.raises(UnknownSymbolError, match="Unknown symbol"):
        portfolio.buy("AAPL", Decimal("1"))

def test_portfolio_negative_quantity():
    """Business rule: positive quantity only."""
    market = MarketProvider()
    portfolio = Portfolio("test-user", market)
    portfolio.wallet.credit(Decimal("100000"))
    
    with pytest.raises(ValueError, match="positive"):
        portfolio.buy("INFY", Decimal("0"))
    with pytest.raises(ValueError, match="positive"):
        portfolio.sell("INFY", Decimal("-1"))
