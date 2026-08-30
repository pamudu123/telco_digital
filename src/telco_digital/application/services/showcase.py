"""Read-only showcase application services. No SQL here."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from telco_digital.application.capability_status import (
    ARTIFACT_LINKS,
    CapabilityManifest,
    Walkthrough,
    get_manifest,
    get_walkthroughs,
)
from telco_digital.application.commands.commands import GetCustomerStateQuery
from telco_digital.application.demo_dataset import END_AT
from telco_digital.application.queries.showcase import (
    Customer360,
    EvidenceSeries,
    OverviewCounts,
    PersonaSummary,
    Retailer360,
)
from telco_digital.application.services.common import NotFoundError
from telco_digital.application.services.customer_state import get_customer_state
from telco_digital.application.unit_of_work.protocol import UnitOfWork


class ShowcaseQueries(Protocol):
    async def overview(self, *, as_of: datetime, queried_at: datetime) -> OverviewCounts: ...

    async def evidence(self, *, as_of: datetime, queried_at: datetime) -> EvidenceSeries: ...

    async def list_personas(self) -> tuple[PersonaSummary, ...]: ...

    async def customer_facts(self, observed, *, queried_at: datetime) -> Customer360: ...

    async def retailer_facts(
        self, retailer_ref: str, *, as_of: datetime, queried_at: datetime
    ) -> Retailer360 | None: ...


async def get_overview(
    queries: ShowcaseQueries, *, as_of: datetime, queried_at: datetime
) -> OverviewCounts:
    return await queries.overview(as_of=as_of, queried_at=queried_at)


async def get_evidence(
    queries: ShowcaseQueries, *, as_of: datetime, queried_at: datetime
) -> EvidenceSeries:
    return await queries.evidence(as_of=as_of, queried_at=queried_at)


async def list_personas(queries: ShowcaseQueries) -> tuple[PersonaSummary, ...]:
    return await queries.list_personas()


async def get_customer_360(
    uow: UnitOfWork,
    queries: ShowcaseQueries,
    *,
    customer_ref: str,
    as_of: datetime,
    queried_at: datetime,
) -> Customer360:
    observed = await get_customer_state(
        uow, GetCustomerStateQuery(customer_ref=customer_ref, as_of=as_of)
    )
    return await queries.customer_facts(observed, queried_at=queried_at)


async def get_retailer_360(
    queries: ShowcaseQueries,
    *,
    retailer_ref: str,
    as_of: datetime,
    queried_at: datetime,
) -> Retailer360:
    facts = await queries.retailer_facts(retailer_ref, as_of=as_of, queried_at=queried_at)
    if facts is None:
        raise NotFoundError(f"Unknown retailer: {retailer_ref}")
    return facts


def capability_manifest() -> CapabilityManifest:
    return get_manifest()


def walkthroughs() -> tuple[Walkthrough, ...]:
    return get_walkthroughs()


def artifact_links() -> tuple[dict[str, str], ...]:
    return ARTIFACT_LINKS


def default_as_of() -> datetime:
    return END_AT
