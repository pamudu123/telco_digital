from __future__ import annotations

from telco_digital.application.clock import Clock, SystemClock
from telco_digital.application.commands.commands import RecordUsageCommand
from telco_digital.application.queries.dtos import CommandResult
from telco_digital.application.services.common import (
    new_correlation_id,
    record_activity,
    require_customer,
)
from telco_digital.application.unit_of_work.protocol import UnitOfWork
from telco_digital.domain.entities import ActivityEvent, UsageEvent
from telco_digital.domain.enums import EventType
from telco_digital.domain.rules.travel import location_at
from telco_digital.domain.value_objects import normalize_country


async def record_usage(
    uow: UnitOfWork,
    command: RecordUsageCommand,
    *,
    clock: Clock | None = None,
) -> CommandResult:
    clock = clock or SystemClock()
    correlation_id = new_correlation_id(command.correlation_id)
    recorded_at = clock.now()

    async with uow:
        customer = await require_customer(uow, command.customer_ref)
        if command.country:
            country = normalize_country(command.country)
        else:
            travels = await uow.travels.list_as_of(customer.id, command.occurred_at)
            country = location_at(
                home_country=customer.home_country,
                travels=list(travels),
                as_of=command.occurred_at,
            ).country_code

        usage = UsageEvent(
            customer_id=customer.id,
            occurred_at=command.occurred_at,
            usage_type=command.usage_type,
            data_mb=command.data_mb,
            country_code=country,
            network_type=command.network_type,
        )
        event = ActivityEvent(
            entity_type="usage",
            entity_id=usage.id,
            customer_id=customer.id,
            event_type=EventType.USAGE_RECORDED,
            occurred_at=command.occurred_at,
            recorded_at=recorded_at,
            source=command.source,
            correlation_id=correlation_id,
            payload={
                "data_mb": str(command.data_mb),
                "usage_type": command.usage_type.value,
                "country_code": country,
            },
        )
        usage.source_event_id = event.id
        await uow.usage_events.add(usage)
        await record_activity(
            uow,
            event=event,
            aggregate_type="customer",
            aggregate_id=customer.id,
            recorded_at=recorded_at,
        )
        await uow.commit()

    return CommandResult(
        customer_id=customer.id,
        event_id=event.id,
        correlation_id=correlation_id,
        extra={"usage_id": str(usage.id), "country_code": country},
    )
