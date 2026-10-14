from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agropolia.auth.dependencies import TenantContext, get_tenant_context
from agropolia.auth.models import AuthIdentity
from agropolia.db import get_db
from agropolia.errors import DomainError

from .schemas import MembershipView, MeView, OrganizationView, UserView

router = APIRouter(tags=["organization"])


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


def mask_identifier(method: str, value: str) -> str:
    if method == "email":
        return mask_email(value)
    if len(value) < 6:
        return "***"
    return f"{value[:2]}***{value[-4:]}"


async def to_me(context: TenantContext, db: AsyncSession) -> MeView:
    identity = await db.scalar(
        select(AuthIdentity).where(
            AuthIdentity.user_id == context.user.id,
            AuthIdentity.is_primary.is_(True),
        )
    )
    if identity is None:
        raise DomainError("AUTH_IDENTITY_MISSING", "У пользователя отсутствует идентификатор входа", 500)
    return MeView(
        user=UserView(
            id=context.user.id,
            name=context.user.name,
            auth_method=identity.type,
            identifier_masked=mask_identifier(identity.type, identity.normalized_value),
        ),
        organization=OrganizationView(
            id=context.organization.id,
            type=context.organization.type,
            inn=context.organization.inn,
            name=context.organization.name,
        ),
        membership=MembershipView(role=context.membership.role),
    )


@router.get("/me", response_model=MeView)
async def me(
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
) -> MeView:
    return await to_me(context, db)


@router.get("/organizations/{organization_id}", response_model=OrganizationView)
async def organization(
    organization_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
) -> OrganizationView:
    if organization_id != context.organization.id:
        raise DomainError("NOT_FOUND", "Организация не найдена", 404)
    return OrganizationView(
        id=context.organization.id,
        type=context.organization.type,
        inn=context.organization.inn,
        name=context.organization.name,
    )
