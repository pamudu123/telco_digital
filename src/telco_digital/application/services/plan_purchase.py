from __future__ import annotations

from telco_digital.application.clock import Clock, SystemClock
from telco_digital.application.commands.commands import PurchasePlanCommand
from telco_digital.application.queries.dtos import CommandResult
from telco_digital.application.services.common import (
    NotFoundError,
    new_correlation_id,
    primary_account,
    record_activity,
    require_customer,
)
from telco_digital.application.unit_of_work.protocol import UnitOfWork
from telco_digital.domain.entities import ActivityEvent, BalanceLedgerEntry, Subscription
from telco_digital.domain.enums import EventType, LedgerEntryType, SubscriptionStatus


async def purchase_plan(
    uow: UnitOfWork,
    command: PurchasePlanCommand,
    *,
    clock: Clock | None = None,
) -> CommandResult:
    clock = clock or SystemClock()
    correlation_id = new_correlation_id(command.correlation_id)
    recorded_at = clock.now()

    async with uow:
        customer = await require_customer(uow, command.customer_ref)
        plan = await uow.plans.get_by_code(command.plan_code)
        if plan is None or not plan.active:
            raise NotFoundError(f"Unknown or inactive plan: {command.plan_code}")
        account = await primary_account(uow, customer.id)

        event = ActivityEvent(
            entity_type="subscription",
            entity_id=customer.id,
            customer_id=customer.id,
            event_type=EventType.PLAN_PURCHASED,
            occurred_at=command.occurred_at,
            recorded_at=recorded_at,
            source=command.source,
            correlation_id=correlation_id,
            payload={
                "plan_code": plan.plan_code,
                "price": str(plan.price),
                "currency": plan.currency,
            },
        )

        for sub in await uow.subscriptions.list_by_customer(customer.id):
            current = sub.started_at <= command.occurred_at and (
                sub.ended_at is None or sub.ended_at > command.occurred_at
            )
            if not current:
                continue
            existing_plan = await uow.plans.get_by_id(sub.plan_id)
            if existing_plan is not None and existing_plan.plan_type == plan.plan_type:
                sub.ended_at = command.occurred_at
                sub.status = SubscriptionStatus.ENDED
                await uow.subscriptions.update(sub)

        subscription = Subscription(
            customer_id=customer.id,
            plan_id=plan.id,
            started_at=command.occurred_at,
            status=SubscriptionStatus.ACTIVE,
            source_event_id=event.id,
        )
        event.entity_id = subscription.id
        ledger = BalanceLedgerEntry(
            account_id=account.id,
            customer_id=customer.id,
            entry_type=LedgerEntryType.PLAN_BUY,
            amount=-plan.price,
            currency=plan.currency,
            occurred_at=command.occurred_at,
            source_event_id=event.id,
        )
        await uow.subscriptions.add(subscription)
        await uow.ledgers.add(ledger)
        await record_activity(
            uow,
            event=event,
            aggregate_type="subscription",
            aggregate_id=subscription.id,
            recorded_at=recorded_at,
        )
        await uow.commit()

    return CommandResult(
        customer_id=customer.id,
        event_id=event.id,
        correlation_id=correlation_id,
        extra={"subscription_id": str(subscription.id), "plan_code": plan.plan_code},
    )
