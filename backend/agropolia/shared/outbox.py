from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from agropolia.db import SessionFactory
from agropolia.shared.models import OutboxEvent
from agropolia.shared.nats import EventEnvelope


class OutboxPublisher:
    def __init__(self, jetstream, batch_size: int = 50) -> None:
        self.jetstream = jetstream
        self.batch_size = batch_size

    async def publish_batch(self) -> int:
        published = 0
        async with SessionFactory() as db:
            async with db.begin():
                rows = (await db.execute(select(OutboxEvent).where(OutboxEvent.published_at.is_(None), OutboxEvent.available_at <= datetime.now(timezone.utc)).order_by(OutboxEvent.created_at).limit(self.batch_size).with_for_update(skip_locked=True))).scalars().all()
                for row in rows:
                    envelope = EventEnvelope(event_id=row.id, topic=row.topic, payload=row.payload, trace_id=row.trace_id)
                    try:
                        await self.jetstream.publish(row.topic, envelope.encode())
                    except Exception as exc:
                        row.attempts += 1
                        row.last_error = type(exc).__name__
                        continue
                    row.published_at = datetime.now(timezone.utc)
                    row.attempts += 1
                    row.last_error = None
                    published += 1
        return published

    async def run(self, stop_event: asyncio.Event, interval_seconds: float = 1.0) -> None:
        while not stop_event.is_set():
            await self.publish_batch()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            except TimeoutError:
                pass
