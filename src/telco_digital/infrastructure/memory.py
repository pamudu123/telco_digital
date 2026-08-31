from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

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
from telco_digital.domain.enums import PlanType, UsageType


def _as_of_ok(occurred_at: datetime, as_of: datetime) -> bool:
    return occurred_at <= as_of


class _Store[T]:
    def __init__(self) -> None:
        self.items: dict[UUID, T] = {}

    async def add(self, item: T) -> None:
        self.items[item.id] = item  # type: ignore[attr-defined]

    def all(self) -> list[T]:
        return list(self.items.values())


class InMemoryCustomerRepository:
    def __init__(self, store: _Store[Customer]) -> None:
        self._store = store

    async def add(self, customer: Customer) -> None:
        await self._store.add(customer)

    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        return self._store.items.get(customer_id)

    async def get_by_ref(self, customer_ref: str) -> Customer | None:
        for customer in self._store.all():
            if customer.customer_ref == customer_ref:
                return customer
        return None

    async def list_all(self) -> list[Customer]:
        return self._store.all()


class InMemoryAccountRepository:
    def __init__(self, store: _Store[Account]) -> None:
        self._store = store

    async def add(self, account: Account) -> None:
        await self._store.add(account)

    async def get_by_id(self, account_id: UUID) -> Account | None:
        return self._store.items.get(account_id)

    async def list_by_customer(self, customer_id: UUID) -> list[Account]:
        accounts = [a for a in self._store.all() if a.customer_id == customer_id]
        return sorted(accounts, key=lambda account: (account.created_at, account.account_ref))


class InMemoryDeviceRepository:
    def __init__(self, store: _Store[Device]) -> None:
        self._store = store

    async def add(self, device: Device) -> None:
        await self._store.add(device)

    async def get_by_id(self, device_id: UUID) -> Device | None:
        return self._store.items.get(device_id)

    async def get_by_ref(self, device_ref: str) -> Device | None:
        for device in self._store.all():
            if device.device_ref == device_ref:
                return device
        return None


class InMemoryCustomerDeviceRepository:
    def __init__(self, store: _Store[CustomerDevice]) -> None:
        self._store = store

    async def add(self, link: CustomerDevice) -> None:
        await self._store.add(link)

    async def list_by_customer(self, customer_id: UUID) -> list[CustomerDevice]:
        return [link for link in self._store.all() if link.customer_id == customer_id]

    async def list_by_device(self, device_id: UUID) -> list[CustomerDevice]:
        return [link for link in self._store.all() if link.device_id == device_id]

    async def active_at(self, customer_id: UUID, as_of: datetime) -> CustomerDevice | None:
        matches = [
            link
            for link in await self.list_by_customer(customer_id)
            if link.valid_from <= as_of and (link.valid_to is None or link.valid_to > as_of)
        ]
        if not matches:
            return None
        return max(matches, key=lambda link: link.valid_from)


class InMemoryPlanRepository:
    def __init__(self, store: _Store[Plan]) -> None:
        self._store = store

    async def add(self, plan: Plan) -> None:
        await self._store.add(plan)

    async def get_by_id(self, plan_id: UUID) -> Plan | None:
        return self._store.items.get(plan_id)

    async def get_by_code(self, plan_code: str) -> Plan | None:
        for plan in self._store.all():
            if plan.plan_code == plan_code:
                return plan
        return None

    async def list_active(
        self, *, plan_type: PlanType | None = None, country_code: str | None = None
    ) -> list[Plan]:
        plans = [p for p in self._store.all() if p.active]
        if plan_type is not None:
            plans = [p for p in plans if p.plan_type == plan_type]
        if country_code is not None:
            plans = [p for p in plans if p.country_code == country_code]
        return plans


class InMemorySubscriptionRepository:
    def __init__(self, store: _Store[Subscription], plans: _Store[Plan]) -> None:
        self._store = store
        self._plans = plans

    async def add(self, subscription: Subscription) -> None:
        await self._store.add(subscription)

    async def list_by_customer(self, customer_id: UUID) -> list[Subscription]:
        return [s for s in self._store.all() if s.customer_id == customer_id]

    async def active_at(
        self,
        customer_id: UUID,
        as_of: datetime,
        *,
        plan_type: PlanType | None = None,
    ) -> Subscription | None:
        matches = [
            s
            for s in await self.list_by_customer(customer_id)
            if s.started_at <= as_of
            and (s.ended_at is None or s.ended_at > as_of)
            and (
                (plan := self._plans.items.get(s.plan_id)) is not None
                and s.started_at + timedelta(days=plan.validity_days) > as_of
            )
        ]
        if plan_type is not None:
            plan_ids = {p.id for p in self._plans.all() if p.plan_type == plan_type}
            matches = [s for s in matches if s.plan_id in plan_ids]
        if not matches:
            return None
        return max(matches, key=lambda s: s.started_at)

    async def update(self, subscription: Subscription) -> None:
        if subscription.id not in self._store.items:
            raise LookupError(f"Unknown subscription: {subscription.id}")
        self._store.items[subscription.id] = subscription


class InMemoryLedgerRepository:
    def __init__(self, store: _Store[BalanceLedgerEntry]) -> None:
        self._store = store

    async def add(self, entry: BalanceLedgerEntry) -> None:
        await self._store.add(entry)

    async def list_by_customer(self, customer_id: UUID) -> list[BalanceLedgerEntry]:
        return [e for e in self._store.all() if e.customer_id == customer_id]

    async def balance_at(self, account_id: UUID, as_of: datetime) -> Decimal:
        total = Decimal("0")
        for entry in self._store.all():
            if entry.account_id == account_id and _as_of_ok(entry.occurred_at, as_of):
                total += entry.amount
        return total


class InMemoryRechargeRepository:
    def __init__(self, store: _Store[Recharge]) -> None:
        self._store = store

    async def add(self, recharge: Recharge) -> None:
        await self._store.add(recharge)

    async def list_by_customer(self, customer_id: UUID) -> list[Recharge]:
        return [r for r in self._store.all() if r.customer_id == customer_id]

    async def list_as_of(self, customer_id: UUID, as_of: datetime) -> list[Recharge]:
        return [
            r for r in await self.list_by_customer(customer_id) if _as_of_ok(r.occurred_at, as_of)
        ]


class InMemoryUsageRepository:
    def __init__(self, store: _Store[UsageEvent]) -> None:
        self._store = store

    async def add(self, usage: UsageEvent) -> None:
        await self._store.add(usage)

    async def list_by_customer(self, customer_id: UUID) -> list[UsageEvent]:
        return [u for u in self._store.all() if u.customer_id == customer_id]

    async def list_as_of(self, customer_id: UUID, as_of: datetime) -> list[UsageEvent]:
        return [
            u for u in await self.list_by_customer(customer_id) if _as_of_ok(u.occurred_at, as_of)
        ]

    async def total_mb(
        self,
        customer_id: UUID,
        *,
        start: datetime,
        end: datetime,
        usage_type: UsageType | None = None,
    ) -> Decimal:
        total = Decimal("0")
        for usage in await self.list_by_customer(customer_id):
            if usage.occurred_at < start or usage.occurred_at > end:
                continue
            if usage_type is not None and usage.usage_type != usage_type:
                continue
            total += usage.data_mb
        return total


class InMemoryTravelRepository:
    def __init__(self, store: _Store[Travel]) -> None:
        self._store = store

    async def add(self, travel: Travel) -> None:
        await self._store.add(travel)

    async def list_by_customer(self, customer_id: UUID) -> list[Travel]:
        return [t for t in self._store.all() if t.customer_id == customer_id]

    async def list_as_of(self, customer_id: UUID, as_of: datetime) -> list[Travel]:
        return [t for t in await self.list_by_customer(customer_id) if t.started_at <= as_of]

    async def list_peer_customer_ids(
        self,
        *,
        exclude_customer_id: UUID,
        as_of: datetime,
        destination: str | None = None,
        limit: int = 25,
    ) -> list[UUID]:
        latest: dict[UUID, datetime] = {}
        for travel in self._store.all():
            if travel.customer_id == exclude_customer_id:
                continue
            if travel.started_at > as_of:
                continue
            if destination is not None and travel.country_code != destination:
                continue
            current = latest.get(travel.customer_id)
            if current is None or travel.started_at > current:
                latest[travel.customer_id] = travel.started_at
        ordered = sorted(latest, key=lambda customer_id: latest[customer_id], reverse=True)
        return ordered[:limit]

    async def update(self, travel: Travel) -> None:
        if travel.id not in self._store.items:
            raise LookupError(f"Unknown travel: {travel.id}")
        self._store.items[travel.id] = travel


class InMemoryServiceInteractionRepository:
    def __init__(self, store: _Store[ServiceInteraction]) -> None:
        self._store = store

    async def add(self, interaction: ServiceInteraction) -> None:
        await self._store.add(interaction)

    async def list_by_customer(self, customer_id: UUID) -> list[ServiceInteraction]:
        return [i for i in self._store.all() if i.customer_id == customer_id]

    async def open_count(self, customer_id: UUID, as_of: datetime) -> int:
        return sum(
            item.occurred_at <= as_of and (item.resolved_at is None or item.resolved_at > as_of)
            for item in await self.list_by_customer(customer_id)
        )


class InMemoryEventRepository:
    def __init__(self, store: _Store[ActivityEvent]) -> None:
        self._store = store

    async def add(self, event: ActivityEvent) -> None:
        await self._store.add(event)

    async def list_timeline(
        self, customer_id: UUID, *, as_of: datetime | None = None
    ) -> list[ActivityEvent]:
        events = [e for e in self._store.all() if e.customer_id == customer_id]
        if as_of is not None:
            events = [e for e in events if e.occurred_at <= as_of]
        return sorted(events, key=lambda e: (e.occurred_at, e.recorded_at))


class InMemoryOutboxRepository:
    def __init__(self, store: _Store[OutboxEvent]) -> None:
        self._store = store

    async def add(self, event: OutboxEvent) -> None:
        await self._store.add(event)

    async def list_pending(self, limit: int = 100) -> list[OutboxEvent]:
        pending = [e for e in self._store.all() if e.status.value == "PENDING"]
        pending.sort(key=lambda e: e.created_at)
        return pending[:limit]

    async def list_all(self) -> list[OutboxEvent]:
        return self._store.all()


class InMemoryProjectionLagQueries:
    def __init__(self, outbox: InMemoryOutboxRepository) -> None:
        self._outbox = outbox

    async def snapshot(self):
        from telco_digital.application.services.platform import snapshot_from_events

        return snapshot_from_events(await self._outbox.list_all())


class InMemoryWarningRepository:
    def __init__(self, store: _Store[Warning]) -> None:
        self._store = store

    async def add(self, warning: Warning) -> None:
        await self._store.add(warning)

    async def list_by_customer(
        self, customer_id: UUID, *, as_of: datetime | None = None
    ) -> list[Warning]:
        warnings = [w for w in self._store.all() if w.customer_id == customer_id]
        if as_of is not None:
            warnings = [w for w in warnings if w.occurred_at <= as_of]
        return sorted(warnings, key=lambda w: w.occurred_at)


class InMemoryUnitOfWork:
    """Unit of work used by tests and by the POC before Postgres is running."""

    def __init__(self) -> None:
        self._customers = _Store[Customer]()
        self._accounts = _Store[Account]()
        self._devices = _Store[Device]()
        self._customer_devices = _Store[CustomerDevice]()
        self._plans = _Store[Plan]()
        self._subscriptions = _Store[Subscription]()
        self._ledgers = _Store[BalanceLedgerEntry]()
        self._recharges = _Store[Recharge]()
        self._usage = _Store[UsageEvent]()
        self._travels = _Store[Travel]()
        self._interactions = _Store[ServiceInteraction]()
        self._events = _Store[ActivityEvent]()
        self._outbox = _Store[OutboxEvent]()
        self._warnings = _Store[Warning]()
        self.customers = InMemoryCustomerRepository(self._customers)
        self.accounts = InMemoryAccountRepository(self._accounts)
        self.devices = InMemoryDeviceRepository(self._devices)
        self.customer_devices = InMemoryCustomerDeviceRepository(self._customer_devices)
        self.plans = InMemoryPlanRepository(self._plans)
        self.subscriptions = InMemorySubscriptionRepository(self._subscriptions, self._plans)
        self.ledgers = InMemoryLedgerRepository(self._ledgers)
        self.recharges = InMemoryRechargeRepository(self._recharges)
        self.usage_events = InMemoryUsageRepository(self._usage)
        self.travels = InMemoryTravelRepository(self._travels)
        self.service_interactions = InMemoryServiceInteractionRepository(self._interactions)
        self.events = InMemoryEventRepository(self._events)
        self.outbox = InMemoryOutboxRepository(self._outbox)
        self.warnings = InMemoryWarningRepository(self._warnings)
        self.committed = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        return None

    async def __aenter__(self) -> InMemoryUnitOfWork:
        self.committed = False
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            await self.rollback()
