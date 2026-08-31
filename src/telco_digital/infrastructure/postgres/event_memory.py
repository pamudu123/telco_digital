"""PostgreSQL reads for travel episode reconstruction. SQL stays here."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
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

    async def _bundle(self, customer: CustomerModel, as_of: datetime) -> CustomerTravelFacts:
        travels = list(
            (
                await self.session.scalars(
                    select(TravelModel).where(
                        TravelModel.customer_id == customer.id,
                        TravelModel.started_at <= as_of,
                    )
                )
            ).all()
        )
        usage = list(
            (
                await self.session.scalars(
                    select(UsageEventModel).where(
                        UsageEventModel.customer_id == customer.id,
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
                    SubscriptionModel.customer_id == customer.id,
                    SubscriptionModel.started_at <= as_of,
                )
            )
        ).all()
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
        query = (
            select(TravelModel, CustomerModel)
            .join(CustomerModel, CustomerModel.id == TravelModel.customer_id)
            .where(
                TravelModel.customer_id != exclude_customer_id,
                TravelModel.started_at <= as_of,
            )
            .order_by(TravelModel.started_at.desc())
        )
        if destination is not None:
            query = query.where(TravelModel.country_code == destination)
        rows = (await self.session.execute(query.limit(limit))).all()
        customers = {customer.id: customer for _, customer in rows}
        bundles: list[CustomerTravelFacts] = []
        for customer in customers.values():
            bundles.append(await self._bundle(customer, as_of))
        return tuple(bundles)
