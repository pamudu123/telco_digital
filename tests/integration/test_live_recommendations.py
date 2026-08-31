"""Live capability-06 checks; skipped when provider configuration is absent."""

import os
from datetime import datetime

import pytest

from telco_digital.config import get_settings
from telco_digital.infrastructure.postgres.event_memory import PostgresEventMemoryQueries
from telco_digital.infrastructure.postgres.repositories import SqlPlanRepository
from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory
from telco_digital.intelligence.event_memory import EventMemoryService
from telco_digital.intelligence.recommendations import (
    DecisionMode,
    PlanRepositoryCatalogue,
    RecommendationService,
)

pytestmark = pytest.mark.integration

AS_OF = datetime.fromisoformat("2026-08-20T12:00:00+00:00")


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL is required")
@pytest.mark.asyncio
async def test_live_recommendations_rank_u001_roam_15() -> None:
    engine = create_engine(get_settings())
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            result = await RecommendationService(
                EventMemoryService(PostgresEventMemoryQueries(session)),
                PlanRepositoryCatalogue(SqlPlanRepository(session)),
            ).recommend("U001", AS_OF, destination="SG")
    finally:
        await engine.dispose()

    assert result.customer_ref == "U001"
    assert result.mode == DecisionMode.SCENARIO_BASED
    assert result.primary is not None
    assert result.primary.plan_code == "ROAM_15"
