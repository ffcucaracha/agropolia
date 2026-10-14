from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformVersionPolicy(BaseModel):
    latest_version: str
    recommended_version: str
    minimum_supported_version: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGROPOLIA_", env_file=".env", extra="ignore")

    env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+asyncpg://agropolia:agropolia@localhost:5432/agropolia"
    redis_url: str = "redis://localhost:6379/0"
    nats_url: str = "nats://localhost:4222"
    jwt_secret: str = "development-only-change-me"
    otp_secret: str = "development-only-change-me-too"
    dev_otp_code: str = "000000"
    web_origin: str = "http://localhost:5173"
    cookie_secure: bool = False

    auth_email_enabled: bool = True
    auth_phone_enabled: bool = False
    email_delivery_mode: Literal["dev", "smtp"] = "dev"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "no-reply@agropolia.local"
    smtp_from_name: str = "Агрополия"
    smtp_starttls: bool = True
    smtp_ssl: bool = False

    access_ttl_minutes: int = 15
    refresh_ttl_days: int = 30
    preauth_ttl_minutes: int = 10
    otp_ttl_seconds: int = 300
    otp_resend_cooldown_seconds: int = 60
    otp_attempt_limit: int = 5
    otp_attempt_window_seconds: int = 900

    android_latest_version: str = "0.1.0"
    android_recommended_version: str = "0.1.0"
    android_minimum_supported_version: str = "0.1.0"
    ios_latest_version: str = "0.1.0"
    ios_recommended_version: str = "0.1.0"
    ios_minimum_supported_version: str = "0.1.0"

    @model_validator(mode="after")
    def validate_runtime(self) -> "Settings":
        if not self.auth_email_enabled and not self.auth_phone_enabled:
            raise ValueError("at least one authentication method must be enabled")
        if self.auth_phone_enabled:
            raise ValueError("phone authentication is not implemented in I-0")
        if self.env == "production" and self.email_delivery_mode != "smtp":
            raise ValueError("production email OTP requires SMTP delivery mode")
        if self.email_delivery_mode == "smtp" and not self.smtp_host:
            raise ValueError("SMTP host is required when email delivery mode is smtp")
        if self.env == "production" and (len(self.jwt_secret) < 32 or len(self.otp_secret) < 32):
            raise ValueError("production JWT/OTP secrets must be at least 32 characters")
        return self

    @property
    def enabled_auth_methods(self) -> list[str]:
        return ["email"] if self.auth_email_enabled else []

    @property
    def version_policies(self) -> dict[str, PlatformVersionPolicy]:
        return {
            "android": PlatformVersionPolicy(
                latest_version=self.android_latest_version,
                recommended_version=self.android_recommended_version,
                minimum_supported_version=self.android_minimum_supported_version,
            ),
            "ios": PlatformVersionPolicy(
                latest_version=self.ios_latest_version,
                recommended_version=self.ios_recommended_version,
                minimum_supported_version=self.ios_minimum_supported_version,
            ),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
