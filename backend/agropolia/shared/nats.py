from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agropolia.shared.models import InboxEvent


@dataclass(slots=True)
class EventEnvelope:
    event_id: UUID
    topic: str
    payload: dict[str, Any]
    trace_id: str | None = None

    def encode(self) -> bytes:
        return json.dumps({"event_id": str(self.event_id), "topic": self.topic, "payload": self.payload, "trace_id": self.trace_id}, separators=(",", ":")).encode()

    @classmethod
    def decode(cls, raw: bytes) -> "EventEnvelope":
        data = json.loads(raw)
        return cls(event_id=UUID(data["event_id"]), topic=data["topic"], payload=data["payload"], trace_id=data.get("trace_id"))


async def ensure_inbox_once(db: AsyncSession, consumer: str, envelope: EventEnvelope, handler: Callable[[AsyncSession, EventEnvelope], Awaitable[None]]) -> bool:
    existing = await db.get(InboxEvent, {"event_id": envelope.event_id, "consumer": consumer})
    if existing is not None:
        return False
    try:
        async with db.begin_nested():
            await handler(db, envelope)
            db.add(InboxEvent(event_id=envelope.event_id, consumer=consumer))
            await db.flush()
    except IntegrityError:
        return False
    return True
