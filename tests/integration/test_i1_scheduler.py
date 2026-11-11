import asyncio
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from agropolia.db import SessionFactory
from agropolia.main import create_app
from agropolia.shared.models import OutboxEvent
from agropolia.workspace.scheduler import scan_due_tasks
from tests.integration.test_i1_workspace import field_payload, register_owner


def test_deadline_scheduling_is_durable_and_idempotent():
    with TestClient(create_app()) as client:
        auth, _ = register_owner(client, "i1-deadline@example.test", "300001007")
        field_id = client.post("/api/v1/fields", headers=auth, json=field_payload()).json()["id"]
        due = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        response = client.post("/api/v1/tasks", headers=auth, json={
            "field_id": field_id, "title": "Просроченная задача", "due_at": due,
        })
        assert response.status_code == 201, response.text
        task_id = response.json()["id"]

        async def check():
            assert await scan_due_tasks() >= 1
            assert await scan_due_tasks() == 0
            async with SessionFactory() as db:
                records = (await db.scalars(select(OutboxEvent).where(
                    OutboxEvent.topic == "events.task.deadline",
                    OutboxEvent.payload["task_id"].astext == task_id,
                ))).all()
            assert len(records) == 1

        asyncio.run(check())
