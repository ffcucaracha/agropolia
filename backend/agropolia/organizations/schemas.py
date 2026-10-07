from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class UserView(BaseModel):
    id: UUID
    name: str | None
    phone_masked: str


class OrganizationView(BaseModel):
    id: UUID
    type: str
    inn: str
    name: str


class MembershipView(BaseModel):
    role: str


class MeView(BaseModel):
    user: UserView
    organization: OrganizationView
    membership: MembershipView
