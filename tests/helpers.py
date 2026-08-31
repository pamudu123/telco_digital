from datetime import datetime, timedelta
from decimal import Decimal

from telco_digital.intelligence.features import CustomerFeatures, GraphFeatures
from telco_digital.intelligence.features.service import FeatureGroup


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def features_from_uow(uow, customer_ref: str, as_of: datetime) -> CustomerFeatures:
    customer = await uow.customers.get_by_ref(customer_ref)
    start_30 = as_of - timedelta(days=30)
    start_60 = as_of - timedelta(days=60)
    start_90 = as_of - timedelta(days=90)
    start_365 = as_of - timedelta(days=365)
    usage = [
        row
        for row in await uow.usage_events.list_as_of(customer.id, as_of)
        if row.occurred_at >= start_90
    ]
    usage_30 = [row for row in usage if row.occurred_at >= start_30]
    previous = [row for row in usage if start_60 <= row.occurred_at < start_30]
    current_mb = float(sum((row.data_mb for row in usage_30), Decimal("0")))
    previous_mb = float(sum((row.data_mb for row in previous), Decimal("0")))
    recharges = [
        row
        for row in await uow.recharges.list_as_of(customer.id, as_of)
        if row.occurred_at >= start_90
    ]
    recharge_30 = [row for row in recharges if row.occurred_at >= start_30]
    small = sum(row.amount <= Decimal("500") for row in recharge_30)
    service = [
        row
        for row in await uow.service_interactions.list_by_customer(customer.id)
        if start_90 <= row.occurred_at <= as_of
    ]
    travels = [
        row
        for row in await uow.travels.list_as_of(customer.id, as_of)
        if row.started_at >= start_365
    ]
    roam = sum(
        max(
            0,
            (
                (row.ended_at if row.ended_at and row.ended_at <= as_of else as_of) - row.started_at
            ).days,
        )
        for row in travels
    )
    subscriptions = [
        row
        for row in await uow.subscriptions.list_by_customer(customer.id)
        if row.started_at <= as_of and row.started_at >= start_365
    ]
    change = None if previous_mb == 0 else round((current_mb - previous_mb) / previous_mb, 6)
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
                    "data_mb_30d": current_mb,
                    "data_mb_90d": float(sum((row.data_mb for row in usage), Decimal("0"))),
                    "data_mb_change_ratio": change,
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
                    "small_recharge_count_30d": small,
                    "frequent_small_recharge_evidence": small >= 3,
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
            "travel": FeatureGroup(
                window_days=365,
                values={"trip_count_365d": len(travels), "roaming_days_365d": roam},
            ),
        },
        graph=GraphFeatures(available=False, values={}),
        provenance=("in-memory seed facts",),
    )
