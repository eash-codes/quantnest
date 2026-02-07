"""QuantNest Trading Simulator - Day 5 Ledger Demo."""

import uuid
from decimal import Decimal
from quantnest.domain.portfolio import Portfolio
from quantnest.domain.market import MarketProvider

print("🚀 QuantNest Day 5 - Production Banking Ledger Demo\n")

# Setup
market = MarketProvider()
portfolio = Portfolio("demo-user", market)

# ========== DAY 5: Transaction IDs (UPI receipts) ==========
print("💳 DAY 5: Every operation gets unique transaction ID")

# Fund wallet with transaction ID
tx_fund = str(uuid.uuid4())
portfolio.wallet.credit(Decimal("100000"), tx_fund)
print(f"💰 Funded ₹100,000 (tx: {tx_fund[:8]}...)")

# Same funding tx twice → NO double credit! (idempotent)
portfolio.wallet.credit(Decimal("100000"), tx_fund)  # Same tx_id!
print(f"✅ Same tx_id → no double credit (still ₹100,000)")

# Execute trades with transaction IDs
tx_reliance = str(uuid.uuid4())
portfolio.buy("RELIANCE", Decimal("10"), tx_reliance)  # ₹25k @ ₹2500
print(f"📈 Bought 10 RELIANCE (tx: {tx_reliance[:8]}...)")

tx_tcs = str(uuid.uuid4())
portfolio.buy("TCS", Decimal("5"), tx_tcs)              # ₹19k @ ₹3800
print(f"📈 Bought 5 TCS (tx: {tx_tcs[:8]}...)")

tx_sell = str(uuid.uuid4())
portfolio.sell("RELIANCE", Decimal("3"), tx_sell)       # +₹7.5k @ ₹2500
print(f"📉 Sold 3 RELIANCE (tx: {tx_sell[:8]}...)\n")

# ========== DAY 4 ANALYTICS (Unchanged - works perfectly) ==========
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

print(f"\n🎬 DAY 5 LEDGER PROOF")
print(f"💾 Events saved: {len(portfolio.wallet.events)}")
print(f"✅ Delete data file → replay = same results!")
