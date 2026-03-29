"""Order Execution Engine - Day 8 Order Management System."""

from decimal import Decimal
from typing import Optional, List
import uuid

from .order import Order, OrderStatus, OrderSide, OrderType
from .portfolio import Portfolio
from .wallet import Wallet
from .market import MarketProvider
from .trade import Trade
from quantnest.infra.storage import load_orders, save_order, append_order


class OrderExecutionError(Exception):
    """Base exception for order execution errors."""
    pass


class InsufficientFundsError(OrderExecutionError):
    """Raised when wallet has insufficient funds."""
    pass


class InsufficientPositionsError(OrderExecutionError):
    """Raised when portfolio has insufficient positions to sell."""
    pass


class InvalidSymbolError(OrderExecutionError):
    """Raised when symbol is not found in market."""
    pass


class OrderExecutionEngine:
    """
    Executes orders and manages the order lifecycle.
    
    Responsibilities:
    1. Receive new orders
    2. Validate orders against business rules
    3. Execute trades through portfolio
    4. Update order status
    5. Persist orders to storage
    
    This separates user intent (Order) from execution (Trade).
    """
    
    def __init__(self):
        self._market = MarketProvider()
    
    def place_order(
        self,
        wallet_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        order_type: str = "MARKET",
        limit_price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        transaction_id: Optional[str] = None
    ) -> Order:
        """
        Place a new order for execution.
        
        Args:
            wallet_id: The wallet placing the order
            symbol: Asset symbol (e.g., RELIANCE, TCS)
            side: BUY or SELL
            quantity: Number of shares
            order_type: MARKET, LIMIT, or STOP_LOSS
            limit_price: For LIMIT orders
            stop_price: For STOP_LOSS orders
            transaction_id: Unique ID for idempotency
        
        Returns:
            Order object with status (PENDING, FILLED, or REJECTED)
        """
        # Create order
        order = Order(
            wallet_id=wallet_id,
            symbol=symbol.upper(),
            side=side.upper(),
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            transaction_id=transaction_id
        )
        
        # Validate order
        try:
            self._validate_order(order)
        except OrderExecutionError as e:
            order.reject(str(e))
            save_order(wallet_id, order)
            return order
        
        # Execute order based on type
        try:
            if order_type == OrderType.MARKET:
                self._execute_market_order(order)
            elif order_type == OrderType.LIMIT:
                self._execute_limit_order(order)
            elif order_type == OrderType.STOP_LOSS:
                self._execute_stop_loss_order(order)
            else:
                order.reject(f"Unknown order type: {order_type}")
        except OrderExecutionError as e:
            order.reject(str(e))
        except Exception as e:
            order.reject(f"Execution error: {str(e)}")
        
        # Persist order
        save_order(wallet_id, order)
        
        return order
    
    def _validate_order(self, order: Order) -> None:
        """
        Validate order before execution.
        
        Raises:
            OrderExecutionError: If order is invalid
        """
        # Validate quantity
        if order.quantity <= 0:
            raise OrderExecutionError("Quantity must be positive")
        
        # Validate symbol
        try:
            self._market.get_price(order.symbol)
        except Exception:
            raise InvalidSymbolError(f"Unknown symbol: {order.symbol}")
        
        # Check funds/positions based on side
        if order.side == OrderSide.BUY:
            self._validate_buy_order(order)
        elif order.side == OrderSide.SELL:
            self._validate_sell_order(order)
        else:
            raise OrderExecutionError(f"Invalid order side: {order.side}")
        
        # Validate limit/stop prices for relevant order types
        if order.order_type == OrderType.LIMIT and order.limit_price is None:
            raise OrderExecutionError("LIMIT order requires limit_price")
        
        if order.order_type == OrderType.STOP_LOSS and order.stop_price is None:
            raise OrderExecutionError("STOP_LOSS order requires stop_price")
    
    def _validate_buy_order(self, order: Order) -> None:
        """Validate buy order has sufficient funds."""
        portfolio = Portfolio(order.wallet_id, self._market)
        price = self._market.get_price(order.symbol)
        total_cost = price * order.quantity
        
        if total_cost > portfolio.cash():
            raise InsufficientFundsError(
                f"Insufficient funds: need ₹{total_cost}, have ₹{portfolio.cash()}"
            )
    
    def _validate_sell_order(self, order: Order) -> None:
        """Validate sell order has sufficient positions."""
        portfolio = Portfolio(order.wallet_id, self._market)
        owned = portfolio.positions.get(order.symbol, Decimal("0"))
        
        if order.quantity > owned:
            raise InsufficientPositionsError(
                f"Insufficient positions: own {owned}, trying to sell {order.quantity}"
            )
    
    def _execute_market_order(self, order: Order) -> None:
        """Execute a market order immediately at current price."""
        portfolio = Portfolio(order.wallet_id, self._market)
        price = self._market.get_price(order.symbol)
        
        # Check price constraints for limit orders
        if order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY and price > order.limit_price:
                raise OrderExecutionError(
                    f"Market price ₹{price} exceeds limit ₹{order.limit_price}"
                )
            if order.side == OrderSide.SELL and price < order.limit_price:
                raise OrderExecutionError(
                    f"Market price ₹{price} below limit ₹{order.limit_price}"
                )
        
        # Execute the trade through portfolio
        if order.side == OrderSide.BUY:
            portfolio.buy(order.symbol, order.quantity, order.transaction_id)
        else:
            portfolio.sell(order.symbol, order.quantity, order.transaction_id)
        
        # Mark order as filled
        order.fill(order.quantity, price)
    
    def _execute_limit_order(self, order: Order) -> None:
        """Execute a limit order if market price meets conditions."""
        # Limit orders are executed immediately if price conditions are met
        self._execute_market_order(order)
    
    def _execute_stop_loss_order(self, order: Order) -> None:
        """Execute a stop-loss order if trigger price is reached."""
        # For simplicity, execute immediately if stop price is reached
        # In a real system, this would monitor prices over time
        current_price = self._market.get_price(order.symbol)
        
        if order.side == OrderSide.SELL and current_price <= order.stop_price:
            self._execute_market_order(order)
        elif order.side == OrderSide.BUY and current_price >= order.stop_price:
            self._execute_market_order(order)
        else:
            # Stop condition not met, keep as pending
            order.status = OrderStatus.PENDING
    
    def get_order(self, wallet_id: str, order_id: str) -> Optional[Order]:
        """Get a specific order by ID."""
        orders = load_orders(wallet_id)
        for order in orders:
            if order.order_id == order_id:
                return order
        return None
    
    def get_orders(
        self,
        wallet_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Order]:
        """
        Get orders for a wallet with optional filtering.
        
        Args:
            wallet_id: The wallet ID
            status: Filter by status (PENDING, FILLED, REJECTED)
            symbol: Filter by symbol
            limit: Maximum number of orders to return
            offset: Number of orders to skip
        
        Returns:
            List of orders matching criteria
        """
        orders = load_orders(wallet_id)
        
        # Filter by status
        if status:
            orders = [o for o in orders if o.status == status]
        
        # Filter by symbol
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        # Sort by timestamp (newest first)
        orders.sort(key=lambda o: o.timestamp, reverse=True)
        
        # Apply pagination
        return orders[offset:offset + limit]
    
    def cancel_order(self, wallet_id: str, order_id: str) -> Optional[Order]:
        """
        Cancel a pending order.
        
        Only PENDING or PARTIAL orders can be cancelled.
        
        Args:
            wallet_id: The wallet ID
            order_id: The order to cancel
        
        Returns:
            The cancelled order, or None if not found
        """
        order = self.get_order(wallet_id, order_id)
        
        if not order:
            return None
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
            raise OrderExecutionError(
                f"Cannot cancel order with status {order.status}"
            )
        
        order.status = OrderStatus.CANCELLED
        save_order(wallet_id, order)
        
        return order
