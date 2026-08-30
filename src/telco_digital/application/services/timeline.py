from __future__ import annotations

from telco_digital.application.commands.commands import GetTimelineQuery
from telco_digital.application.queries.dtos import TimelineEntry
from telco_digital.application.services.common import require_customer
from telco_digital.application.unit_of_work.protocol import UnitOfWork


async def get_timeline(uow: UnitOfWork, query: GetTimelineQuery) -> list[TimelineEntry]:
    async with uow:
        customer = await require_customer(uow, query.customer_ref)
        events = await uow.events.list_timeline(customer.id, as_of=query.as_of)
        return [
            TimelineEntry(
                event_id=event.id,
                event_type=str(event.event_type),
                occurred_at=event.occurred_at,
                recorded_at=event.recorded_at,
                payload=event.payload,
            )
            for event in events
        ]
