"""Live capability-04 checks; skipped when provider configuration is absent."""

import os
from datetime import datetime

import pytest

from telco_digital.config import get_settings
from telco_digital.infrastructure.neo4j.features import Neo4jFeatureQueries
from telco_digital.infrastructure.postgres.event_memory import PostgresEventMemoryQueries
from telco_digital.infrastructure.postgres.features import PostgresTemporalFeatureQueries
from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory
from telco_digital.intelligence.behaviour import BehaviourService
from telco_digital.intelligence.event_memory import EventMemoryService
from telco_digital.intelligence.features import (
    CustomerFeatureService,
    GraphFeatureService,
    TemporalFeatureService,
)

pytestmark = pytest.mark.integration

AS_OF = datetime.fromisoformat("2026-08-21T00:00:00+00:00")


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL is required")
@pytest.mark.asyncio
async def test_live_behaviour_marks_u002_price_sensitive() -> None:
    engine = create_engine(get_settings())
    factory = create_session_factory(engine)
    settings = get_settings()
    try:
        async with factory() as session:
            result = await BehaviourService(
                CustomerFeatureService(
                    TemporalFeatureService(PostgresTemporalFeatureQueries(session)),
                    GraphFeatureService(Neo4jFeatureQueries(settings)),
                ),
                EventMemoryService(PostgresEventMemoryQueries(session)),
            ).evaluate("U002", AS_OF)
    finally:
        await engine.dispose()

    assert result.customer_ref == "U002"
    assert any(item.trait == "PRICE_SENSITIVE" for item in result.traits)
