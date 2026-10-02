from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agropolia.config import get_settings
from agropolia.db import get_db
from agropolia.errors import DomainError
from agropolia.organizations.models import Membership, Organization

from .models import Session, User
from .tokens import TokenService

bearer = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class AuthContext:
    user: User
    session: Session


@dataclass(slots=True)
class TenantContext(AuthContext):
    membership: Membership
    organization: Organization


async def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    if credentials is None:
        raise DomainError("AUTH_REQUIRED", "Требуется авторизация", 401)
    payload = TokenService(get_settings()).decode_access(credentials.credentials)
    try:
        user_id = UUID(payload["sub"])
        session_id = UUID(payload["sid"])
    except (KeyError, ValueError) as exc:
        raise DomainError("INVALID_TOKEN", "Некорректный токен", 401) from exc
    session = await db.get(Session, session_id)
    user = await db.get(User, user_id)
    if session is None or user is None or session.user_id != user.id or session.revoked_at is not None:
        raise DomainError("SESSION_INVALID", "Сессия завершена", 401)
    return AuthContext(user=user, session=session)


async def get_tenant_context(
    auth: AuthContext = Depends(get_auth_context),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    rows = (await db.execute(select(Membership).where(Membership.user_id == auth.user.id))).scalars().all()
    if not rows:
        raise DomainError("ORG_CONTEXT_MISSING", "Пользователь не состоит в организации", 403)
    if x_org_id is None:
        if len(rows) != 1:
            raise DomainError("ORG_CONTEXT_REQUIRED", "Укажите активную организацию", 400)
        membership = rows[0]
    else:
        try:
            requested = UUID(x_org_id)
        except ValueError as exc:
            raise DomainError("NOT_FOUND", "Организация не найдена", 404) from exc
        membership = next((row for row in rows if row.org_id == requested), None)
        if membership is None:
            # Do not reveal whether another tenant's organization exists.
            raise DomainError("NOT_FOUND", "Организация не найдена", 404)
    organization = await db.get(Organization, membership.org_id)
    if organization is None:
        raise DomainError("NOT_FOUND", "Организация не найдена", 404)
    return TenantContext(user=auth.user, session=auth.session, membership=membership, organization=organization)
