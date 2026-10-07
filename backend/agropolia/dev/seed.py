from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from agropolia.auth.models import User
from agropolia.config import get_settings
from agropolia.db import SessionFactory, engine
from agropolia.ids import uuid7
from agropolia.organizations.models import Consent, Membership, Organization

TEST_PHONE = "+79990000001"
TEST_NAME = "Тестовый пользователь"
TEST_ORG_TYPE = "KFH"
TEST_ORG_INN = "9999999998"
TEST_ORG_NAME = "Тестовое КФХ"
TEST_CONSENT_VERSION = "i0-pd-1"


async def seed() -> None:
    settings = get_settings()
    if settings.env not in {"development", "test"}:
        raise RuntimeError("Dev seed is allowed only in development/test environments")

    async with SessionFactory() as db:
        async with db.begin():
            user = await db.scalar(select(User).where(User.phone == TEST_PHONE))
            if user is None:
                user = User(id=uuid7(), phone=TEST_PHONE, name=TEST_NAME)
                db.add(user)
                await db.flush()

            organization = await db.scalar(
                select(Organization).where(Organization.inn == TEST_ORG_INN)
            )
            if organization is None:
                organization = Organization(
                    id=uuid7(),
                    type=TEST_ORG_TYPE,
                    inn=TEST_ORG_INN,
                    name=TEST_ORG_NAME,
                    contact_phone=TEST_PHONE,
                )
                db.add(organization)
                await db.flush()

            membership = await db.scalar(
                select(Membership).where(
                    Membership.user_id == user.id,
                    Membership.org_id == organization.id,
                )
            )
            if membership is None:
                db.add(
                    Membership(
                        id=uuid7(),
                        user_id=user.id,
                        org_id=organization.id,
                        role="owner",
                    )
                )

            consent = await db.scalar(
                select(Consent).where(
                    Consent.user_id == user.id,
                    Consent.type == "personal_data",
                    Consent.text_version == TEST_CONSENT_VERSION,
                )
            )
            if consent is None:
                db.add(
                    Consent(
                        id=uuid7(),
                        user_id=user.id,
                        type="personal_data",
                        text_version=TEST_CONSENT_VERSION,
                        granted_at=datetime.now(timezone.utc),
                        channel="dev_seed",
                        device_context="dev-seed",
                    )
                )

    await engine.dispose()
    print("Development test user is ready:")
    print(f"  phone: {TEST_PHONE}")
    print(f"  OTP:   {settings.dev_otp_code}")
    print(f"  org:   {TEST_ORG_NAME}")
    print(f"  INN:   {TEST_ORG_INN}")


if __name__ == "__main__":
    asyncio.run(seed())
