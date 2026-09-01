from __future__ import annotations

import os

from sqlalchemy.engine import URL, make_url
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


def uses_transaction_pooler(url: URL) -> bool:
    """Detect a Supavisor transaction-pooler target, which cannot cache statements."""
    host = (url.host or "").lower()
    return "pooler.supabase.com" in host or url.port == 6543


def running_serverless() -> bool:
    return bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    settings = settings or get_settings()
    database_url = async_database_url(settings.database_url)
    engine_options: dict = {"pool_pre_ping": settings.database_pool_pre_ping}

    transaction_pooler = (
        settings.database_pool_mode == "transaction" or uses_transaction_pooler(database_url)
    )
    if transaction_pooler:
        database_url = database_url.update_query_dict({"prepared_statement_cache_size": "0"})
        engine_options["connect_args"] = {"statement_cache_size": 0}

    if running_serverless():
        engine_options["poolclass"] = NullPool
    else:
        # A long-running FastAPI process can safely reuse client connections to
        # Supavisor. Transaction-level pooling still requires both asyncpg
        # statement caches to remain disabled, but it does not require opening
        # a new TCP/TLS connection for every HTTP request.
        engine_options.update(
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout_seconds,
            pool_recycle=settings.database_pool_recycle_seconds,
        )

    return create_async_engine(database_url, **engine_options)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def check_database_connection(engine: AsyncEngine) -> None:
    """Raise when PostgreSQL cannot accept a simple query."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
