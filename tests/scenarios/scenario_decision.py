"""Scenario: decisions stay catalogue-safe and churn is not a discount."""

from datetime import datetime

import pytest
from tests.helpers import features_from_uow

from telco_digital.application.seed import seed_demo_customers
from telco_digital.copilot import CopilotService
from telco_digital.decisioning import DecisionAction, DecisionEngine
from telco_digital.intelligence.behaviour import BehaviourService
from telco_digital.intelligence.churn import ChurnService
from telco_digital.intelligence.event_memory import EventMemoryService
from telco_digital.intelligence.event_memory.uow import UnitOfWorkEventMemoryQueries
from telco_digital.intelligence.recommendations import (
    PlanRepositoryCatalogue,
    RecommendationService,
)

AUGUST = datetime.fromisoformat("2026-08-20T12:00:00+00:00")
CHURN_AS_OF = datetime.fromisoformat("2026-08-21T00:00:00+00:00")


class _UowFeatures:
    def __init__(self, uow) -> None:
        self.uow = uow

    async def calculate(self, customer_ref: str, as_of: datetime):
        return await features_from_uow(self.uow, customer_ref, as_of)


def _engine(uow) -> DecisionEngine:
    memory = EventMemoryService(UnitOfWorkEventMemoryQueries(uow))
    features = _UowFeatures(uow)
    return DecisionEngine(
        RecommendationService(memory, PlanRepositoryCatalogue(uow.plans)),
        BehaviourService(features, memory),
        ChurnService(features),
    )


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_u001_presents_roam_15(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    document = await _engine(uow).evaluate("U001", AUGUST, destination="SG")
    assert document.action == DecisionAction.PRESENT_OFFER
    assert document.target_plan_code == "ROAM_15"
    assert "HISTORICAL_EPISODE" in document.reason_codes
    assert "CATALOGUE_MATCH" in document.reason_codes
    assert "DURATION_UNKNOWN" in document.reason_codes


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_u004_support_follow_up_is_not_a_discount(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    document = await _engine(uow).evaluate("U004", CHURN_AS_OF)
    assert document.action == DecisionAction.SUPPORT_FOLLOW_UP
    assert document.target_plan_code is None
    text = f"{document.explanation.what} {document.explanation.why}".lower()
    assert "discount" in text
    assert "not" in text
    assert "20%" not in text
    assert "FAKE_PLAN" not in text


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_copilot_fallback_for_u001(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    answer = await CopilotService(_engine(uow)).answer(
        "Why is U001 receiving this recommendation?",
        "U001",
        AUGUST,
        destination="SG",
    )
    assert answer.source == "deterministic_fallback"
    assert "ROAM_15" in answer.answer
    assert "duration" in answer.answer.lower()
    assert "unknown" in answer.answer.lower()
    assert "FAKE_PLAN" not in answer.answer
