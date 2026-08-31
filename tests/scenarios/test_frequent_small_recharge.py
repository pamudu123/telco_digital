"""Repeated 100 top-ups yield FREQUENT_SMALL_RECHARGE_PATTERN."""

from decimal import Decimal

import pytest
from tests.helpers import utc

from telco_digital.application.seed import seed_demo_customers
from telco_digital.domain.enums import WarningType


@pytest.mark.scenario
@pytest.mark.asyncio
async def test_u002_frequent_small_recharge_pattern(uow, clock) -> None:
    await seed_demo_customers(uow, clock=clock)
    customer = await uow.customers.get_by_ref("U002")
    warnings = await uow.warnings.list_by_customer(customer.id)
    types = {w.warning_type for w in warnings}
    assert WarningType.FREQUENT_SMALL_RECHARGE_PATTERN in types
    pattern = next(
        warning
        for warning in warnings
        if warning.warning_type == WarningType.FREQUENT_SMALL_RECHARGE_PATTERN
    )
    assert pattern.evidence["small_recharge_count_30d"] == 5

    recharges = await uow.recharges.list_as_of(customer.id, utc("2026-08-21T00:00:00+00:00"))
    assert [r.amount for r in sorted(recharges, key=lambda r: r.occurred_at)] == [
        Decimal("100")
    ] * 5
