from __future__ import annotations

import asyncio
import signal

from nats.aio.client import Client as NATS

from agropolia.config import get_settings
from agropolia.shared.outbox import OutboxPublisher


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
    publisher = OutboxPublisher(js)
    try:
        await publisher.run(stop)
    finally:
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
