from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agropolia.db import SessionFactory
from agropolia.shared.nats import EventEnvelope, ensure_inbox_once

from .models import Notification, NotificationPreference


async def handle_task_event(db: AsyncSession, envelope: EventEnvelope) -> None:
    payload = envelope.payload
    org_id = UUID(payload["org_id"])
    user_id = UUID(payload["user_id"])
    preference = await db.scalar(select(NotificationPreference).where(
        NotificationPreference.org_id == org_id,
        NotificationPreference.user_id == user_id,
    ))
    if preference and not preference.task_events:
        return
    db.add(Notification(
        org_id=org_id, user_id=user_id, event_id=envelope.event_id,
        kind=payload["kind"], title=payload["title"],
        task_id=UUID(payload["task_id"]),
    ))


async def consume_task_event(envelope: EventEnvelope) -> bool:
    async with SessionFactory() as db:
        async with db.begin():
            return await ensure_inbox_once(db, "i1-task-notifications", envelope, handle_task_event)
