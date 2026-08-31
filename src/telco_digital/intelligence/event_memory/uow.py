"""Unit-of-work adapter for event memory. Uses repository abstractions, not SQL."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from telco_digital.application.services.common import NotFoundError
from telco_digital.application.unit_of_work.protocol import UnitOfWork
from telco_digital.intelligence.event_memory.service import (
    CustomerTravelFacts,
    RawSubscription,
    RawTravel,
    RawUsage,
)


class UnitOfWorkEventMemoryQueries:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def _bundle(self, customer, as_of: datetime) -> CustomerTravelFacts:
        travels = [
            RawTravel(
                id=travel.id,
                customer_id=customer.id,
                customer_ref=customer.customer_ref,
                destination=travel.country_code,
                started_at=travel.started_at,
                ended_at=travel.ended_at,
            )
            for travel in await self.uow.travels.list_as_of(customer.id, as_of)
        ]
        usage = [
            RawUsage(
                customer_id=row.customer_id,
                occurred_at=row.occurred_at,
                data_mb=row.data_mb,
                country_code=row.country_code,
            )
            for row in await self.uow.usage_events.list_as_of(customer.id, as_of)
        ]
        subscriptions: list[RawSubscription] = []
        for subscription in await self.uow.subscriptions.list_by_customer(customer.id):
            if subscription.started_at > as_of:
                continue
            plan = await self.uow.plans.get_by_id(subscription.plan_id)
            if plan is None:
                continue
            subscriptions.append(
                RawSubscription(
                    customer_id=customer.id,
                    plan_code=plan.plan_code,
                    plan_type=str(plan.plan_type),
                    plan_data_mb=plan.data_mb,
                    plan_country=plan.country_code,
                    started_at=subscription.started_at,
                    ended_at=subscription.ended_at,
                )
            )
        return CustomerTravelFacts(
            customer_id=customer.id,
            customer_ref=customer.customer_ref,
            travels=tuple(travels),
            usage=tuple(usage),
            subscriptions=tuple(subscriptions),
        )

    async def load_customer(self, customer_ref: str, as_of: datetime) -> CustomerTravelFacts:
        async with self.uow:
            customer = await self.uow.customers.get_by_ref(customer_ref)
            if customer is None:
                raise NotFoundError(f"Unknown customer: {customer_ref}")
            return await self._bundle(customer, as_of)

    async def load_peers(
        self,
        *,
        exclude_customer_id: UUID,
        destination: str | None,
        as_of: datetime,
        limit: int = 25,
    ) -> tuple[CustomerTravelFacts, ...]:
        async with self.uow:
            peers: list[CustomerTravelFacts] = []
            for customer in await self.uow.customers.list_all():
                if customer.id == exclude_customer_id:
                    continue
                bundle = await self._bundle(customer, as_of)
                travels = bundle.travels
                if destination is not None:
                    travels = tuple(row for row in travels if row.destination == destination)
                if not travels:
                    continue
                peers.append(bundle.model_copy(update={"travels": travels}))
                if len(peers) >= limit:
                    break
            return tuple(peers)
