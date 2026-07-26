"""Enhanced storage with position and trade tracking for Day 7+."""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any
from decimal import Decimal
from quantnest.domain.events import DomainEvent
from quantnest.domain.trade import Trade
from quantnest.domain.order import Order
from datetime import datetime

def get_event_file(wallet_id: str) -> Path:
    return Path(f"data/wallet_events_{wallet_id}.json")

def get_position_file(wallet_id: str) -> Path:
    return Path(f"data/positions_{wallet_id}.json")

def get_trade_file(wallet_id: str) -> Path:
    return Path(f"data/trades_{wallet_id}.json")

def get_order_file(wallet_id: str) -> Path:
    return Path(f"data/orders_{wallet_id}.json")

def load_events(wallet_id: str = None) -> List[DomainEvent]:
    if wallet_id is None:
        return []  # Tests get fresh wallet

    event_file = get_event_file(wallet_id)
    event_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        text = event_file.read_text().strip()
        if not text:
            return []
        raw_events = json.loads(text)
        return [DomainEvent.from_dict(e) for e in raw_events]
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def append_event(event: DomainEvent, wallet_id: str = None) -> None:
    if wallet_id is None:
        return  # Tests don't persist

    events = load_events(wallet_id) + [event]
    event_file = get_event_file(wallet_id)
    event_file.parent.mkdir(parents=True, exist_ok=True)
    event_file.write_text(json.dumps([e.to_dict() for e in events], indent=2))

def load_positions(wallet_id: str) -> Dict[str, float]:
    """Load persisted positions for a wallet."""
    pos_file = get_position_file(wallet_id)
    try:
        if pos_file.exists():
            content = pos_file.read_text().strip()
            if content:
                return json.loads(content)
        return {}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_positions(wallet_id: str, positions: Dict[str, float]) -> None:
    """Save positions for a wallet."""
    pos_file = get_position_file(wallet_id)
    pos_file.parent.mkdir(parents=True, exist_ok=True)
    pos_file.write_text(json.dumps(positions, indent=2))

def load_trades(wallet_id: str) -> List[Trade]:
    """Load persisted trades for a wallet, preserving original timestamp and trade_id."""
    trade_file = get_trade_file(wallet_id)
    try:
        if trade_file.exists():
            content = trade_file.read_text().strip()
            if content:
                trades_data = json.loads(content)
                return [
                    Trade(
                        symbol=t["symbol"],
                        side=t["side"],
                        quantity=Decimal(str(t["quantity"])),
                        price=Decimal(str(t["price"])),
                        timestamp=datetime.fromisoformat(t["timestamp"]),
                        trade_id=t.get("trade_id", str(uuid.uuid4()))
                    )
                    for t in trades_data
                ]
        return []
    except (json.JSONDecodeError, FileNotFoundError, KeyError):
        return []

def save_trade(wallet_id: str, trade: Trade) -> None:
    """Append a trade to the wallet's trade file. Dedup by trade_id."""
    trades = load_trades(wallet_id)

    # Deduplicate strictly by trade_id
    if any(t.trade_id == trade.trade_id for t in trades):
        return

    trades.append(trade)

    trade_file = get_trade_file(wallet_id)
    trade_file.parent.mkdir(parents=True, exist_ok=True)

    trades_data = [
        {
            "trade_id": t.trade_id,
            "symbol": t.symbol,
            "side": t.side,
            "quantity": float(t.quantity),
            "price": float(t.price),
            "timestamp": t.timestamp.isoformat()
        }
        for t in trades
    ]
    trade_file.write_text(json.dumps(trades_data, indent=2))

def load_orders(wallet_id: str) -> List[Order]:
    """Load persisted orders for a wallet."""
    order_file = get_order_file(wallet_id)
    try:
        if order_file.exists():
            content = order_file.read_text().strip()
            if content:
                orders_data = json.loads(content)
                return [Order.from_dict(o) for o in orders_data]
        return []
    except (json.JSONDecodeError, FileNotFoundError, KeyError):
        return []

def save_order(wallet_id: str, order: Order) -> None:
    """Save or update an order in the wallet's order file."""
    orders = load_orders(wallet_id)
    
    # Check if order already exists and update it
    order_exists = False
    for i, existing_order in enumerate(orders):
        if existing_order.order_id == order.order_id:
            orders[i] = order
            order_exists = True
            break
    
    if not order_exists:
        orders.append(order)
    
    order_file = get_order_file(wallet_id)
    order_file.parent.mkdir(parents=True, exist_ok=True)
    
    orders_data = [o.to_dict() for o in orders]
    order_file.write_text(json.dumps(orders_data, indent=2))

def append_order(wallet_id: str, order: Order) -> None:
    """Append a new order (alias for save_order for new orders)."""
    save_order(wallet_id, order)