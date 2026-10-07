from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from agropolia.auth.dependencies import TenantContext, get_tenant_context
from agropolia.errors import DomainError

from .schemas import MembershipView, MeView, OrganizationView, UserView

router = APIRouter(tags=["organization"])


def mask_phone(phone: str) -> str:
    if len(phone) < 6:
        return "***"
    return f"{phone[:2]}***{phone[-4:]}"


def to_me(context: TenantContext) -> MeView:
    return MeView(
        user=UserView(id=context.user.id, name=context.user.name, phone_masked=mask_phone(context.user.phone)),
        organization=OrganizationView(id=context.organization.id, type=context.organization.type, inn=context.organization.inn, name=context.organization.name),
        membership=MembershipView(role=context.membership.role),
    )


@router.get("/me", response_model=MeView)
async def me(context: TenantContext = Depends(get_tenant_context)) -> MeView:
    return to_me(context)


@router.get("/organizations/{organization_id}", response_model=OrganizationView)
async def organization(organization_id: UUID, context: TenantContext = Depends(get_tenant_context)) -> OrganizationView:
    if organization_id != context.organization.id:
        raise DomainError("NOT_FOUND", "Организация не найдена", 404)
    return OrganizationView(id=context.organization.id, type=context.organization.type, inn=context.organization.inn, name=context.organization.name)
