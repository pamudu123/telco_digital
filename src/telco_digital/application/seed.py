from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from telco_digital.application.clock import Clock, SystemClock
from telco_digital.application.commands.commands import (
    CreateCustomerCommand,
    CreatePlanCommand,
    EndTravelCommand,
    PurchasePlanCommand,
    RecordRechargeCommand,
    RecordServiceInteractionCommand,
    RecordTravelCommand,
    RecordUsageCommand,
)
from telco_digital.application.services.catalog import create_plan
from telco_digital.application.services.customer import create_customer
from telco_digital.application.services.plan_purchase import purchase_plan
from telco_digital.application.services.recharge import record_recharge
from telco_digital.application.services.service_interaction import record_service_interaction
from telco_digital.application.services.travel import end_travel, record_travel
from telco_digital.application.services.usage import record_usage
from telco_digital.application.unit_of_work.protocol import UnitOfWork
from telco_digital.domain.enums import AccountType, UsageType
from telco_digital.domain.value_objects import normalize_country


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


CATALOGUE = [
    CreatePlanCommand(
        plan_code="PLAN_A",
        name="Local Data A",
        plan_type="LOCAL",
        data_mb=10240,
        validity_days=30,
        price=Decimal("300"),
        currency="LKR",
        created_at=_dt("2025-01-01T00:00:00+00:00"),
    ),
    CreatePlanCommand(
        plan_code="ROAM_5",
        name="Roaming 5GB",
        plan_type="ROAMING",
        data_mb=5120,
        validity_days=5,
        price=Decimal("150"),
        currency="LKR",
        country_code="SG",
        created_at=_dt("2025-01-01T00:00:00+00:00"),
    ),
    CreatePlanCommand(
        plan_code="ROAM_15",
        name="Roaming 15GB",
        plan_type="ROAMING",
        data_mb=15360,
        validity_days=15,
        price=Decimal("350"),
        currency="LKR",
        country_code="SG",
        created_at=_dt("2025-01-01T00:00:00+00:00"),
    ),
    CreatePlanCommand(
        plan_code="ROAM_30",
        name="Roaming 30GB",
        plan_type="ROAMING",
        data_mb=30720,
        validity_days=30,
        price=Decimal("600"),
        currency="LKR",
        country_code="SG",
        created_at=_dt("2025-01-01T00:00:00+00:00"),
    ),
]


async def seed_catalogue(uow: UnitOfWork, *, clock: Clock | None = None) -> None:
    for plan in CATALOGUE:
        await create_plan(uow, plan, clock=clock)


async def seed_demo_customers(uow: UnitOfWork, *, clock: Clock | None = None) -> None:
    """Deterministic U001–U005 personas from the locked plan."""
    clock = clock or SystemClock()
    await seed_catalogue(uow, clock=clock)
    await _seed_u001(uow, clock)
    await _seed_u002(uow, clock)
    await _seed_u003(uow, clock)
    await _seed_u004(uow, clock)
    await _seed_u005(uow, clock)


async def _seed_u001(uow: UnitOfWork, clock: Clock) -> None:
    """Frequent traveller, heavy data. March Singapore trip used for memory."""
    await create_customer(
        uow,
        CreateCustomerCommand(
            customer_ref="U001",
            home_country="Sri Lanka",
            account_type=AccountType.PREPAID,
            customer_since=_dt("2024-01-15T00:00:00+00:00"),
            device_ref="D001",
            device_model="Pixel",
            correlation_id="seed-u001",
        ),
        clock=clock,
    )
    await record_recharge(
        uow,
        RecordRechargeCommand(
            customer_ref="U001",
            amount=Decimal("2000"),
            occurred_at=_dt("2026-03-01T08:00:00+00:00"),
            correlation_id="seed-u001",
        ),
        clock=clock,
    )
    await purchase_plan(
        uow,
        PurchasePlanCommand(
            customer_ref="U001",
            plan_code="PLAN_A",
            occurred_at=_dt("2026-03-01T08:05:00+00:00"),
            correlation_id="seed-u001",
        ),
        clock=clock,
    )
    await record_travel(
        uow,
        RecordTravelCommand(
            customer_ref="U001",
            country="Singapore",
            started_at=_dt("2026-03-10T08:00:00+00:00"),
            correlation_id="seed-u001",
        ),
        clock=clock,
    )
    await purchase_plan(
        uow,
        PurchasePlanCommand(
            customer_ref="U001",
            plan_code="ROAM_15",
            occurred_at=_dt("2026-03-10T09:00:00+00:00"),
            correlation_id="seed-u001",
        ),
        clock=clock,
    )
    # 11.4 GB across the trip
    usage_days = [
        ("2026-03-10T20:00:00+00:00", Decimal("1800")),
        ("2026-03-11T20:00:00+00:00", Decimal("2100")),
        ("2026-03-12T20:00:00+00:00", Decimal("1900")),
        ("2026-03-13T20:00:00+00:00", Decimal("1700")),
        ("2026-03-14T20:00:00+00:00", Decimal("1600")),
        ("2026-03-15T20:00:00+00:00", Decimal("1400")),
        ("2026-03-16T12:00:00+00:00", Decimal("900")),
    ]
    for occurred, mb in usage_days:
        await record_usage(
            uow,
            RecordUsageCommand(
                customer_ref="U001",
                occurred_at=_dt(occurred),
                data_mb=mb,
                usage_type=UsageType.STREAMING,
                country="Singapore",
                correlation_id="seed-u001",
            ),
            clock=clock,
        )
    await end_travel(
        uow,
        EndTravelCommand(
            customer_ref="U001",
            ended_at=_dt("2026-03-16T18:00:00+00:00"),
            correlation_id="seed-u001",
        ),
        clock=clock,
    )


async def _seed_u002(uow: UnitOfWork, clock: Clock) -> None:
    """Price sensitive, frequent small recharge. Shares D001 for graph demo."""
    await create_customer(
        uow,
        CreateCustomerCommand(
            customer_ref="U002",
            home_country="Sri Lanka",
            account_type=AccountType.PREPAID,
            customer_since=_dt("2024-06-01T00:00:00+00:00"),
            device_ref="D001",
            correlation_id="seed-u002",
        ),
        clock=clock,
    )
    for day in ("05", "08", "12", "16", "20"):
        await record_recharge(
            uow,
            RecordRechargeCommand(
                customer_ref="U002",
                amount=Decimal("100"),
                occurred_at=_dt(f"2026-08-{day}T10:00:00+00:00"),
                correlation_id="seed-u002",
            ),
            clock=clock,
        )


async def _seed_u003(uow: UnitOfWork, clock: Clock) -> None:
    """High value, stable control customer."""
    await create_customer(
        uow,
        CreateCustomerCommand(
            customer_ref="U003",
            home_country="Sri Lanka",
            account_type=AccountType.POSTPAID,
            customer_since=_dt("2020-03-01T00:00:00+00:00"),
            device_ref="D003",
            correlation_id="seed-u003",
        ),
        clock=clock,
    )
    await record_recharge(
        uow,
        RecordRechargeCommand(
            customer_ref="U003",
            amount=Decimal("5000"),
            occurred_at=_dt("2026-08-01T09:00:00+00:00"),
            correlation_id="seed-u003",
        ),
        clock=clock,
    )
    await purchase_plan(
        uow,
        PurchasePlanCommand(
            customer_ref="U003",
            plan_code="PLAN_A",
            occurred_at=_dt("2026-08-01T09:05:00+00:00"),
            correlation_id="seed-u003",
        ),
        clock=clock,
    )


async def _seed_u004(uow: UnitOfWork, clock: Clock) -> None:
    """Declining engagement and network problems — churn persona."""
    await create_customer(
        uow,
        CreateCustomerCommand(
            customer_ref="U004",
            home_country="Sri Lanka",
            account_type=AccountType.PREPAID,
            customer_since=_dt("2023-01-01T00:00:00+00:00"),
            device_ref="D004",
            correlation_id="seed-u004",
        ),
        clock=clock,
    )
    await record_recharge(
        uow,
        RecordRechargeCommand(
            customer_ref="U004",
            amount=Decimal("1000"),
            occurred_at=_dt("2026-05-01T09:00:00+00:00"),
            correlation_id="seed-u004",
        ),
        clock=clock,
    )
    await purchase_plan(
        uow,
        PurchasePlanCommand(
            customer_ref="U004",
            plan_code="PLAN_A",
            occurred_at=_dt("2026-05-01T09:10:00+00:00"),
            correlation_id="seed-u004",
        ),
        clock=clock,
    )
    await record_usage(
        uow,
        RecordUsageCommand(
            customer_ref="U004",
            occurred_at=_dt("2026-05-10T18:00:00+00:00"),
            data_mb=Decimal("2500"),
            usage_type=UsageType.STREAMING,
            correlation_id="seed-u004",
        ),
        clock=clock,
    )
    await record_usage(
        uow,
        RecordUsageCommand(
            customer_ref="U004",
            occurred_at=_dt("2026-08-10T18:00:00+00:00"),
            data_mb=Decimal("200"),
            usage_type=UsageType.BROWSING,
            correlation_id="seed-u004",
        ),
        clock=clock,
    )
    await record_service_interaction(
        uow,
        RecordServiceInteractionCommand(
            customer_ref="U004",
            interaction_type="NETWORK_ISSUE",
            occurred_at=_dt("2026-08-12T11:00:00+00:00"),
            severity="HIGH",
            status="OPEN",
            correlation_id="seed-u004",
        ),
        clock=clock,
    )
    await record_service_interaction(
        uow,
        RecordServiceInteractionCommand(
            customer_ref="U004",
            interaction_type="COMPLAINT",
            occurred_at=_dt("2026-08-18T11:00:00+00:00"),
            severity="MEDIUM",
            status="OPEN",
            correlation_id="seed-u004",
        ),
        clock=clock,
    )


async def _seed_u005(uow: UnitOfWork, clock: Clock) -> None:
    """Suspicious device/wallet relationships — graph fraud persona."""
    await create_customer(
        uow,
        CreateCustomerCommand(
            customer_ref="U005",
            home_country="Sri Lanka",
            account_type=AccountType.PREPAID,
            customer_since=_dt("2026-07-01T00:00:00+00:00"),
            device_ref="D001",
            correlation_id="seed-u005",
        ),
        clock=clock,
    )
    await record_recharge(
        uow,
        RecordRechargeCommand(
            customer_ref="U005",
            amount=Decimal("800"),
            occurred_at=_dt("2026-08-01T12:00:00+00:00"),
            correlation_id="seed-u005",
        ),
        clock=clock,
    )


def country_code(name: str) -> str:
    return normalize_country(name)
