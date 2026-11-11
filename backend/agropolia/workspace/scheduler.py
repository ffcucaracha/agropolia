from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from agropolia.config import get_settings
from agropolia.db import SessionFactory
from agropolia.shared.models import OutboxEvent

from .models import SyncOperation, Task


async def scan_due_tasks() -> int:
    """Persist deadline jobs and reminder state in the same transaction.

    Multiple schedulers use SKIP LOCKED; database state remains authoritative
    across worker restarts and NATS redeliveries.
    """
    count = 0
    async with SessionFactory() as db:
        async with db.begin():
            now = datetime.now(timezone.utc)
            rows = (await db.scalars(
                select(Task).where(
                    Task.due_at.is_not(None), Task.due_at <= now,
                    Task.reminded_at.is_(None),
                    Task.status.in_(("new", "accepted", "in_progress", "blocked")),
                ).order_by(Task.due_at).limit(100).with_for_update(skip_locked=True)
            )).all()
            for task in rows:
                task.reminded_at = now
                db.add(OutboxEvent(topic="events.task.deadline", payload={
                    "org_id": str(task.org_id),
                    "user_id": str(task.assignee_id),
                    "task_id": str(task.id),
                    "kind": "task_deadline",
                    "title": f"Срок задачи «{task.title}» наступил",
                }))
                count += 1
    return count


async def prune_sync_operations() -> int:
    days = get_settings().sync_idempotency_retention_days
    if days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with SessionFactory() as db:
        async with db.begin():
            result = await db.execute(delete(SyncOperation).where(SyncOperation.processed_at < cutoff))
    return result.rowcount or 0


async def scheduler_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await scan_due_tasks()
            await prune_sync_operations()
        except Exception as exc:
            # Never include SQL bind parameters or personal data in operational logs.
            import logging
            logging.getLogger("agropolia.scheduler").error(
                "scheduler_scan_failed", extra={"error_type": type(exc).__name__}
            )
        try:
            await asyncio.wait_for(stop.wait(), timeout=get_settings().task_reminder_scan_seconds)
        except TimeoutError:
            pass
