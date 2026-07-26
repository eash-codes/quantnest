# Day 8: Order Management System (OMS)

## Overview
Day 8 introduces a **formal Order Management System (OMS)** to separate **user trading intent** from **trade execution**. This is a critical architectural evolution that mirrors real-world brokerage infrastructure used by platforms like Zerodha, Robinhood, and Interactive Brokers.

## Core Concept: Order ≠ Trade

### Before Day 8 (Direct Trading)
```
User → Portfolio.buy() → Trade → Wallet → Ledger
```
**Problem**: No separation between intent and execution. No order tracking, no rejection handling, no order lifecycle.

### After Day 8 (Order Management)
```
User → Order Created → Order Engine → Validation → Execution → Trade → Portfolio → Wallet Ledger
```
**Solution**: Clear separation of concerns with full order lifecycle management.

## Key Architectural Change

| Concept | Before Day 8 | After Day 8 |
|---------|--------------|-------------|
| **User Intent** | Direct trade execution | Order object |
| **Execution** | Immediate | Validated and processed |
| **Status** | None | PENDING, FILLED, REJECTED, CANCELLED |
| **Tracking** | None | Full order history |
| **Rejection** | Exception only | Structured rejection with reason |
| **Idempotency** | Transaction ID only | Order ID + Transaction ID |

## What We Built

### 1. Order Entity (`quantnest/domain/order.py`)

Represents **user trading intent** with full lifecycle management.

#### Key Fields
```python
order_id: str           # Unique identifier
wallet_id: str          # Owner
symbol: str             # Asset ticker
side: str               # BUY or SELL
quantity: Decimal       # Number of shares
order_type: str         # MARKET, LIMIT, STOP_LOSS
status: str             # PENDING, FILLED, REJECTED, CANCELLED, PARTIAL
timestamp: datetime     # Creation time
transaction_id: str     # Idempotency key
```

#### Order Status Lifecycle
```
PENDING → FILLED
        → REJECTED
        → CANCELLED
        → PARTIAL
```

#### Status Definitions
| Status | Meaning |
|--------|---------|
| **PENDING** | Order received, awaiting execution |
| **FILLED** | Completely executed |
| **REJECTED** | Failed validation (insufficient funds, invalid symbol, etc.) |
| **CANCELLED** | User cancelled before execution |
| **PARTIAL** | Partially executed (for large orders) |

### 2. Order Execution Engine (`quantnest/domain/order_engine.py`)

The **brain** of the OMS - responsible for processing orders and executing trades.

#### Responsibilities
1. **Receive Orders**: Accept new order requests
2. **Validate**: Check business rules (funds, positions, valid symbols)
3. **Execute**: Process trades through portfolio
4. **Update Status**: Mark orders as FILLED, REJECTED, etc.
5. **Persist**: Save orders to storage for history

#### Execution Flow
```
place_order()
    ↓
_validate_order()
    ↓
_execute_order()
    ↓
_create_trade()
    ↓
_update_portfolio()
    ↓
_save_order()
```

#### Validation Rules
The engine rejects orders when:
| Condition | Reason |
|-----------|--------|
| `quantity <= 0` | Invalid order |
| Insufficient funds | Cannot buy |
| Selling more than owned | Overselling |
| Invalid symbol | Market validation |
| Missing limit price (for LIMIT orders) | Invalid order type |

### 3. Order Persistence (`quantnest/infra/storage.py`)

Enhanced storage layer to persist orders separately from trades.

#### New Functions
- `load_orders(wallet_id)` - Load all orders for a wallet
- `save_order(wallet_id, order)` - Save or update an order
- `append_order(wallet_id, order)` - Add new order

#### Storage Format
```json
[
  {
    "order_id": "ORD123",
    "wallet_id": "demo-user",
    "symbol": "RELIANCE",
    "side": "BUY",
    "quantity": "10.0",
    "order_type": "MARKET",
    "status": "FILLED",
    "filled_quantity": "10.0",
    "average_fill_price": "2500.00",
    "timestamp": "2026-03-29T17:16:59.338618"
  }
]
```

### 4. Order API Endpoints (`quantnest/api/orders.py`)

New REST endpoints for order management.

#### POST /orders/
Place a new order.

**Request:**
```bash
POST /orders/?wallet_id=demo-user&symbol=TCS&side=BUY&quantity=10.0
X-Transaction-ID: unique-txn-id
```

**Response (Filled):**
```json
{
  "order_id": "ORD123",
  "wallet_id": "demo-user",
  "symbol": "TCS",
  "side": "BUY",
  "quantity": 10.0,
  "order_type": "MARKET",
  "status": "FILLED",
  "filled_quantity": 10.0,
  "average_fill_price": 3800.0,
  "transaction_id": "unique-txn-id"
}
```

**Response (Rejected):**
```json
{
  "order_id": "ORD124",
  "wallet_id": "demo-user",
  "symbol": "TCS",
  "side": "BUY",
  "quantity": 100.0,
  "status": "REJECTED",
  "rejection_reason": "Insufficient funds: need ₹380000, have ₹4450"
}
```

#### GET /orders/{wallet_id}
Get order history with filtering.

**Query Parameters:**
- `status` - Filter by status (PENDING, FILLED, REJECTED)
- `symbol` - Filter by symbol
- `limit` - Pagination limit
- `offset` - Pagination offset

#### GET /orders/{wallet_id}/{order_id}
Get a specific order by ID.

#### POST /orders/{wallet_id}/{order_id}/cancel
Cancel a pending or partially filled order.

### 5. Updated Command Handlers (`quantnest/application/handlers/__init__.py`)

Refactored to use OrderEngine instead of direct portfolio calls.

**Before:**
```python
class BuyAssetHandler:
    def handle(self, command):
        portfolio = Portfolio(wallet_id, market)
        portfolio.buy(symbol, quantity, transaction_id)
        return {...}
```

**After:**
```python
class BuyAssetHandler:
    def handle(self, command):
        engine = OrderExecutionEngine()
        order = engine.place_order(
            wallet_id=wallet_id,
            symbol=symbol,
            side="BUY",
            quantity=quantity
        )
        return {
            "order_id": order.order_id,
            "order_status": order.status,
            ...
        }
```

### 6. Enhanced History Service (`quantnest/application/queries/history_service.py`)

Updated to load from real order storage instead of deriving from trades.

**Before:**
```python
def get_orders(self, wallet_id):
    # Derived from trades (always FILLED)
    trades = portfolio.trades
    orders = [OrderHistoryItem(status="FILLED", ...) for t in trades]
```

**After:**
```python
def get_orders(self, wallet_id):
    # Load from actual order storage
    orders = load_orders(wallet_id)
    # Returns PENDING, FILLED, REJECTED, etc.
```

### 7. Enhanced Timeline

Timeline now includes order lifecycle events:
- `order_placed` - When order is created
- `order_filled` - When order is executed
- `order_rejected` - When order fails validation

## File Structure

```
quantnest/
├── domain/
│   ├── order.py              # NEW - Order entity
│   └── order_engine.py       # NEW - Execution engine
├── application/
│   ├── handlers/
│   │   └── __init__.py       # UPDATED - Use OrderEngine
│   └── queries/
│       └── history_service.py # UPDATED - Load from order storage
├── infra/
│   └── storage.py            # UPDATED - Order persistence
└── api/
    ├── orders.py             # NEW - Order endpoints
    └── main.py               # UPDATED - Register orders router
```

## Testing Verified

### ✅ Order Placement
```bash
curl -X POST "http://localhost:8000/orders/?wallet_id=test-user2&symbol=TCS&side=BUY&quantity=1.0"
```
**Result**: Order created with status FILLED

### ✅ Order Rejection
```bash
curl -X POST "http://localhost:8000/orders/?wallet_id=test-user2&symbol=TCS&side=BUY&quantity=100.0"
```
**Result**: Order REJECTED with reason "Insufficient funds"

### ✅ Order History
```bash
curl "http://localhost:8000/orders/test-user2"
```
**Result**: Returns all orders with correct status

### ✅ Timeline Integration
```bash
curl "http://localhost:8000/history/portfolio/test-user2/timeline"
```
**Result**: Includes order_placed, order_filled, order_rejected events

## Key Design Principles

### 1. Order ≠ Trade
- **Order**: User intent to buy/sell
- **Trade**: Execution result
- An order can create multiple trades (partial fills)
- A trade always comes from an order

### 2. Separation of Concerns
| Module | Responsibility |
|--------|---------------|
| Order | User intent, status tracking |
| Order Engine | Validation, execution logic |
| Portfolio | Position management |
| Wallet | Cash ledger |
| Events | Financial audit trail |

### 3. Order Lifecycle Management
Every order goes through a defined lifecycle:
```
Created → Validated → Executed → Filled/Rejected
                ↓
            Cancelled (optional)
```

### 4. Idempotency
- **Order ID**: Unique identifier for the order
- **Transaction ID**: Idempotency key to prevent duplicates
- Same transaction ID = same order (no double execution)

### 5. Error Handling
- **Validation Errors**: Return REJECTED status with reason
- **Execution Errors**: Exception handling with proper error messages
- **HTTP Status Codes**: 400 (bad request), 409 (conflict), 500 (server error)

## Benefits Achieved

### 1. Realistic Brokerage Simulation
- Mirrors real-world trading platforms
- Proper order lifecycle management
- Support for advanced order types (LIMIT, STOP_LOSS)

### 2. Better User Experience
- Clear order status tracking
- Rejection reasons for debugging
- Order history for auditing

### 3. Foundation for Advanced Features
- **Limit Orders**: Buy/sell at specific price
- **Stop-Loss Orders**: Automatic sell at threshold
- **Partial Fills**: Large orders executed in parts
- **Order Cancellation**: Cancel pending orders

### 4. Improved Architecture
- Clear separation: intent vs execution
- Single responsibility: each module has one job
- Testability: each component can be tested independently

### 5. Audit Trail
- Full order history
- Order lifecycle tracking
- Rejection reasons documented

## Integration with Day 9 (History Layer)

Day 8 OMS integrates seamlessly with Day 9 history layer:

### Order History Endpoint
```
GET /history/portfolio/{wallet_id}/orders
```
Returns actual orders from persistent storage with full lifecycle.

### Timeline Events
Timeline now includes:
- `order_placed` - User intent recorded
- `order_filled` - Execution successful
- `order_rejected` - Validation failed

This provides **complete observability** of the trading process.

## Definition of Done

✅ Order entity with status lifecycle  
✅ OrderExecutionEngine with validation  
✅ Order persistence to storage  
✅ Command handlers use OrderEngine  
✅ Order API endpoints working  
✅ Order history loads from storage  
✅ Timeline includes order events  
✅ Order rejection with reasons  
✅ Idempotency preserved  
✅ Existing functionality unchanged  

## What's Next (Day 10+)

With Day 8 complete, you can now build:

### 1. Advanced Order Types
- **LIMIT Orders**: Execute only at specific price
- **STOP_LOSS Orders**: Trigger at threshold price
- **GTT Orders**: Good Till Triggered

### 2. Order Book Simulation
- Bid/ask spreads
- Order matching engine
- Market depth visualization

### 3. Real-Time Features
- WebSocket order status updates
- Live order book
- Real-time portfolio updates

### 4. Settlement Processing
- T+1/T+2 settlement cycles
- Float account management
- Stock-backed payments

## Strategic Impact

Day 8 transforms QuantNest from a **simple trading system** into a **production-grade order management platform**.

### Before Day 8
```
User → Buy → Trade (done)
```

### After Day 8
```
User → Order → Validate → Execute → Trade → Ledger
       ↓        ↓          ↓
    Track   Reject if   Update
    Status  needed      Status
```

This is the architecture used by **real stock brokerages** worldwide.

## Comparison with Real Brokerages

| Feature | Zerodha/Robinhood | QuantNest Day 8 |
|---------|-------------------|-----------------|
| Order Entity | ✅ Yes | ✅ Yes |
| Order Engine | ✅ Yes | ✅ Yes |
| Order Status | ✅ PENDING/FILLED/REJECTED | ✅ Same |
| Order History | ✅ Yes | ✅ Yes |
| Market Orders | ✅ Yes | ✅ Yes |
| Limit Orders | ✅ Yes | ⚠️ Partial (infrastructure ready) |
| Stop-Loss | ✅ Yes | ⚠️ Partial (infrastructure ready) |
| Order Cancellation | ✅ Yes | ✅ Yes |
| Idempotency | ✅ Yes | ✅ Yes |

## Conclusion

Day 8 completes the **core brokerage architecture**. QuantNest now models the fundamental mechanics of a stock trading platform, including:

- ✅ Order management
- ✅ Trade execution
- ✅ Portfolio updates
- ✅ Wallet ledger
- ✅ Event sourcing
- ✅ Full audit trail

This milestone marks the transition from a **portfolio calculator** to a **true trading simulation engine** ready for production use.
