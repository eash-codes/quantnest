# QuantNest 🚀
Intelligent portfolio simulator and stock-backed payment platform

## Day 9 Progress
✅ Complete History & Observability Layer
✅ Trade history, order history, wallet events
✅ Unified timeline of all activities
✅ Activity summaries and statistics
✅ Pagination and date filtering
✅ Command Model Implementation (CQRS)
✅ POST endpoints for credit/debit/buy/sell
✅ Transaction ID idempotency
✅ Enhanced error handling

**Architecture**:
- `api/` = HTTP interfaces (FastAPI)
- `application/` = Use cases, commands, handlers, queries
- `domain/` = Business rules & event sourcing
- `infra/` = Storage & external services

**Command Endpoints**:
- POST /portfolio/{wallet_id}/credit - Credit funds
- POST /portfolio/{wallet_id}/debit - Debit funds  
- POST /portfolio/{wallet_id}/buy - Buy assets
- POST /portfolio/{wallet_id}/sell - Sell assets

**Query Endpoints**:
- GET /portfolio/{wallet_id}/summary - Portfolio analytics
- GET /history/portfolio/{wallet_id}/trades - Trade history
- GET /history/portfolio/{wallet_id}/orders - Order history
- GET /history/wallet/{wallet_id}/events - Wallet audit trail
- GET /history/portfolio/{wallet_id}/timeline - Unified timeline
- GET /history/portfolio/{wallet_id}/activity-summary - Activity stats

