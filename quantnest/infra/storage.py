import json
from pathlib import Path
from typing import List
from quantnest.domain.events import DomainEvent

EVENT_FILE = Path("data/wallet_events.json")

def load_events() -> List[DomainEvent]:
    if not EVENT_FILE.exists():
        return []

    try:
        text = EVENT_FILE.read_text().strip()
        if not text:
            return []
        raw_events = json.loads(text)
        return [DomainEvent.from_dict(e) for e in raw_events]
    except json.JSONDecodeError:
        return []
def append_event(event: DomainEvent) -> None:
    events = load_events()
    events.append(event)
    EVENT_FILE.write_text(json.dumps([e.to_dict() for e in events], indent=2))
