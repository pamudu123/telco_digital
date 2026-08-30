from __future__ import annotations

from telco_digital.application.clock import Clock, SystemClock
from telco_digital.application.commands.commands import CreatePlanCommand
from telco_digital.application.unit_of_work.protocol import UnitOfWork
from telco_digital.domain.entities import Plan
from telco_digital.domain.enums import PlanType
from telco_digital.domain.value_objects import normalize_country


async def create_plan(
    uow: UnitOfWork,
    command: CreatePlanCommand,
    *,
    clock: Clock | None = None,
) -> Plan:
    _ = clock or SystemClock()
    country = normalize_country(command.country_code) if command.country_code else None
    async with uow:
        existing = await uow.plans.get_by_code(command.plan_code)
        if existing is not None:
            return existing
        plan = Plan(
            plan_code=command.plan_code,
            name=command.name,
            plan_type=PlanType(command.plan_type),
            data_mb=command.data_mb,
            validity_days=command.validity_days,
            price=command.price,
            currency=command.currency,
            country_code=country,
            country_group=command.country_group,
            active=True,
            created_at=command.created_at,
        )
        await uow.plans.add(plan)
        await uow.commit()
        return plan
