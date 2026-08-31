from __future__ import annotations

from telco_digital.application.clock import Clock, SystemClock
from telco_digital.application.commands.commands import RecordRechargeCommand
from telco_digital.application.queries.dtos import CommandResult
from telco_digital.application.services.common import (
    new_correlation_id,
    persist_warning,
    primary_account,
    record_activity,
    require_customer,
)
from telco_digital.application.unit_of_work.protocol import UnitOfWork
from telco_digital.domain.entities import ActivityEvent, BalanceLedgerEntry, Recharge, Warning
from telco_digital.domain.enums import EventType, LedgerEntryType, WarningSeverity, WarningType
from telco_digital.domain.rules.recharge import (
    frequent_small_recharge_pattern,
    small_recharges_in_window,
)


async def record_recharge(
    uow: UnitOfWork,
    command: RecordRechargeCommand,
    *,
    clock: Clock | None = None,
) -> CommandResult:
    clock = clock or SystemClock()
    correlation_id = new_correlation_id(command.correlation_id)
    recorded_at = clock.now()
    warnings: list[str] = []

    async with uow:
        customer = await require_customer(uow, command.customer_ref)
        account = await primary_account(uow, customer.id)
        currency = command.currency or account.currency

        recharge = Recharge(
            customer_id=customer.id,
            account_id=account.id,
            amount=command.amount,
            currency=currency,
            occurred_at=command.occurred_at,
            channel=command.channel,
        )
        event = ActivityEvent(
            entity_type="recharge",
            entity_id=recharge.id,
            customer_id=customer.id,
            event_type=EventType.RECHARGE_RECORDED,
            occurred_at=command.occurred_at,
            recorded_at=recorded_at,
            source=command.source,
            correlation_id=correlation_id,
            payload={
                "amount": str(command.amount),
                "currency": currency,
                "channel": command.channel,
            },
        )
        recharge.source_event_id = event.id
        ledger = BalanceLedgerEntry(
            account_id=account.id,
            customer_id=customer.id,
            entry_type=LedgerEntryType.RECHARGE,
            amount=command.amount,
            currency=currency,
            occurred_at=command.occurred_at,
            source_event_id=event.id,
        )
        await uow.recharges.add(recharge)
        await uow.ledgers.add(ledger)
        await record_activity(
            uow,
            event=event,
            aggregate_type="account",
            aggregate_id=account.id,
            recorded_at=recorded_at,
        )

        history = list(await uow.recharges.list_as_of(customer.id, command.occurred_at))
        if frequent_small_recharge_pattern(history, as_of=command.occurred_at):
            matched = small_recharges_in_window(history, as_of=command.occurred_at)
            warning = Warning(
                customer_id=customer.id,
                warning_type=WarningType.FREQUENT_SMALL_RECHARGE_PATTERN,
                severity=WarningSeverity.MEDIUM,
                occurred_at=command.occurred_at,
                as_of=command.occurred_at,
                related_event_id=event.id,
                evidence={
                    "small_recharge_count_30d": len(matched),
                    "latest_amount": str(command.amount),
                },
            )
            await persist_warning(
                uow,
                warning,
                clock=clock,
                source=command.source,
                correlation_id=correlation_id,
            )
            warnings.append(WarningType.FREQUENT_SMALL_RECHARGE_PATTERN.value)

        await uow.commit()

    return CommandResult(
        customer_id=customer.id,
        event_id=event.id,
        correlation_id=correlation_id,
        warnings=warnings,
        extra={"recharge_id": str(recharge.id)},
    )
