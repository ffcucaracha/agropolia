"""Private attachments for observations and task completion.

Revision ID: 20261111_0004
Revises: 20261111_0003
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261111_0004"
down_revision = "20261111_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("org.organizations.id"), nullable=False),
        sa.Column("owner_type", sa.String(16), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth.users.id"), nullable=False),
        sa.Column("client_media_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("mime", sa.String(80), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("client_media_id", "org_id", name="uq_media_upload_id_per_org"),
        sa.CheckConstraint("owner_type IN ('observation','task')", name="ck_media_owner_type_valid"),
        schema="scouting",
    )
    op.create_index("ix_scouting_media_org_id", "media", ["org_id"], schema="scouting")
    op.create_index("ix_scouting_media_owner_id", "media", ["owner_id"], schema="scouting")


def downgrade() -> None:
    op.drop_index("ix_scouting_media_owner_id", table_name="media", schema="scouting")
    op.drop_index("ix_scouting_media_org_id", table_name="media", schema="scouting")
    op.drop_table("media", schema="scouting")
