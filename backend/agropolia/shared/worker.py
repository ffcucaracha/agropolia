from __future__ import annotations

import asyncio
import signal

from nats.aio.client import Client as NATS

from agropolia.config import get_settings
from agropolia.shared.outbox import OutboxPublisher
from agropolia.shared.nats import EventEnvelope
from agropolia.workspace.notify_consumer import consume_task_event


async def main() -> None:
    settings = get_settings()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    nc = NATS()
    await nc.connect(servers=[settings.nats_url], reconnect_time_wait=2, max_reconnect_attempts=-1)
    js = nc.jetstream()
    try:
        await js.add_stream(name="AGROPOLIA_EVENTS", subjects=["events.>", "jobs.>"])
    except Exception:
        pass
    async def on_task_event(message):
        try:
            envelope = EventEnvelope.decode(message.data)
            await consume_task_event(envelope)
            await message.ack()
        except Exception:
            await message.nak()

    subscription = await js.subscribe(
        "events.task.>", stream="AGROPOLIA_EVENTS",
        durable="i1-task-notifications", manual_ack=True, cb=on_task_event,
    )
    publisher = OutboxPublisher(js)
    try:
        await publisher.run(stop)
    finally:
        await subscription.unsubscribe()
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
