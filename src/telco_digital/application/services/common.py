from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from telco_digital.application.clock import Clock
from telco_digital.application.unit_of_work.protocol import UnitOfWork
from telco_digital.domain.entities import ActivityEvent, Customer, OutboxEvent, Warning
from telco_digital.domain.enums import AccountStatus, EventType, OutboxStatus


class NotFoundError(LookupError):
    pass


class AlreadyExistsError(ValueError):
    pass


async def require_customer(uow: UnitOfWork, customer_ref: str) -> Customer:
    customer = await uow.customers.get_by_ref(customer_ref)
    if customer is None:
        raise NotFoundError(f"Unknown customer: {customer_ref}")
    return customer


async def primary_account(uow: UnitOfWork, customer_id):
    accounts = await uow.accounts.list_by_customer(customer_id)
    active = [account for account in accounts if account.status == AccountStatus.ACTIVE]
    if not active:
        raise NotFoundError(f"No account for customer {customer_id}")
    return min(active, key=lambda account: (account.created_at, account.account_ref, account.id))


def new_correlation_id(existing: str | None) -> str:
    return existing or uuid4().hex


async def record_activity(
    uow: UnitOfWork,
    *,
    event: ActivityEvent,
    aggregate_type: str,
    aggregate_id,
    recorded_at: datetime,
) -> tuple[ActivityEvent, OutboxEvent]:
    await uow.events.add(event)
    outbox = event.to_outbox(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        created_at=recorded_at,
    )
    outbox.status = OutboxStatus.PENDING
    await uow.outbox.add(outbox)
    return event, outbox


async def persist_warning(
    uow: UnitOfWork,
    warning: Warning,
    *,
    clock: Clock,
    source: str,
    correlation_id: str,
) -> None:
    warning.created_at = clock.now()
    await uow.warnings.add(warning)
    event = ActivityEvent(
        entity_type="warning",
        entity_id=warning.id,
        customer_id=warning.customer_id,
        event_type=EventType.WARNING_RAISED,
        occurred_at=warning.occurred_at,
        recorded_at=clock.now(),
        source=source,
        correlation_id=correlation_id,
        payload={
            "warning_type": warning.warning_type.value,
            "severity": warning.severity.value,
            "evidence": warning.evidence,
        },
    )
    await record_activity(
        uow,
        event=event,
        aggregate_type="warning",
        aggregate_id=warning.id,
        recorded_at=event.recorded_at,
    )
