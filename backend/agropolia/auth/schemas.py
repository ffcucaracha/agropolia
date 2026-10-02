from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from agropolia.security import normalize_phone


OtpPurpose = Literal["login", "register"]


class OtpRequest(BaseModel):
    phone: str
    device_id: str = Field(min_length=8, max_length=160)
    purpose: OtpPurpose

    @field_validator("phone")
    @classmethod
    def normalize(cls, value: str) -> str:
        return normalize_phone(value)


class OtpRequestResult(BaseModel):
    expires_in: int
    dev_code: str | None = None


class OtpVerifyRequest(OtpRequest):
    code: str = Field(pattern=r"^\d{6}$")


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class OtpVerifyResult(BaseModel):
    registration_token: str | None = None
    tokens: TokenPair | None = None


class RegisterRequest(BaseModel):
    registration_token: str
    name: str = Field(min_length=1, max_length=160)
    organization_type: Literal["SHO", "KFH"]
    organization_inn: str
    organization_name: str = Field(min_length=1, max_length=255)
    consent_version: str = Field(min_length=1, max_length=64)
    consent_accepted: bool


class RefreshRequest(BaseModel):
    refresh_token: str | None = None
    device_id: str = Field(min_length=8, max_length=160)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
