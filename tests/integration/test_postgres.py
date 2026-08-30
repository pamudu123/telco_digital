"""PostgreSQL integration tests. Skipped unless DATABASE_URL is configured."""

import os

import pytest
from sqlalchemy import inspect, text

from telco_digital.config import get_settings
from telco_digital.infrastructure.postgres.models import SCHEMAS
from telco_digital.infrastructure.postgres.session import create_engine

pytestmark = pytest.mark.integration

requires_postgres = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not exported — configure PostgreSQL before running integration tests",
)


@requires_postgres
@pytest.mark.asyncio
async def test_postgres_has_locked_schema() -> None:
    engine = create_engine(get_settings())

    try:
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT 1")) == 1
            schemas = await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).get_schema_names()
            )
            revision = await connection.scalar(
                text("SELECT version_num FROM public.alembic_version")
            )
    finally:
        await engine.dispose()

    assert set(SCHEMAS).issubset(schemas)
    assert revision == "0002_poc_query_indexes"
