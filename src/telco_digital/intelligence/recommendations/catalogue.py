"""Real-catalogue offers for travel recommendations.

Intelligence never invents a plan. Candidates come only from active catalogue
rows already stored in PostgreSQL.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from telco_digital.application.unit_of_work.protocol import PlanRepository
from telco_digital.domain.enums import PlanType


class CataloguePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_code: str
    name: str
    plan_type: str
    data_mb: int
    validity_days: int
    price: float
    currency: str
    country_code: str | None = None
    active: bool = True


class CatalogueReader(Protocol):
    async def list_roaming(self, *, country_code: str | None) -> tuple[CataloguePlan, ...]: ...


def catalogue_plan_from_entity(plan) -> CataloguePlan:
    price = plan.price
    return CataloguePlan(
        plan_code=plan.plan_code,
        name=plan.name,
        plan_type=str(plan.plan_type),
        data_mb=int(plan.data_mb),
        validity_days=int(plan.validity_days),
        price=float(price if not isinstance(price, Decimal) else price),
        currency=plan.currency,
        country_code=plan.country_code,
        active=bool(plan.active),
    )


class PlanRepositoryCatalogue:
    """Adapts the existing plan repository. No new SQL is added."""

    def __init__(self, repository: PlanRepository) -> None:
        self.repository = repository

    async def list_roaming(self, *, country_code: str | None) -> tuple[CataloguePlan, ...]:
        plans = await self.repository.list_active(plan_type=PlanType.ROAMING)
        offers = []
        for plan in plans:
            if not plan.active:
                continue
            if country_code and plan.country_code not in (None, country_code):
                continue
            offers.append(catalogue_plan_from_entity(plan))
        return tuple(offers)
