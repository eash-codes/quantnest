# Day 7: Command Model Implementation

## Overview
Day 7 introduces Command Query Responsibility Segregation (CQRS) pattern with explicit command models to enable safe mutations while preserving the read-only nature of our existing query endpoints. This establishes a clear separation between commands (intents to change state) and queries (reading state).

## Key Changes Made

### 1. Command DTOs (Data Transfer Objects)
Created explicit command models in `application/commands/`:
- `CreditWalletCommand`: Intent to add funds to a wallet
- `DebitWalletCommand`: Intent to remove funds from a wallet
- `BuyAssetCommand`: Intent to purchase an asset
- `SellAssetCommand`: Intent to sell an asset

These are not domain objects but intent objects that validate external input before domain processing.

### 2. Command Handlers
Implemented command handlers in `application/handlers/`:
- `CreditWalletHandler`: Processes credit commands
- `DebitWalletHandler`: Processes debit commands
- `BuyAssetHandler`: Processes buy commands
- `SellAssetHandler`: Processes sell commands

Handlers responsibilities:
- Load wallets/portfolios from infrastructure
- Execute domain logic
- Persist events
- Return safe response DTOs

### 3. New API Endpoints
Added POST endpoints to `api/portfolio.py`:
- `POST /portfolio/{wallet_id}/credit`: Credit funds to wallet
- `POST /portfolio/{wallet_id}/debit`: Debit funds from wallet
- `POST /portfolio/{wallet_id}/buy`: Buy assets
- `POST /portfolio/{wallet_id}/sell`: Sell assets

### 4. Idempotency Support
All mutation endpoints support:
- `X-Transaction-ID` header for idempotency
- Transaction ID in request body for idempotency
- Duplicate transaction IDs result in safe responses with no double processing

### 5. Error Handling
Standardized error responses:
- 400 → Validation errors
- 404 → Wallet not found (though not implemented yet)
- 409 → Business rule violations (insufficient funds, unknown symbols)
- 500 → Internal server errors

## Architecture Pattern Applied

### CQRS (Command Query Responsibility Segregation)
- **Commands**: Intent to change state (POST endpoints)
- **Queries**: Reading state (GET endpoints from Day 6)
- **Separation**: Clear distinction between read and write operations

### Flow for Command Processing
```
HTTP Request → Pydantic Validation → Command DTO → Handler → Domain → Event Storage → Response
```

## Code Structure

```
quantnest/
├── application/
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── wallet_commands.py      # CreditWalletCommand, DebitWalletCommand
│   │   └── portfolio_commands.py   # BuyAssetCommand, SellAssetCommand
│   ├── handlers/
│   │   ├── __init__.py
│   │   └── (all handlers in __init__.py for simplicity)
│   └── portfolio_service.py        # Existing read-only service
├── api/
│   └── portfolio.py                # Updated with POST endpoints
└── domain/                         # Unchanged - domain purity maintained
```

## Key Principles Maintained

1. **Domain Purity**: Domain layer remains unaware of HTTP/API concerns
2. **Event Sourcing**: Still relies on event replay for state computation
3. **Idempotency**: Transaction ID safety preserved from Day 5
4. **Financial Correctness**: All business rules remain in domain layer
5. **Audit Trail**: All operations create proper event records

## Testing Strategy

### Unit Tests for Commands
- Validate command DTOs with various inputs
- Test error conditions and edge cases

### Application Tests for Handlers
- Test handlers in isolation
- Verify proper domain interaction
- Confirm event persistence

### API Tests
- Test end-to-end command flow
- Verify idempotency with duplicate transaction IDs
- Confirm proper error responses

## Example Usage

### Credit Funds
```bash
curl -X POST "http://localhost:8000/portfolio/demo-user/credit" \
  -H "X-Transaction-ID: txn-123" \
  -d "amount=1000.0"
```

### Buy Assets
```bash
curl -X POST "http://localhost:8000/portfolio/demo-user/buy" \
  -H "X-Transaction-ID: txn-456" \
  -d "symbol=TCS&quantity=2.0"
```

## Benefits Achieved

1. **Controlled Mutations**: All state changes go through explicit command handlers
2. **Input Validation**: External input validated before domain processing
3. **Idempotency**: Safe retry mechanisms with transaction IDs
4. **Audit Trail**: Clear record of user intents and system responses
5. **Scalability**: Clear patterns for future command types
6. **Safety**: Domain business rules preserved while enabling mutations

## Next Steps (Day 8)

With command models in place, Day 8 can focus on:
- Cross-wallet transfers
- Advanced order types
- Settlement processing
- More sophisticated error handling

## Definition of Done

✅ POST credit endpoint works  
✅ POST buy endpoint works  
✅ Duplicate transaction ID is safe  
✅ Ledger still replays correctly  
✅ All Day 5 tests still pass  
✅ All Day 6 endpoints still work  
✅ No domain file imports FastAPI  

## Strategic Impact

After Day 7, QuantNest becomes:
- ✅ Event-sourced with mutation capability
- ✅ API-exposed with proper command handling
- ✅ Idempotent with transaction safety
- ✅ Ledger-safe with audit trails
- ✅ Ready for complex operations in Day 8+

This establishes the foundation for building a complete paper trading platform with proper financial controls and audit capabilities.