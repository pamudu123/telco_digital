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
    async def rows(model: Any) -> list[dict[str, Any]]:
        for attempt in range(1, retries + 1):
            try:
                async with engine.connect() as connection:
                    result = await connection.execute(select(model.__table__))
                    return [
                        {key: neo4j_value(value) for key, value in row.items()}
                        for row in result.mappings()
                    ]
            except DBAPIError:
                if attempt == retries:
                    raise
                await asyncio.sleep(attempt)
        raise AssertionError("unreachable")

    return GraphSnapshot(
        customers=await rows(CustomerModel),
        accounts=await rows(AccountModel),
        devices=await rows(DeviceModel),
        customer_devices=await rows(CustomerDeviceModel),
        plans=await rows(PlanModel),
        subscriptions=await rows(SubscriptionModel),
        wallets=await rows(WalletModel),
        merchants=await rows(MerchantModel),
        transactions=await rows(MoneyTransactionModel),
        distributors=await rows(DistributorModel),
        retailers=await rows(RetailerModel),
        sales_agents=await rows(SalesAgentModel),
        products=await rows(SfaProductModel),
        sales=await rows(SaleModel),
        inventory_events=await rows(InventoryEventModel),
    )
