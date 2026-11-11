from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field as PField


class FieldCreate(BaseModel):
    name: str = PField(min_length=1, max_length=160)
    crop_name: str = PField(min_length=1, max_length=120)
    area_ha: float = PField(gt=0, le=10000000)
    sowing_date: date | None = None


class FieldEdit(BaseModel):
    name: str = PField(min_length=1, max_length=160)
    crop_name: str = PField(min_length=1, max_length=120)
    area_ha: float = PField(gt=0, le=10000000)
    sowing_date: date | None = None


class ObservationCreate(BaseModel):
    field_id: UUID
    kind: Literal["disease", "pest", "weed", "damage", "crop_state", "other"]
    text: str = PField(default="", max_length=10000)
    taken_at: datetime | None = None


class TaskCreate(BaseModel):
    field_id: UUID
    observation_id: UUID | None = None
    title: str = PField(min_length=1, max_length=200)
    description: str = PField(default="", max_length=10000)
    priority: Literal["low", "normal", "high"] = "normal"
    due_at: datetime | None = None
    checklist: list[str] = PField(default_factory=list, max_length=30)


class TaskTransition(BaseModel):
    status: Literal["accepted", "in_progress", "blocked", "done", "verified"]
    blocked_reason: str | None = PField(default=None, max_length=1000)


class NotificationSettings(BaseModel):
    task_events: bool


class SyncCommand(BaseModel):
    client_op_id: UUID
    type: Literal[
        "field.create", "field.update", "observation.create",
        "task.create", "task.transition", "notification.read", "notification.preference",
    ]
    entity_id: UUID | None = None
    base_version: int | None = PField(default=None, ge=1)
    payload: dict = PField(default_factory=dict)


class SyncBatch(BaseModel):
    ops: list[SyncCommand] = PField(min_length=1, max_length=50)
