from __future__ import annotations

from telco_digital.application.clock import Clock, SystemClock
from telco_digital.application.commands.commands import RecordServiceInteractionCommand
from telco_digital.application.queries.dtos import CommandResult
from telco_digital.application.services.common import (
    new_correlation_id,
    record_activity,
    require_customer,
)
from telco_digital.application.unit_of_work.protocol import UnitOfWork
from telco_digital.domain.entities import ActivityEvent, ServiceInteraction
from telco_digital.domain.enums import EventType


async def record_service_interaction(
    uow: UnitOfWork,
    command: RecordServiceInteractionCommand,
    *,
    clock: Clock | None = None,
) -> CommandResult:
    clock = clock or SystemClock()
    correlation_id = new_correlation_id(command.correlation_id)
    recorded_at = clock.now()

    async with uow:
        customer = await require_customer(uow, command.customer_ref)
        interaction = ServiceInteraction(
            customer_id=customer.id,
            interaction_type=command.interaction_type,
            occurred_at=command.occurred_at,
            status=command.status,
            category=command.category,
            severity=command.severity,
        )
        event = ActivityEvent(
            entity_type="service_interaction",
            entity_id=interaction.id,
            customer_id=customer.id,
            event_type=EventType.SERVICE_INTERACTION_RECORDED,
            occurred_at=command.occurred_at,
            recorded_at=recorded_at,
            source=command.source,
            correlation_id=correlation_id,
            payload={
                "interaction_type": command.interaction_type,
                "status": command.status,
                "severity": command.severity,
            },
        )
        interaction.source_event_id = event.id
        await uow.service_interactions.add(interaction)
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
        extra={"interaction_id": str(interaction.id)},
    )
