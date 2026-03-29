# QuantNest 🚀
Intelligent portfolio simulator and stock-backed payment platform

## Day 9 Progress
✅ Complete History & Observability Layer
✅ Trade history, order history, wallet events
✅ Unified timeline of all activities
✅ Activity summaries and statistics
✅ Pagination and date filtering

## Day 8 Progress
✅ Order Management System (OMS)
✅ Order entity with lifecycle (PENDING/FILLED/REJECTED/CANCELLED)
✅ Order Execution Engine with validation
✅ Market, LIMIT, and STOP_LOSS order support
✅ Order persistence and history
✅ Order cancellation

## Day 7 Progress
✅ Command Model Implementation (CQRS)
✅ POST endpoints for credit/debit/buy/sell
✅ Transaction ID idempotency
✅ Command handlers and DTOs
✅ Enhanced error handling

**Architecture**:
- `api/` = HTTP interfaces (FastAPI)
- `application/` = Use cases, commands, handlers, queries
- `domain/` = Business rules & event sourcing
- `infra/` = Storage & external services

**Order Endpoints**:
- POST /orders - Place new order (BUY/SELL)
- GET /orders/{wallet_id} - Get order history
- GET /orders/{wallet_id}/{order_id} - Get specific order
- POST /orders/{wallet_id}/{order_id}/cancel - Cancel order

**Command Endpoints**:
- POST /portfolio/{wallet_id}/credit - Credit funds
- POST /portfolio/{wallet_id}/debit - Debit funds  
- POST /portfolio/{wallet_id}/buy - Buy assets (uses OMS)
- POST /portfolio/{wallet_id}/sell - Sell assets (uses OMS)

**Query Endpoints**:
- GET /portfolio/{wallet_id}/summary - Portfolio analytics
- GET /history/portfolio/{wallet_id}/trades - Trade history
- GET /history/portfolio/{wallet_id}/orders - Order history
- GET /history/wallet/{wallet_id}/events - Wallet audit trail
- GET /history/portfolio/{wallet_id}/timeline - Unified timeline
- GET /history/portfolio/{wallet_id}/activity-summary - Activity stats

