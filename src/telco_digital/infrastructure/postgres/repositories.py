from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from telco_digital.domain.entities import (
    Account,
    ActivityEvent,
    BalanceLedgerEntry,
    Customer,
    CustomerDevice,
    Device,
    OutboxEvent,
    Plan,
    Recharge,
    ServiceInteraction,
    Subscription,
    Travel,
    UsageEvent,
    Warning,
)
from telco_digital.domain.enums import (
    AccountStatus,
    AccountType,
    CustomerStatus,
    LedgerEntryType,
    OutboxStatus,
    PlanType,
    SubscriptionStatus,
    UsageType,
    WarningSeverity,
    WarningType,
)
from telco_digital.infrastructure.postgres.models import (
    AccountModel,
    ActivityEventModel,
    BalanceLedgerModel,
    CustomerDeviceModel,
    CustomerModel,
    DeviceModel,
    OutboxEventModel,
    PlanModel,
    RechargeModel,
    ServiceInteractionModel,
    SubscriptionModel,
    TravelModel,
    UsageEventModel,
    WarningModel,
)


class SqlCustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, customer: Customer) -> None:
        self.session.add(
            CustomerModel(
                id=customer.id,
                customer_ref=customer.customer_ref,
                home_country=customer.home_country,
                account_type=customer.account_type.value,
                status=customer.status.value,
                customer_since=customer.customer_since,
                created_at=customer.created_at,
                updated_at=customer.updated_at,
            )
        )
        # Customer creation adds dependent account/device rows in the same UoW.
        # Flush the aggregate root first so database FK ordering is explicit.
        await self.session.flush()

    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        row = await self.session.get(CustomerModel, customer_id)
        return _to_customer(row) if row else None

    async def get_by_ref(self, customer_ref: str) -> Customer | None:
        result = await self.session.execute(
            select(CustomerModel).where(CustomerModel.customer_ref == customer_ref)
        )
        row = result.scalar_one_or_none()
        return _to_customer(row) if row else None

    async def list_all(self) -> list[Customer]:
        result = await self.session.execute(select(CustomerModel))
        return [_to_customer(r) for r in result.scalars()]


class SqlAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, account: Account) -> None:
        self.session.add(
            AccountModel(
                id=account.id,
                customer_id=account.customer_id,
                account_ref=account.account_ref,
                account_type=account.account_type.value,
                currency=account.currency,
                status=account.status.value,
                created_at=account.created_at,
            )
        )

    async def get_by_id(self, account_id: UUID) -> Account | None:
        row = await self.session.get(AccountModel, account_id)
        return _to_account(row) if row else None

    async def list_by_customer(self, customer_id: UUID) -> list[Account]:
        result = await self.session.execute(
            select(AccountModel).where(AccountModel.customer_id == customer_id)
        )
        return [_to_account(r) for r in result.scalars()]


class SqlDeviceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, device: Device) -> None:
        self.session.add(
            DeviceModel(
                id=device.id,
                device_ref=device.device_ref,
                device_type=device.device_type,
                model=device.model,
                fingerprint=device.fingerprint,
                first_seen_at=device.first_seen_at,
            )
        )
        # A customer-device link may be added immediately after this repository call.
        await self.session.flush()

    async def get_by_id(self, device_id: UUID) -> Device | None:
        row = await self.session.get(DeviceModel, device_id)
        return _to_device(row) if row else None

    async def get_by_ref(self, device_ref: str) -> Device | None:
        result = await self.session.execute(
            select(DeviceModel).where(DeviceModel.device_ref == device_ref)
        )
        row = result.scalar_one_or_none()
        return _to_device(row) if row else None


class SqlCustomerDeviceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, link: CustomerDevice) -> None:
        self.session.add(
            CustomerDeviceModel(
                id=link.id,
                customer_id=link.customer_id,
                device_id=link.device_id,
                valid_from=link.valid_from,
                valid_to=link.valid_to,
            )
        )

    async def list_by_customer(self, customer_id: UUID) -> list[CustomerDevice]:
        result = await self.session.execute(
            select(CustomerDeviceModel).where(
                CustomerDeviceModel.customer_id == customer_id
            )
        )
        return [_to_customer_device(r) for r in result.scalars()]

    async def list_by_device(self, device_id: UUID) -> list[CustomerDevice]:
        result = await self.session.execute(
            select(CustomerDeviceModel).where(CustomerDeviceModel.device_id == device_id)
        )
        return [_to_customer_device(r) for r in result.scalars()]

    async def active_at(self, customer_id: UUID, as_of: datetime) -> CustomerDevice | None:
        result = await self.session.execute(
            select(CustomerDeviceModel)
            .where(
                CustomerDeviceModel.customer_id == customer_id,
                CustomerDeviceModel.valid_from <= as_of,
                (CustomerDeviceModel.valid_to.is_(None))
                | (CustomerDeviceModel.valid_to > as_of),
            )
            .order_by(CustomerDeviceModel.valid_from.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return _to_customer_device(row) if row else None


class SqlPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, plan: Plan) -> None:
        self.session.add(
            PlanModel(
                id=plan.id,
                plan_code=plan.plan_code,
                name=plan.name,
                plan_type=plan.plan_type.value,
                data_mb=plan.data_mb,
                validity_days=plan.validity_days,
                price=plan.price,
                currency=plan.currency,
                country_code=plan.country_code,
                country_group=plan.country_group,
                active=plan.active,
                created_at=plan.created_at,
            )
        )

    async def get_by_id(self, plan_id: UUID) -> Plan | None:
        row = await self.session.get(PlanModel, plan_id)
        return _to_plan(row) if row else None

    async def get_by_code(self, plan_code: str) -> Plan | None:
        result = await self.session.execute(
            select(PlanModel).where(PlanModel.plan_code == plan_code)
        )
        row = result.scalar_one_or_none()
        return _to_plan(row) if row else None

    async def list_active(
        self, *, plan_type: PlanType | None = None, country_code: str | None = None
    ) -> list[Plan]:
        stmt: Select[tuple[PlanModel]] = select(PlanModel).where(PlanModel.active.is_(True))
        if plan_type is not None:
            stmt = stmt.where(PlanModel.plan_type == plan_type.value)
        if country_code is not None:
            stmt = stmt.where(PlanModel.country_code == country_code)
        result = await self.session.execute(stmt)
        return [_to_plan(r) for r in result.scalars()]


class SqlSubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, subscription: Subscription) -> None:
        self.session.add(
            SubscriptionModel(
                id=subscription.id,
                customer_id=subscription.customer_id,
                plan_id=subscription.plan_id,
                started_at=subscription.started_at,
                ended_at=subscription.ended_at,
                status=subscription.status.value,
                source_event_id=subscription.source_event_id,
            )
        )

    async def list_by_customer(self, customer_id: UUID) -> list[Subscription]:
        result = await self.session.execute(
            select(SubscriptionModel).where(SubscriptionModel.customer_id == customer_id)
        )
        return [_to_subscription(r) for r in result.scalars()]

    async def active_at(
        self,
        customer_id: UUID,
        as_of: datetime,
        *,
        plan_type: PlanType | None = None,
    ) -> Subscription | None:
        stmt = (
            select(SubscriptionModel)
            .where(
                SubscriptionModel.customer_id == customer_id,
                SubscriptionModel.started_at <= as_of,
                (SubscriptionModel.ended_at.is_(None))
                | (SubscriptionModel.ended_at > as_of),
            )
            .order_by(SubscriptionModel.started_at.desc())
        )
        if plan_type is not None:
            stmt = stmt.join(PlanModel).where(PlanModel.plan_type == plan_type.value)
        result = await self.session.execute(stmt.limit(1))
        row = result.scalar_one_or_none()
        return _to_subscription(row) if row else None

    async def update(self, subscription: Subscription) -> None:
        row = await self.session.get(SubscriptionModel, subscription.id)
        if row is None:
            return
        row.ended_at = subscription.ended_at
        row.status = subscription.status.value
        row.source_event_id = subscription.source_event_id


class SqlLedgerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, entry: BalanceLedgerEntry) -> None:
        self.session.add(
            BalanceLedgerModel(
                id=entry.id,
                account_id=entry.account_id,
                customer_id=entry.customer_id,
                entry_type=entry.entry_type.value,
                amount=entry.amount,
                currency=entry.currency,
                occurred_at=entry.occurred_at,
                source_event_id=entry.source_event_id,
            )
        )

    async def list_by_customer(self, customer_id: UUID) -> list[BalanceLedgerEntry]:
        result = await self.session.execute(
            select(BalanceLedgerModel).where(BalanceLedgerModel.customer_id == customer_id)
        )
        return [_to_ledger(r) for r in result.scalars()]

    async def balance_at(self, account_id: UUID, as_of: datetime) -> Decimal:
        result = await self.session.execute(
            select(func.coalesce(func.sum(BalanceLedgerModel.amount), 0)).where(
                BalanceLedgerModel.account_id == account_id,
                BalanceLedgerModel.occurred_at <= as_of,
            )
        )
        value = result.scalar_one()
        return Decimal(value)


class SqlRechargeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, recharge: Recharge) -> None:
        self.session.add(
            RechargeModel(
                id=recharge.id,
                customer_id=recharge.customer_id,
                account_id=recharge.account_id,
                amount=recharge.amount,
                currency=recharge.currency,
                occurred_at=recharge.occurred_at,
                channel=recharge.channel,
                source_event_id=recharge.source_event_id,
            )
        )

    async def list_by_customer(self, customer_id: UUID) -> list[Recharge]:
        result = await self.session.execute(
            select(RechargeModel).where(RechargeModel.customer_id == customer_id)
        )
        return [_to_recharge(r) for r in result.scalars()]

    async def list_as_of(self, customer_id: UUID, as_of: datetime) -> list[Recharge]:
        result = await self.session.execute(
            select(RechargeModel).where(
                RechargeModel.customer_id == customer_id,
                RechargeModel.occurred_at <= as_of,
            )
        )
        return [_to_recharge(r) for r in result.scalars()]


class SqlUsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, usage: UsageEvent) -> None:
        self.session.add(
            UsageEventModel(
                id=usage.id,
                customer_id=usage.customer_id,
                occurred_at=usage.occurred_at,
                usage_type=usage.usage_type.value,
                data_mb=usage.data_mb,
                country_code=usage.country_code,
                network_type=usage.network_type,
                source_event_id=usage.source_event_id,
            )
        )

    async def list_by_customer(self, customer_id: UUID) -> list[UsageEvent]:
        result = await self.session.execute(
            select(UsageEventModel).where(UsageEventModel.customer_id == customer_id)
        )
        return [_to_usage(r) for r in result.scalars()]

    async def list_as_of(self, customer_id: UUID, as_of: datetime) -> list[UsageEvent]:
        result = await self.session.execute(
            select(UsageEventModel).where(
                UsageEventModel.customer_id == customer_id,
                UsageEventModel.occurred_at <= as_of,
            )
        )
        return [_to_usage(r) for r in result.scalars()]

    async def total_mb(
        self,
        customer_id: UUID,
        *,
        start: datetime,
        end: datetime,
        usage_type: UsageType | None = None,
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(UsageEventModel.data_mb), 0)).where(
            UsageEventModel.customer_id == customer_id,
            UsageEventModel.occurred_at >= start,
            UsageEventModel.occurred_at <= end,
        )
        if usage_type is not None:
            stmt = stmt.where(UsageEventModel.usage_type == usage_type.value)
        result = await self.session.execute(stmt)
        return Decimal(result.scalar_one())


class SqlTravelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, travel: Travel) -> None:
        self.session.add(
            TravelModel(
                id=travel.id,
                customer_id=travel.customer_id,
                country_code=travel.country_code,
                started_at=travel.started_at,
                ended_at=travel.ended_at,
                source=travel.source,
                start_event_id=travel.start_event_id,
                end_event_id=travel.end_event_id,
            )
        )

    async def list_by_customer(self, customer_id: UUID) -> list[Travel]:
        result = await self.session.execute(
            select(TravelModel).where(TravelModel.customer_id == customer_id)
        )
        return [_to_travel(r) for r in result.scalars()]

    async def list_as_of(self, customer_id: UUID, as_of: datetime) -> list[Travel]:
        result = await self.session.execute(
            select(TravelModel).where(
                TravelModel.customer_id == customer_id,
                TravelModel.started_at <= as_of,
            )
        )
        return [_to_travel(r) for r in result.scalars()]

    async def update(self, travel: Travel) -> None:
        row = await self.session.get(TravelModel, travel.id)
        if row is None:
            return
        row.ended_at = travel.ended_at
        row.end_event_id = travel.end_event_id


class SqlServiceInteractionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, interaction: ServiceInteraction) -> None:
        self.session.add(
            ServiceInteractionModel(
                id=interaction.id,
                customer_id=interaction.customer_id,
                interaction_type=interaction.interaction_type,
                occurred_at=interaction.occurred_at,
                category=interaction.category,
                severity=interaction.severity,
                status=interaction.status,
                resolved_at=interaction.resolved_at,
                source_event_id=interaction.source_event_id,
            )
        )

    async def list_by_customer(self, customer_id: UUID) -> list[ServiceInteraction]:
        result = await self.session.execute(
            select(ServiceInteractionModel).where(
                ServiceInteractionModel.customer_id == customer_id
            )
        )
        return [_to_interaction(r) for r in result.scalars()]

    async def open_count(self, customer_id: UUID, as_of: datetime) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(ServiceInteractionModel)
            .where(
                ServiceInteractionModel.customer_id == customer_id,
                ServiceInteractionModel.occurred_at <= as_of,
                (ServiceInteractionModel.resolved_at.is_(None))
                | (ServiceInteractionModel.resolved_at > as_of),
            )
        )
        return int(result.scalar_one())


class SqlEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, event: ActivityEvent) -> None:
        self.session.add(
            ActivityEventModel(
                id=event.id,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                customer_id=event.customer_id,
                event_type=str(event.event_type),
                occurred_at=event.occurred_at,
                recorded_at=event.recorded_at,
                source=event.source,
                correlation_id=event.correlation_id,
                idempotency_key=event.idempotency_key,
                payload=event.payload,
            )
        )

    async def list_timeline(
        self, customer_id: UUID, *, as_of: datetime | None = None
    ) -> list[ActivityEvent]:
        stmt = select(ActivityEventModel).where(
            ActivityEventModel.customer_id == customer_id
        )
        if as_of is not None:
            stmt = stmt.where(ActivityEventModel.occurred_at <= as_of)
        stmt = stmt.order_by(
            ActivityEventModel.occurred_at, ActivityEventModel.recorded_at
        )
        result = await self.session.execute(stmt)
        return [_to_event(r) for r in result.scalars()]


class SqlOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, event: OutboxEvent) -> None:
        self.session.add(
            OutboxEventModel(
                id=event.id,
                event_id=event.event_id,
                event_type=event.event_type,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                payload=event.payload,
                created_at=event.created_at,
                processed_at=event.processed_at,
                attempt_count=event.attempt_count,
                last_error=event.last_error,
                status=event.status.value,
            )
        )

    async def list_pending(self, limit: int = 100) -> list[OutboxEvent]:
        result = await self.session.execute(
            select(OutboxEventModel)
            .where(OutboxEventModel.status == OutboxStatus.PENDING.value)
            .order_by(OutboxEventModel.created_at)
            .limit(limit)
        )
        return [_to_outbox(r) for r in result.scalars()]


class SqlWarningRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, warning: Warning) -> None:
        self.session.add(
            WarningModel(
                id=warning.id,
                customer_id=warning.customer_id,
                warning_type=warning.warning_type.value,
                severity=warning.severity.value,
                occurred_at=warning.occurred_at,
                as_of=warning.as_of,
                evidence=warning.evidence,
                related_event_id=warning.related_event_id,
                created_at=warning.created_at,
            )
        )

    async def list_by_customer(
        self, customer_id: UUID, *, as_of: datetime | None = None
    ) -> list[Warning]:
        stmt = select(WarningModel).where(WarningModel.customer_id == customer_id)
        if as_of is not None:
            stmt = stmt.where(WarningModel.occurred_at <= as_of)
        stmt = stmt.order_by(WarningModel.occurred_at)
        result = await self.session.execute(stmt)
        return [_to_warning(r) for r in result.scalars()]


def _to_customer(row: CustomerModel) -> Customer:
    return Customer(
        id=row.id,
        customer_ref=row.customer_ref,
        home_country=row.home_country,
        account_type=AccountType(row.account_type),
        status=CustomerStatus(row.status),
        customer_since=row.customer_since,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_account(row: AccountModel) -> Account:
    return Account(
        id=row.id,
        customer_id=row.customer_id,
        account_ref=row.account_ref,
        account_type=AccountType(row.account_type),
        currency=row.currency,
        status=AccountStatus(row.status),
        created_at=row.created_at,
    )


def _to_device(row: DeviceModel) -> Device:
    return Device(
        id=row.id,
        device_ref=row.device_ref,
        device_type=row.device_type,
        model=row.model,
        fingerprint=row.fingerprint,
        first_seen_at=row.first_seen_at,
    )


def _to_customer_device(row: CustomerDeviceModel) -> CustomerDevice:
    return CustomerDevice(
        id=row.id,
        customer_id=row.customer_id,
        device_id=row.device_id,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
    )


def _to_plan(row: PlanModel) -> Plan:
    return Plan(
        id=row.id,
        plan_code=row.plan_code,
        name=row.name,
        plan_type=PlanType(row.plan_type),
        data_mb=row.data_mb,
        validity_days=row.validity_days,
        price=row.price,
        currency=row.currency,
        country_code=row.country_code,
        country_group=row.country_group,
        active=row.active,
        created_at=row.created_at,
    )


def _to_subscription(row: SubscriptionModel) -> Subscription:
    return Subscription(
        id=row.id,
        customer_id=row.customer_id,
        plan_id=row.plan_id,
        started_at=row.started_at,
        ended_at=row.ended_at,
        status=SubscriptionStatus(row.status),
        source_event_id=row.source_event_id,
    )


def _to_ledger(row: BalanceLedgerModel) -> BalanceLedgerEntry:
    return BalanceLedgerEntry(
        id=row.id,
        account_id=row.account_id,
        customer_id=row.customer_id,
        entry_type=LedgerEntryType(row.entry_type),
        amount=row.amount,
        currency=row.currency,
        occurred_at=row.occurred_at,
        source_event_id=row.source_event_id,
    )


def _to_recharge(row: RechargeModel) -> Recharge:
    return Recharge(
        id=row.id,
        customer_id=row.customer_id,
        account_id=row.account_id,
        amount=row.amount,
        currency=row.currency,
        occurred_at=row.occurred_at,
        channel=row.channel,
        source_event_id=row.source_event_id,
    )


def _to_usage(row: UsageEventModel) -> UsageEvent:
    return UsageEvent(
        id=row.id,
        customer_id=row.customer_id,
        occurred_at=row.occurred_at,
        usage_type=UsageType(row.usage_type),
        data_mb=row.data_mb,
        country_code=row.country_code,
        network_type=row.network_type,
        source_event_id=row.source_event_id,
    )


def _to_travel(row: TravelModel) -> Travel:
    return Travel(
        id=row.id,
        customer_id=row.customer_id,
        country_code=row.country_code,
        started_at=row.started_at,
        ended_at=row.ended_at,
        source=row.source,
        start_event_id=row.start_event_id,
        end_event_id=row.end_event_id,
    )


def _to_interaction(row: ServiceInteractionModel) -> ServiceInteraction:
    return ServiceInteraction(
        id=row.id,
        customer_id=row.customer_id,
        interaction_type=row.interaction_type,
        occurred_at=row.occurred_at,
        category=row.category,
        severity=row.severity,
        status=row.status,
        resolved_at=row.resolved_at,
        source_event_id=row.source_event_id,
    )


def _to_event(row: ActivityEventModel) -> ActivityEvent:
    return ActivityEvent(
        id=row.id,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        customer_id=row.customer_id,
        event_type=row.event_type,
        occurred_at=row.occurred_at,
        recorded_at=row.recorded_at,
        source=row.source,
        correlation_id=row.correlation_id,
        idempotency_key=row.idempotency_key,
        payload=row.payload or {},
    )


def _to_outbox(row: OutboxEventModel) -> OutboxEvent:
    return OutboxEvent(
        id=row.id,
        event_id=row.event_id,
        event_type=row.event_type,
        aggregate_type=row.aggregate_type,
        aggregate_id=row.aggregate_id,
        payload=row.payload or {},
        created_at=row.created_at,
        processed_at=row.processed_at,
        attempt_count=row.attempt_count,
        last_error=row.last_error,
        status=OutboxStatus(row.status),
    )


def _to_warning(row: WarningModel) -> Warning:
    return Warning(
        id=row.id,
        customer_id=row.customer_id,
        warning_type=WarningType(row.warning_type),
        severity=WarningSeverity(row.severity),
        occurred_at=row.occurred_at,
        as_of=row.as_of,
        evidence=row.evidence or {},
        related_event_id=row.related_event_id,
        created_at=row.created_at,
    )
