"""PostgreSQL reads for travel episode reconstruction. SQL stays here."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from telco_digital.application.services.common import NotFoundError
from telco_digital.infrastructure.postgres.models import (
    CustomerModel,
    PlanModel,
    SubscriptionModel,
    TravelModel,
    UsageEventModel,
)
from telco_digital.intelligence.event_memory.service import (
    CustomerTravelFacts,
    RawSubscription,
    RawTravel,
    RawUsage,
)


@dataclass
class _CustomerFactRows:
    travels: list[TravelModel] = field(default_factory=list)
    usage: list[UsageEventModel] = field(default_factory=list)
    subscriptions: list[tuple[SubscriptionModel, PlanModel]] = field(default_factory=list)


class PostgresEventMemoryQueries:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _customer(self, customer_ref: str) -> CustomerModel:
        customer = await self.session.scalar(
            select(CustomerModel).where(CustomerModel.customer_ref == customer_ref)
        )
        if customer is None:
            raise NotFoundError(f"Unknown customer: {customer_ref}")
        return customer

    def _facts(
        self,
        customer: CustomerModel,
        travels: list[TravelModel],
        usage: list[UsageEventModel],
        subscription_rows: list[tuple[SubscriptionModel, PlanModel]],
    ) -> CustomerTravelFacts:
        return CustomerTravelFacts(
            customer_id=customer.id,
            customer_ref=customer.customer_ref,
            travels=tuple(
                RawTravel(
                    id=row.id,
                    customer_id=customer.id,
                    customer_ref=customer.customer_ref,
                    destination=row.country_code,
                    started_at=row.started_at,
                    ended_at=row.ended_at,
                )
                for row in travels
            ),
            usage=tuple(
                RawUsage(
                    customer_id=row.customer_id,
                    occurred_at=row.occurred_at,
                    data_mb=row.data_mb,
                    country_code=row.country_code,
                )
                for row in usage
            ),
            subscriptions=tuple(
                RawSubscription(
                    customer_id=customer.id,
                    plan_code=plan.plan_code,
                    plan_type=plan.plan_type,
                    plan_data_mb=plan.data_mb,
                    plan_country=plan.country_code,
                    started_at=subscription.started_at,
                    ended_at=subscription.ended_at,
                )
                for subscription, plan in subscription_rows
            ),
        )

    async def _bundle(self, customer: CustomerModel, as_of: datetime) -> CustomerTravelFacts:
        grouped = await self._facts_for_customers([customer.id], as_of)
        rows = grouped[customer.id]
        return self._facts(customer, rows.travels, rows.usage, rows.subscriptions)

    async def _peer_customer_ids(
        self,
        *,
        exclude_customer_id: UUID,
        destination: str | None,
        as_of: datetime,
        limit: int,
    ) -> list[UUID]:
        stmt = select(TravelModel.customer_id).where(
            TravelModel.customer_id != exclude_customer_id,
            TravelModel.started_at <= as_of,
        )
        if destination is not None:
            stmt = stmt.where(TravelModel.country_code == destination)
        rows = await self.session.scalars(
            stmt.group_by(TravelModel.customer_id)
            .order_by(func.max(TravelModel.started_at).desc())
            .limit(limit)
        )
        return list(rows)

    async def _facts_for_customers(
        self, customer_ids: list[UUID], as_of: datetime
    ) -> dict[UUID, _CustomerFactRows]:
        grouped = {customer_id: _CustomerFactRows() for customer_id in customer_ids}
        if not customer_ids:
            return grouped

        travel_rows = list(
            (
                await self.session.scalars(
                    select(TravelModel).where(
                        TravelModel.customer_id.in_(customer_ids),
                        TravelModel.started_at <= as_of,
                    )
                )
            ).all()
        )
        usage_rows = list(
            (
                await self.session.scalars(
                    select(UsageEventModel).where(
                        UsageEventModel.customer_id.in_(customer_ids),
                        UsageEventModel.occurred_at <= as_of,
                    )
                )
            ).all()
        )
        subscription_rows = (
            await self.session.execute(
                select(SubscriptionModel, PlanModel)
                .join(PlanModel, PlanModel.id == SubscriptionModel.plan_id)
                .where(
                    SubscriptionModel.customer_id.in_(customer_ids),
                    SubscriptionModel.started_at <= as_of,
                )
            )
        ).all()

        travels_by: dict[UUID, list[TravelModel]] = defaultdict(list)
        for row in travel_rows:
            travels_by[row.customer_id].append(row)
        usage_by: dict[UUID, list[UsageEventModel]] = defaultdict(list)
        for row in usage_rows:
            usage_by[row.customer_id].append(row)
        subscriptions_by: dict[UUID, list[tuple[SubscriptionModel, PlanModel]]] = defaultdict(list)
        for subscription, plan in subscription_rows:
            subscriptions_by[subscription.customer_id].append((subscription, plan))

        for customer_id in customer_ids:
            grouped[customer_id] = _CustomerFactRows(
                travels=travels_by[customer_id],
                usage=usage_by[customer_id],
                subscriptions=subscriptions_by[customer_id],
            )
        return grouped

    async def load_customer(self, customer_ref: str, as_of: datetime) -> CustomerTravelFacts:
        customer = await self._customer(customer_ref)
        return await self._bundle(customer, as_of)

    async def load_peers(
        self,
        *,
        exclude_customer_id: UUID,
        destination: str | None,
        as_of: datetime,
        limit: int = 25,
    ) -> tuple[CustomerTravelFacts, ...]:
        peer_ids = await self._peer_customer_ids(
            exclude_customer_id=exclude_customer_id,
            destination=destination,
            as_of=as_of,
            limit=limit,
        )
        if not peer_ids:
            return ()
        customers = {
            row.id: row
            for row in (
                await self.session.scalars(
                    select(CustomerModel).where(CustomerModel.id.in_(peer_ids))
                )
            ).all()
        }
        facts = await self._facts_for_customers(peer_ids, as_of)
        bundles: list[CustomerTravelFacts] = []
        for customer_id in peer_ids:
            customer = customers.get(customer_id)
            if customer is None:
                continue
            rows = facts[customer_id]
            bundles.append(self._facts(customer, rows.travels, rows.usage, rows.subscriptions))
        return tuple(bundles)
