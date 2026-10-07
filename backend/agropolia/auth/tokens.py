from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt

from agropolia.config import Settings
from agropolia.errors import DomainError
from agropolia.security import secret_hash


class TokenService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _encode(self, claims: dict[str, Any], ttl: timedelta) -> str:
        now = datetime.now(timezone.utc)
        payload = {**claims, "iat": now, "exp": now + ttl, "iss": "agropolia"}
        return jwt.encode(payload, self.settings.jwt_secret, algorithm="HS256")

    def _decode(self, token: str, expected_type: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=["HS256"], issuer="agropolia")
        except jwt.PyJWTError as exc:
            raise DomainError("INVALID_TOKEN", "Недействительный или истёкший токен", 401) from exc
        if payload.get("typ") != expected_type:
            raise DomainError("INVALID_TOKEN", "Недействительный тип токена", 401)
        return payload

    def create_access(self, user_id: UUID, session_id: UUID) -> str:
        return self._encode(
            {"typ": "access", "sub": str(user_id), "sid": str(session_id)},
            timedelta(minutes=self.settings.access_ttl_minutes),
        )

    def decode_access(self, token: str) -> dict[str, Any]:
        return self._decode(token, "access")

    def create_registration(self, phone: str, device_id: str) -> str:
        return self._encode(
            {"typ": "registration", "phone": phone, "device_id": device_id},
            timedelta(minutes=self.settings.preauth_ttl_minutes),
        )

    def decode_registration(self, token: str) -> dict[str, Any]:
        return self._decode(token, "registration")

    @staticmethod
    def new_refresh_token() -> str:
        return secrets.token_urlsafe(48)

    @staticmethod
    def refresh_hash(token: str) -> str:
        return secret_hash(token)
