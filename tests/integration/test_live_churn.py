"""Live capability-05 checks; skipped when provider configuration is absent."""

import os
from datetime import datetime

import pytest

from telco_digital.config import get_settings
from telco_digital.infrastructure.neo4j.features import Neo4jFeatureQueries
from telco_digital.infrastructure.postgres.features import PostgresTemporalFeatureQueries
from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory
from telco_digital.intelligence.churn import ChurnService
from telco_digital.intelligence.features import (
    CustomerFeatureService,
    GraphFeatureService,
    TemporalFeatureService,
)

pytestmark = pytest.mark.integration

AS_OF = datetime.fromisoformat("2026-08-21T00:00:00+00:00")


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL is required")
@pytest.mark.asyncio
async def test_live_churn_marks_u004_high_risk() -> None:
    engine = create_engine(get_settings())
    factory = create_session_factory(engine)
    settings = get_settings()
    try:
        async with factory() as session:
            result = await ChurnService(
                CustomerFeatureService(
                    TemporalFeatureService(PostgresTemporalFeatureQueries(session)),
                    GraphFeatureService(Neo4jFeatureQueries(settings)),
                )
            ).predict("U004", AS_OF)
    finally:
        await engine.dispose()

    assert result.customer_ref == "U004"
    assert result.risk_band == "HIGH"
    assert result.drivers
