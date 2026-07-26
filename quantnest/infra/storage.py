"""Legacy module-level storage API, now backed by the database.

This module exists only for backwards compatibility with older call sites and
scripts. Each function opens a short transaction and delegates to the SQL
repositories in :mod:`quantnest.infra.db.repositories`.

New code should depend on the repository *ports* and receive an implementation
by injection — see :mod:`quantnest.domain.ports` and :mod:`quantnest.api.deps`.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Dict, List, Optional

from quantnest.domain.events import DomainEvent
from quantnest.domain.order import Order
from quantnest.domain.trade import Trade

from .db.repositories import (
    SqlEventStore,
    SqlOrderRepository,
    SqlPositionRepository,
    SqlTradeRepository,
)
from .db.session import session_scope

logger = logging.getLogger(__name__)


# ── Wallet events ────────────────────────────────────────────────────────


def load_events(wallet_id: Optional[str] = None) -> List[DomainEvent]:
    if wallet_id is None:
        return []
    with session_scope() as session:
        return SqlEventStore(session).load_events(wallet_id)


def append_event(event: DomainEvent, wallet_id: Optional[str] = None) -> None:
    if wallet_id is None:
        return
    with session_scope() as session:
        SqlEventStore(session).append_event(wallet_id, event)


# ── Positions ────────────────────────────────────────────────────────────


def load_positions(wallet_id: str) -> Dict[str, float]:
    with session_scope() as session:
        positions = SqlPositionRepository(session).load_positions(wallet_id)
    return {symbol: float(quantity) for symbol, quantity in positions.items()}


def save_positions(wallet_id: str, positions: Dict[str, float]) -> None:
    converted = {symbol: Decimal(str(quantity)) for symbol, quantity in positions.items()}
    with session_scope() as session:
        SqlPositionRepository(session).save_positions(wallet_id, converted)


# ── Trades ───────────────────────────────────────────────────────────────


def load_trades(wallet_id: str) -> List[Trade]:
    with session_scope() as session:
        return SqlTradeRepository(session).load_trades(wallet_id)


def save_trade(wallet_id: str, trade: Trade) -> None:
    with session_scope() as session:
        SqlTradeRepository(session).save_trade(wallet_id, trade)


# ── Orders ───────────────────────────────────────────────────────────────


def load_orders(wallet_id: str) -> List[Order]:
    with session_scope() as session:
        return SqlOrderRepository(session).load_orders(wallet_id)


def save_order(wallet_id: str, order: Order) -> None:
    with session_scope() as session:
        SqlOrderRepository(session).save_order(wallet_id, order)


def append_order(wallet_id: str, order: Order) -> None:
    """Alias retained for compatibility with older call sites."""
    save_order(wallet_id, order)
