"""Bulk loader for the deterministic POC dataset."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from telco_digital.application.demo_dataset import DATASET_VERSION, DatasetBundle
from telco_digital.infrastructure.postgres.models import (
    AccountModel,
    ActivityEventModel,
    BalanceLedgerModel,
    CampaignInteractionModel,
    CampaignModel,
    CustomerDeviceModel,
    CustomerModel,
    DeviceModel,
    DistributorModel,
    InventoryEventModel,
    LoyaltyAccountModel,
    LoyaltyLedgerModel,
    MerchantModel,
    MoneyTransactionModel,
    OutboxEventModel,
    PlanModel,
    RechargeModel,
    RetailerModel,
    SaleModel,
    SalesAgentModel,
    ServiceInteractionModel,
    SfaProductModel,
    SubscriptionModel,
    TravelModel,
    UsageEventModel,
    WalletModel,
)

TABLES = {
    "plans": PlanModel.__table__,
    "campaigns": CampaignModel.__table__,
    "merchants": MerchantModel.__table__,
    "distributors": DistributorModel.__table__,
    "sfa_products": SfaProductModel.__table__,
    "customers": CustomerModel.__table__,
    "accounts": AccountModel.__table__,
    "devices": DeviceModel.__table__,
    "customer_devices": CustomerDeviceModel.__table__,
    "wallets": WalletModel.__table__,
    "loyalty_accounts": LoyaltyAccountModel.__table__,
    "retailers": RetailerModel.__table__,
    "sales_agents": SalesAgentModel.__table__,
    "subscriptions": SubscriptionModel.__table__,
    "recharges": RechargeModel.__table__,
    "balance_ledger": BalanceLedgerModel.__table__,
    "usage_events": UsageEventModel.__table__,
    "travels": TravelModel.__table__,
    "service_interactions": ServiceInteractionModel.__table__,
    "loyalty_ledger": LoyaltyLedgerModel.__table__,
    "campaign_interactions": CampaignInteractionModel.__table__,
    "money_transactions": MoneyTransactionModel.__table__,
    "sales": SaleModel.__table__,
    "inventory_events": InventoryEventModel.__table__,
    "activity_events": ActivityEventModel.__table__,
    "outbox_events": OutboxEventModel.__table__,
}

INSERT_ORDER = tuple(TABLES)
DELETE_ORDER = tuple(reversed(INSERT_ORDER))


async def load_dataset(
    engine: AsyncEngine,
    bundle: DatasetBundle,
    *,
    batch_size: int = 750,
) -> dict[str, int]:
    """Insert all rows in one transaction; deterministic primary keys make reruns safe."""
    attempted: dict[str, int] = {}
    async with engine.begin() as connection:
        for name in INSERT_ORDER:
            rows = bundle.rows.get(name, [])
            attempted[name] = len(rows)
            for start in range(0, len(rows), batch_size):
                statement = pg_insert(TABLES[name]).values(rows[start : start + batch_size])
                await connection.execute(statement.on_conflict_do_nothing())
    return attempted


async def reset_dataset(engine: AsyncEngine, bundle: DatasetBundle) -> dict[str, int]:
    """Delete only deterministic rows owned by this dataset version."""
    deleted: dict[str, int] = {}
    async with engine.begin() as connection:
        for name in DELETE_ORDER:
            rows = bundle.rows.get(name, [])
            ids = [row["id"] for row in rows]
            total = 0
            for start in range(0, len(ids), 750):
                result = await connection.execute(
                    delete(TABLES[name]).where(TABLES[name].c.id.in_(ids[start : start + 750]))
                )
                total += result.rowcount or 0
            deleted[name] = total
    return deleted


async def validate_dataset(
    engine: AsyncEngine,
    expected: Mapping[str, int],
) -> dict[str, Any]:
    """Validate core POC ownership, event parity, and expected customer population."""
    async with engine.connect() as connection:
        new_customers = await connection.scalar(
            select(func.count())
            .select_from(CustomerModel)
            .where(
                CustomerModel.customer_ref.in_(["U006", "U007", "U008", "U009", "U010"])
                | CustomerModel.customer_ref.like("BG%")
            )
        )
        activity_events = await connection.scalar(
            select(func.count())
            .select_from(ActivityEventModel)
            .where(ActivityEventModel.source == DATASET_VERSION)
        )
        outbox_events = await connection.scalar(
            select(func.count())
            .select_from(OutboxEventModel)
            .where(OutboxEventModel.payload["dataset_version"].astext == DATASET_VERSION)
        )
        total_customers = await connection.scalar(select(func.count()).select_from(CustomerModel))
    expected_new = expected.get("customers", 0)
    return {
        "dataset_version": DATASET_VERSION,
        "new_customer_rows": int(new_customers or 0),
        "expected_new_customer_rows": expected_new,
        "total_customer_rows": int(total_customers or 0),
        "activity_event_rows": int(activity_events or 0),
        "outbox_event_rows": int(outbox_events or 0),
        "event_outbox_parity": activity_events == outbox_events,
        "customer_count_valid": new_customers == expected_new,
        "valid": activity_events == outbox_events and new_customers == expected_new,
    }
