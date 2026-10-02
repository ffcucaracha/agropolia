from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agropolia.db import Base
from agropolia.ids import uuid7


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("inn", name="uq_org_organizations_inn"),
        CheckConstraint("type IN ('SHO','KFH')", name="type_i0"),
        {"schema": "org"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    inn: Mapped[str] = mapped_column(String(12), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "org_id", name="uq_org_memberships_user_org"), {"schema": "org"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("org.organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = ({"schema": "org"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    text_version: Mapped[str] = mapped_column(String(64), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    device_context: Mapped[str | None] = mapped_column(String(160))
    ip_address: Mapped[str | None] = mapped_column(INET())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
