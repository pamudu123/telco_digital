"""Scenario: computed twins compose seed facts without becoming a table."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from telco_digital.application.commands.commands import GetCustomerStateQuery
from telco_digital.application.seed import seed_demo_customers
from telco_digital.application.services.customer_state import get_customer_state
from telco_digital.intelligence.behaviour import build_behaviour
from telco_digital.intelligence.churn import score_churn
from telco_digital.intelligence.digital_twin import assemble_customer_twin
from telco_digital.intelligence.event_memory import EventMemoryService
from telco_digital.intelligence.event_memory.uow import UnitOfWorkEventMemoryQueries
from telco_digital.intelligence.features import CustomerFeatures, GraphFeatures
from telco_digital.intelligence.features.service import FeatureGroup
from telco_digital.intelligence.recommendations import (
    DecisionMode,
    PlanRepositoryCatalogue,
    build_recommendation,
)

AUGUST = datetime.fromisoformat("2026-08-20T12:00:00+00:00")


async def _features_from_uow(uow, customer_ref: str, as_of: datetime) -> CustomerFeatures:
    customer = await uow.customers.get_by_ref(customer_ref)
    start_30 = as_of - timedelta(days=30)
    start_90 = as_of - timedelta(days=90)
    usage = [
        row
        for row in await uow.usage_events.list_as_of(customer.id, as_of)
        if row.occurred_at >= start_90
    ]
    usage_30 = [row for row in usage if row.occurred_at >= start_30]
    recharges = [
        row
        for row in await uow.recharges.list_as_of(customer.id, as_of)
        if row.occurred_at >= start_90
    ]
    recharge_30 = [row for row in recharges if row.occurred_at >= start_30]
    travels = list(await uow.travels.list_as_of(customer.id, as_of))
    return CustomerFeatures(
        customer_id=customer.id,
        customer_ref=customer.customer_ref,
        as_of=as_of,
        computed_at=as_of,
        temporal={
            "usage": FeatureGroup(
                window_days=30,
                values={
                    "data_mb_30d": float(sum((row.data_mb for row in usage_30), Decimal("0"))),
                    "data_mb_90d": float(sum((row.data_mb for row in usage), Decimal("0"))),
                },
            ),
            "recharge": FeatureGroup(
                window_days=30,
                values={
                    "count_30d": len(recharge_30),
                    "amount_30d": float(sum((row.amount for row in recharge_30), Decimal("0"))),
                },
            ),
            "travel": FeatureGroup(
                window_days=365,
                values={"trip_count_365d": len(travels), "roaming_days_365d": 6},
            ),
        },
        graph=GraphFeatures(available=False, values={}),
        provenance=("in-memory seed facts",),
        unknowns=("Neo4j graph features are unavailable; values are not assumed to be zero.",),
    )


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_u001_twin_retrieves_march_episode_and_roam_15(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    observed = await get_customer_state(
        uow, GetCustomerStateQuery(customer_ref="U001", as_of=AUGUST)
    )
    context = await EventMemoryService(UnitOfWorkEventMemoryQueries(uow)).recall(
        "U001", AUGUST, destination="SG"
    )
    features = await _features_from_uow(uow, "U001", AUGUST)
    catalogue = await PlanRepositoryCatalogue(uow.plans).list_roaming(country_code="SG")
    twin = assemble_customer_twin(
        observed,
        features,
        context,
        build_behaviour(features, context.historical_episodes),
        score_churn(features),
        build_recommendation(context, catalogue),
    )
    assert twin.historical.top_plan == "ROAM_15"
    assert twin.historical.top_duration_days == 6
    assert twin.historical.top_usage_gb == 11.4
    assert twin.recommended.mode == DecisionMode.SCENARIO_BASED
    assert twin.recommended.primary_plan_code == "ROAM_15"
    assert {item.trait for item in twin.inferred.traits} >= {
        "FREQUENT_TRAVELLER",
        "HEAVY_DATA_USER",
    }
    assert twin.customer_context.current_situation.duration_known is False
    assert any("not persisted" in item.lower() for item in twin.provenance)
