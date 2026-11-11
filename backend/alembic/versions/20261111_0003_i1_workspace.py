"""I-1 manual fields, private scouting, tasks, notifications and sync.

Revision ID: 20261111_0003
Revises: 20261014_0002
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261111_0003"
down_revision = "20261014_0002"
branch_labels = None
depends_on = None

U = postgresql.UUID(as_uuid=True)
T = sa.DateTime(timezone=True)


def uuid(): return sa.Column("id", U, primary_key=True)
def timecols(version=True):
    out = [
        sa.Column("created_at", T, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", T, nullable=False, server_default=sa.text("now()")),
    ]
    if version: out.append(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    return out


def upgrade() -> None:
    for schema in ("field", "scouting", "tasks", "notify", "sync"):
        op.execute(sa.text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

    op.create_table(
        "fields", uuid(),
        sa.Column("org_id", U, sa.ForeignKey("org.organizations.id"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("crop_name", sa.String(120), nullable=False),
        sa.Column("area_ha", sa.Numeric(12, 3), nullable=False),
        sa.Column("sowing_date", T),
        sa.Column("source", sa.String(16), nullable=False, server_default="manual"),
        sa.Column("meteo_field_id", sa.String(128)),
        sa.Column("archived_at", T),
        *timecols(),
        sa.CheckConstraint("area_ha > 0", name="ck_fields_area_positive"),
        sa.CheckConstraint("source IN ('manual','meteo')", name="ck_fields_source_valid"),
        schema="field",
    )
    op.create_index("ix_field_fields_org_id", "fields", ["org_id"], schema="field")

    op.create_table(
        "observations", uuid(),
        sa.Column("org_id", U, sa.ForeignKey("org.organizations.id"), nullable=False),
        sa.Column("field_id", U, sa.ForeignKey("field.fields.id"), nullable=False),
        sa.Column("author_id", U, sa.ForeignKey("auth.users.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("taken_at", T, nullable=False, server_default=sa.text("now()")),
        sa.Column("visibility", sa.String(12), nullable=False, server_default="private"),
        *timecols(),
        sa.CheckConstraint("kind IN ('disease','pest','weed','damage','crop_state','other')", name="ck_observations_kind_valid"),
        schema="scouting",
    )
    op.create_index("ix_scouting_observations_org_id", "observations", ["org_id"], schema="scouting")
    op.create_index("ix_scouting_observations_field_id", "observations", ["field_id"], schema="scouting")

    op.create_table(
        "tasks", uuid(),
        sa.Column("org_id", U, sa.ForeignKey("org.organizations.id"), nullable=False),
        sa.Column("field_id", U, sa.ForeignKey("field.fields.id"), nullable=False),
        sa.Column("observation_id", U, sa.ForeignKey("scouting.observations.id")),
        sa.Column("author_id", U, sa.ForeignKey("auth.users.id"), nullable=False),
        sa.Column("assignee_id", U, sa.ForeignKey("auth.users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("due_at", T),
        sa.Column("checklist", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(24), nullable=False, server_default="new"),
        sa.Column("blocked_reason", sa.Text()),
        sa.Column("completed_at", T),
        sa.Column("verified_at", T),
        *timecols(),
        sa.CheckConstraint("status IN ('new','accepted','in_progress','blocked','done','verified')", name="ck_tasks_status_valid"),
        sa.CheckConstraint("priority IN ('low','normal','high')", name="ck_tasks_priority_valid"),
        schema="tasks",
    )
    op.create_index("ix_tasks_tasks_org_id", "tasks", ["org_id"], schema="tasks")
    op.create_index("ix_tasks_tasks_field_id", "tasks", ["field_id"], schema="tasks")

    op.create_table(
        "work_log", uuid(),
        sa.Column("org_id", U, sa.ForeignKey("org.organizations.id"), nullable=False),
        sa.Column("field_id", U, sa.ForeignKey("field.fields.id"), nullable=False),
        sa.Column("task_id", U, sa.ForeignKey("tasks.tasks.id"), nullable=False),
        sa.Column("performed_by", U, sa.ForeignKey("auth.users.id"), nullable=False),
        sa.Column("performed_at", T, nullable=False),
        sa.Column("created_at", T, nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("task_id", name="uq_work_log_one_completion_per_task"),
        schema="tasks",
    )
    op.create_index("ix_tasks_work_log_org_id", "work_log", ["org_id"], schema="tasks")

    op.create_table(
        "notifications", uuid(),
        sa.Column("org_id", U, sa.ForeignKey("org.organizations.id"), nullable=False),
        sa.Column("user_id", U, sa.ForeignKey("auth.users.id"), nullable=False),
        sa.Column("event_id", U, nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("task_id", U, sa.ForeignKey("tasks.tasks.id")),
        sa.Column("read_at", T),
        sa.Column("created_at", T, nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("event_id", "user_id", name="uq_notifications_event_per_user"),
        schema="notify",
    )
    op.create_index("ix_notify_notifications_org_id", "notifications", ["org_id"], schema="notify")
    op.create_index("ix_notify_notifications_user_id", "notifications", ["user_id"], schema="notify")

    op.create_table(
        "preferences", uuid(),
        sa.Column("org_id", U, sa.ForeignKey("org.organizations.id"), nullable=False),
        sa.Column("user_id", U, sa.ForeignKey("auth.users.id"), nullable=False),
        sa.Column("task_events", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("user_id", "org_id", name="uq_preferences_user_org"),
        schema="notify",
    )

    op.create_table(
        "operations",
        sa.Column("client_op_id", U, primary_key=True),
        sa.Column("org_id", U, sa.ForeignKey("org.organizations.id"), nullable=False),
        sa.Column("user_id", U, sa.ForeignKey("auth.users.id"), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column("processed_at", T, nullable=False, server_default=sa.text("now()")),
        schema="sync",
    )
    op.create_index("ix_sync_operations_org_id", "operations", ["org_id"], schema="sync")

    op.create_table(
        "changes",
        sa.Column("seq", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("org_id", U, sa.ForeignKey("org.organizations.id"), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", U, nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", T, nullable=False, server_default=sa.text("now()")),
        schema="sync",
    )
    op.create_index("ix_sync_changes_org_id", "changes", ["org_id"], schema="sync")


def downgrade() -> None:
    for schema in ("sync","notify","tasks","scouting","field"):
        op.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
