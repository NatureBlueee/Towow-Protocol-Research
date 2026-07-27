from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Event(BaseModel):
    id: str = Field(default_factory=lambda: f"evt_{uuid4().hex}")
    event_type: str
    aggregate_id: str
    actor_id: str
    payload: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    previous_hash: str = "GENESIS"
    event_hash: str = ""

    def canonical_bytes(self) -> bytes:
        body = self.model_dump(mode="json", exclude={"event_hash"})
        return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def seal(self) -> "Event":
        self.event_hash = hashlib.sha256(self.canonical_bytes()).hexdigest()
        return self


class EventStore:
    def __init__(self) -> None:
        self._events: list[Event] = []

    def append(self, event_type: str, aggregate_id: str, actor_id: str, payload: dict[str, Any]) -> Event:
        prev = self._events[-1].event_hash if self._events else "GENESIS"
        event = Event(
            event_type=event_type,
            aggregate_id=aggregate_id,
            actor_id=actor_id,
            payload=payload,
            previous_hash=prev,
        ).seal()
        self._events.append(event)
        return event

    def events(self, aggregate_id: str | None = None) -> list[Event]:
        if aggregate_id is None:
            return list(self._events)
        return [e for e in self._events if e.aggregate_id == aggregate_id]

    def verify_chain(self) -> bool:
        previous = "GENESIS"
        for event in self._events:
            if event.previous_hash != previous:
                return False
            expected = hashlib.sha256(event.canonical_bytes()).hexdigest()
            if expected != event.event_hash:
                return False
            previous = event.event_hash
        return True
