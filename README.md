# QuantNest 🚀
Intelligent portfolio simulator

## Day 7 Progress
✅ Command Model Implementation (CQRS)
✅ POST endpoints for credit/debit/buy/sell
✅ Transaction ID idempotency
✅ Command handlers and DTOs
✅ Enhanced error handling

**Architecture**:
- `api/` = HTTP interfaces (FastAPI)
- `application/` = Use cases & command handlers
- `domain/` = Business rules & event sourcing
- `infra/` = Storage & external services

**Endpoints**:
- GET /portfolio/{wallet_id}/summary - Portfolio analytics
- POST /portfolio/{wallet_id}/credit - Credit funds
- POST /portfolio/{wallet_id}/debit - Debit funds  
- POST /portfolio/{wallet_id}/buy - Buy assets
- POST /portfolio/{wallet_id}/sell - Sell assets

