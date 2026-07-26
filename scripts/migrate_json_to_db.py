#!/usr/bin/env python3
"""Migrate the legacy ``data/*.json`` files into the SQL database.

Idempotent: re-running skips records that already exist, so it is safe to run
repeatedly. The original JSON files are read-only and left untouched as a backup.

Usage:
    python scripts/migrate_json_to_db.py [--data-dir data] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List

# Allow running directly from a source checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from quantnest.infra.db.models import (  # noqa: E402
    OrderRow,
    PositionRow,
    TradeRow,
    WalletEventRow,
)
from quantnest.infra.db.session import init_db, session_scope  # noqa: E402
from quantnest.infra.logging import configure_logging  # noqa: E402

logger = logging.getLogger("quantnest.migrate")


def _read_json(path: Path):
    try:
        text = path.read_text().strip()
        return json.loads(text) if text else None
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Skipping unreadable file", extra={"file": str(path), "error": str(exc)})
        return None


def _parse_timestamp(value) -> datetime:
    if not value:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return datetime.utcnow()


def _wallet_ids(data_dir: Path) -> List[str]:
    ids = set()
    for pattern, prefix in (
        ("wallet_events_*.json", "wallet_events_"),
        ("positions_*.json", "positions_"),
        ("trades_*.json", "trades_"),
        ("orders_*.json", "orders_"),
    ):
        for path in data_dir.glob(pattern):
            ids.add(path.stem[len(prefix) :])
    return sorted(ids)


def migrate_events(session, wallet_id: str, records: Iterable[dict]) -> int:
    inserted = 0
    for record in records or []:
        transaction_id = record.get("transaction_id") or str(uuid.uuid4())

        # The (wallet_id, transaction_id) pair is unique, so this is our key.
        exists = session.scalar(
            select(WalletEventRow.id).where(
                WalletEventRow.wallet_id == wallet_id,
                WalletEventRow.transaction_id == transaction_id,
            )
        )
        if exists is not None:
            continue

        payload = record.get("payload") or {}
        session.add(
            WalletEventRow(
                event_id=record.get("event_id") or str(uuid.uuid4()),
                wallet_id=wallet_id,
                event_type=record["event_type"],
                transaction_id=transaction_id,
                amount=Decimal(str(payload.get("amount", "0"))),
                payload=payload,
                timestamp=_parse_timestamp(record.get("timestamp")),
            )
        )
        inserted += 1
    return inserted


def migrate_positions(session, wallet_id: str, records: Dict[str, float]) -> int:
    written = 0
    for symbol, quantity in (records or {}).items():
        value = Decimal(str(quantity))
        if value <= 0:
            continue

        row = session.scalar(
            select(PositionRow).where(
                PositionRow.wallet_id == wallet_id, PositionRow.symbol == symbol
            )
        )
        if row is None:
            session.add(PositionRow(wallet_id=wallet_id, symbol=symbol, quantity=value))
            written += 1
        elif Decimal(str(row.quantity)) != value:
            row.quantity = value
            written += 1
    return written


def _stable_trade_id(wallet_id: str, record: dict, index: int) -> str:
    """Derive a deterministic ID for legacy trades that predate ``trade_id``.

    A random UUID would make the migration non-idempotent: every re-run would
    re-insert the same trade under a new ID. Hashing the trade's natural key
    keeps the result stable across runs.
    """
    natural_key = "|".join(
        [
            wallet_id,
            str(index),
            str(record.get("symbol", "")),
            str(record.get("side", "")),
            str(record.get("quantity", "")),
            str(record.get("price", "")),
            str(record.get("timestamp", "")),
        ]
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"quantnest:trade:{natural_key}"))


def migrate_trades(session, wallet_id: str, records: Iterable[dict]) -> int:
    inserted = 0
    for index, record in enumerate(records or []):
        trade_id = record.get("trade_id") or _stable_trade_id(wallet_id, record, index)

        if session.scalar(select(TradeRow.id).where(TradeRow.trade_id == trade_id)) is not None:
            continue

        session.add(
            TradeRow(
                trade_id=trade_id,
                wallet_id=wallet_id,
                symbol=record["symbol"],
                side=record["side"],
                quantity=Decimal(str(record["quantity"])),
                price=Decimal(str(record["price"])),
                timestamp=_parse_timestamp(record.get("timestamp")),
            )
        )
        inserted += 1
    return inserted


def migrate_orders(session, wallet_id: str, records: Iterable[dict]) -> int:
    inserted = 0
    for record in records or []:
        order_id = record.get("order_id") or str(uuid.uuid4())

        if session.scalar(select(OrderRow.id).where(OrderRow.order_id == order_id)) is not None:
            continue

        def decimal_or_none(key):
            raw = record.get(key)
            return Decimal(str(raw)) if raw not in (None, "") else None

        session.add(
            OrderRow(
                order_id=order_id,
                wallet_id=wallet_id,
                symbol=record["symbol"],
                side=record["side"],
                quantity=Decimal(str(record["quantity"])),
                order_type=record.get("order_type", "MARKET"),
                status=record.get("status", "PENDING"),
                limit_price=decimal_or_none("limit_price"),
                stop_price=decimal_or_none("stop_price"),
                filled_quantity=Decimal(str(record.get("filled_quantity", "0"))),
                average_fill_price=decimal_or_none("average_fill_price"),
                rejection_reason=record.get("rejection_reason"),
                transaction_id=record.get("transaction_id"),
                timestamp=_parse_timestamp(record.get("timestamp")),
            )
        )
        inserted += 1
    return inserted


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate QuantNest JSON data into SQL.")
    parser.add_argument("--data-dir", default="data", help="Directory holding the JSON files")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    args = parser.parse_args()

    configure_logging(level="INFO", fmt="console")

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error("Data directory not found", extra={"path": str(data_dir)})
        return 1

    init_db()

    wallet_ids = _wallet_ids(data_dir)
    if not wallet_ids:
        logger.info("No JSON data files found; nothing to migrate")
        return 0

    logger.info("Discovered wallets", extra={"count": len(wallet_ids)})

    totals = {"events": 0, "positions": 0, "trades": 0, "orders": 0}

    for wallet_id in wallet_ids:
        with session_scope() as session:
            events = migrate_events(
                session, wallet_id, _read_json(data_dir / f"wallet_events_{wallet_id}.json") or []
            )
            positions = migrate_positions(
                session, wallet_id, _read_json(data_dir / f"positions_{wallet_id}.json") or {}
            )
            trades = migrate_trades(
                session, wallet_id, _read_json(data_dir / f"trades_{wallet_id}.json") or []
            )
            orders = migrate_orders(
                session, wallet_id, _read_json(data_dir / f"orders_{wallet_id}.json") or []
            )

            if args.dry_run:
                session.rollback()

            totals["events"] += events
            totals["positions"] += positions
            totals["trades"] += trades
            totals["orders"] += orders

            logger.info(
                "Migrated wallet",
                extra={
                    "wallet_id": wallet_id,
                    "events": events,
                    "positions": positions,
                    "trades": trades,
                    "orders": orders,
                },
            )

    logger.info(
        "Migration complete" + (" (dry run — nothing written)" if args.dry_run else ""),
        extra=totals,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
