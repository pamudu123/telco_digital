from decimal import Decimal

import pytest
from pydantic import ValidationError
from tests.helpers import utc

from telco_digital.application.commands.commands import (
    CreateCustomerCommand,
    EndTravelCommand,
    RecordRechargeCommand,
    RecordServiceInteractionCommand,
    RecordTravelCommand,
    RecordUsageCommand,
)
from telco_digital.application.services.customer import create_customer
from telco_digital.application.services.travel import end_travel, record_travel


@pytest.mark.parametrize(
    ("command_type", "kwargs"),
    [
        (
            RecordRechargeCommand,
            {
                "customer_ref": "U001",
                "amount": Decimal("0"),
                "occurred_at": utc("2026-08-20T10:00:00+00:00"),
            },
        ),
        (
            RecordUsageCommand,
            {
                "customer_ref": "U001",
                "data_mb": Decimal("-1"),
                "occurred_at": utc("2026-08-20T10:00:00+00:00"),
            },
        ),
    ],
)
def test_non_positive_facts_are_rejected(command_type, kwargs) -> None:
    with pytest.raises(ValidationError):
        command_type(**kwargs)


def test_invalid_travel_range_is_rejected() -> None:
    with pytest.raises(ValidationError, match="ended_at"):
        RecordTravelCommand(
            customer_ref="U001",
            country="SG",
            started_at=utc("2026-08-20T10:00:00+00:00"),
            ended_at=utc("2026-08-20T09:00:00+00:00"),
        )


def test_invalid_interaction_enum_is_rejected() -> None:
    with pytest.raises(ValidationError, match="interaction_type"):
        RecordServiceInteractionCommand(
            customer_ref="U001",
            interaction_type="COMPLAINTS",
            occurred_at=utc("2026-08-20T10:00:00+00:00"),
        )


@pytest.mark.asyncio
async def test_end_travel_rejects_time_before_start(uow, clock) -> None:
    await create_customer(
        uow,
        CreateCustomerCommand(
            customer_ref="U001",
            home_country="LK",
            customer_since=utc("2024-01-01T00:00:00+00:00"),
        ),
        clock=clock,
    )
    travel = await record_travel(
        uow,
        RecordTravelCommand(
            customer_ref="U001",
            country="SG",
            started_at=utc("2026-08-20T10:00:00+00:00"),
        ),
        clock=clock,
    )
    with pytest.raises(ValueError, match="ended_at"):
        await end_travel(
            uow,
            EndTravelCommand(
                customer_ref="U001",
                travel_id=travel.extra["travel_id"],
                ended_at=utc("2026-08-20T09:00:00+00:00"),
            ),
            clock=clock,
        )
