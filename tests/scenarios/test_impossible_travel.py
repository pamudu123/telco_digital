"""Given U001 Singapore at 09:00, when USA travel is entered at 10:00,
the event remains stored and IMPOSSIBLE_TRAVEL is generated.
"""

import pytest
from tests.helpers import utc

from telco_digital.application.commands.commands import (
    CreateCustomerCommand,
    GetTimelineQuery,
    RecordTravelCommand,
)
from telco_digital.application.services.customer import create_customer
from telco_digital.application.services.timeline import get_timeline
from telco_digital.application.services.travel import record_travel
from telco_digital.domain.enums import EventType, WarningType


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_impossible_travel_is_stored_not_rejected(uow, clock) -> None:
    await create_customer(
        uow,
        CreateCustomerCommand(
            customer_ref="U001",
            home_country="Sri Lanka",
            customer_since=utc("2024-01-15T00:00:00+00:00"),
        ),
        clock=clock,
    )
    first = await record_travel(
        uow,
        RecordTravelCommand(
            customer_ref="U001",
            country="Singapore",
            started_at=utc("2026-08-26T09:00:00+00:00"),
        ),
        clock=clock,
    )
    assert WarningType.IMPOSSIBLE_TRAVEL.value not in first.warnings

    second = await record_travel(
        uow,
        RecordTravelCommand(
            customer_ref="U001",
            country="USA",
            started_at=utc("2026-08-26T10:00:00+00:00"),
        ),
        clock=clock,
    )
    assert WarningType.IMPOSSIBLE_TRAVEL.value in second.warnings

    timeline = await get_timeline(uow, GetTimelineQuery(customer_ref="U001"))
    travel_events = [e for e in timeline if e.event_type == EventType.TRAVEL_STARTED.value]
    assert len(travel_events) == 2
    countries = {e.payload["country"] for e in travel_events}
    assert countries == {"SG", "US"}

    warning_events = [e for e in timeline if e.event_type == EventType.WARNING_RAISED.value]
    assert any(
        e.payload.get("warning_type") == WarningType.IMPOSSIBLE_TRAVEL.value for e in warning_events
    )
    customer = await uow.customers.get_by_ref("U001")
    travels = await uow.travels.list_by_customer(customer.id)
    assert len(travels) == 2


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_impossible_travel_uses_latest_return_time(uow, clock) -> None:
    await create_customer(
        uow,
        CreateCustomerCommand(
            customer_ref="RETURNING",
            home_country="Sri Lanka",
            customer_since=utc("2024-01-15T00:00:00+00:00"),
        ),
        clock=clock,
    )
    await record_travel(
        uow,
        RecordTravelCommand(
            customer_ref="RETURNING",
            country="USA",
            started_at=utc("2026-08-26T08:00:00+00:00"),
            ended_at=utc("2026-08-26T09:00:00+00:00"),
        ),
        clock=clock,
    )
    result = await record_travel(
        uow,
        RecordTravelCommand(
            customer_ref="RETURNING",
            country="Singapore",
            started_at=utc("2026-08-26T10:00:00+00:00"),
        ),
        clock=clock,
    )
    assert WarningType.IMPOSSIBLE_TRAVEL.value in result.warnings

    timeline = await get_timeline(uow, GetTimelineQuery(customer_ref="RETURNING"))
    assert sum(event.event_type == EventType.TRAVEL_ENDED.value for event in timeline) == 1


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_backdated_travel_detects_later_started_overlap(uow, clock) -> None:
    await create_customer(
        uow,
        CreateCustomerCommand(
            customer_ref="BACKDATED",
            home_country="Sri Lanka",
            customer_since=utc("2024-01-15T00:00:00+00:00"),
        ),
        clock=clock,
    )
    await record_travel(
        uow,
        RecordTravelCommand(
            customer_ref="BACKDATED",
            country="USA",
            started_at=utc("2026-08-26T10:00:00+00:00"),
        ),
        clock=clock,
    )
    result = await record_travel(
        uow,
        RecordTravelCommand(
            customer_ref="BACKDATED",
            country="Singapore",
            started_at=utc("2026-08-26T09:00:00+00:00"),
            ended_at=utc("2026-08-26T12:00:00+00:00"),
        ),
        clock=clock,
    )
    assert WarningType.OVERLAPPING_TRAVEL.value in result.warnings
