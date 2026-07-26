"""SQLAlchemy implementations of the domain repository ports.

Each repository maps between ORM rows and domain objects. The domain never
sees a ``Session``, a ``Row`` or any SQLAlchemy type.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from quantnest.domain.events import DomainEvent, FundsCredited, FundsDebited
from quantnest.domain.order import Order
from quantnest.domain.trade import Trade

from .models import OrderRow, PositionRow, TradeRow, WalletEventRow

logger = logging.getLogger(__name__)


def _to_decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


class SqlEventStore:
    """:class:`~quantnest.domain.ports.EventStore` backed by ``wallet_events``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def load_events(self, wallet_id: str) -> List[DomainEvent]:
        rows = self._session.scalars(
            select(WalletEventRow)
            .where(WalletEventRow.wallet_id == wallet_id)
            .order_by(WalletEventRow.timestamp, WalletEventRow.id)
        ).all()
        return [self._to_domain(row) for row in rows]

    def append_event(self, wallet_id: str, event: DomainEvent) -> None:
        amount = _to_decimal(event.payload.get("amount", "0"))

        row = WalletEventRow(
            event_id=str(event.event_id),
            wallet_id=wallet_id,
            event_type=event.event_type,
            transaction_id=event.transaction_id,
            amount=amount,
            payload=dict(event.payload),
            timestamp=event.timestamp,
        )
        self._session.add(row)
        # Surface a duplicate transaction_id immediately rather than at commit.
        self._session.flush()

    @staticmethod
    def _to_domain(row: WalletEventRow) -> DomainEvent:
        amount = _to_decimal(row.amount)
        cls = FundsCredited if row.event_type == "FundsCredited" else FundsDebited

        event = cls(transaction_id=row.transaction_id, amount=amount)
        event.timestamp = row.timestamp
        try:
            event.event_id = uuid.UUID(row.event_id)
        except (ValueError, AttributeError, TypeError):
            pass
        return event


class SqlPositionRepository:
    """:class:`~quantnest.domain.ports.PositionRepository` backed by ``positions``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def load_positions(self, wallet_id: str) -> Dict[str, Decimal]:
        rows = self._session.scalars(
            select(PositionRow).where(PositionRow.wallet_id == wallet_id)
        ).all()
        return {
            row.symbol: _to_decimal(row.quantity)
            for row in rows
            if _to_decimal(row.quantity) > 0
        }

    def save_positions(self, wallet_id: str, positions: Dict[str, Decimal]) -> None:
        existing = {
            row.symbol: row
            for row in self._session.scalars(
                select(PositionRow).where(PositionRow.wallet_id == wallet_id)
            ).all()
        }

        # Upsert everything currently held.
        for symbol, quantity in positions.items():
            value = _to_decimal(quantity)
            if value <= 0:
                continue

            row = existing.pop(symbol, None)
            if row is None:
                self._session.add(
                    PositionRow(wallet_id=wallet_id, symbol=symbol, quantity=value)
                )
            else:
                row.quantity = value

        # Anything left over has been fully sold.
        for symbol in existing:
            self._session.execute(
                delete(PositionRow).where(
                    PositionRow.wallet_id == wallet_id, PositionRow.symbol == symbol
                )
            )

        self._session.flush()


class SqlTradeRepository:
    """:class:`~quantnest.domain.ports.TradeRepository` backed by ``trades``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def load_trades(self, wallet_id: str) -> List[Trade]:
        rows = self._session.scalars(
            select(TradeRow)
            .where(TradeRow.wallet_id == wallet_id)
            .order_by(TradeRow.timestamp, TradeRow.id)
        ).all()

        return [
            Trade(
                symbol=row.symbol,
                side=row.side,
                quantity=_to_decimal(row.quantity),
                price=_to_decimal(row.price),
                timestamp=row.timestamp,
                trade_id=row.trade_id,
            )
            for row in rows
        ]

    def save_trade(self, wallet_id: str, trade: Trade) -> None:
        # Idempotent on trade_id, matching the JSON store's behaviour.
        exists = self._session.scalar(
            select(TradeRow.id).where(TradeRow.trade_id == trade.trade_id)
        )
        if exists is not None:
            return

        self._session.add(
            TradeRow(
                trade_id=trade.trade_id,
                wallet_id=wallet_id,
                symbol=trade.symbol,
                side=trade.side,
                quantity=_to_decimal(trade.quantity),
                price=_to_decimal(trade.price),
                timestamp=trade.timestamp,
            )
        )
        self._session.flush()


class SqlOrderRepository:
    """:class:`~quantnest.domain.ports.OrderRepository` backed by ``orders``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def load_orders(self, wallet_id: str) -> List[Order]:
        rows = self._session.scalars(
            select(OrderRow)
            .where(OrderRow.wallet_id == wallet_id)
            .order_by(OrderRow.timestamp, OrderRow.id)
        ).all()
        return [self._to_domain(row) for row in rows]

    def get_order(self, wallet_id: str, order_id: str) -> Optional[Order]:
        row = self._session.scalar(
            select(OrderRow).where(
                OrderRow.wallet_id == wallet_id, OrderRow.order_id == order_id
            )
        )
        return self._to_domain(row) if row else None

    def save_order(self, wallet_id: str, order: Order) -> None:
        row = self._session.scalar(select(OrderRow).where(OrderRow.order_id == order.order_id))

        if row is None:
            row = OrderRow(order_id=order.order_id, wallet_id=wallet_id)
            self._session.add(row)

        row.symbol = order.symbol
        row.side = order.side
        row.quantity = _to_decimal(order.quantity)
        row.order_type = order.order_type
        row.status = order.status
        row.limit_price = _to_decimal(order.limit_price) if order.limit_price is not None else None
        row.stop_price = _to_decimal(order.stop_price) if order.stop_price is not None else None
        row.filled_quantity = _to_decimal(order.filled_quantity)
        row.average_fill_price = (
            _to_decimal(order.average_fill_price) if order.average_fill_price is not None else None
        )
        row.rejection_reason = order.rejection_reason
        row.transaction_id = order.transaction_id
        row.timestamp = order.timestamp

        self._session.flush()

    @staticmethod
    def _to_domain(row: OrderRow) -> Order:
        return Order(
            wallet_id=row.wallet_id,
            symbol=row.symbol,
            side=row.side,
            quantity=_to_decimal(row.quantity),
            order_type=row.order_type,
            status=row.status,
            order_id=row.order_id,
            timestamp=row.timestamp,
            limit_price=_to_decimal(row.limit_price) if row.limit_price is not None else None,
            stop_price=_to_decimal(row.stop_price) if row.stop_price is not None else None,
            filled_quantity=_to_decimal(row.filled_quantity),
            average_fill_price=(
                _to_decimal(row.average_fill_price) if row.average_fill_price is not None else None
            ),
            rejection_reason=row.rejection_reason,
            transaction_id=row.transaction_id,
        )
