from decimal import Decimal
from quantnest.domain.portfolio import Portfolio
from quantnest.domain.market import MarketProvider

# Setup
market = MarketProvider()
portfolio = Portfolio("user-1", market)

# Fund wallet directly (since it's private in Portfolio)
portfolio.wallet.credit(Decimal("100000"))

# Trade
portfolio.buy("RELIANCE", Decimal("10"))
portfolio.sell("RELIANCE", Decimal("5"))

print("Wallet balance:", portfolio.wallet.balance)
print("RELIANCE position:", portfolio.positions.get("RELIANCE", 0))
print("Trades:", len(portfolio.trades))
