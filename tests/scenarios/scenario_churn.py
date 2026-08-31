"""Scenario: U004 declining engagement scores HIGH churn with drivers."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from telco_digital.application.seed import seed_demo_customers
from telco_digital.intelligence.churn import score_churn
from telco_digital.intelligence.features import CustomerFeatures, GraphFeatures
from telco_digital.intelligence.features.service import FeatureGroup

AS_OF = datetime.fromisoformat("2026-08-21T00:00:00+00:00")


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
    service = [
        row
        for row in await uow.service_interactions.list_by_customer(customer.id)
        if row.occurred_at <= as_of and row.occurred_at >= start_90
    ]
    subscriptions = [
        row
        for row in await uow.subscriptions.list_by_customer(customer.id)
        if row.started_at <= as_of and row.started_at >= as_of - timedelta(days=365)
    ]
    return CustomerFeatures(
        customer_id=customer.id,
        customer_ref=customer.customer_ref,
        as_of=as_of,
        computed_at=as_of,
        temporal={
            "usage": FeatureGroup(
                window_days=30,
                values={
                    "event_count_30d": len(usage_30),
                    "data_mb_30d": float(sum((row.data_mb for row in usage_30), Decimal("0"))),
                    "data_mb_90d": float(sum((row.data_mb for row in usage), Decimal("0"))),
                    "data_mb_change_ratio": None,
                },
            ),
            "recharge": FeatureGroup(
                window_days=30,
                values={
                    "count_30d": len(recharge_30),
                    "amount_30d": float(sum((row.amount for row in recharge_30), Decimal("0"))),
                    "average_90d": (
                        float(sum((row.amount for row in recharges), Decimal("0")) / len(recharges))
                        if recharges
                        else None
                    ),
                },
            ),
            "service": FeatureGroup(
                window_days=90,
                values={
                    "interaction_count_90d": len(service),
                    "complaint_count_90d": sum(
                        row.interaction_type == "COMPLAINT" for row in service
                    ),
                    "open_count": sum(row.status == "OPEN" for row in service),
                },
            ),
            "plan": FeatureGroup(
                window_days=365,
                values={"subscription_count_365d": len(subscriptions)},
            ),
        },
        graph=GraphFeatures(available=False, values={}),
        provenance=("in-memory seed facts",),
    )


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_u004_seed_scores_high_churn(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    features = await _features_from_uow(uow, "U004", AS_OF)
    document = score_churn(features)
    assert document.risk_band == "HIGH"
    assert document.feature_snapshot["data_mb_30d"] == 200.0
    assert document.feature_snapshot["complaint_count_90d"] == 1.0
    assert document.feature_snapshot["open_ticket_count"] == 2.0
    assert document.drivers
    assert document.source == "derived_live"


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_u003_seed_stays_low_churn(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    features = await _features_from_uow(uow, "U003", AS_OF)
    document = score_churn(features)
    assert document.risk_band == "LOW"
