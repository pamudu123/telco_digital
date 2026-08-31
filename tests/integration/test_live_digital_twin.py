"""Live capability-09 checks; skipped when provider configuration is absent."""

import os
from datetime import datetime

import pytest

from telco_digital.config import get_settings
from telco_digital.infrastructure.postgres.event_memory import PostgresEventMemoryQueries
from telco_digital.infrastructure.postgres.features import PostgresTemporalFeatureQueries
from telco_digital.infrastructure.postgres.repositories import SqlPlanRepository
from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory
from telco_digital.infrastructure.postgres.unit_of_work import SqlAlchemyUnitOfWork
from telco_digital.intelligence.digital_twin import DigitalTwinService, UnitOfWorkStateReader
from telco_digital.intelligence.event_memory import EventMemoryService
from telco_digital.intelligence.features import (
    CustomerFeatureService,
    GraphFeatureService,
    TemporalFeatureService,
)
from telco_digital.intelligence.features.service import GraphFeatures
from telco_digital.intelligence.recommendations import PlanRepositoryCatalogue

pytestmark = pytest.mark.integration

AS_OF = datetime.fromisoformat("2026-08-20T12:00:00+00:00")


class _UnavailableGraph:
    async def calculate(self, customer_ref: str, as_of: datetime) -> GraphFeatures:
        return GraphFeatures(
            available=False,
            values={},
            unknowns=("Live twin test does not require Neo4j.",),
        )


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL is required")
@pytest.mark.asyncio
async def test_live_customer_twin_ranks_u001_roam_15() -> None:
    engine = create_engine(get_settings())
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            uow = SqlAlchemyUnitOfWork(session)
            features = CustomerFeatureService(
                TemporalFeatureService(PostgresTemporalFeatureQueries(session)),
                GraphFeatureService(_UnavailableGraph()),
            )
            result = await DigitalTwinService(
                UnitOfWorkStateReader(uow),
                features,
                EventMemoryService(PostgresEventMemoryQueries(session)),
                PlanRepositoryCatalogue(SqlPlanRepository(session)),
            ).build("U001", AS_OF, destination="SG")
    finally:
        await engine.dispose()

    assert result.customer_ref == "U001"
    assert result.historical.top_plan == "ROAM_15"
    assert result.recommended.primary_plan_code == "ROAM_15"
    assert result.source == "derived_live"
