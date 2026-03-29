"""History service for querying trades, orders, wallet events, and timeline."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
import uuid

from quantnest.domain.wallet import Wallet
from quantnest.domain.portfolio import Portfolio
from quantnest.domain.market import MarketProvider
from quantnest.domain.order import OrderStatus
from quantnest.domain.order_engine import OrderExecutionEngine
from quantnest.infra.storage import load_events, load_orders
from quantnest.application.queries.history_dtos import (
    TradeHistoryItem,
    OrderHistoryItem,
    WalletEventItem,
    TimelineEvent,
    PaginatedResponse
)


class HistoryService:
    """Service for querying historical data across all sources."""
    
    def __init__(self):
        self._market = MarketProvider()
    
    def get_trades(self, wallet_id: str, symbol: Optional[str] = None,
                   limit: int = 50, offset: int = 0) -> PaginatedResponse:
        """Get trade history for a wallet."""
        portfolio = Portfolio(wallet_id, self._market)
        trades = portfolio.trades
        
        # Filter by symbol if provided
        if symbol:
            trades = [t for t in trades if t.symbol == symbol]
        
        # Sort by timestamp (newest first)
        trades.sort(key=lambda t: t.timestamp, reverse=True)
        
        total = len(trades)
        trades_page = trades[offset:offset + limit]
        
        items = [
            TradeHistoryItem(
                trade_id=f"trade-{wallet_id}-{idx}",
                wallet_id=wallet_id,
                symbol=t.symbol,
                side=t.side,
                quantity=float(t.quantity),
                price=float(t.price),
                total_value=float(t.total_value),
                timestamp=t.timestamp
            )
            for idx, t in enumerate(trades_page)
        ]
        
        return PaginatedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + limit < total
        )
    
    def get_orders(self, wallet_id: str, status: Optional[str] = None,
                   limit: int = 50, offset: int = 0) -> PaginatedResponse:
        """
        Get order history for a wallet from persistent order storage.
        
        Returns actual orders with their lifecycle (PENDING, FILLED, REJECTED, etc.)
        """
        orders = load_orders(wallet_id)
        
        # Filter by status if provided
        if status:
            orders = [o for o in orders if o.status == status]
        
        # Sort by timestamp (newest first)
        orders.sort(key=lambda o: o.timestamp, reverse=True)
        
        total = len(orders)
        orders_page = orders[offset:offset + limit]
        
        items = [
            OrderHistoryItem(
                order_id=o.order_id,
                wallet_id=o.wallet_id,
                symbol=o.symbol,
                side=o.side,
                quantity=float(o.quantity),
                order_type=o.order_type,
                status=o.status,
                price=float(o.average_fill_price) if o.average_fill_price else None,
                timestamp=o.timestamp
            )
            for o in orders_page
        ]
        
        return PaginatedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + limit < total
        )
    
    def get_wallet_events(self, wallet_id: str, event_type: Optional[str] = None,
                          limit: int = 100, offset: int = 0) -> PaginatedResponse:
        """Get wallet event history (ledger audit trail)."""
        events = load_events(wallet_id)
        
        # Filter by event type if provided
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda e: e.timestamp, reverse=True)
        
        total = len(events)
        events_page = events[offset:offset + limit]
        
        items = [
            WalletEventItem(
                event_id=str(e.event_id),
                wallet_id=wallet_id,
                event_type=e.event_type,
                amount=float(Decimal(e.payload["amount"])),
                transaction_id=e.transaction_id,
                timestamp=e.timestamp
            )
            for e in events_page
        ]
        
        return PaginatedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + limit < total
        )
    
    def get_timeline(self, wallet_id: str, start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None,
                     limit: int = 100, offset: int = 0) -> PaginatedResponse:
        """
        Get unified chronological timeline of all events.
        
        Combines:
        - Wallet events (credits/debits)
        - Orders (placed/filled/rejected)
        - Trades (buy/sell executions)
        
        All sorted by timestamp.
        """
        timeline_events: List[TimelineEvent] = []
        
        # Get wallet events
        wallet_events = load_events(wallet_id)
        for event in wallet_events:
            # Apply date filtering
            if start_date and event.timestamp < start_date:
                continue
            if end_date and event.timestamp > end_date:
                continue
            
            event_type = "wallet_credit" if event.event_type == "FundsCredited" else "wallet_debit"
            timeline_events.append(
                TimelineEvent(
                    event_type=event_type,
                    timestamp=event.timestamp,
                    wallet_id=wallet_id,
                    metadata={
                        "amount": float(Decimal(event.payload["amount"])),
                        "transaction_id": event.transaction_id,
                        "event_id": str(event.event_id)
                    }
                )
            )
        
        # Get orders
        orders = load_orders(wallet_id)
        for order in orders:
            # Apply date filtering
            if start_date and order.timestamp < start_date:
                continue
            if end_date and order.timestamp > end_date:
                continue
            
            # Add order placed event
            timeline_events.append(
                TimelineEvent(
                    event_type="order_placed",
                    timestamp=order.timestamp,
                    wallet_id=wallet_id,
                    metadata={
                        "order_id": order.order_id,
                        "symbol": order.symbol,
                        "side": order.side,
                        "quantity": float(order.quantity),
                        "order_type": order.order_type,
                        "status": order.status
                    }
                )
            )
            
            # Add order filled event if order was filled
            if order.is_filled or order.is_partial:
                timeline_events.append(
                    TimelineEvent(
                        event_type="order_filled",
                        timestamp=order.timestamp,
                        wallet_id=wallet_id,
                        metadata={
                            "order_id": order.order_id,
                            "symbol": order.symbol,
                            "side": order.side,
                            "filled_quantity": float(order.filled_quantity),
                            "average_price": float(order.average_fill_price) if order.average_fill_price else None,
                            "status": order.status
                        }
                    )
                )
            
            # Add order rejected event if order was rejected
            if order.is_rejected:
                timeline_events.append(
                    TimelineEvent(
                        event_type="order_rejected",
                        timestamp=order.timestamp,
                        wallet_id=wallet_id,
                        metadata={
                            "order_id": order.order_id,
                            "symbol": order.symbol,
                            "side": order.side,
                            "quantity": float(order.quantity),
                            "rejection_reason": order.rejection_reason
                        }
                    )
                )
        
        # Get trades
        portfolio = Portfolio(wallet_id, self._market)
        trades = portfolio.trades
        for trade in trades:
            # Apply date filtering
            if start_date and trade.timestamp < start_date:
                continue
            if end_date and trade.timestamp > end_date:
                continue
            
            timeline_events.append(
                TimelineEvent(
                    event_type="trade_executed",
                    timestamp=trade.timestamp,
                    wallet_id=wallet_id,
                    metadata={
                        "symbol": trade.symbol,
                        "side": trade.side,
                        "quantity": float(trade.quantity),
                        "price": float(trade.price),
                        "total_value": float(trade.total_value)
                    }
                )
            )
        
        # Sort all events by timestamp (newest first)
        timeline_events.sort(key=lambda e: e.timestamp, reverse=True)
        
        total = len(timeline_events)
        timeline_page = timeline_events[offset:offset + limit]
        
        return PaginatedResponse(
            items=timeline_page,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + limit < total
        )
    
    def get_activity_summary(self, wallet_id: str) -> Dict[str, Any]:
        """Get summary of portfolio activity."""
        # Get wallet events
        events = load_events(wallet_id)
        
        # Get trades
        portfolio = Portfolio(wallet_id, self._market)
        trades = portfolio.trades
        
        # Calculate statistics
        if not events and not trades:
            return {
                "wallet_id": wallet_id,
                "total_trades": 0,
                "total_wallet_events": 0,
                "first_activity": None,
                "last_activity": None,
                "most_traded_symbol": None
            }
        
        # Find first and last activity
        all_timestamps = [e.timestamp for e in events] + [t.timestamp for t in trades]
        all_timestamps.sort()
        
        # Count trades by symbol
        symbol_counts: Dict[str, int] = {}
        for trade in trades:
            symbol_counts[trade.symbol] = symbol_counts.get(trade.symbol, 0) + 1
        
        most_traded = max(symbol_counts.items(), key=lambda x: x[1])[0] if symbol_counts else None
        
        return {
            "wallet_id": wallet_id,
            "total_trades": len(trades),
            "total_wallet_events": len(events),
            "first_activity": all_timestamps[0].isoformat() if all_timestamps else None,
            "last_activity": all_timestamps[-1].isoformat() if all_timestamps else None,
            "most_traded_symbol": most_traded,
            "symbols_traded": list(symbol_counts.keys())
        }
