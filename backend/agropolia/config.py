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

    access_ttl_minutes: int = 15
    refresh_ttl_days: int = 30
    preauth_ttl_minutes: int = 10
    otp_ttl_seconds: int = 300
    otp_attempt_limit: int = 5
    otp_attempt_window_seconds: int = 900

    android_latest_version: str = "0.1.0"
    android_recommended_version: str = "0.1.0"
    android_minimum_supported_version: str = "0.1.0"
    ios_latest_version: str = "0.1.0"
    ios_recommended_version: str = "0.1.0"
    ios_minimum_supported_version: str = "0.1.0"


    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.env == "production" and (len(self.jwt_secret) < 32 or len(self.otp_secret) < 32):
            raise ValueError("production JWT/OTP secrets must be at least 32 characters")
        return self

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
