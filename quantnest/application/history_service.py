"""Query service for trades, orders, wallet events and the unified timeline.

Reads go straight through the repository ports; unlike the previous version
this no longer materialises a full Portfolio aggregate (and therefore no longer
triggers live price lookups) just to list historical rows.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from quantnest.application.queries.history_dtos import (
    OrderHistoryItem,
    PaginatedResponse,
    TimelineEvent,
    TradeHistoryItem,
    WalletEventItem,
)
from quantnest.domain.ports import EventStore, OrderRepository, TradeRepository

logger = logging.getLogger(__name__)


class HistoryService:
    """Paginated historical queries."""

    def __init__(
        self,
        *,
        event_store: Optional[EventStore] = None,
        trade_repository: Optional[TradeRepository] = None,
        order_repository: Optional[OrderRepository] = None,
    ) -> None:
        self._event_store = event_store
        self._trade_repository = trade_repository
        self._order_repository = order_repository

    # ── Trades ───────────────────────────────────────────────────────────

    def get_trades(
        self,
        wallet_id: str,
        symbol: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResponse:
        trades = list(self._trade_repository.load_trades(wallet_id)) if self._trade_repository else []

        if symbol:
            needle = symbol.upper().strip()
            trades = [t for t in trades if t.symbol == needle]

        trades.sort(key=lambda t: t.timestamp, reverse=True)
        page = trades[offset : offset + limit]

        items = [
            TradeHistoryItem(
                trade_id=trade.trade_id,
                wallet_id=wallet_id,
                symbol=trade.symbol,
                side=trade.side,
                quantity=float(trade.quantity),
                price=float(trade.price),
                total_value=float(trade.total_value),
                timestamp=trade.timestamp,
            )
            for trade in page
        ]

        return self._paginate(items, len(trades), limit, offset)

    # ── Orders ───────────────────────────────────────────────────────────

    def get_orders(
        self,
        wallet_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResponse:
        orders = list(self._order_repository.load_orders(wallet_id)) if self._order_repository else []

        if status:
            needle = status.upper().strip()
            orders = [o for o in orders if o.status == needle]

        orders.sort(key=lambda o: o.timestamp, reverse=True)
        page = orders[offset : offset + limit]

        items = [
            OrderHistoryItem(
                order_id=order.order_id,
                wallet_id=wallet_id,
                symbol=order.symbol,
                side=order.side,
                quantity=float(order.quantity),
                order_type=order.order_type,
                status=order.status,
                price=float(order.average_fill_price) if order.average_fill_price else None,
                timestamp=order.timestamp,
            )
            for order in page
        ]

        return self._paginate(items, len(orders), limit, offset)

    # ── Wallet events ────────────────────────────────────────────────────

    def get_wallet_events(
        self,
        wallet_id: str,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> PaginatedResponse:
        events = list(self._event_store.load_events(wallet_id)) if self._event_store else []

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        events.sort(key=lambda e: e.timestamp, reverse=True)
        page = events[offset : offset + limit]

        items = [
            WalletEventItem(
                event_id=str(event.event_id),
                wallet_id=wallet_id,
                event_type=event.event_type,
                amount=float(Decimal(event.payload["amount"])),
                transaction_id=event.transaction_id,
                timestamp=event.timestamp,
            )
            for event in page
        ]

        return self._paginate(items, len(events), limit, offset)

    # ── Timeline ─────────────────────────────────────────────────────────

    def get_timeline(
        self,
        wallet_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> PaginatedResponse:
        """Chronological merge of wallet events, orders and trades."""
        timeline: List[TimelineEvent] = []

        def in_range(moment: datetime) -> bool:
            if start_date and moment < start_date:
                return False
            if end_date and moment > end_date:
                return False
            return True

        if self._event_store:
            for event in self._event_store.load_events(wallet_id):
                if not in_range(event.timestamp):
                    continue
                timeline.append(
                    TimelineEvent(
                        event_type=(
                            "wallet_credit"
                            if event.event_type == "FundsCredited"
                            else "wallet_debit"
                        ),
                        timestamp=event.timestamp,
                        wallet_id=wallet_id,
                        metadata={
                            "amount": float(Decimal(event.payload["amount"])),
                            "transaction_id": event.transaction_id,
                            "event_id": str(event.event_id),
                        },
                    )
                )

        if self._order_repository:
            for order in self._order_repository.load_orders(wallet_id):
                if not in_range(order.timestamp):
                    continue

                timeline.append(
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
                            "status": order.status,
                        },
                    )
                )

                if order.is_filled or order.is_partial:
                    timeline.append(
                        TimelineEvent(
                            event_type="order_filled",
                            timestamp=order.timestamp,
                            wallet_id=wallet_id,
                            metadata={
                                "order_id": order.order_id,
                                "symbol": order.symbol,
                                "side": order.side,
                                "filled_quantity": float(order.filled_quantity),
                                "average_price": (
                                    float(order.average_fill_price)
                                    if order.average_fill_price
                                    else None
                                ),
                                "status": order.status,
                            },
                        )
                    )

                if order.is_rejected:
                    timeline.append(
                        TimelineEvent(
                            event_type="order_rejected",
                            timestamp=order.timestamp,
                            wallet_id=wallet_id,
                            metadata={
                                "order_id": order.order_id,
                                "symbol": order.symbol,
                                "side": order.side,
                                "quantity": float(order.quantity),
                                "rejection_reason": order.rejection_reason,
                            },
                        )
                    )

        if self._trade_repository:
            for trade in self._trade_repository.load_trades(wallet_id):
                if not in_range(trade.timestamp):
                    continue
                timeline.append(
                    TimelineEvent(
                        event_type="trade_executed",
                        timestamp=trade.timestamp,
                        wallet_id=wallet_id,
                        metadata={
                            "symbol": trade.symbol,
                            "side": trade.side,
                            "quantity": float(trade.quantity),
                            "price": float(trade.price),
                            "total_value": float(trade.total_value),
                        },
                    )
                )

        timeline.sort(key=lambda e: e.timestamp, reverse=True)
        return self._paginate(timeline[offset : offset + limit], len(timeline), limit, offset)

    # ── Activity summary ─────────────────────────────────────────────────

    def get_activity_summary(self, wallet_id: str) -> Dict[str, Any]:
        events = list(self._event_store.load_events(wallet_id)) if self._event_store else []
        trades = list(self._trade_repository.load_trades(wallet_id)) if self._trade_repository else []

        if not events and not trades:
            return {
                "wallet_id": wallet_id,
                "total_trades": 0,
                "total_wallet_events": 0,
                "first_activity": None,
                "last_activity": None,
                "most_traded_symbol": None,
                "symbols_traded": [],
            }

        timestamps = sorted([e.timestamp for e in events] + [t.timestamp for t in trades])

        symbol_counts: Dict[str, int] = {}
        for trade in trades:
            symbol_counts[trade.symbol] = symbol_counts.get(trade.symbol, 0) + 1

        most_traded = max(symbol_counts.items(), key=lambda pair: pair[1])[0] if symbol_counts else None

        return {
            "wallet_id": wallet_id,
            "total_trades": len(trades),
            "total_wallet_events": len(events),
            "first_activity": timestamps[0].isoformat() if timestamps else None,
            "last_activity": timestamps[-1].isoformat() if timestamps else None,
            "most_traded_symbol": most_traded,
            "symbols_traded": list(symbol_counts.keys()),
        }

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _paginate(items: List[Any], total: int, limit: int, offset: int) -> PaginatedResponse:
        return PaginatedResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + limit < total,
        )
