from __future__ import annotations

from telco_digital.application.clock import Clock, SystemClock
from telco_digital.application.commands.commands import EndTravelCommand, RecordTravelCommand
from telco_digital.application.queries.dtos import CommandResult
from telco_digital.application.services.common import (
    NotFoundError,
    new_correlation_id,
    persist_warning,
    record_activity,
    require_customer,
)
from telco_digital.application.unit_of_work.protocol import UnitOfWork
from telco_digital.domain.entities import ActivityEvent, Travel, Warning
from telco_digital.domain.enums import EventType, WarningSeverity, WarningType
from telco_digital.domain.rules.travel import is_impossible_travel, location_at


async def evaluate_travel_warnings(
    *,
    customer,
    existing_travels: list[Travel],
    new_travel: Travel,
) -> list[Warning]:
    warnings: list[Warning] = []
    previous = [t for t in existing_travels if t.id != new_travel.id]
    loc = location_at(
        home_country=customer.home_country,
        travels=previous,
        as_of=new_travel.started_at,
    )
    from_time = loc.since or customer.customer_since
    if is_impossible_travel(
        from_country=loc.country_code,
        from_time=from_time,
        to_country=new_travel.country_code,
        to_time=new_travel.started_at,
    ):
        warnings.append(
            Warning(
                customer_id=customer.id,
                warning_type=WarningType.IMPOSSIBLE_TRAVEL,
                severity=WarningSeverity.HIGH,
                occurred_at=new_travel.started_at,
                as_of=new_travel.started_at,
                related_event_id=new_travel.start_event_id,
                evidence={
                    "from_country": loc.country_code,
                    "from_source": loc.source,
                    "from_time": from_time.isoformat(),
                    "to_country": new_travel.country_code,
                    "to_time": new_travel.started_at.isoformat(),
                    "note": "Event is stored; marked suspicious rather than rejected.",
                },
            )
        )

    overlapping = [
        t
        for t in previous
        if (new_travel.ended_at is None or t.started_at < new_travel.ended_at)
        and (t.ended_at is None or t.ended_at > new_travel.started_at)
    ]
    if overlapping:
        warnings.append(
            Warning(
                customer_id=customer.id,
                warning_type=WarningType.OVERLAPPING_TRAVEL,
                severity=WarningSeverity.MEDIUM,
                occurred_at=new_travel.started_at,
                as_of=new_travel.started_at,
                related_event_id=new_travel.start_event_id,
                evidence={
                    "open_travel_ids": [str(t.id) for t in overlapping],
                    "open_countries": [t.country_code for t in overlapping],
                },
            )
        )
    return warnings


async def record_travel(
    uow: UnitOfWork,
    command: RecordTravelCommand,
    *,
    clock: Clock | None = None,
) -> CommandResult:
    clock = clock or SystemClock()
    correlation_id = new_correlation_id(command.correlation_id)
    recorded_at = clock.now()
    warning_codes: list[str] = []

    async with uow:
        customer = await require_customer(uow, command.customer_ref)
        travel = Travel(
            customer_id=customer.id,
            country_code=command.normalized_country(),
            started_at=command.started_at,
            ended_at=command.ended_at,
            source=command.source,
        )
        event = ActivityEvent(
            entity_type="travel",
            entity_id=travel.id,
            customer_id=customer.id,
            event_type=EventType.TRAVEL_STARTED,
            occurred_at=command.started_at,
            recorded_at=recorded_at,
            source=command.source,
            correlation_id=correlation_id,
            payload={
                "country": travel.country_code,
                "ended_at": command.ended_at.isoformat() if command.ended_at else None,
                "duration_known": command.ended_at is not None,
            },
        )
        travel.start_event_id = event.id
        end_event = None
        if travel.ended_at is not None:
            end_event = ActivityEvent(
                entity_type="travel",
                entity_id=travel.id,
                customer_id=customer.id,
                event_type=EventType.TRAVEL_ENDED,
                occurred_at=travel.ended_at,
                recorded_at=recorded_at,
                source=command.source,
                correlation_id=correlation_id,
                payload={"country": travel.country_code},
            )
            travel.end_event_id = end_event.id
        existing = list(await uow.travels.list_by_customer(customer.id))
        await uow.travels.add(travel)
        await record_activity(
            uow,
            event=event,
            aggregate_type="travel",
            aggregate_id=travel.id,
            recorded_at=recorded_at,
        )
        if end_event is not None:
            await record_activity(
                uow,
                event=end_event,
                aggregate_type="travel",
                aggregate_id=travel.id,
                recorded_at=recorded_at,
            )
        for warning in await evaluate_travel_warnings(
            customer=customer,
            existing_travels=existing,
            new_travel=travel,
        ):
            warning.related_event_id = event.id
            await persist_warning(
                uow,
                warning,
                clock=clock,
                source=command.source,
                correlation_id=correlation_id,
            )
            warning_codes.append(warning.warning_type.value)
        await uow.commit()

    return CommandResult(
        customer_id=customer.id,
        event_id=event.id,
        correlation_id=correlation_id,
        warnings=warning_codes,
        extra={
            "travel_id": str(travel.id),
            "country_code": travel.country_code,
            "duration_known": travel.duration_known,
        },
    )


async def end_travel(
    uow: UnitOfWork,
    command: EndTravelCommand,
    *,
    clock: Clock | None = None,
) -> CommandResult:
    clock = clock or SystemClock()
    correlation_id = new_correlation_id(command.correlation_id)
    recorded_at = clock.now()

    async with uow:
        customer = await require_customer(uow, command.customer_ref)
        travels = list(await uow.travels.list_by_customer(customer.id))
        if command.travel_id:
            match = next((t for t in travels if t.id == command.travel_id), None)
        else:
            open_trips = [
                t for t in travels if t.ended_at is None and t.started_at <= command.ended_at
            ]
            match = max(open_trips, key=lambda t: t.started_at) if open_trips else None
        if match is None:
            raise NotFoundError("No open travel to end")
        if match.ended_at is not None:
            raise ValueError("Travel has already ended")
        if command.ended_at < match.started_at:
            raise ValueError("ended_at must be greater than or equal to started_at")

        event = ActivityEvent(
            entity_type="travel",
            entity_id=match.id,
            customer_id=customer.id,
            event_type=EventType.TRAVEL_ENDED,
            occurred_at=command.ended_at,
            recorded_at=recorded_at,
            source=command.source,
            correlation_id=correlation_id,
            payload={"country": match.country_code},
        )
        match.ended_at = command.ended_at
        match.end_event_id = event.id
        await uow.travels.update(match)
        await record_activity(
            uow,
            event=event,
            aggregate_type="travel",
            aggregate_id=match.id,
            recorded_at=recorded_at,
        )
        await uow.commit()

    return CommandResult(
        customer_id=customer.id,
        event_id=event.id,
        correlation_id=correlation_id,
        extra={"travel_id": str(match.id)},
    )
