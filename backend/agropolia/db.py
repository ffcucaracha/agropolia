from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import get_settings

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(AsyncAttrs, DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


settings = get_settings()
engine_options = {"pool_pre_ping": True}
if settings.env == "test":
    engine_options["poolclass"] = NullPool
engine = create_async_engine(settings.database_url, **engine_options)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
