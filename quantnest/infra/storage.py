import json
from pathlib import Path
from typing import List
from quantnest.domain.events import DomainEvent

def get_event_file(wallet_id: str) -> Path:
    return Path(f"data/wallet_events_{wallet_id}.json")

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
