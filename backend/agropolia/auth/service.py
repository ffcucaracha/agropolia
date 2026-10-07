from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agropolia.config import Settings
from agropolia.errors import DomainError
from agropolia.ids import uuid7
from agropolia.security import validate_inn
from agropolia.shared.models import SecurityAuditLog
from agropolia.organizations.models import Consent, Membership, Organization

from .models import Session, User
from .schemas import RegisterRequest, TokenPair
from .tokens import TokenService


class AuthService:
    def __init__(self, settings: Settings, token_service: TokenService) -> None:
        self.settings = settings
        self.tokens = token_service

    async def find_user_by_phone(self, db: AsyncSession, phone: str) -> User | None:
        return await db.scalar(select(User).where(User.phone == phone))

    async def issue_session(self, db: AsyncSession, user_id: UUID, device_id: str) -> tuple[Session, TokenPair]:
        refresh = self.tokens.new_refresh_token()
        session = Session(
            id=uuid7(),
            user_id=user_id,
            device_id=device_id,
            refresh_hash=self.tokens.refresh_hash(refresh),
            refresh_expires_at=datetime.now(timezone.utc) + timedelta(days=self.settings.refresh_ttl_days),
        )
        db.add(session)
        await db.flush()
        access = self.tokens.create_access(user_id, session.id)
        return session, TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=self.settings.access_ttl_minutes * 60,
        )

    async def login(self, db: AsyncSession, phone: str, device_id: str, ip_address: str | None) -> TokenPair:
        async with db.begin():
            user = await self.find_user_by_phone(db, phone)
            if user is None:
                raise DomainError("AUTH_USER_NOT_FOUND", "Пользователь не зарегистрирован", 404)
            session, tokens = await self.issue_session(db, user.id, device_id)
            db.add(SecurityAuditLog(actor_id=user.id, action="auth.login", target_type="session", target_id=str(session.id), ip_address=ip_address, details={"device_id": device_id}))
        return tokens

    async def register(self, db: AsyncSession, request: RegisterRequest, registration: dict, ip_address: str | None) -> TokenPair:
        if not request.consent_accepted:
            raise DomainError("CONSENT_REQUIRED", "Необходимо согласие на обработку персональных данных", 400)
        try:
            inn = validate_inn(request.organization_inn)
        except ValueError as exc:
            raise DomainError("VALIDATION_ERROR", str(exc), 422) from exc
        phone = str(registration["phone"])
        device_id = str(registration["device_id"])
        async with db.begin():
            if await self.find_user_by_phone(db, phone):
                raise DomainError("AUTH_USER_EXISTS", "Пользователь уже зарегистрирован", 409)
            duplicate = await db.scalar(select(Organization.id).where(Organization.inn == inn))
            if duplicate:
                raise DomainError("ORG_INN_EXISTS", "Организация с таким ИНН уже существует", 409)

            user = User(id=uuid7(), phone=phone, name=request.name.strip())
            organization = Organization(
                id=uuid7(),
                type=request.organization_type,
                inn=inn,
                name=request.organization_name.strip(),
                contact_phone=phone,
            )
            membership = Membership(id=uuid7(), user_id=user.id, org_id=organization.id, role="owner")
            consent = Consent(
                id=uuid7(),
                user_id=user.id,
                type="personal_data",
                text_version=request.consent_version,
                granted_at=datetime.now(timezone.utc),
                channel="app",
                device_context=device_id,
                ip_address=ip_address,
            )
            db.add_all([user, organization])
            await db.flush()
            db.add_all([membership, consent])
            await db.flush()
            session, tokens = await self.issue_session(db, user.id, device_id)
            db.add(SecurityAuditLog(actor_id=user.id, action="auth.register", target_type="organization", target_id=str(organization.id), ip_address=ip_address, details={"session_id": str(session.id)}))
        return tokens

    async def refresh(self, db: AsyncSession, refresh_token: str, device_id: str, ip_address: str | None) -> TokenPair:
        token_hash = self.tokens.refresh_hash(refresh_token)
        reused = False
        pair: TokenPair | None = None
        async with db.begin():
            session = await db.scalar(
                select(Session).where(or_(Session.refresh_hash == token_hash, Session.previous_refresh_hash == token_hash)).with_for_update()
            )
            if session is None:
                raise DomainError("INVALID_REFRESH", "Сессия не найдена", 401)
            now = datetime.now(timezone.utc)
            if session.revoked_at is not None or session.refresh_expires_at <= now:
                raise DomainError("INVALID_REFRESH", "Сессия завершена", 401)
            if session.device_id != device_id:
                raise DomainError("SESSION_DEVICE_MISMATCH", "Сессия привязана к другому устройству", 401)
            if session.previous_refresh_hash == token_hash:
                session.revoked_at = now
                session.version += 1
                db.add(SecurityAuditLog(actor_id=session.user_id, action="auth.refresh_reuse", target_type="session", target_id=str(session.id), ip_address=ip_address, details={}))
                reused = True
            else:
                new_refresh = self.tokens.new_refresh_token()
                session.previous_refresh_hash = session.refresh_hash
                session.refresh_hash = self.tokens.refresh_hash(new_refresh)
                session.updated_at = now
                session.version += 1
                access = self.tokens.create_access(session.user_id, session.id)
                pair = TokenPair(access_token=access, refresh_token=new_refresh, expires_in=self.settings.access_ttl_minutes * 60)
        if reused:
            raise DomainError("REFRESH_REUSED", "Повторное использование refresh token; сессия отозвана", 401)
        assert pair is not None
        return pair

    async def logout(self, db: AsyncSession, session_id: UUID, user_id: UUID, ip_address: str | None) -> None:
        session = await db.get(Session, session_id, with_for_update=True)
        if session and session.user_id == user_id and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            session.version += 1
            db.add(SecurityAuditLog(actor_id=user_id, action="auth.logout", target_type="session", target_id=str(session.id), ip_address=ip_address, details={}))
        await db.commit()
