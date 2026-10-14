import asyncio

import pytest
from nats.aio.client import Client as NATS

from agropolia.config import get_settings
from agropolia.db import SessionFactory
from agropolia.ids import uuid7
from agropolia.shared.models import OutboxEvent
from agropolia.shared.nats import EventEnvelope, ensure_inbox_once
from agropolia.shared.outbox import OutboxPublisher


@pytest.mark.asyncio
async def test_outbox_publish_and_inbox_deduplicate():
    settings = get_settings(); nc = NATS(); await nc.connect(servers=[settings.nats_url]); js = nc.jetstream()
    try: await js.add_stream(name="AGROPOLIA_EVENTS_TEST", subjects=["events.test.>"])
    except Exception: pass
    received = asyncio.Future(); event_id = uuid7()
    async def callback(msg):
        if not received.done(): received.set_result(EventEnvelope.decode(msg.data))
        await msg.ack()
    sub = await js.subscribe("events.test.probe", durable=f"i0-test-{event_id}", cb=callback, manual_ack=True)
    async with SessionFactory() as db:
        async with db.begin(): db.add(OutboxEvent(id=event_id, topic="events.test.probe", payload={"kind": "probe"}))
    assert await OutboxPublisher(js).publish_batch() == 1
    envelope = await asyncio.wait_for(received, 5); assert envelope.event_id == event_id
    calls = 0
    async def handler(db, event):
        nonlocal calls; calls += 1
    async with SessionFactory() as db:
        async with db.begin(): assert await ensure_inbox_once(db, "i0-test", envelope, handler) is True
        async with db.begin(): assert await ensure_inbox_once(db, "i0-test", envelope, handler) is False
    assert calls == 1; await sub.unsubscribe(); await nc.drain()
