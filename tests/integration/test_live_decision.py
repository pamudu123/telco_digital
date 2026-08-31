"""Live capability-10/11 checks; skipped when provider configuration is absent."""

import os
from datetime import datetime

import pytest

from telco_digital.api.stack import copilot_service, decision_engine
from telco_digital.config import get_settings
from telco_digital.decisioning import DecisionAction
from telco_digital.infrastructure.postgres.session import create_engine, create_session_factory

pytestmark = pytest.mark.integration

AS_OF = datetime.fromisoformat("2026-08-20T12:00:00+00:00")


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL is required")
@pytest.mark.asyncio
async def test_live_decision_u001_presents_roam_15() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            result = await decision_engine(session, settings).evaluate(
                "U001", AS_OF, destination="SG"
            )
    finally:
        await engine.dispose()
    assert result.action == DecisionAction.PRESENT_OFFER
    assert result.target_plan_code == "ROAM_15"


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL is required")
@pytest.mark.asyncio
async def test_live_copilot_fallback_mentions_roam_15() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            result = await copilot_service(session, settings).answer(
                "Why is U001 receiving this recommendation?",
                "U001",
                AS_OF,
                destination="SG",
            )
    finally:
        await engine.dispose()
    assert "ROAM_15" in result.answer
    assert "FAKE_PLAN" not in result.answer
