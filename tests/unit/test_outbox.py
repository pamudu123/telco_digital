from decimal import Decimal

import pytest

from telco_digital.application.commands.commands import (
    CreateCustomerCommand,
    RecordRechargeCommand,
)
from telco_digital.application.services.customer import create_customer
from telco_digital.application.services.recharge import record_recharge
from telco_digital.domain.enums import EventType, OutboxStatus
from tests.helpers import utc


@pytest.mark.asyncio
async def test_recharge_writes_domain_event_and_outbox(uow, clock) -> None:
    await create_customer(
        uow,
        CreateCustomerCommand(
            customer_ref="U200",
            home_country="LK",
            customer_since=utc("2026-01-01T00:00:00+00:00"),
        ),
        clock=clock,
    )
    result = await record_recharge(
        uow,
        RecordRechargeCommand(
            customer_ref="U200",
            amount=Decimal("500"),
            occurred_at=utc("2026-08-01T10:00:00+00:00"),
        ),
        clock=clock,
    )
    customer = await uow.customers.get_by_ref("U200")
    events = await uow.events.list_timeline(customer.id)
    types = [str(e.event_type) for e in events]
    assert EventType.CUSTOMER_CREATED.value in types
    assert EventType.RECHARGE_RECORDED.value in types
    pending = await uow.outbox.list_pending()
    assert any(item.event_id == result.event_id for item in pending)
    assert all(item.status == OutboxStatus.PENDING for item in pending)
    assert len(await uow.ledgers.list_by_customer(customer.id)) == 1
