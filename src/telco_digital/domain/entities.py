from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from telco_digital.domain.enums import (
    AccountStatus,
    AccountType,
    CustomerStatus,
    EventType,
    InteractionStatus,
    InteractionType,
    LedgerEntryType,
    OutboxStatus,
    PlanType,
    SubscriptionStatus,
    UsageType,
    WarningSeverity,
    WarningType,
)


def new_id() -> UUID:
    return uuid4()


@dataclass(slots=True)
class Customer:
    customer_ref: str
    home_country: str
    account_type: AccountType
    status: CustomerStatus
    customer_since: datetime
    created_at: datetime
    updated_at: datetime
    id: UUID = field(default_factory=new_id)


@dataclass(slots=True)
class Account:
    customer_id: UUID
    account_ref: str
    account_type: AccountType
    currency: str
    status: AccountStatus
    created_at: datetime
    id: UUID = field(default_factory=new_id)


@dataclass(slots=True)
class Device:
    device_ref: str
    device_type: str
    model: str
    fingerprint: str
    first_seen_at: datetime
    id: UUID = field(default_factory=new_id)


@dataclass(slots=True)
class CustomerDevice:
    customer_id: UUID
    device_id: UUID
    valid_from: datetime
    valid_to: datetime | None = None
    id: UUID = field(default_factory=new_id)


@dataclass(slots=True)
class Plan:
    plan_code: str
    name: str
    plan_type: PlanType
    data_mb: int
    validity_days: int
    price: Decimal
    currency: str
    active: bool
    created_at: datetime
    country_code: str | None = None
    country_group: str | None = None
    id: UUID = field(default_factory=new_id)


@dataclass(slots=True)
class Subscription:
    customer_id: UUID
    plan_id: UUID
    started_at: datetime
    status: SubscriptionStatus
    ended_at: datetime | None = None
    source_event_id: UUID | None = None
    id: UUID = field(default_factory=new_id)


@dataclass(slots=True)
class BalanceLedgerEntry:
    account_id: UUID
    customer_id: UUID
    entry_type: LedgerEntryType
    amount: Decimal
    currency: str
    occurred_at: datetime
    source_event_id: UUID | None = None
    id: UUID = field(default_factory=new_id)


@dataclass(slots=True)
class Recharge:
    customer_id: UUID
    account_id: UUID
    amount: Decimal
    currency: str
    occurred_at: datetime
    channel: str | None = None
    source_event_id: UUID | None = None
    id: UUID = field(default_factory=new_id)


@dataclass(slots=True)
class UsageEvent:
    customer_id: UUID
    occurred_at: datetime
    usage_type: UsageType
    data_mb: Decimal
    country_code: str
    network_type: str | None = None
    source_event_id: UUID | None = None
    id: UUID = field(default_factory=new_id)


@dataclass(slots=True)
class Travel:
    customer_id: UUID
    country_code: str
    started_at: datetime
    ended_at: datetime | None = None
    source: str | None = None
    start_event_id: UUID | None = None
    end_event_id: UUID | None = None
    id: UUID = field(default_factory=new_id)

    @property
    def duration_known(self) -> bool:
        return self.ended_at is not None


@dataclass(slots=True)
class ServiceInteraction:
    customer_id: UUID
    interaction_type: InteractionType
    occurred_at: datetime
    status: InteractionStatus
    category: str | None = None
    severity: str | None = None
    resolved_at: datetime | None = None
    source_event_id: UUID | None = None
    id: UUID = field(default_factory=new_id)


@dataclass(slots=True)
class ActivityEvent:
    entity_type: str
    entity_id: UUID
    event_type: EventType | str
    occurred_at: datetime
    recorded_at: datetime
    source: str
    customer_id: UUID | None = None
    correlation_id: str | None = None
    idempotency_key: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=new_id)

    def to_outbox(
        self,
        *,
        aggregate_type: str,
        aggregate_id: UUID,
        created_at: datetime,
    ) -> OutboxEvent:
        return OutboxEvent(
            event_id=self.id,
            event_type=str(self.event_type),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload={
                "activity_event_id": str(self.id),
                "customer_id": str(self.customer_id) if self.customer_id else None,
                "occurred_at": self.occurred_at.isoformat(),
                "payload": self.payload,
            },
            created_at=created_at,
        )


@dataclass(slots=True)
class OutboxEvent:
    event_id: UUID
    event_type: str
    aggregate_type: str
    aggregate_id: UUID
    payload: dict[str, Any]
    created_at: datetime
    processed_at: datetime | None = None
    attempt_count: int = 0
    last_error: str | None = None
    status: OutboxStatus = OutboxStatus.PENDING
    id: UUID = field(default_factory=new_id)


@dataclass(slots=True)
class Warning:
    customer_id: UUID
    warning_type: WarningType
    severity: WarningSeverity
    occurred_at: datetime
    as_of: datetime
    evidence: dict[str, Any] = field(default_factory=dict)
    related_event_id: UUID | None = None
    created_at: datetime | None = None
    id: UUID = field(default_factory=new_id)
