"""Scenario: U002 repeated small recharges yield PRICE_SENSITIVE."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from telco_digital.application.seed import seed_demo_customers
from telco_digital.intelligence.behaviour import build_behaviour
from telco_digital.intelligence.event_memory import EventMemoryService
from telco_digital.intelligence.event_memory.uow import UnitOfWorkEventMemoryQueries
from telco_digital.intelligence.features import CustomerFeatures, GraphFeatures
from telco_digital.intelligence.features.service import FeatureGroup

AS_OF = datetime.fromisoformat("2026-08-21T00:00:00+00:00")


async def _features_from_uow(uow, customer_ref: str, as_of: datetime) -> CustomerFeatures:
    customer = await uow.customers.get_by_ref(customer_ref)
    window_start = as_of - timedelta(days=30)
    recharges = [
        row
        for row in await uow.recharges.list_as_of(customer.id, as_of)
        if row.occurred_at >= window_start
    ]
    small = sum(row.amount <= Decimal("500") for row in recharges)
    amount = sum((row.amount for row in recharges), Decimal("0"))
    travels = list(await uow.travels.list_as_of(customer.id, as_of))
    roam_days = 0
    for row in travels:
        end = row.ended_at if row.ended_at and row.ended_at <= as_of else as_of
        roam_days += max(0, (end - row.started_at).days)
    return CustomerFeatures(
        customer_id=customer.id,
        customer_ref=customer.customer_ref,
        as_of=as_of,
        computed_at=as_of,
        temporal={
            "recharge": FeatureGroup(
                window_days=30,
                values={
                    "small_recharge_count_30d": small,
                    "frequent_small_recharge_evidence": small >= 3,
                    "amount_30d": float(amount),
                },
            ),
            "travel": FeatureGroup(
                window_days=365,
                values={"trip_count_365d": len(travels), "roaming_days_365d": roam_days},
            ),
        },
        graph=GraphFeatures(available=False, values={}),
        provenance=("in-memory seed facts",),
    )


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_u002_seed_recharges_yield_price_sensitive(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    features = await _features_from_uow(uow, "U002", AS_OF)
    document = build_behaviour(features)
    traits = {item.trait: item for item in document.traits}
    assert "PRICE_SENSITIVE" in traits
    assert traits["PRICE_SENSITIVE"].evidence["small_recharge_count_30d"] == 5


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_u001_seed_travel_supports_traveller_trait(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    features = await _features_from_uow(uow, "U001", AS_OF)
    recalled = await EventMemoryService(UnitOfWorkEventMemoryQueries(uow)).recall(
        "U001", AS_OF, destination="SG"
    )
    document = build_behaviour(features, recalled.historical_episodes)
    traits = {item.trait for item in document.traits}
    assert "FREQUENT_TRAVELLER" in traits
    assert "HEAVY_DATA_USER" in traits
