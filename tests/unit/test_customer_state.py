from decimal import Decimal

import pytest
from tests.helpers import utc

from telco_digital.application.commands.commands import (
    CreateCustomerCommand,
    GetCustomerStateQuery,
    PurchasePlanCommand,
    RecordRechargeCommand,
)
from telco_digital.application.seed import seed_catalogue
from telco_digital.application.services.customer import create_customer
from telco_digital.application.services.customer_state import get_customer_state
from telco_digital.application.services.plan_purchase import purchase_plan
from telco_digital.application.services.recharge import record_recharge


@pytest.mark.asyncio
async def test_balance_ignores_future_recharge(uow, clock) -> None:
    await seed_catalogue(uow, clock=clock)
    await create_customer(
        uow,
        CreateCustomerCommand(
            customer_ref="U100",
            home_country="LK",
            customer_since=utc("2026-01-01T00:00:00+00:00"),
        ),
        clock=clock,
    )
    await record_recharge(
        uow,
        RecordRechargeCommand(
            customer_ref="U100",
            amount=Decimal("500"),
            occurred_at=utc("2026-08-01T10:00:00+00:00"),
        ),
        clock=clock,
    )
    await record_recharge(
        uow,
        RecordRechargeCommand(
            customer_ref="U100",
            amount=Decimal("100"),
            occurred_at=utc("2026-08-20T10:00:00+00:00"),
        ),
        clock=clock,
    )
    before = await get_customer_state(
        uow, GetCustomerStateQuery(customer_ref="U100", as_of=utc("2026-08-10T00:00:00+00:00"))
    )
    after = await get_customer_state(
        uow, GetCustomerStateQuery(customer_ref="U100", as_of=utc("2026-08-21T00:00:00+00:00"))
    )
    assert before.balance_amount == Decimal("500")
    assert after.balance_amount == Decimal("600")


@pytest.mark.asyncio
async def test_plan_at_point_in_time(uow, clock) -> None:
    await seed_catalogue(uow, clock=clock)
    await create_customer(
        uow,
        CreateCustomerCommand(
            customer_ref="U101",
            home_country="LK",
            customer_since=utc("2026-01-01T00:00:00+00:00"),
        ),
        clock=clock,
    )
    await record_recharge(
        uow,
        RecordRechargeCommand(
            customer_ref="U101",
            amount=Decimal("1000"),
            occurred_at=utc("2026-03-01T08:00:00+00:00"),
        ),
        clock=clock,
    )
    await purchase_plan(
        uow,
        PurchasePlanCommand(
            customer_ref="U101",
            plan_code="PLAN_A",
            occurred_at=utc("2026-03-01T08:05:00+00:00"),
        ),
        clock=clock,
    )
    await purchase_plan(
        uow,
        PurchasePlanCommand(
            customer_ref="U101",
            plan_code="ROAM_15",
            occurred_at=utc("2026-03-10T09:00:00+00:00"),
        ),
        clock=clock,
    )
    march_2 = await get_customer_state(
        uow, GetCustomerStateQuery(customer_ref="U101", as_of=utc("2026-03-02T00:00:00+00:00"))
    )
    march_10 = await get_customer_state(
        uow, GetCustomerStateQuery(customer_ref="U101", as_of=utc("2026-03-10T12:00:00+00:00"))
    )
    march_26 = await get_customer_state(
        uow, GetCustomerStateQuery(customer_ref="U101", as_of=utc("2026-03-26T00:00:00+00:00"))
    )
    april = await get_customer_state(
        uow, GetCustomerStateQuery(customer_ref="U101", as_of=utc("2026-04-02T00:00:00+00:00"))
    )
    assert march_2.current_plan_code == "PLAN_A"
    assert march_10.current_plan_code == "ROAM_15"
    assert march_26.current_plan_code == "PLAN_A"
    assert april.current_plan_code is None
    assert march_10.balance_amount == Decimal("1000") - Decimal("300") - Decimal("350")
