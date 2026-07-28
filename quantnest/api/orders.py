"""Order Management API."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query, status

from quantnest.api.deps import (
    AuthServiceDep,
    CurrentUserDep,
    HistoryServiceDep,
    OrderEngineDep,
    TransactionIdDep,
    WalletIdDep,
)
from quantnest.api.schemas import OrderResponse, PlaceOrderRequest
from quantnest.domain.exceptions import OrderNotFoundError
from quantnest.domain.order import Order

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])


def _to_response(order: Order) -> OrderResponse:
    return OrderResponse(
        order_id=order.order_id,
        wallet_id=order.wallet_id,
        symbol=order.symbol,
        side=order.side,
        quantity=float(order.quantity),
        order_type=order.order_type,
        status=order.status,
        filled_quantity=float(order.filled_quantity),
        average_fill_price=(
            float(order.average_fill_price) if order.average_fill_price is not None else None
        ),
        rejection_reason=order.rejection_reason,
        transaction_id=order.transaction_id,
        timestamp=order.timestamp,
    )


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place an order",
)
async def place_order(
    request: PlaceOrderRequest,
    transaction_id: TransactionIdDep,
    engine: OrderEngineDep,
    current_user: CurrentUserDep,
    auth: AuthServiceDep,
) -> OrderResponse:
    """Place a MARKET, LIMIT or STOP_LOSS order.

    Rejections are returned as an order carrying ``status=REJECTED`` and a
    ``rejection_reason``, rather than as an HTTP error, so every attempt is
    auditable.

    The wallet id arrives in the body rather than the path, so it cannot use
    the path-based ``WalletIdDep``. Ownership is therefore checked explicitly
    here — without it this endpoint would bypass the entire ownership model.
    """
    wallet_id = auth.authorize_wallet(current_user, request.wallet_id)

    order = engine.place_order(
        wallet_id=wallet_id,
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        order_type=request.order_type,
        limit_price=request.limit_price,
        stop_price=request.stop_price,
        transaction_id=transaction_id,
    )
    return _to_response(order)


@router.get("/{wallet_id}", summary="List orders for a wallet")
async def list_orders(
    wallet_id: WalletIdDep,
    service: HistoryServiceDep,
    status_filter: Optional[str] = Query(
        None, alias="status", max_length=16, description="Filter by order status"
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    result = service.get_orders(wallet_id, status=status_filter, limit=limit, offset=offset)
    return result.model_dump()


@router.get("/{wallet_id}/{order_id}", response_model=OrderResponse, summary="Fetch one order")
async def get_order(
    wallet_id: WalletIdDep,
    order_id: str,
    engine: OrderEngineDep,
) -> OrderResponse:
    order = engine.get_order(wallet_id, order_id)
    if order is None:
        raise OrderNotFoundError(f"No order {order_id} exists for wallet {wallet_id}")
    return _to_response(order)


@router.post(
    "/{wallet_id}/{order_id}/cancel",
    response_model=OrderResponse,
    summary="Cancel a pending order",
)
async def cancel_order(
    wallet_id: WalletIdDep,
    order_id: str,
    engine: OrderEngineDep,
) -> OrderResponse:
    """Cancel an order. Only PENDING or PARTIAL orders may be cancelled."""
    order = engine.cancel_order(wallet_id, order_id)
    if order is None:
        raise OrderNotFoundError(f"No order {order_id} exists for wallet {wallet_id}")
    return _to_response(order)
