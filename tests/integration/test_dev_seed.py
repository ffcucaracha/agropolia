import pytest
from sqlalchemy import func, select

from agropolia.auth.models import User
from agropolia.db import SessionFactory
from agropolia.dev.seed import TEST_ORG_INN, TEST_PHONE, seed
from agropolia.organizations.models import Membership, Organization


@pytest.mark.asyncio
async def test_dev_seed_is_idempotent():
    await seed()
    await seed()

    async with SessionFactory() as db:
        user_count = await db.scalar(
            select(func.count()).select_from(User).where(User.phone == TEST_PHONE)
        )
        org_count = await db.scalar(
            select(func.count()).select_from(Organization).where(
                Organization.inn == TEST_ORG_INN
            )
        )
        user = await db.scalar(select(User).where(User.phone == TEST_PHONE))
        organization = await db.scalar(
            select(Organization).where(Organization.inn == TEST_ORG_INN)
        )
        membership_count = await db.scalar(
            select(func.count()).select_from(Membership).where(
                Membership.user_id == user.id,
                Membership.org_id == organization.id,
            )
        )

    assert user_count == 1
    assert org_count == 1
    assert membership_count == 1
