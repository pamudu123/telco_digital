"""Read an authoritative PostgreSQL snapshot for the rebuildable graph."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from telco_digital.infrastructure.neo4j.projector import GraphSnapshot
from telco_digital.infrastructure.postgres.models import (
    AccountModel,
    CustomerDeviceModel,
    CustomerModel,
    DeviceModel,
    DistributorModel,
    InventoryEventModel,
    MerchantModel,
    MoneyTransactionModel,
    PlanModel,
    RetailerModel,
    SaleModel,
    SalesAgentModel,
    SfaProductModel,
    SubscriptionModel,
    WalletModel,
)


def neo4j_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


async def load_graph_snapshot(engine: AsyncEngine, *, retries: int = 3) -> GraphSnapshot:
    models = {
        "customers": CustomerModel,
        "accounts": AccountModel,
        "devices": DeviceModel,
        "customer_devices": CustomerDeviceModel,
        "plans": PlanModel,
        "subscriptions": SubscriptionModel,
        "wallets": WalletModel,
        "merchants": MerchantModel,
        "transactions": MoneyTransactionModel,
        "distributors": DistributorModel,
        "retailers": RetailerModel,
        "sales_agents": SalesAgentModel,
        "products": SfaProductModel,
        "sales": SaleModel,
        "inventory_events": InventoryEventModel,
    }
    for attempt in range(1, retries + 1):
        try:
            async with engine.connect() as raw_connection:
                connection = await raw_connection.execution_options(
                    isolation_level="REPEATABLE READ"
                )
                async with connection.begin():
                    snapshot_rows: dict[str, list[dict[str, Any]]] = {}
                    for name, model in models.items():
                        result = await connection.execute(select(model.__table__))
                        snapshot_rows[name] = [
                            {key: neo4j_value(value) for key, value in row.items()}
                            for row in result.mappings()
                        ]
            return GraphSnapshot(**snapshot_rows)
        except DBAPIError:
            if attempt == retries:
                raise
            await asyncio.sleep(attempt)
    raise AssertionError("unreachable")
