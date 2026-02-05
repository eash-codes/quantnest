"""QuantNest Trading Simulator - Day 4 Demo."""

from decimal import Decimal
from quantnest.domain.portfolio import Portfolio
from quantnest.domain.market import MarketProvider

print("🚀 QuantNest Day 4 - Portfolio Analytics Demo\n")

# Setup
market = MarketProvider()
portfolio = Portfolio("demo-user", market)

# Fund the wallet
portfolio.wallet.credit(Decimal("100000"))
print(f"💰 Wallet funded: ₹{portfolio.wallet.balance:,}")

# Execute trades
portfolio.buy("RELIANCE", Decimal("10"))  # ₹25k @ ₹2500
print(f"📈 Bought 10 RELIANCE shares")

portfolio.buy("TCS", Decimal("5"))         # ₹19k @ ₹3800
print(f"📈 Bought 5 TCS shares")

portfolio.sell("RELIANCE", Decimal("3"))   # +₹7.5k @ ₹2500
print(f"📉 Sold 3 RELIANCE shares\n")

# ========== DAY 4 ANALYTICS ==========
print("📊 PORTFOLIO ANALYTICS")
print("=" * 40)

print(f"💵 Cash:               ₹{portfolio.cash():,.2f}")
print(f"📊 RELIANCE value:     ₹{portfolio.asset_value('RELIANCE'):.2f}")
print(f"📊 TCS value:          ₹{portfolio.asset_value('TCS'):.2f}")
print(f"📊 Total asset value:  ₹{portfolio.total_asset_value():,.2f}")
print(f"💎 Total portfolio:    ₹{portfolio.total_value():,.2f}")

print(f"\n📈 AVERAGE COSTS")
print(f"RELIANCE avg cost: ₹{portfolio.avg_cost('RELIANCE'):.2f}")
print(f"TCS avg cost:      ₹{portfolio.avg_cost('TCS'):.2f}")

print(f"\n🎯 UNREALIZED P&L")
print(f"RELIANCE P&L: ₹{portfolio.unrealized_pnl('RELIANCE'):.2f}")
print(f"TCS P&L:      ₹{portfolio.unrealized_pnl('TCS'):.2f}")

print(f"\n📊 ALLOCATIONS")
alloc = portfolio.allocations()
for asset, pct in sorted(alloc.items(), key=lambda x: x[1], reverse=True):
    pct_str = f"{pct:.1%}"
    print(f"  {asset:10} {pct_str}")

print(f"\n🚨 HEALTH SIGNALS")
signals = portfolio.health_signals()
if signals:
    for signal in signals:
        print(f"  ⚠️  {signal}")
else:
    print("  ✅ All clear")
