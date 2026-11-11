from __future__ import annotations

import hashlib
import json
from datetime import datetime, time, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from agropolia.auth.dependencies import TenantContext
from agropolia.errors import DomainError
from agropolia.ids import uuid7
from agropolia.shared.models import OutboxEvent

from .models import (
    ChangeLog, Field, Notification, NotificationPreference,
    Observation, SyncOperation, Task, WorkLogEntry, utcnow,
)
from .schemas import (
    FieldCreate, FieldEdit, NotificationSettings, ObservationCreate,
    SyncCommand, TaskCreate, TaskTransition,
)


def field_view(item: Field) -> dict:
    return dict(id=str(item.id), name=item.name, crop_name=item.crop_name,
                area_ha=float(item.area_ha), sowing_date=item.sowing_date.date().isoformat()
                if item.sowing_date else None, source=item.source,
                meteo_field_id=item.meteo_field_id, version=item.version,
                created_at=item.created_at.isoformat())


def observation_view(item: Observation) -> dict:
    return dict(id=str(item.id), field_id=str(item.field_id), kind=item.kind,
                text=item.text, taken_at=item.taken_at.isoformat(),
                author_id=str(item.author_id), visibility=item.visibility,
                version=item.version, created_at=item.created_at.isoformat())


def task_view(item: Task) -> dict:
    return dict(id=str(item.id), field_id=str(item.field_id),
                observation_id=str(item.observation_id) if item.observation_id else None,
                title=item.title, description=item.description, priority=item.priority,
                due_at=item.due_at.isoformat() if item.due_at else None,
                checklist=item.checklist, status=item.status,
                blocked_reason=item.blocked_reason,
                author_id=str(item.author_id), assignee_id=str(item.assignee_id),
                completed_at=item.completed_at.isoformat() if item.completed_at else None,
                verified_at=item.verified_at.isoformat() if item.verified_at else None,
                version=item.version, created_at=item.created_at.isoformat())


def notification_view(item: Notification) -> dict:
    return dict(id=str(item.id), kind=item.kind, title=item.title,
                task_id=str(item.task_id) if item.task_id else None,
                read_at=item.read_at.isoformat() if item.read_at else None,
                created_at=item.created_at.isoformat())


async def owned_field(db: AsyncSession, org_id: UUID, field_id: UUID) -> Field:
    item = await db.scalar(select(Field).where(Field.id == field_id, Field.org_id == org_id, Field.archived_at.is_(None)))
    if item is None:
        raise DomainError("NOT_FOUND", "Поле не найдено", 404)
    return item


async def owned_observation(db: AsyncSession, org_id: UUID, observation_id: UUID) -> Observation:
    item = await db.scalar(select(Observation).where(Observation.id == observation_id, Observation.org_id == org_id))
    if item is None:
        raise DomainError("NOT_FOUND", "Наблюдение не найдено", 404)
    return item


async def owned_task(db: AsyncSession, org_id: UUID, task_id: UUID, lock: bool = False) -> Task:
    q = select(Task).where(Task.id == task_id, Task.org_id == org_id)
    if lock:
        q = q.with_for_update()
    item = await db.scalar(q)
    if item is None:
        raise DomainError("NOT_FOUND", "Задача не найдена", 404)
    return item


def assert_owner(context: TenantContext) -> None:
    # I-1 is explicitly owner-only until FR-ORG-02/03 introduces staff roles.
    if context.membership.role != "owner":
        raise DomainError("PERMISSION_DENIED", "Недостаточно прав", 403)


def require_version(current: int, base: int | None) -> None:
    if base is None or current != base:
        raise DomainError("CONFLICT", "Данные изменились. Обновите страницу и повторите действие.", 409)


async def operation(
    db: AsyncSession, context: TenantContext, command: SyncCommand,
) -> dict:
    """Exactly-once mutation recording with an advisory lock on client_op_id.

    The caller owns a PostgreSQL transaction; no external network calls inside it.
    """
    assert_owner(context)
    signature = hashlib.sha256(
        json.dumps(command.model_dump(mode="json", exclude={"client_op_id"}),
                   sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    lock_id = int.from_bytes(command.client_op_id.bytes[:8], "big", signed=True)
    await db.execute(text("SELECT pg_advisory_xact_lock(:value)"), {"value": lock_id})
    previous = await db.get(SyncOperation, command.client_op_id)
    if previous is not None:
        if previous.user_id != context.user.id or previous.org_id != context.organization.id or previous.payload_hash != signature:
            raise DomainError("CONFLICT", "Идентификатор операции использован с другими данными", 409)
        return {"state": "duplicate", "result": previous.result}

    org = context.organization.id
    user = context.user.id
    kind = command.type
    payload = command.payload
    entity = None
    event: OutboxEvent | None = None
    try:
        if kind == "field.create":
            data = FieldCreate.model_validate(payload)
            entity = Field(org_id=org, name=data.name.strip(), crop_name=data.crop_name.strip(),
                           area_ha=data.area_ha,
                           sowing_date=datetime.combine(data.sowing_date, time.min, tzinfo=timezone.utc)
                           if data.sowing_date else None, source="manual")
            db.add(entity)
            await db.flush()
            result = field_view(entity)
            domain = "field"

        elif kind == "field.update":
            if command.entity_id is None:
                raise DomainError("VALIDATION_ERROR", "Нужен ID поля", 422)
            entity = await db.scalar(select(Field).where(
                Field.id == command.entity_id, Field.org_id == org, Field.archived_at.is_(None)
            ).with_for_update())
            if entity is None:
                raise DomainError("NOT_FOUND", "Поле не найдено", 404)
            if entity.source != "manual":
                raise DomainError("PERMISSION_DENIED", "Поля Meteo нельзя редактировать здесь", 403)
            require_version(entity.version, command.base_version)
            data = FieldEdit.model_validate(payload)
            entity.name = data.name.strip()
            entity.crop_name = data.crop_name.strip()
            entity.area_ha = data.area_ha
            entity.sowing_date = datetime.combine(data.sowing_date, time.min, tzinfo=timezone.utc) if data.sowing_date else None
            entity.version += 1
            entity.updated_at = utcnow()
            await db.flush()
            result = field_view(entity)
            domain = "field"

        elif kind == "observation.create":
            data = ObservationCreate.model_validate(payload)
            await owned_field(db, org, data.field_id)
            entity = Observation(org_id=org, field_id=data.field_id, author_id=user,
                                 kind=data.kind, text=data.text, taken_at=data.taken_at or utcnow(),
                                 visibility="private")
            db.add(entity)
            await db.flush()
            result = observation_view(entity)
            domain = "observation"

        elif kind == "task.create":
            data = TaskCreate.model_validate(payload)
            await owned_field(db, org, data.field_id)
            if data.observation_id:
                observation = await owned_observation(db, org, data.observation_id)
                if observation.field_id != data.field_id:
                    raise DomainError("VALIDATION_ERROR", "Наблюдение относится к другому полю", 422)
            entity = Task(org_id=org, field_id=data.field_id, observation_id=data.observation_id,
                          author_id=user, assignee_id=user, title=data.title.strip(),
                          description=data.description, priority=data.priority,
                          due_at=data.due_at, checklist=data.checklist, status="new")
            db.add(entity)
            await db.flush()
            result = task_view(entity)
            domain = "task"
            event = OutboxEvent(topic="events.task.created", payload={
                "org_id": str(org), "user_id": str(user), "task_id": str(entity.id),
                "kind": "task_created", "title": f"Создана задача: {entity.title}",
            })

        elif kind == "task.transition":
            if command.entity_id is None:
                raise DomainError("VALIDATION_ERROR", "Нужен ID задачи", 422)
            entity = await owned_task(db, org, command.entity_id, lock=True)
            require_version(entity.version, command.base_version)
            data = TaskTransition.model_validate(payload)
            transitions = {
                "new": {"accepted", "blocked"},
                "accepted": {"in_progress", "blocked"},
                "in_progress": {"done", "blocked"},
                "blocked": {"accepted"},
                "done": {"verified"},
                "verified": set(),
            }
            if data.status not in transitions[entity.status]:
                raise DomainError("INVALID_TRANSITION", "Недопустимый переход статуса", 409)
            if data.status == "blocked" and not (data.blocked_reason or "").strip():
                raise DomainError("VALIDATION_ERROR", "Укажите причину блокировки", 422)
            entity.status = data.status
            entity.blocked_reason = data.blocked_reason.strip() if data.status == "blocked" and data.blocked_reason else None
            entity.updated_at = utcnow()
            entity.version += 1
            if data.status == "done":
                entity.completed_at = utcnow()
                db.add(WorkLogEntry(org_id=org, field_id=entity.field_id,
                                    task_id=entity.id, performed_by=user, performed_at=entity.completed_at))
            if data.status == "verified":
                entity.verified_at = utcnow()
            await db.flush()
            result = task_view(entity)
            domain = "task"
            event = OutboxEvent(topic="events.task.changed", payload={
                "org_id": str(org), "user_id": str(user), "task_id": str(entity.id),
                "kind": f"task_{data.status}", "title": f"Задача «{entity.title}»: {data.status}",
            })

        elif kind == "notification.read":
            if command.entity_id is None:
                raise DomainError("VALIDATION_ERROR", "Нужен ID уведомления", 422)
            entity = await db.scalar(select(Notification).where(
                Notification.id == command.entity_id, Notification.org_id == org,
                Notification.user_id == user
            ).with_for_update())
            if entity is None:
                raise DomainError("NOT_FOUND", "Уведомление не найдено", 404)
            if entity.read_at is None:
                entity.read_at = utcnow()
            await db.flush()
            result = notification_view(entity)
            domain = "notification"

        elif kind == "notification.preference":
            data = NotificationSettings.model_validate(payload)
            entity = await db.scalar(select(NotificationPreference).where(
                NotificationPreference.user_id == user, NotificationPreference.org_id == org
            ).with_for_update())
            if entity is None:
                entity = NotificationPreference(org_id=org, user_id=user, task_events=data.task_events)
                db.add(entity)
            else:
                entity.task_events = data.task_events
            await db.flush()
            result = {"task_events": entity.task_events}
            domain = "preference"

        else:
            raise DomainError("VALIDATION_ERROR", "Неизвестная операция", 422)

    except ValidationError as exc:
        raise DomainError("VALIDATION_ERROR", "Некорректные данные", 422) from exc

    db.add(SyncOperation(client_op_id=command.client_op_id, org_id=org, user_id=user,
                         payload_hash=signature, result=result))
    if entity is not None and domain != "preference":
        db.add(ChangeLog(org_id=org, entity_type=domain,
                         entity_id=entity.id, payload=result))
    if event is not None:
        db.add(event)
    await db.flush()
    return {"state": "applied", "result": result}
