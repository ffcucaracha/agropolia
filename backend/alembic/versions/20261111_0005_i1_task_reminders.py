"""Persist scheduled task notification state.

Revision ID: 20261111_0005
Revises: 20261111_0004
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261111_0005"
down_revision = "20261111_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("reminded_at", sa.DateTime(timezone=True)), schema="tasks")
    op.create_index("ix_tasks_tasks_due_open", "tasks", ["due_at", "reminded_at"], schema="tasks")


def downgrade() -> None:
    op.drop_index("ix_tasks_tasks_due_open", table_name="tasks", schema="tasks")
    op.drop_column("tasks", "reminded_at", schema="tasks")
