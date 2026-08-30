"""Read DTOs for the capability-00 read-only showcase."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EvidenceSource = Literal["live_database", "capability_00_artifact", "unavailable"]


class ShowcaseModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class DomainCoverage(ShowcaseModel):
    domain: str
    demonstrated_data: str
    existing_application: str
    live: bool


class OverviewCounts(ShowcaseModel):
    source: EvidenceSource
    as_of: datetime
    dataset_version: str
    queried_at: datetime
    generated_rows: int
    total_database_rows: int
    total_customers: int
    background_customers: int
    golden_personas: int
    activity_events: int
    outbox_events: int
    event_outbox_parity: bool
    period_start: datetime
    period_end: datetime
    generated_row_counts: dict[str, int]
    domain_coverage: tuple[DomainCoverage, ...]


class SeriesPoint(ShowcaseModel):
    label: str
    value: float


class EvidenceSeries(ShowcaseModel):
    source: EvidenceSource
    as_of: datetime
    dataset_version: str
    queried_at: datetime
    generated_rows_by_table: tuple[SeriesPoint, ...]
    persona_distribution: tuple[SeriesPoint, ...]
    monthly_activity: tuple[SeriesPoint, ...]


class PersonaSummary(ShowcaseModel):
    customer_ref: str
    persona: str
    label: str
    golden: bool
    present: bool


class ProvenanceBlock(ShowcaseModel):
    source: EvidenceSource
    as_of: datetime
    dataset_version: str
    table: str


class FactRecord(ShowcaseModel):
    kind: str
    occurred_at: datetime | None = None
    summary: str
    detail: dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceBlock


class Customer360(ShowcaseModel):
    source: EvidenceSource
    as_of: datetime
    dataset_version: str
    queried_at: datetime
    customer_ref: str
    persona: str | None
    home_country: str
    account_type: str
    status: str
    customer_since: datetime
    observed_country: str | None = None
    observed_country_source: str | None = None
    current_plan_code: str | None = None
    current_plan_name: str | None = None
    subscription_status: str | None = None
    subscription_started_at: datetime | None = None
    balance_amount: Decimal | None = None
    currency: str | None = None
    loyalty_points: int = 0
    device_ref: str | None = None
    active_complaints: int = 0
    trip_duration_known: bool | None = None
    unknowns: tuple[str, ...] = ()
    usage: tuple[FactRecord, ...] = ()
    recharges: tuple[FactRecord, ...] = ()
    travels: tuple[FactRecord, ...] = ()
    service_interactions: tuple[FactRecord, ...] = ()
    loyalty: tuple[FactRecord, ...] = ()
    campaigns: tuple[FactRecord, ...] = ()
    wallet: tuple[FactRecord, ...] = ()
    devices: tuple[FactRecord, ...] = ()
    timeline: tuple[FactRecord, ...] = ()


class Retailer360(ShowcaseModel):
    source: EvidenceSource
    as_of: datetime
    dataset_version: str
    queried_at: datetime
    retailer_ref: str
    name: str
    region: str
    status: str
    sales: tuple[FactRecord, ...] = ()
    inventory: tuple[FactRecord, ...] = ()


DOMAIN_COVERAGE: tuple[DomainCoverage, ...] = (
    DomainCoverage(
        domain="Telco",
        demonstrated_data="Plans, subscriptions, usage, recharge, travel, service interactions",
        existing_application="Selfcare",
        live=True,
    ),
    DomainCoverage(
        domain="Marketing",
        demonstrated_data="Campaigns and responses",
        existing_application="adReach, Viber",
        live=True,
    ),
    DomainCoverage(
        domain="Loyalty",
        demonstrated_data="Accounts and point ledger",
        existing_application="Loyalty Management",
        live=True,
    ),
    DomainCoverage(
        domain="Money",
        demonstrated_data="Wallets, merchants and transactions",
        existing_application="Mobile Money",
        live=True,
    ),
    DomainCoverage(
        domain="Sales",
        demonstrated_data="Distributors, retailers, agents, products, sales and inventory events",
        existing_application="SFA",
        live=True,
    ),
    DomainCoverage(
        domain="Shared activity",
        demonstrated_data="Immutable activity history and transactional outbox",
        existing_application="All applications",
        live=True,
    ),
)


def display_persona(code: str | None) -> str:
    if not code:
        return "Unknown"
    return code.replace("_", " ").title()
