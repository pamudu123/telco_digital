"""SQLAlchemy point-in-time customer feature queries."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telco_digital.infrastructure.postgres.models import (
    CampaignInteractionModel,
    CustomerModel,
    LoyaltyLedgerModel,
    MoneyTransactionModel,
    PlanModel,
    RechargeModel,
    ServiceInteractionModel,
    SubscriptionModel,
    TravelModel,
    UsageEventModel,
)


def _sum(rows: list, field: str) -> float:
    return float(sum((getattr(row, field) or Decimal(0) for row in rows), Decimal(0)))


def _change(current: float, previous: float) -> float | None:
    return None if previous == 0 else round((current - previous) / previous, 6)


class PostgresTemporalFeatureQueries:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _rows(self, model, customer_id: UUID, time_field, start, as_of):
        result = await self.session.execute(
            select(model).where(
                model.customer_id == customer_id,
                time_field >= start,
                time_field <= as_of,
            )
        )
        return list(result.scalars())

    async def calculate(self, customer_ref: str, as_of: datetime) -> tuple[UUID, dict]:
        customer = await self.session.scalar(
            select(CustomerModel).where(CustomerModel.customer_ref == customer_ref)
        )
        if customer is None:
            raise LookupError(f"Unknown customer: {customer_ref}")
        d30, d60, d90, d365 = (
            as_of - timedelta(days=30),
            as_of - timedelta(days=60),
            as_of - timedelta(days=90),
            as_of - timedelta(days=365),
        )
        usage90 = await self._rows(
            UsageEventModel, customer.id, UsageEventModel.occurred_at, d90, as_of
        )
        current_usage = [row for row in usage90 if row.occurred_at >= d30]
        previous_usage = [row for row in usage90 if d60 <= row.occurred_at < d30]
        current_mb, previous_mb = _sum(current_usage, "data_mb"), _sum(previous_usage, "data_mb")

        recharges = await self._rows(
            RechargeModel, customer.id, RechargeModel.occurred_at, d90, as_of
        )
        recharge30 = [row for row in recharges if row.occurred_at >= d30]
        money = await self._rows(
            MoneyTransactionModel, customer.id, MoneyTransactionModel.occurred_at, d90, as_of
        )
        merchant_ids = {row.merchant_id for row in money if row.merchant_id is not None}

        subscriptions = list(
            (
                await self.session.execute(
                    select(SubscriptionModel, PlanModel)
                    .join(PlanModel, PlanModel.id == SubscriptionModel.plan_id)
                    .where(
                        SubscriptionModel.customer_id == customer.id,
                        SubscriptionModel.started_at <= as_of,
                    )
                    .order_by(SubscriptionModel.started_at.desc())
                )
            ).all()
        )
        current_plan = next(
            (
                plan
                for subscription, plan in subscriptions
                if subscription.ended_at is None or subscription.ended_at > as_of
            ),
            None,
        )
        travels = await self._rows(TravelModel, customer.id, TravelModel.started_at, d365, as_of)
        roaming_days = sum(
            max(
                0,
                (
                    (row.ended_at if row.ended_at and row.ended_at <= as_of else as_of)
                    - row.started_at
                ).days,
            )
            for row in travels
        )
        service = await self._rows(
            ServiceInteractionModel,
            customer.id,
            ServiceInteractionModel.occurred_at,
            d90,
            as_of,
        )
        loyalty = await self._rows(
            LoyaltyLedgerModel, customer.id, LoyaltyLedgerModel.occurred_at, d90, as_of
        )
        campaigns = await self._rows(
            CampaignInteractionModel,
            customer.id,
            CampaignInteractionModel.occurred_at,
            d90,
            as_of,
        )
        conversions = sum(row.interaction_type == "CONVERTED" for row in campaigns)
        exposures = sum(
            row.interaction_type in {"RECEIVED", "OPENED", "CLICKED", "CONVERTED"}
            for row in campaigns
        )
        loyalty_net = sum(
            row.points if row.entry_type == "EARN" else -row.points for row in loyalty
        )
        return customer.id, {
            "usage": {
                "window_days": 30,
                "values": {
                    "event_count_30d": len(current_usage),
                    "event_count_90d": len(usage90),
                    "data_mb_30d": current_mb,
                    "data_mb_90d": _sum(usage90, "data_mb"),
                    "data_mb_previous_30d": previous_mb,
                    "data_mb_change_ratio": _change(current_mb, previous_mb),
                },
            },
            "recharge": {
                "window_days": 30,
                "values": {
                    "count_30d": len(recharge30),
                    "amount_30d": _sum(recharge30, "amount"),
                    "average_90d": round(_sum(recharges, "amount") / len(recharges), 4)
                    if recharges
                    else None,
                    "small_recharge_count_30d": sum(row.amount <= 500 for row in recharge30),
                    "frequent_small_recharge_evidence": sum(row.amount <= 500 for row in recharge30)
                    >= 3,
                },
            },
            "money": {
                "window_days": 90,
                "values": {
                    "transaction_count_90d": len(money),
                    "spend_90d": _sum(money, "amount"),
                    "unique_merchants_90d": len(merchant_ids),
                },
            },
            "plan": {
                "values": {
                    "current_plan_code": current_plan.plan_code if current_plan else None,
                    "subscription_count_365d": sum(
                        subscription.started_at >= d365 for subscription, _ in subscriptions
                    ),
                }
            },
            "travel": {
                "window_days": 365,
                "values": {
                    "trip_count_365d": len(travels),
                    "roaming_days_365d": roaming_days,
                    "currently_travelling": any(
                        row.started_at <= as_of and (row.ended_at is None or row.ended_at > as_of)
                        for row in travels
                    ),
                },
            },
            "service": {
                "window_days": 90,
                "values": {
                    "interaction_count_90d": len(service),
                    "complaint_count_90d": sum(
                        row.interaction_type == "COMPLAINT" for row in service
                    ),
                    "open_count": sum(
                        row.status == "OPEN"
                        and (row.resolved_at is None or row.resolved_at > as_of)
                        for row in service
                    ),
                },
            },
            "loyalty": {
                "window_days": 90,
                "values": {"entry_count_90d": len(loyalty), "net_points_90d": loyalty_net},
            },
            "campaign": {
                "window_days": 90,
                "values": {
                    "interaction_count_90d": len(campaigns),
                    "exposure_count_90d": exposures,
                    "conversion_count_90d": conversions,
                    "conversion_rate_90d": round(conversions / exposures, 6) if exposures else None,
                },
            },
        }
