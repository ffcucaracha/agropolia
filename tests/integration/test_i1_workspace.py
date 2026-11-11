from __future__ import annotations

import asyncio
import io
import uuid

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from agropolia.db import SessionFactory
from agropolia.main import create_app
from agropolia.shared.models import OutboxEvent
from agropolia.shared.nats import EventEnvelope
from agropolia.workspace.notify_consumer import consume_task_event
from tests.integration.test_auth_flow import register


def headers(token: str, org_id: str | None = None):
    result = {"Authorization": f"Bearer {token}", "X-Client-Platform": "web"}
    if org_id:
        result["X-Org-Id"] = org_id
    return result


def field_payload(name="Первое поле"):
    return {"name": name, "crop_name": "Пшеница", "area_ha": 120.5, "sowing_date": "2026-05-01"}


def register_owner(client, email, digits):
    tokens, _ = register(client, email, digits)
    auth = headers(tokens["access_token"])
    org_id = client.get("/api/v1/me", headers=auth).json()["organization"]["id"]
    return auth, org_id


def test_i1_field_observation_task_journal_and_concurrency():
    with TestClient(create_app()) as client:
        auth, org = register_owner(client, "i1-owner-a@example.test", "300001001")
        second, second_org = register_owner(client, "i1-owner-b@example.test", "300001002")

        create = client.post("/api/v1/fields", headers=auth, json=field_payload())
        assert create.status_code == 201, create.text
        field = create.json()
        assert field["source"] == "manual" and field["area_ha"] == 120.5
        assert field["version"] == 1
        assert len(client.get("/api/v1/fields", headers=auth).json()) == 1

        hidden = client.get(f"/api/v1/fields/{field['id']}", headers=second)
        assert hidden.status_code == 404
        cross_edit = client.patch(
            f"/api/v1/fields/{field['id']}", headers={**second, "If-Match-Version": "1"},
            json=field_payload("Чужая попытка"),
        )
        assert cross_edit.status_code == 404

        edit = client.patch(
            f"/api/v1/fields/{field['id']}", headers={**auth, "If-Match-Version": "1"},
            json=field_payload("Поле после правки"),
        )
        assert edit.status_code == 200, edit.text
        assert edit.json()["version"] == 2
        stale = client.patch(
            f"/api/v1/fields/{field['id']}", headers={**auth, "If-Match-Version": "1"},
            json=field_payload("Устаревшая правка"),
        )
        assert stale.status_code == 409
        assert stale.json()["code"] == "CONFLICT"

        observation = client.post("/api/v1/observations", headers=auth, json={
            "field_id": field["id"], "kind": "crop_state", "text": "Есть изменения на листьях",
        })
        assert observation.status_code == 201, observation.text
        obs_id = observation.json()["id"]
        assert observation.json()["visibility"] == "private"
        assert len(client.get("/api/v1/observations?search=листьях", headers=auth).json()) == 1
        assert client.get(f"/api/v1/observations/{obs_id}", headers=second).status_code == 404

        task = client.post("/api/v1/tasks", headers=auth, json={
            "field_id": field["id"], "observation_id": obs_id, "title": "Проверить листья",
            "description": "Повторный осмотр", "priority": "high", "checklist": ["Осмотреть ряд"],
        })
        assert task.status_code == 201, task.text
        item = task.json()
        assert item["status"] == "new"
        task_id = item["id"]

        wrong_field = client.post("/api/v1/tasks", headers=second, json={
            "field_id": field["id"], "title": "Не моя задача",
        })
        assert wrong_field.status_code == 404

        for status, reason in (
            ("accepted", None),
            ("in_progress", None),
            ("blocked", "Нет техники"),
            ("accepted", None),
            ("in_progress", None),
            ("done", None),
            ("verified", None),
        ):
            transition = client.post(
                f"/api/v1/tasks/{task_id}/transition",
                headers={**auth, "If-Match-Version": str(item["version"])},
                json={"status": status, "blocked_reason": reason},
            )
            assert transition.status_code == 200, transition.text
            item = transition.json()
            assert item["status"] == status

        log = client.get("/api/v1/work-log", headers=auth).json()
        assert len(log) == 1 and log[0]["task_id"] == task_id
        assert client.get("/api/v1/work-log", headers=second).json() == []
        forbidden = client.post(
            f"/api/v1/tasks/{task_id}/transition",
            headers={**auth, "If-Match-Version": str(item["version"])},
            json={"status": "accepted"},
        )
        assert forbidden.status_code == 409
        assert forbidden.json()["code"] == "INVALID_TRANSITION"
        assert client.get("/api/v1/work-log", headers=auth).json() == log


def test_i1_sync_batch_idempotency_and_conflict():
    with TestClient(create_app()) as client:
        auth, _ = register_owner(client, "i1-sync@example.test", "300001003")
        field_id = str(uuid.uuid4())
        op_id = str(uuid.uuid4())
        cmd = {
            "client_op_id": op_id, "type": "field.create",
            "entity_id": field_id, "payload": field_payload("Offline поле"),
        }
        batch = {"ops": [cmd]}
        first = client.post("/api/v1/sync/ops", headers=auth, json=batch)
        second = client.post("/api/v1/sync/ops", headers=auth, json=batch)
        third = client.post("/api/v1/sync/ops", headers=auth, json=batch)
        assert first.status_code == second.status_code == third.status_code == 200
        assert first.json()["results"][0]["state"] == "applied"
        assert second.json()["results"][0]["state"] == "duplicate"
        assert third.json()["results"][0]["state"] == "duplicate"
        assert len(client.get("/api/v1/fields", headers=auth).json()) == 1
        assert first.json()["results"][0]["result"]["id"] == field_id

        changed_payload = {
            **cmd, "payload": field_payload("Другой payload"),
        }
        duplicate_mismatch = client.post("/api/v1/sync/ops", headers=auth, json={"ops": [changed_payload]})
        assert duplicate_mismatch.json()["results"][0]["code"] == "CONFLICT"

        obs_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        dependent = client.post("/api/v1/sync/ops", headers=auth, json={"ops": [
            {"client_op_id": str(uuid.uuid4()), "type": "observation.create", "entity_id": obs_id,
             "payload": {"field_id": field_id, "kind": "other", "text": "Автономное наблюдение"}},
            {"client_op_id": str(uuid.uuid4()), "type": "task.create", "entity_id": task_id,
             "payload": {"field_id": field_id, "observation_id": obs_id, "title": "Автономная задача"}},
        ]})
        assert [r["state"] for r in dependent.json()["results"]] == ["applied", "applied"]
        changes = client.get("/api/v1/sync/changes?since=0", headers=auth).json()
        assert len(changes["changes"]) >= 3
        assert changes["next_cursor"] > 0


def test_i1_blocked_requires_reason_and_task_event_notification():
    with TestClient(create_app()) as client:
        auth, _ = register_owner(client, "i1-notif@example.test", "300001004")
        field_id = client.post("/api/v1/fields", headers=auth, json=field_payload()).json()["id"]
        created = client.post("/api/v1/tasks", headers=auth, json={
            "field_id": field_id, "title": "Подготовить осмотр",
        })
        assert created.status_code == 201
        task = created.json()
        blocked = client.post(
            f"/api/v1/tasks/{task['id']}/transition",
            headers={**auth, "If-Match-Version": "1"},
            json={"status": "blocked"},
        )
        assert blocked.status_code == 422

        async def consume():
            async with SessionFactory() as db:
                record = await db.scalar(select(OutboxEvent).where(
                    OutboxEvent.topic == "events.task.created",
                    OutboxEvent.payload["task_id"].astext == task["id"],
                ))
            assert record is not None
            event = EventEnvelope(event_id=record.id, topic=record.topic, payload=record.payload)
            assert await consume_task_event(event) is True
            assert await consume_task_event(event) is False

        asyncio.run(consume())
        notices = client.get("/api/v1/notifications", headers=auth).json()
        assert len(notices) == 1
        read = client.post(f"/api/v1/notifications/{notices[0]['id']}/read", headers=auth)
        assert read.status_code == 200
        assert read.json()["read_at"] is not None
        settings = client.put("/api/v1/notification-settings", headers=auth, json={"task_events": False})
        assert settings.status_code == 200


def test_i1_photo_private_content_and_tenant_acl():
    with TestClient(create_app()) as client:
        auth, _ = register_owner(client, "i1-photo-a@example.test", "300001005")
        other, _ = register_owner(client, "i1-photo-b@example.test", "300001006")
        field_id = client.post("/api/v1/fields", headers=auth, json=field_payload()).json()["id"]
        observation_id = client.post("/api/v1/observations", headers=auth, json={
            "field_id": field_id, "kind": "other", "text": "Фото наблюдения",
        }).json()["id"]
        buffer = io.BytesIO()
        Image.new("RGB", (200, 200), (42, 100, 42)).save(buffer, format="JPEG")
        body = buffer.getvalue()
        upload_id = str(uuid.uuid4())
        def send():
            return client.post(
                f"/api/v1/media/observation/{observation_id}", headers=auth,
                files={"file": ("field.jpg", io.BytesIO(body), "image/jpeg")},
                data={"client_media_id": upload_id},
            )
        created = send()
        assert created.status_code == 201, created.text
        assert created.json()["size_bytes"] <= 1_500_000
        assert send().json()["id"] == created.json()["id"]
        content_id = created.json()["id"]
        fetched = client.get(f"/api/v1/media-file/{content_id}", headers=auth)
        assert fetched.status_code == 200 and fetched.content.startswith(b"\xff\xd8")
        assert fetched.headers["cache-control"] == "private, no-store"
        assert client.get(f"/api/v1/media/content/{content_id}", headers=other).status_code == 404
        assert client.get(f"/api/v1/media/observation/{observation_id}", headers=other).status_code == 404
