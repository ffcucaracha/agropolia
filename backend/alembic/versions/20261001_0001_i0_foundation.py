"""I-0 foundation schemas and tables.

Revision ID: 20261001_0001
Revises:
Create Date: 2026-10-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261001_0001"
down_revision = None
branch_labels = None
depends_on = None


def uuid_col(nullable: bool = False):
    return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=nullable)


def timestamps():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    for schema in ("auth", "org", "shared"):
        op.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    op.create_table("users", uuid_col(), sa.Column("phone", sa.String(32), nullable=False), sa.Column("name", sa.String(160), nullable=True), sa.Column("status", sa.String(32), nullable=False, server_default="active"), *timestamps(), sa.UniqueConstraint("phone", name="uq_auth_users_phone"), schema="auth")
    op.create_table("sessions", uuid_col(), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False), sa.Column("device_id", sa.String(160), nullable=False), sa.Column("refresh_hash", sa.String(64), nullable=False), sa.Column("previous_refresh_hash", sa.String(64), nullable=True), sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True), *timestamps(), sa.UniqueConstraint("refresh_hash", name="uq_auth_sessions_refresh_hash"), schema="auth")
    op.create_index("ix_auth_sessions_user_device", "sessions", ["user_id", "device_id"], schema="auth")
    op.create_table("organizations", uuid_col(), sa.Column("type", sa.String(16), nullable=False), sa.Column("inn", sa.String(12), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("contact_phone", sa.String(32), nullable=False), *timestamps(), sa.CheckConstraint("type IN ('SHO','KFH')", name="ck_organizations_type_i0"), sa.UniqueConstraint("inn", name="uq_org_organizations_inn"), schema="org")
    op.create_table("memberships", uuid_col(), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False), sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("role", sa.String(32), nullable=False), sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), *timestamps(), sa.UniqueConstraint("user_id", "org_id", name="uq_org_memberships_user_org"), schema="org")
    op.create_index("ix_org_memberships_org_user", "memberships", ["org_id", "user_id"], schema="org")
    op.create_table("consents", uuid_col(), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False), sa.Column("type", sa.String(64), nullable=False), sa.Column("text_version", sa.String(64), nullable=False), sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True), sa.Column("channel", sa.String(32), nullable=False), sa.Column("device_context", sa.String(160), nullable=True), sa.Column("ip_address", postgresql.INET(), nullable=True), *timestamps(), schema="org")
    op.create_index("ix_org_consents_user_type", "consents", ["user_id", "type"], schema="org")
    op.create_table("outbox_events", uuid_col(), sa.Column("topic", sa.String(160), nullable=False), sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False), sa.Column("trace_id", sa.String(64), nullable=True), sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"), sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("published_at", sa.DateTime(timezone=True), nullable=True), sa.Column("last_error", sa.Text(), nullable=True), *timestamps(), schema="shared")
    op.create_index("ix_shared_outbox_pending", "outbox_events", ["published_at", "available_at"], schema="shared")
    op.create_table("inbox_events", sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("consumer", sa.String(160), nullable=False), sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.PrimaryKeyConstraint("event_id", "consumer", name="pk_shared_inbox_events"), schema="shared")
    op.create_table("security_audit_logs", uuid_col(), sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("action", sa.String(120), nullable=False), sa.Column("target_type", sa.String(80), nullable=True), sa.Column("target_id", sa.String(80), nullable=True), sa.Column("ip_address", postgresql.INET(), nullable=True), sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), schema="shared")


def downgrade() -> None:
    op.drop_table("security_audit_logs", schema="shared")
    op.drop_table("inbox_events", schema="shared")
    op.drop_index("ix_shared_outbox_pending", table_name="outbox_events", schema="shared")
    op.drop_table("outbox_events", schema="shared")
    op.drop_index("ix_org_consents_user_type", table_name="consents", schema="org")
    op.drop_table("consents", schema="org")
    op.drop_index("ix_org_memberships_org_user", table_name="memberships", schema="org")
    op.drop_table("memberships", schema="org")
    op.drop_table("organizations", schema="org")
    op.drop_index("ix_auth_sessions_user_device", table_name="sessions", schema="auth")
    op.drop_table("sessions", schema="auth")
    op.drop_table("users", schema="auth")
    for schema in ("shared", "org", "auth"):
        op.execute(sa.text(f"DROP SCHEMA IF EXISTS {schema}"))
