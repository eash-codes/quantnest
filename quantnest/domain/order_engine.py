"""Order Execution Engine — validates and executes orders.

Separates user *intent* (:class:`~quantnest.domain.order.Order`) from
execution *result* (:class:`~quantnest.domain.trade.Trade`).

All collaborators arrive by constructor injection, so the engine has no
knowledge of how orders are stored or where prices come from.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import List, Optional

from .exceptions import (
    InsufficientFundsError,
    InsufficientPositionsError,
    OrderExecutionError,
    OrderStateError,
    UnknownSymbolError,
    ValidationError,
)
from .order import Order, OrderSide, OrderStatus, OrderType
from .portfolio import Portfolio
from .ports import (
    EventStore,
    InMemoryOrderRepository,
    MarketDataProvider,
    OrderRepository,
    PositionRepository,
    TradeRepository,
)

logger = logging.getLogger(__name__)


class OrderExecutionEngine:
    """Receives orders, validates them, executes them and records the outcome."""

    def __init__(
        self,
        market: Optional[MarketDataProvider] = None,
        *,
        order_repository: Optional[OrderRepository] = None,
        event_store: Optional[EventStore] = None,
        position_repository: Optional[PositionRepository] = None,
        trade_repository: Optional[TradeRepository] = None,
    ) -> None:
        if market is None:
            from .market import MarketProvider

            market = MarketProvider()

        self._market = market
        self._orders: OrderRepository = order_repository or InMemoryOrderRepository()
        self._event_store = event_store
        self._position_repository = position_repository
        self._trade_repository = trade_repository

    # ── Public API ───────────────────────────────────────────────────────

    def place_order(
        self,
        wallet_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        order_type: str = OrderType.MARKET,
        limit_price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        transaction_id: Optional[str] = None,
    ) -> Order:
        """Place an order and return it with a terminal or pending status.

        Business rejections are recorded on the order rather than raised, so
        the caller always receives an auditable record.
        """
        order = Order(
            wallet_id=wallet_id,
            symbol=symbol.upper().strip(),
            side=side.upper().strip(),
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            transaction_id=transaction_id,
        )

        try:
            self._validate_order(order)
        except (
            ValidationError,
            InsufficientFundsError,
            InsufficientPositionsError,
            UnknownSymbolError,
            OrderExecutionError,
        ) as exc:
            order.reject(str(exc))
            logger.info(
                "Order rejected during validation",
                extra={
                    "wallet_id": wallet_id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "reason": str(exc),
                },
            )
            self._orders.save_order(wallet_id, order)
            return order

        try:
            self._execute(order)
        except (
            ValidationError,
            InsufficientFundsError,
            InsufficientPositionsError,
            UnknownSymbolError,
            OrderExecutionError,
        ) as exc:
            order.reject(str(exc))
            logger.info(
                "Order rejected during execution",
                extra={"wallet_id": wallet_id, "symbol": order.symbol, "reason": str(exc)},
            )
        except Exception:
            logger.exception(
                "Unexpected error while executing order",
                extra={"wallet_id": wallet_id, "symbol": order.symbol},
            )
            order.reject("Order execution failed due to an internal error")

        self._orders.save_order(wallet_id, order)
        return order

    def get_order(self, wallet_id: str, order_id: str) -> Optional[Order]:
        return self._orders.get_order(wallet_id, order_id)

    def get_orders(
        self,
        wallet_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Order]:
        orders = self._orders.load_orders(wallet_id)

        if status:
            orders = [o for o in orders if o.status == status]
        if symbol:
            orders = [o for o in orders if o.symbol == symbol.upper().strip()]

        orders.sort(key=lambda o: o.timestamp, reverse=True)
        return orders[offset : offset + limit]

    def cancel_order(self, wallet_id: str, order_id: str) -> Optional[Order]:
        """Cancel a PENDING or PARTIAL order."""
        order = self._orders.get_order(wallet_id, order_id)
        if order is None:
            return None

        if order.status not in (OrderStatus.PENDING, OrderStatus.PARTIAL):
            raise OrderStateError(f"Cannot cancel an order with status {order.status}")

        order.status = OrderStatus.CANCELLED
        self._orders.save_order(wallet_id, order)
        return order

    # ── Validation ───────────────────────────────────────────────────────

    def _validate_order(self, order: Order) -> None:
        if order.quantity <= 0:
            raise ValidationError("Quantity must be positive")

        if order.side not in (OrderSide.BUY, OrderSide.SELL):
            raise ValidationError(f"Invalid order side: {order.side}")

        if order.order_type == OrderType.LIMIT and order.limit_price is None:
            raise ValidationError("A LIMIT order requires a limit price")

        if order.order_type == OrderType.STOP_LOSS and order.stop_price is None:
            raise ValidationError("A STOP_LOSS order requires a stop price")

        # Confirms the symbol is priceable; raises UnknownSymbolError otherwise.
        price = self._market.get_price(order.symbol)

        portfolio = self._build_portfolio(order.wallet_id)

        if order.side == OrderSide.BUY:
            cost = price * order.quantity
            available = portfolio.cash()
            if cost > available:
                raise InsufficientFundsError(
                    f"Insufficient funds: this order costs {cost} but only {available} is available"
                )
        else:
            owned = portfolio.positions.get(order.symbol, Decimal("0"))
            if order.quantity > owned:
                raise InsufficientPositionsError(
                    f"Insufficient holdings: attempting to sell {order.quantity} "
                    f"but only {owned} held"
                )

    # ── Execution ────────────────────────────────────────────────────────

    def _execute(self, order: Order) -> None:
        if order.order_type == OrderType.MARKET:
            self._execute_market_order(order)
        elif order.order_type == OrderType.LIMIT:
            self._execute_limit_order(order)
        elif order.order_type == OrderType.STOP_LOSS:
            self._execute_stop_loss_order(order)
        else:
            raise ValidationError(f"Unknown order type: {order.order_type}")

    def _execute_market_order(self, order: Order) -> None:
        portfolio = self._build_portfolio(order.wallet_id)
        price = self._market.get_price(order.symbol)

        if order.side == OrderSide.BUY:
            portfolio.buy(order.symbol, order.quantity, order.transaction_id)
        else:
            portfolio.sell(order.symbol, order.quantity, order.transaction_id)

        order.fill(order.quantity, price)

        logger.info(
            "Order filled",
            extra={
                "wallet_id": order.wallet_id,
                "order_id": order.order_id,
                "symbol": order.symbol,
                "side": order.side,
                "quantity": str(order.quantity),
                "price": str(price),
            },
        )

    def _execute_limit_order(self, order: Order) -> None:
        price = self._market.get_price(order.symbol)

        if order.side == OrderSide.BUY and price > order.limit_price:
            raise OrderExecutionError(
                f"Market price {price} exceeds the limit price {order.limit_price}"
            )
        if order.side == OrderSide.SELL and price < order.limit_price:
            raise OrderExecutionError(
                f"Market price {price} is below the limit price {order.limit_price}"
            )

        self._execute_market_order(order)

    def _execute_stop_loss_order(self, order: Order) -> None:
        price = self._market.get_price(order.symbol)

        triggered = (order.side == OrderSide.SELL and price <= order.stop_price) or (
            order.side == OrderSide.BUY and price >= order.stop_price
        )

        if triggered:
            self._execute_market_order(order)
        else:
            # Stop not reached; the order rests until a later price check.
            order.status = OrderStatus.PENDING

    # ── Helpers ──────────────────────────────────────────────────────────

    def _build_portfolio(self, wallet_id: str) -> Portfolio:
        return Portfolio(
            wallet_id,
            self._market,
            event_store=self._event_store,
            position_repository=self._position_repository,
            trade_repository=self._trade_repository,
        )
