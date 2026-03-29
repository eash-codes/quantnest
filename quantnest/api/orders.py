"""Order Management API endpoints - Day 8 OMS."""

from fastapi import APIRouter, HTTPException, Header, Query
from decimal import Decimal
from typing import Optional

from quantnest.domain.order import OrderStatus
from quantnest.domain.order_engine import OrderExecutionEngine
from quantnest.application.queries import HistoryService

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/")
async def place_order(
    wallet_id: str,
    symbol: str,
    side: str,
    quantity: float,
    order_type: str = Query(default="MARKET", description="MARKET, LIMIT, or STOP_LOSS"),
    limit_price: Optional[float] = Query(None, description="Limit price for LIMIT orders"),
    x_transaction_id: Optional[str] = Header(None, description="Idempotency key")
):
    """
    Place a new order (BUY or SELL).
    
    - **wallet_id**: The wallet placing the order
    - **symbol**: Asset symbol (e.g., RELIANCE, TCS)
    - **side**: BUY or SELL
    - **quantity**: Number of shares
    - **order_type**: MARKET, LIMIT, or STOP_LOSS
    - **limit_price**: Required for LIMIT orders
    - **x_transaction_id**: Optional idempotency key
    
    Returns order with status (PENDING, FILLED, or REJECTED).
    """
    try:
        engine = OrderExecutionEngine()
        order = engine.place_order(
            wallet_id=wallet_id,
            symbol=symbol.upper(),
            side=side.upper(),
            quantity=Decimal(str(quantity)),
            order_type=order_type,
            limit_price=Decimal(str(limit_price)) if limit_price else None,
            transaction_id=x_transaction_id
        )
        
        return {
            "order_id": order.order_id,
            "wallet_id": order.wallet_id,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": float(order.quantity),
            "order_type": order.order_type,
            "status": order.status,
            "filled_quantity": float(order.filled_quantity),
            "average_fill_price": float(order.average_fill_price) if order.average_fill_price else None,
            "rejection_reason": order.rejection_reason,
            "transaction_id": order.transaction_id,
            "timestamp": order.timestamp.isoformat()
        }
    except Exception as e:
        error_msg = str(e)
        if "InsufficientFundsError" in type(e).__name__:
            raise HTTPException(status_code=409, detail=error_msg)
        elif "InsufficientPositionsError" in type(e).__name__:
            raise HTTPException(status_code=409, detail=error_msg)
        elif "InvalidSymbolError" in type(e).__name__:
            raise HTTPException(status_code=400, detail=error_msg)
        elif "Quantity must be positive" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=error_msg)

@router.get("/{wallet_id}")
async def get_orders(
    wallet_id: str,
    status: Optional[str] = Query(None, description="Filter by status (PENDING, FILLED, REJECTED)"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(50, ge=1, le=500, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip")
):
    """Get order history for a wallet."""
    try:
        service = HistoryService()
        result = service.get_orders(wallet_id, status=status, limit=limit, offset=offset)
        return result.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{wallet_id}/{order_id}")
async def get_order(wallet_id: str, order_id: str):
    """Get a specific order by ID."""
    try:
        engine = OrderExecutionEngine()
        order = engine.get_order(wallet_id, order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return {
            "order_id": order.order_id,
            "wallet_id": order.wallet_id,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": float(order.quantity),
            "order_type": order.order_type,
            "status": order.status,
            "filled_quantity": float(order.filled_quantity),
            "average_fill_price": float(order.average_fill_price) if order.average_fill_price else None,
            "rejection_reason": order.rejection_reason,
            "timestamp": order.timestamp.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{wallet_id}/{order_id}/cancel")
async def cancel_order(wallet_id: str, order_id: str):
    """
    Cancel a pending or partially filled order.
    
    Only PENDING or PARTIAL orders can be cancelled.
    """
    try:
        engine = OrderExecutionEngine()
        order = engine.cancel_order(wallet_id, order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return {
            "order_id": order.order_id,
            "wallet_id": order.wallet_id,
            "symbol": order.symbol,
            "status": order.status,
            "message": "Order cancelled successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Cannot cancel" in error_msg:
            raise HTTPException(status_code=409, detail=error_msg)
        raise HTTPException(status_code=500, detail=str(e))
