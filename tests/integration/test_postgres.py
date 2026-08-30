"""PostgreSQL integration tests. Skipped unless DATABASE_URL is reachable."""

import os

import pytest

pytestmark = pytest.mark.integration

requires_postgres = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set — start docker compose to run Milestone 1 against Postgres",
)


@requires_postgres
@pytest.mark.asyncio
async def test_postgres_not_configured_here() -> None:
    pytest.skip("Wired in Milestone 1 follow-up once local Postgres is running")
