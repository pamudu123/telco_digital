"""Scenario: historical reconstruction of U001's March Singapore trip."""

from decimal import Decimal

import pytest

from telco_digital.application.commands.commands import GetCustomerStateQuery, GetTimelineQuery
from telco_digital.application.seed import seed_demo_customers
from telco_digital.application.services.customer_state import get_customer_state
from telco_digital.application.services.timeline import get_timeline
from tests.helpers import utc


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_u001_reconstructed_at_arbitrary_timestamps(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)

    before_trip = await get_customer_state(
        uow, GetCustomerStateQuery(customer_ref="U001", as_of=utc("2026-03-09T12:00:00+00:00"))
    )
    assert before_trip.country_name == "Sri Lanka"
    assert before_trip.current_plan_code == "PLAN_A"
    assert before_trip.device_ref == "D001"
    assert before_trip.balance_amount == Decimal("1700")

    during_trip = await get_customer_state(
        uow, GetCustomerStateQuery(customer_ref="U001", as_of=utc("2026-03-10T10:00:00+00:00"))
    )
    assert during_trip.country_name == "Singapore"
    assert during_trip.country_source == "travel"
    assert during_trip.current_plan_code == "ROAM_15"
    assert during_trip.trip_duration_known is False
    assert during_trip.balance_amount == Decimal("1350")

    after_trip = await get_customer_state(
        uow, GetCustomerStateQuery(customer_ref="U001", as_of=utc("2026-03-16T19:00:00+00:00"))
    )
    assert after_trip.country_name == "Sri Lanka"
    assert after_trip.trip_duration_known is True

    usage = await uow.usage_events.total_mb(
        (await uow.customers.get_by_ref("U001")).id,
        start=utc("2026-03-10T00:00:00+00:00"),
        end=utc("2026-03-16T23:59:59+00:00"),
    )
    assert usage == Decimal("11400")

    timeline = await get_timeline(
        uow, GetTimelineQuery(customer_ref="U001", as_of=utc("2026-03-10T08:30:00+00:00"))
    )
    types = [entry.event_type for entry in timeline]
    assert "TRAVEL_STARTED" in types
    assert "TRAVEL_ENDED" not in types
