from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from telco_digital.application.demo_dataset import END_AT
from telco_digital.config import Settings
from telco_digital.infrastructure.postgres.platform import PostgresProjectionLagQueries
from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory
from telco_digital.infrastructure.postgres.showcase import PostgresShowcaseQueries
from telco_digital.infrastructure.postgres.unit_of_work import SqlAlchemyUnitOfWork


def attach_runtime(app: FastAPI, settings: Settings) -> None:
    engine: AsyncEngine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def require_showcase(settings: Settings = Depends(get_settings_dep)) -> Settings:
    if not settings.showcase_enabled:
        raise HTTPException(status_code=404, detail="Showcase is disabled")
    return settings


def parse_as_of(value: str | None) -> datetime:
    if value is None or value.strip() == "":
        return END_AT
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="as_of must be a timezone-aware ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise HTTPException(
            status_code=422, detail="as_of must be a timezone-aware ISO-8601 timestamp"
        )
    return parsed


def as_of_query(as_of: str | None = Query(default=None)) -> datetime:
    return parse_as_of(as_of)


async def get_queries(request: Request) -> AsyncIterator[PostgresShowcaseQueries]:
    factory: async_sessionmaker = request.app.state.session_factory
    async with factory() as session:
        yield PostgresShowcaseQueries(session)


async def get_as_of_queries(
    request: Request,
    as_of: datetime = Depends(as_of_query),
) -> AsyncIterator[tuple[datetime, PostgresShowcaseQueries]]:
    factory: async_sessionmaker = request.app.state.session_factory
    async with factory() as session:
        yield as_of, PostgresShowcaseQueries(session)


def get_uow(request: Request) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(request.app.state.session_factory)


async def get_lag_queries(request: Request) -> AsyncIterator[PostgresProjectionLagQueries]:
    factory: async_sessionmaker = request.app.state.session_factory
    async with factory() as session:
        yield PostgresProjectionLagQueries(session)
