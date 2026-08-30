#!/usr/bin/env python3
"""Seed deterministic demo customers U001–U005."""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telco_digital.application.clock import SystemClock
from telco_digital.application.commands.commands import GetCustomerStateQuery
from telco_digital.application.seed import seed_demo_customers
from telco_digital.application.services.customer_state import get_customer_state
from telco_digital.infrastructure.memory import InMemoryUnitOfWork


async def main() -> None:
    uow = InMemoryUnitOfWork()
    clock = SystemClock()
    await seed_demo_customers(uow, clock=clock)
    as_of = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    for ref in ("U001", "U002", "U003", "U004", "U005"):
        state = await get_customer_state(
            uow, GetCustomerStateQuery(customer_ref=ref, as_of=as_of)
        )
        print(
            f"{state.customer_ref}  country={state.country_name}  "
            f"plan={state.current_plan_code}  balance={state.balance_amount} {state.currency}  "
            f"device={state.device_ref}  warnings={state.warnings}"
        )


if __name__ == "__main__":
    asyncio.run(main())
