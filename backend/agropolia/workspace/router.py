from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agropolia.auth.dependencies import TenantContext, get_tenant_context
from agropolia.db import get_db
from agropolia.errors import DomainError
from agropolia.ids import uuid7

from .models import (
    ChangeLog, Field, Notification, NotificationPreference, Observation, Task, WorkLogEntry,
)
from .schemas import (
    FieldCreate, FieldEdit, NotificationSettings, ObservationCreate,
    SyncBatch, SyncCommand, TaskCreate, TaskTransition,
)
from .service import (
    field_view, notification_view, observation_view, operation,
    owned_field, owned_observation, owned_task, task_view,
)

router = APIRouter(tags=["workspace"])


async def write(db: AsyncSession, context: TenantContext, cmd: SyncCommand) -> dict:
    try:
        outcome = await operation(db, context, cmd)
        await db.commit()
        return outcome["result"]
    except Exception:
        await db.rollback()
        raise


def command(typ: str, payload: dict, key: UUID | None, entity_id: UUID | None = None,
            base_version: int | None = None) -> SyncCommand:
    return SyncCommand(
        client_op_id=key or uuid7(), type=typ, payload=payload,
        entity_id=entity_id, base_version=base_version,
    )


@router.get("/fields")
async def fields(
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.scalars(select(Field).where(
        Field.org_id == context.organization.id, Field.archived_at.is_(None)
    ).order_by(Field.created_at.desc()))).all()
    return [field_view(item) for item in rows]


@router.post("/fields", status_code=201)
async def create_field(
    data: FieldCreate,
    idempotency_key: UUID | None = Header(default=None, alias="Idempotency-Key"),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    return await write(db, context, command("field.create", data.model_dump(mode="json"), idempotency_key))


@router.get("/fields/{field_id}")
async def get_field(
    field_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    return field_view(await owned_field(db, context.organization.id, field_id))


@router.patch("/fields/{field_id}")
async def edit_field(
    field_id: UUID,
    data: FieldEdit,
    base_version: int = Header(alias="If-Match-Version"),
    idempotency_key: UUID | None = Header(default=None, alias="Idempotency-Key"),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    return await write(db, context, command(
        "field.update", data.model_dump(mode="json"), idempotency_key,
        entity_id=field_id, base_version=base_version,
    ))


@router.get("/observations")
async def observations(
    field_id: UUID | None = None,
    kind: str | None = None,
    search: str | None = None,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    q = select(Observation).where(Observation.org_id == context.organization.id)
    if field_id:
        q = q.where(Observation.field_id == field_id)
    if kind:
        q = q.where(Observation.kind == kind)
    if search:
        q = q.where(Observation.text.ilike(f"%{search.replace('%','').replace('_','')}%"))
    rows = (await db.scalars(q.order_by(Observation.taken_at.desc()).limit(200))).all()
    return [observation_view(item) for item in rows]


@router.post("/observations", status_code=201)
async def create_observation(
    data: ObservationCreate,
    idempotency_key: UUID | None = Header(default=None, alias="Idempotency-Key"),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    return await write(db, context, command("observation.create", data.model_dump(mode="json"), idempotency_key))


@router.get("/observations/{observation_id}")
async def get_observation(
    observation_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    return observation_view(await owned_observation(db, context.organization.id, observation_id))


@router.get("/tasks")
async def tasks(
    field_id: UUID | None = None,
    status: str | None = None,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    q = select(Task).where(Task.org_id == context.organization.id)
    if field_id:
        q = q.where(Task.field_id == field_id)
    if status:
        q = q.where(Task.status == status)
    rows = (await db.scalars(q.order_by(Task.created_at.desc()).limit(250))).all()
    return [task_view(item) for item in rows]


@router.post("/tasks", status_code=201)
async def create_task(
    data: TaskCreate,
    idempotency_key: UUID | None = Header(default=None, alias="Idempotency-Key"),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    return await write(db, context, command("task.create", data.model_dump(mode="json"), idempotency_key))


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    return task_view(await owned_task(db, context.organization.id, task_id))


@router.post("/tasks/{task_id}/transition")
async def transition_task(
    task_id: UUID,
    data: TaskTransition,
    base_version: int = Header(alias="If-Match-Version"),
    idempotency_key: UUID | None = Header(default=None, alias="Idempotency-Key"),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    return await write(db, context, command(
        "task.transition", data.model_dump(mode="json"), idempotency_key,
        entity_id=task_id, base_version=base_version,
    ))


@router.get("/work-log")
async def work_log(
    field_id: UUID | None = None,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    q = select(WorkLogEntry, Task.title).join(
        Task, Task.id == WorkLogEntry.task_id
    ).where(WorkLogEntry.org_id == context.organization.id)
    if field_id:
        q = q.where(WorkLogEntry.field_id == field_id)
    rows = (await db.execute(q.order_by(WorkLogEntry.performed_at.desc()).limit(200))).all()
    return [
        dict(id=str(row.id), field_id=str(row.field_id), task_id=str(row.task_id),
             title=title, performed_by=str(row.performed_by),
             performed_at=row.performed_at.isoformat())
        for row, title in rows
    ]


@router.get("/notifications")
async def notifications(
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.scalars(select(Notification).where(
        Notification.org_id == context.organization.id,
        Notification.user_id == context.user.id,
    ).order_by(Notification.created_at.desc()).limit(100))).all()
    return [notification_view(row) for row in rows]


@router.post("/notifications/{notification_id}/read")
async def read_notification(
    notification_id: UUID,
    idempotency_key: UUID | None = Header(default=None, alias="Idempotency-Key"),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    return await write(db, context, command(
        "notification.read", {}, idempotency_key, entity_id=notification_id,
    ))


@router.get("/notification-settings")
async def notification_settings(
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    row = await db.scalar(select(NotificationPreference).where(
        NotificationPreference.user_id == context.user.id,
        NotificationPreference.org_id == context.organization.id,
    ))
    return {"task_events": row.task_events if row else True}


@router.put("/notification-settings")
async def update_notification_settings(
    data: NotificationSettings,
    idempotency_key: UUID | None = Header(default=None, alias="Idempotency-Key"),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    return await write(db, context, command(
        "notification.preference", data.model_dump(), idempotency_key,
    ))


@router.post("/sync/ops")
async def sync_ops(
    data: SyncBatch,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    results = []
    for item in data.ops:
        try:
            outcome = await operation(db, context, item)
            await db.commit()
            results.append({"client_op_id": str(item.client_op_id), **outcome})
        except DomainError as exc:
            await db.rollback()
            results.append({"client_op_id": str(item.client_op_id),
                            "state": "rejected", "code": exc.code, "message": exc.message,
                            "details": exc.details})
        except Exception:
            await db.rollback()
            raise
    return {"results": results}


@router.get("/sync/changes")
async def sync_changes(
    since: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.scalars(select(ChangeLog).where(
        ChangeLog.org_id == context.organization.id,
        ChangeLog.seq > since,
    ).order_by(ChangeLog.seq).limit(limit))).all()
    return {"changes": [
        {"seq": row.seq, "entity_type": row.entity_type,
         "entity_id": str(row.entity_id), "payload": row.payload}
        for row in rows
    ], "next_cursor": rows[-1].seq if rows else since}
