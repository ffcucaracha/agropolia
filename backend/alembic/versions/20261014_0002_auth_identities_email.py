"""Move authentication identifier from User.phone to auth.identities.

Revision ID: 20261014_0002
Revises: 20261001_0001
Create Date: 2026-10-14
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261014_0002"
down_revision = "20261001_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("value", sa.String(320), nullable=False),
        sa.Column("normalized_value", sa.String(320), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("type", "normalized_value", name="uq_auth_identities_type_value"),
        schema="auth",
    )
    op.create_index("ix_auth_identities_user_id", "identities", ["user_id"], schema="auth")

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, phone FROM auth.users WHERE phone IS NOT NULL")).fetchall()
    now = datetime.now(timezone.utc)
    identities = sa.table(
        "identities",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("user_id", postgresql.UUID(as_uuid=True)),
        sa.column("type", sa.String()),
        sa.column("value", sa.String()),
        sa.column("normalized_value", sa.String()),
        sa.column("verified_at", sa.DateTime(timezone=True)),
        sa.column("is_primary", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("version", sa.Integer()),
        schema="auth",
    )
    if rows:
        op.bulk_insert(
            identities,
            [
                {
                    "id": uuid.uuid4(),
                    "user_id": row.id,
                    "type": "phone",
                    "value": row.phone,
                    "normalized_value": row.phone,
                    "verified_at": now,
                    "is_primary": True,
                    "created_at": now,
                    "updated_at": now,
                    "version": 1,
                }
                for row in rows
            ],
        )

    op.drop_constraint("uq_auth_users_phone", "users", schema="auth", type_="unique")
    op.drop_column("users", "phone", schema="auth")
    op.alter_column("organizations", "contact_phone", schema="org", existing_type=sa.String(32), nullable=True)


def downgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(32), nullable=True), schema="auth")
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE auth.users u
               SET phone = i.normalized_value
              FROM auth.identities i
             WHERE i.user_id = u.id
               AND i.type = 'phone'
               AND i.is_primary = true
            """
        )
    )
    op.create_unique_constraint("uq_auth_users_phone", "users", ["phone"], schema="auth")
    op.alter_column("organizations", "contact_phone", schema="org", existing_type=sa.String(32), nullable=False)
    op.drop_index("ix_auth_identities_user_id", table_name="identities", schema="auth")
    op.drop_table("identities", schema="auth")
