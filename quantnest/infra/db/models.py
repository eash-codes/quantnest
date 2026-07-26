"""SQLAlchemy ORM models.

Money and quantities use ``Numeric`` rather than ``Float`` so values are exact
— a float column would silently corrupt a ledger.

The schema is intentionally portable: swapping SQLite for PostgreSQL is a
``DATABASE_URL`` change, with no model edits required.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

#: Precision for cash amounts and prices.
MONEY = Numeric(20, 4)
#: Precision for share quantities (fractional shares supported).
QUANTITY = Numeric(20, 8)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for every QuantNest table."""


class WalletEventRow(Base):
    """Append-only wallet ledger. Rows are never updated or deleted."""

    __tablename__ = "wallet_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    wallet_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[float] = mapped_column(MONEY, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        # Enforces wallet-scoped idempotency at the database level, so a
        # retried request cannot double-apply even under concurrency.
        UniqueConstraint("wallet_id", "transaction_id", name="uq_wallet_transaction"),
        Index("ix_wallet_events_wallet_ts", "wallet_id", "timestamp"),
    )


class PositionRow(Base):
    """Current holdings. One row per wallet and symbol."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[float] = mapped_column(QUANTITY, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    __table_args__ = (UniqueConstraint("wallet_id", "symbol", name="uq_wallet_symbol"),)


class TradeRow(Base):
    """Immutable record of an executed trade."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    wallet_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[float] = mapped_column(QUANTITY, nullable=False)
    price: Mapped[float] = mapped_column(MONEY, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (Index("ix_trades_wallet_ts", "wallet_id", "timestamp"),)


class OrderRow(Base):
    """Order lifecycle record: PENDING, FILLED, PARTIAL, REJECTED, CANCELLED."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    wallet_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[float] = mapped_column(QUANTITY, nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    limit_price: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    stop_price: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    filled_quantity: Mapped[float] = mapped_column(QUANTITY, nullable=False, default=0)
    average_fill_price: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (Index("ix_orders_wallet_ts", "wallet_id", "timestamp"),)
