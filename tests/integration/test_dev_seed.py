import pytest
from sqlalchemy import func, select

from agropolia.auth.models import AuthIdentity
from agropolia.db import SessionFactory
from agropolia.dev.seed import TEST_EMAIL, TEST_ORG_INN, seed
from agropolia.organizations.models import Membership, Organization


@pytest.mark.asyncio
async def test_dev_seed_is_idempotent():
    await seed()
    await seed()

    async with SessionFactory() as db:
        identity_count = await db.scalar(
            select(func.count()).select_from(AuthIdentity).where(
                AuthIdentity.type == "email",
                AuthIdentity.normalized_value == TEST_EMAIL,
            )
        )
        identity = await db.scalar(
            select(AuthIdentity).where(
                AuthIdentity.type == "email",
                AuthIdentity.normalized_value == TEST_EMAIL,
            )
        )
        organization = await db.scalar(
            select(Organization).where(Organization.inn == TEST_ORG_INN)
        )
        membership_count = await db.scalar(
            select(func.count()).select_from(Membership).where(
                Membership.user_id == identity.user_id,
                Membership.org_id == organization.id,
            )
        )

    assert identity_count == 1
    assert membership_count == 1
