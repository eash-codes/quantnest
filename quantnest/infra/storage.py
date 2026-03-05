"""Enhanced storage with position tracking for Day 7."""

import json
from pathlib import Path
from typing import List, Dict, Any
from decimal import Decimal
from quantnest.domain.events import DomainEvent

def get_event_file(wallet_id: str) -> Path:
    return Path(f"data/wallet_events_{wallet_id}.json")

def get_position_file(wallet_id: str) -> Path:
    return Path(f"data/positions_{wallet_id}.json")

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