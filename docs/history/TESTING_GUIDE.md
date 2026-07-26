# QuantNest Complete Testing & Verification Guide

This document contains **all commands** you need to test and verify the entire QuantNest project. Follow these steps to validate that everything works correctly.

---

## 📋 Prerequisites

### 1. Activate Virtual Environment
```bash
cd /Users/eashubhthapliyal/Desktop/quantnest
source .venv/bin/activate
```

### 2. Start the Server
```bash
# In Terminal 1
uvicorn quantnest.api.main:app --reload
```

**Expected Output:**
```
INFO: Will watch for changes in these directories: [...]
INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO: Started reloader process [...]
INFO: Started server process [...]
INFO: Application startup complete.
```

### 3. Open Second Terminal
Open a new terminal window for running the curl commands below.

```bash
# In Terminal 2
cd /Users/eashubhthapliyal/Desktop/quantnest
source .venv/bin/activate
```

---

## 🧪 Complete Test Suite

### **Test 1: Verify Server is Running**

```bash
curl http://localhost:8000/
```

**Expected Response:**
```json
{
  "message": "QuantNest Day 9 - Trading Platform with History & Observability"
}
```

✅ **Verify:** You see the welcome message.

---

### **Test 2: Check API Documentation (Swagger UI)**

Open your browser:
```bash
open http://localhost:8000/docs
```

✅ **Verify:** You see the interactive API documentation with all endpoints grouped by tags:
- `portfolio` - Portfolio operations
- `orders` - Order management
- `history` - History & timeline

---

## 💰 Wallet Operations (Adding/Removing Balance)

### **Test 3: Credit Wallet (Add Funds)**

```bash
curl -X POST "http://localhost:8000/portfolio/demo-user/credit" \
  -H "Content-Type: application/json" \
  -H "X-Transaction-ID: txn-credit-001" \
  -d '{"amount": 100000.0}'
```

**Expected Response:**
```json
{
  "wallet_id": "demo-user",
  "amount": 100000.0,
  "transaction_id": "txn-credit-001",
  "new_balance": 100000.0,
  "message": "Successfully credited ₹100000.0 to wallet demo-user"
}
```

✅ **Verify:** 
- `new_balance` shows ₹100,000
- `transaction_id` matches what you sent
- Success message displayed

---

### **Test 4: Verify Credit Idempotency**

Run the **exact same command again** with the same transaction ID:

```bash
curl -X POST "http://localhost:8000/portfolio/demo-user/credit" \
  -H "Content-Type: application/json" \
  -H "X-Transaction-ID: txn-credit-001" \
  -d '{"amount": 100000.0}'
```

**Expected Response:**
```json
{
  "wallet_id": "demo-user",
  "amount": 100000.0,
  "transaction_id": "txn-credit-001",
  "new_balance": 100000.0,
  "message": "Successfully credited ₹100000.0 to wallet demo-user"
}
```

✅ **Verify:** 
- `new_balance` is still ₹100,000 (NOT ₹200,000)
- The duplicate transaction was safely ignored
- **This proves idempotency works!**

---

### **Test 5: Check Portfolio Summary**

```bash
curl http://localhost:8000/portfolio/demo-user/summary
```

**Expected Response:**
```json
{
  "wallet_id": "demo-user",
  "cash": 100000.0,
  "total_asset_value": 0.0,
  "total_value": 100000.0,
  "positions": {},
  "unrealized_pnl": {},
  "allocations": {"cash": 1.0},
  "health_signals": [],
  "event_count": 1
}
```

✅ **Verify:**
- `cash` = ₹100,000 (what you just credited)
- `total_value` = ₹100,000 (cash only, no assets yet)
- `positions` = {} (empty, no stocks bought yet)
- `allocations` = {"cash": 1.0} (100% in cash)

---

## 📈 Buying Shares (Order Management)

### **Test 6: Buy Shares (Market Order)**

```bash
curl -X POST "http://localhost:8000/orders/?wallet_id=demo-user&symbol=TCS&side=BUY&quantity=5.0" \
  -H "X-Transaction-ID: txn-buy-001"
```

**Expected Response:**
```json
{
  "order_id": "a1b2c3d4-...",
  "wallet_id": "demo-user",
  "symbol": "TCS",
  "side": "BUY",
  "quantity": 5.0,
  "order_type": "MARKET",
  "status": "FILLED",
  "filled_quantity": 5.0,
  "average_fill_price": 3800.0,
  "transaction_id": "txn-buy-001",
  "timestamp": "2026-03-29T..."
}
```

✅ **Verify:**
- `status` = "FILLED" (order executed successfully)
- `average_fill_price` = ₹3,800 (current TCS price)
- `filled_quantity` = 5.0 (all shares bought)

**Cost Calculation:** 5 × ₹3,800 = ₹19,000

---

### **Test 7: Verify Portfolio After Purchase**

```bash
curl http://localhost:8000/portfolio/demo-user/summary
```

**Expected Response:**
```json
{
  "wallet_id": "demo-user",
  "cash": 81000.0,
  "total_asset_value": 19000.0,
  "total_value": 100000.0,
  "positions": {"TCS": 5.0},
  "unrealized_pnl": {"TCS": 19000.0},
  "allocations": {"cash": 0.81, "TCS": 0.19},
  "health_signals": [],
  "event_count": 2
}
```

✅ **Verify:**
- `cash` = ₹81,000 (₹100,000 - ₹19,000)
- `positions` = {"TCS": 5.0} (you now own 5 TCS shares)
- `total_asset_value` = ₹19,000 (value of TCS holdings)
- `allocations` = 81% cash, 19% TCS

---

### **Test 8: Buy Another Stock**

```bash
curl -X POST "http://localhost:8000/orders/?wallet_id=demo-user&symbol=RELIANCE&side=BUY&quantity=10.0" \
  -H "X-Transaction-ID: txn-buy-002"
```

**Expected Response:**
```json
{
  "order_id": "...",
  "symbol": "RELIANCE",
  "side": "BUY",
  "quantity": 10.0,
  "status": "FILLED",
  "average_fill_price": 2500.0,
  "filled_quantity": 10.0
}
```

**Cost Calculation:** 10 × ₹2,500 = ₹25,000

✅ **Verify:**
- Order FILLED at ₹2,500 per share
- `filled_quantity` = 10.0

---

### **Test 9: Verify Updated Portfolio**

```bash
curl http://localhost:8000/portfolio/demo-user/summary
```

**Expected Response:**
```json
{
  "wallet_id": "demo-user",
  "cash": 56000.0,
  "total_asset_value": 44000.0,
  "total_value": 100000.0,
  "positions": {"TCS": 5.0, "RELIANCE": 10.0},
  "unrealized_pnl": {"TCS": 19000.0, "RELIANCE": 25000.0},
  "allocations": {"cash": 0.56, "TCS": 0.19, "RELIANCE": 0.25},
  "health_signals": [],
  "event_count": 3
}
```

✅ **Verify:**
- `cash` = ₹56,000 (₹81,000 - ₹25,000)
- `positions` = TCS: 5, RELIANCE: 10
- `allocations` = 56% cash, 19% TCS, 25% RELIANCE

---

## 📉 Selling Shares

### **Test 10: Sell Shares**

```bash
curl -X POST "http://localhost:8000/orders/?wallet_id=demo-user&symbol=TCS&side=SELL&quantity=2.0" \
  -H "X-Transaction-ID: txn-sell-001"
```

**Expected Response:**
```json
{
  "order_id": "...",
  "symbol": "TCS",
  "side": "SELL",
  "quantity": 2.0,
  "status": "FILLED",
  "average_fill_price": 3800.0,
  "filled_quantity": 2.0
}
```

**Proceeds:** 2 × ₹3,800 = ₹7,600

✅ **Verify:**
- Order FILLED
- You sold 2 TCS shares at ₹3,800 each

---

### **Test 11: Verify Portfolio After Sale**

```bash
curl http://localhost:8000/portfolio/demo-user/summary
```

**Expected Response:**
```json
{
  "wallet_id": "demo-user",
  "cash": 63600.0,
  "total_asset_value": 35200.0,
  "total_value": 98800.0,
  "positions": {"TCS": 3.0, "RELIANCE": 10.0},
  "unrealized_pnl": {"TCS": 11400.0, "RELIANCE": 25000.0},
  "allocations": {"cash": 0.64, "TCS": 0.11, "RELIANCE": 0.25},
  "health_signals": [],
  "event_count": 4
}
```

✅ **Verify:**
- `cash` = ₹63,600 (₹56,000 + ₹7,600)
- `positions["TCS"]` = 3.0 (was 5.0, sold 2.0)
- `total_value` may vary slightly due to rounding

---

## ❌ Testing Error Cases (Validation)

### **Test 12: Insufficient Funds (Order Rejection)**

Try to buy more shares than you can afford:

```bash
curl -X POST "http://localhost:8000/orders/?wallet_id=demo-user&symbol=TCS&side=BUY&quantity=100.0" \
  -H "X-Transaction-ID: txn-buy-fail-001"
```

**Expected Response:**
```json
{
  "order_id": "...",
  "wallet_id": "demo-user",
  "symbol": "TCS",
  "side": "BUY",
  "quantity": 100.0,
  "status": "REJECTED",
  "filled_quantity": 0.0,
  "average_fill_price": null,
  "rejection_reason": "Insufficient funds: need ₹380000.000, have ₹63600.00",
  "transaction_id": "txn-buy-fail-001"
}
```

✅ **Verify:**
- `status` = "REJECTED"
- `rejection_reason` explains why (need ₹380,000, have ₹63,600)
- `filled_quantity` = 0.0 (no shares bought)

---

### **Test 13: Selling More Than Owned (Order Rejection)**

Try to sell more TCS shares than you own (you own 3, try to sell 10):

```bash
curl -X POST "http://localhost:8000/orders/?wallet_id=demo-user&symbol=TCS&side=SELL&quantity=10.0" \
  -H "X-Transaction-ID: txn-sell-fail-001"
```

**Expected Response:**
```json
{
  "order_id": "...",
  "status": "REJECTED",
  "rejection_reason": "Insufficient positions: own 3, trying to sell 10"
}
```

✅ **Verify:**
- `status` = "REJECTED"
- `rejection_reason` = "Insufficient positions"
- No shares were sold

---

### **Test 14: Invalid Symbol (Order Rejection)**

Try to buy a stock that doesn't exist:

```bash
curl -X POST "http://localhost:8000/orders/?wallet_id=demo-user&symbol=INVALID&side=BUY&quantity=1.0" \
  -H "X-Transaction-ID: txn-buy-fail-002"
```

**Expected Response:**
```json
{
  "order_id": "...",
  "status": "REJECTED",
  "rejection_reason": "Unknown symbol: INVALID"
}
```

✅ **Verify:**
- `status` = "REJECTED"
- Error message clearly states the symbol is unknown

---

## 📜 History & Observability

### **Test 15: Get Trade History**

```bash
curl http://localhost:8000/history/portfolio/demo-user/trades
```

**Expected Response:**
```json
{
  "items": [
    {
      "trade_id": "trade-demo-user-0",
      "wallet_id": "demo-user",
      "symbol": "TCS",
      "side": "SELL",
      "quantity": 2.0,
      "price": 3800.0,
      "total_value": 7600.0,
      "timestamp": "..."
    },
    {
      "symbol": "RELIANCE",
      "side": "BUY",
      "quantity": 10.0,
      "price": 2500.0,
      "total_value": 25000.0
    },
    {
      "symbol": "TCS",
      "side": "BUY",
      "quantity": 5.0,
      "price": 3800.0,
      "total_value": 19000.0
    }
  ],
  "total": 3,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

✅ **Verify:**
- Shows all 3 trades (2 buys, 1 sell)
- Most recent trades appear first
- Pagination info included

---

### **Test 16: Get Order History**

```bash
curl http://localhost:8000/orders/demo-user
```

**Expected Response:**
```json
{
  "items": [
    {
      "order_id": "...",
      "symbol": "TCS",
      "side": "SELL",
      "quantity": 2.0,
      "status": "FILLED",
      "price": 3800.0
    },
    {
      "symbol": "TCS",
      "side": "BUY",
      "quantity": 100.0,
      "status": "REJECTED",
      "rejection_reason": "Insufficient funds..."
    },
    {
      "symbol": "RELIANCE",
      "side": "BUY",
      "quantity": 10.0,
      "status": "FILLED",
      "price": 2500.0
    },
    {
      "symbol": "TCS",
      "side": "BUY",
      "quantity": 5.0,
      "status": "FILLED",
      "price": 3800.0
    }
  ],
  "total": 4,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

✅ **Verify:**
- Shows ALL orders (both FILLED and REJECTED)
- Includes the failed order from Test 12
- Most recent orders appear first

---

### **Test 17: Filter Orders by Status**

Get only rejected orders:
```bash
curl "http://localhost:8000/orders/demo-user?status=REJECTED"
```

Get only filled orders:
```bash
curl "http://localhost:8000/orders/demo-user?status=FILLED"
```

✅ **Verify:** Filtering works correctly

---

### **Test 18: Get Wallet Events (Audit Trail)**

```bash
curl http://localhost:8000/history/wallet/demo-user/events
```

**Expected Response:**
```json
{
  "items": [
    {
      "event_id": "...",
      "wallet_id": "demo-user",
      "event_type": "FundsCredited",
      "amount": 7600.0,
      "transaction_id": "txn-sell-001",
      "timestamp": "..."
    },
    {
      "event_type": "FundsDebited",
      "amount": 25000.0,
      "transaction_id": "txn-buy-002",
      "timestamp": "..."
    },
    {
      "event_type": "FundsDebited",
      "amount": 19000.0,
      "transaction_id": "txn-buy-001",
      "timestamp": "..."
    },
    {
      "event_type": "FundsCredited",
      "amount": 100000.0,
      "transaction_id": "txn-credit-001",
      "timestamp": "..."
    }
  ],
  "total": 4,
  "limit": 100,
  "offset": 0,
  "has_more": false
}
```

✅ **Verify:**
- Shows ALL wallet transactions (credits and debits)
- Each event has a unique `transaction_id`
- This is your **complete financial audit trail**

---

### **Test 19: Get Unified Timeline (Most Powerful Feature)**

```bash
curl http://localhost:8000/history/portfolio/demo-user/timeline
```

**Expected Response:**
```json
{
  "items": [
    {
      "event_type": "order_filled",
      "timestamp": "...",
      "wallet_id": "demo-user",
      "metadata": {
        "order_id": "...",
        "symbol": "TCS",
        "side": "SELL",
        "filled_quantity": 2.0,
        "average_price": 3800.0
      }
    },
    {
      "event_type": "wallet_credit",
      "timestamp": "...",
      "metadata": {
        "amount": 7600.0,
        "transaction_id": "txn-sell-001"
      }
    },
    {
      "event_type": "order_placed",
      "timestamp": "...",
      "metadata": {
        "symbol": "TCS",
        "side": "SELL",
        "quantity": 2.0
      }
    },
    {
      "event_type": "wallet_debit",
      "timestamp": "...",
      "metadata": {
        "amount": 25000.0,
        "transaction_id": "txn-buy-002"
      }
    }
  ],
  "total": 8,
  "limit": 100,
  "offset": 0,
  "has_more": false
}
```

✅ **Verify:**
- Shows ALL events in chronological order (newest first)
- Mixes order events (placed/filled) with wallet events (credit/debit)
- This is your **complete activity timeline**

---

### **Test 20: Get Activity Summary**

```bash
curl http://localhost:8000/history/portfolio/demo-user/activity-summary
```

**Expected Response:**
```json
{
  "wallet_id": "demo-user",
  "total_trades": 3,
  "total_wallet_events": 4,
  "first_activity": "2026-03-29T16:50:21.994137",
  "last_activity": "2026-03-29T17:16:59.338618",
  "most_traded_symbol": "TCS",
  "symbols_traded": ["TCS", "RELIANCE"]
}
```

✅ **Verify:**
- `total_trades` = 3 (2 buys + 1 sell)
- `total_wallet_events` = 4 (1 credit + 2 debits + 1 credit from sale)
- `most_traded_symbol` = "TCS" (traded twice)
- Shows symbols you traded

---

## 🔍 Integrity Checks

### **Test 21: Verify Balance Integrity**

```bash
# Get current portfolio summary
curl http://localhost:8000/portfolio/demo-user/summary

# Get wallet events
curl http://localhost:8000/history/wallet/demo-user/events
```

**Manual Verification:**
1. Start with initial credit: +₹100,000
2. Buy TCS (5 × ₹3,800): -₹19,000
3. Buy RELIANCE (10 × ₹2,500): -₹25,000
4. Sell TCS (2 × ₹3,800): +₹7,600

**Expected Cash:** ₹100,000 - ₹19,000 - ₹25,000 + ₹7,600 = **₹63,600**

✅ **Verify:** The `cash` field in portfolio summary matches ₹63,600

---

### **Test 22: Verify Position Integrity**

```bash
curl http://localhost:8000/portfolio/demo-user/summary
```

**Manual Verification:**
1. Bought 5 TCS, sold 2 TCS → **3 TCS remaining**
2. Bought 10 RELIANCE, sold 0 → **10 RELIANCE remaining**

✅ **Verify:** 
- `positions` = {"TCS": 3.0, "RELIANCE": 10.0}
- Matches expected holdings

---

### **Test 23: Verify Order Count Matches Trade Count**

```bash
# Get order history
curl http://localhost:8000/orders/demo-user

# Get trade history
curl http://localhost:8000/history/portfolio/demo-user/trades
```

**Expected:**
- Total orders: 5 (3 filled + 2 rejected)
- Total trades: 3 (only FILLED orders create trades)

✅ **Verify:** 
- Orders include rejected ones
- Trades only include successful executions
- This proves the separation between Order and Trade!

---

## 🧹 Cleanup (Optional)

### **Test 24: Start Fresh with New User**

If you want to test with a clean slate:

```bash
# Create new wallet and fund it
curl -X POST "http://localhost:8000/portfolio/test-user/credit" \
  -H "Content-Type: application/json" \
  -H "X-Transaction-ID: fresh-credit-001" \
  -d '{"amount": 50000.0}'

# Verify empty portfolio
curl http://localhost:8000/portfolio/test-user/summary
```

**Expected Response:**
```json
{
  "wallet_id": "test-user",
  "cash": 50000.0,
  "total_asset_value": 0.0,
  "total_value": 50000.0,
  "positions": {},
  "unrealized_pnl": {},
  "allocations": {"cash": 1.0},
  "health_signals": [],
  "event_count": 1
}
```

✅ **Verify:** Clean slate with ₹50,000 and no positions

---

## 🛑 Stopping the Server

When you're done testing:

**In Terminal 1** (where server is running):
```bash
Press CTRL+C
```

Or in any terminal:
```bash
pkill -f "uvicorn"
```

✅ **Verify:** Server stops and port 8000 is freed

---

## 📊 Quick Reference: Available Market Symbols

| Symbol | Price | Sector |
|--------|-------|--------|
| RELIANCE | ₹2,500 | Energy |
| TCS | ₹3,800 | IT Services |
| INFY | ₹1,650 | IT Services |
| HDFCBANK | ₹1,550 | Banking |

---

## 🎯 Test Scenarios to Try

### **Scenario A: Complete Trading Cycle**
1. Credit wallet with ₹100,000
2. Buy 5 TCS
3. Buy 10 RELIANCE
4. Sell 2 TCS
5. Check portfolio summary
6. Check trade history
7. Check order history
8. Check timeline
9. Verify balance integrity

### **Scenario B: Error Handling**
1. Try to buy shares with insufficient funds
2. Try to sell shares you don't own
3. Try to buy invalid symbol
4. Verify all orders are REJECTED with clear reasons

### **Scenario C: Idempotency**
1. Credit wallet with transaction ID "txn-001"
2. Credit wallet again with same "txn-001"
3. Verify balance only increased once

### **Scenario D: History & Timeline**
1. Execute several trades
2. Get trade history
3. Get order history (includes rejected)
4. Get unified timeline
5. Get activity summary
6. Verify all events are present

---

## ✅ Definition of Done

Your QuantNest project is working correctly if:

- ✅ Wallet can be credited with funds
- ✅ Orders can be placed (BUY/SELL)
- ✅ Orders are validated before execution
- ✅ Insufficient funds/positions result in REJECTED orders
- ✅ Portfolio summary shows correct positions and cash
- ✅ Trade history shows all executed trades
- ✅ Order history shows all orders (including rejected)
- ✅ Wallet events show complete audit trail
- ✅ Unified timeline shows chronological events
- ✅ Activity summary provides accurate statistics
- ✅ Idempotency prevents duplicate transactions
- ✅ Balance integrity is maintained (can be manually verified)
- ✅ Position integrity is maintained (can be manually verified)

---

## 🐛 Troubleshooting

### **Issue: "Connection refused"**
**Solution:** Make sure the server is running in Terminal 1

### **Issue: "Port 8000 already in use"**
**Solution:** Kill existing process:
```bash
lsof -i :8000
kill -9 <PID>
```

### **Issue: Orders not showing in history**
**Solution:** Check if you're using the correct wallet_id in your requests

### **Issue: Balance doesn't match expected**
**Solution:** Recheck all transactions manually:
```bash
# Get all wallet events and sum them
curl http://localhost:8000/history/wallet/{wallet_id}/events
```

---

## 📝 Notes

- All monetary values are in INR (₹)
- Transaction IDs are optional but recommended for idempotency
- Orders are more informative than trades (show rejections too)
- Timeline is the most comprehensive view
- Activity summary is great for quick dashboards

---

**Happy Testing! 🚀**
