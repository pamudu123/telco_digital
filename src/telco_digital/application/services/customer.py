from __future__ import annotations

from telco_digital.application.clock import Clock, SystemClock
from telco_digital.application.commands.commands import CreateCustomerCommand
from telco_digital.application.queries.dtos import CommandResult
from telco_digital.application.services.common import (
    AlreadyExistsError,
    new_correlation_id,
    persist_warning,
    record_activity,
)
from telco_digital.application.unit_of_work.protocol import UnitOfWork
from telco_digital.domain.entities import (
    Account,
    ActivityEvent,
    Customer,
    CustomerDevice,
    Device,
    Warning,
)
from telco_digital.domain.enums import AccountStatus, EventType, WarningSeverity, WarningType


async def create_customer(
    uow: UnitOfWork,
    command: CreateCustomerCommand,
    *,
    clock: Clock | None = None,
) -> CommandResult:
    clock = clock or SystemClock()
    correlation_id = new_correlation_id(command.correlation_id)
    recorded_at = clock.now()
    warnings: list[str] = []

    async with uow:
        if await uow.customers.get_by_ref(command.customer_ref) is not None:
            raise AlreadyExistsError(f"Customer already exists: {command.customer_ref}")

        customer = Customer(
            customer_ref=command.customer_ref,
            home_country=command.normalized_country(),
            account_type=command.account_type,
            status=command.status,
            customer_since=command.customer_since,
            created_at=recorded_at,
            updated_at=recorded_at,
        )
        account = Account(
            customer_id=customer.id,
            account_ref=f"{command.customer_ref}-ACC",
            account_type=command.account_type,
            currency=command.currency,
            status=AccountStatus.ACTIVE,
            created_at=command.customer_since,
        )
        await uow.customers.add(customer)
        await uow.accounts.add(account)

        event = ActivityEvent(
            entity_type="customer",
            entity_id=customer.id,
            customer_id=customer.id,
            event_type=EventType.CUSTOMER_CREATED,
            occurred_at=command.customer_since,
            recorded_at=recorded_at,
            source=command.source,
            correlation_id=correlation_id,
            payload={
                "customer_ref": customer.customer_ref,
                "home_country": customer.home_country,
                "account_id": str(account.id),
            },
        )
        await record_activity(
            uow,
            event=event,
            aggregate_type="customer",
            aggregate_id=customer.id,
            recorded_at=recorded_at,
        )

        if command.device_ref:
            device = await uow.devices.get_by_ref(command.device_ref)
            if device is None:
                device = Device(
                    device_ref=command.device_ref,
                    device_type=command.device_type,
                    model=command.device_model or "UNKNOWN",
                    fingerprint=command.device_fingerprint or command.device_ref,
                    first_seen_at=command.customer_since,
                )
                await uow.devices.add(device)
            else:
                other_links = await uow.customer_devices.list_by_device(device.id)
                active_others = [
                    link
                    for link in other_links
                    if link.valid_to is None or link.valid_to > command.customer_since
                ]
                if active_others:
                    warning = Warning(
                        customer_id=customer.id,
                        warning_type=WarningType.DUPLICATE_DEVICE,
                        severity=WarningSeverity.HIGH,
                        occurred_at=command.customer_since,
                        as_of=command.customer_since,
                        evidence={
                            "device_ref": device.device_ref,
                            "existing_customer_ids": [
                                str(link.customer_id) for link in active_others
                            ],
                        },
                    )
                    await persist_warning(
                        uow,
                        warning,
                        clock=clock,
                        source=command.source,
                        correlation_id=correlation_id,
                    )
                    warnings.append(WarningType.DUPLICATE_DEVICE.value)

            await uow.customer_devices.add(
                CustomerDevice(
                    customer_id=customer.id,
                    device_id=device.id,
                    valid_from=command.customer_since,
                )
            )
            device_event = ActivityEvent(
                entity_type="device",
                entity_id=device.id,
                customer_id=customer.id,
                event_type=EventType.DEVICE_LINKED,
                occurred_at=command.customer_since,
                recorded_at=recorded_at,
                source=command.source,
                correlation_id=correlation_id,
                payload={"device_ref": device.device_ref},
            )
            await record_activity(
                uow,
                event=device_event,
                aggregate_type="device",
                aggregate_id=device.id,
                recorded_at=recorded_at,
            )

        await uow.commit()

    return CommandResult(
        customer_id=customer.id,
        event_id=event.id,
        correlation_id=correlation_id,
        warnings=warnings,
        extra={"account_id": str(account.id)},
    )
