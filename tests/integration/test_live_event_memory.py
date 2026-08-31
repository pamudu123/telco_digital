"""Live capability-03 checks; skipped when provider configuration is absent."""

import os
from datetime import datetime

import pytest

from telco_digital.config import get_settings
from telco_digital.infrastructure.postgres.event_memory import PostgresEventMemoryQueries
from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory
from telco_digital.intelligence.event_memory import EventMemoryService, MatchRank

pytestmark = pytest.mark.integration

AUGUST = datetime.fromisoformat("2026-08-20T12:00:00+00:00")


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL is required")
@pytest.mark.asyncio
async def test_live_event_memory_retrieves_u001_singapore_history() -> None:
    engine = create_engine(get_settings())
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            result = await EventMemoryService(PostgresEventMemoryQueries(session)).recall(
                "U001", AUGUST, destination="SG"
            )
    finally:
        await engine.dispose()

    assert result.customer_ref == "U001"
    assert result.historical_episodes
    top = result.matches[0]
    assert top.rank == MatchRank.SAME_CUSTOMER_SAME_SITUATION
    assert top.episode.destination == "SG"
