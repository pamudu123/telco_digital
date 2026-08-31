from __future__ import annotations

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import text

from telco_digital.config import Settings, get_settings


def async_database_url(database_url: str):
    """Accept provider PostgreSQL URLs while always using the asyncpg driver."""
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+asyncpg")
    return url


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    settings = settings or get_settings()
    database_url = async_database_url(settings.database_url)
    engine_options: dict = {"pool_pre_ping": True}

    if settings.database_pool_mode == "transaction":
        database_url = database_url.update_query_dict({"prepared_statement_cache_size": "0"})
        engine_options.update(
            connect_args={"statement_cache_size": 0},
            poolclass=NullPool,
        )

    return create_async_engine(database_url, **engine_options)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def check_database_connection(engine: AsyncEngine) -> None:
    """Raise when PostgreSQL cannot accept a simple query."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
