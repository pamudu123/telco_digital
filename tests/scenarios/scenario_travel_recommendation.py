"""Scenario: historical Singapore trip is retrieved for a later Singapore situation."""

from datetime import datetime

import pytest

from telco_digital.application.commands.commands import RecordTravelCommand
from telco_digital.application.seed import seed_demo_customers
from telco_digital.application.services.travel import record_travel
from telco_digital.domain.enums import PlanType
from telco_digital.intelligence.event_memory import EventMemoryService, MatchRank
from telco_digital.intelligence.event_memory.uow import UnitOfWorkEventMemoryQueries
from telco_digital.intelligence.recommendations import (
    DecisionMode,
    PlanRepositoryCatalogue,
    RecommendationService,
)

AUGUST = datetime.fromisoformat("2026-08-20T12:00:00+00:00")


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_march_singapore_episode_is_retrieved_for_later_trip(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    await record_travel(
        uow,
        RecordTravelCommand(
            customer_ref="U001",
            country="Singapore",
            started_at=AUGUST,
            correlation_id="scenario-u001-august",
        ),
        clock=clock,
    )

    context = await EventMemoryService(UnitOfWorkEventMemoryQueries(uow)).recall("U001", AUGUST)

    assert context.current_situation.destination == "SG"
    assert context.current_situation.duration_known is False
    assert context.matches
    top = context.matches[0]
    assert top.rank == MatchRank.SAME_CUSTOMER_SAME_SITUATION
    assert top.episode.destination_name == "Singapore"
    assert top.episode.duration_days == 6
    assert top.episode.metrics["usage_gb"] == 11.4
    assert top.episode.actions["plan_selected"] == "ROAM_15"
    assert top.episode.outcome == "No additional package required"
    assert any("duration is unknown" in item for item in context.unknowns)


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_query_destination_retrieves_history_without_open_trip(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    context = await EventMemoryService(UnitOfWorkEventMemoryQueries(uow)).recall(
        "U001", AUGUST, destination="SG"
    )
    assert context.current_situation.source == "query"
    assert context.matches[0].episode.actions["plan_selected"] == "ROAM_15"


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_u001_singapore_ranks_roam_15_with_unknown_duration(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    document = await RecommendationService(
        EventMemoryService(UnitOfWorkEventMemoryQueries(uow)),
        PlanRepositoryCatalogue(uow.plans),
    ).recommend("U001", AUGUST, destination="SG")
    assert document.mode == DecisionMode.SCENARIO_BASED
    assert document.primary is not None
    assert document.primary.plan_code == "ROAM_15"
    assert [item.plan_code for item in document.ranked[:3]][0] == "ROAM_15"
    assert {item.plan_code for item in document.ranked} == {"ROAM_5", "ROAM_15", "ROAM_30"}
    roam = await uow.plans.list_active(plan_type=PlanType.ROAMING, country_code="SG")
    assert {plan.plan_code for plan in roam} == {item.plan_code for item in document.ranked}
