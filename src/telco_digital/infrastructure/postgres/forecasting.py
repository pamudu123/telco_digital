"""SQL adapters for retailer demand history. Keep Cypher out of this module."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telco_digital.application.services.common import NotFoundError
from telco_digital.infrastructure.postgres.models import (
    InventoryEventModel,
    RetailerModel,
    SaleModel,
    SfaProductModel,
)
from telco_digital.intelligence.features.service import validate_as_of
from telco_digital.intelligence.forecasting.series import (
    SalePoint,
    expand_observed_history,
)


class PostgresRetailerDemandQueries:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load(self, retailer_ref: str, as_of: datetime):
        validate_as_of(as_of)
        retailer = (
            await self.session.execute(
                select(RetailerModel).where(RetailerModel.retailer_ref == retailer_ref)
            )
        ).scalar_one_or_none()
        if retailer is None:
            raise NotFoundError(f"Unknown retailer: {retailer_ref}")

        rows = await self.session.execute(
            select(SaleModel, SfaProductModel)
            .join(SfaProductModel, SfaProductModel.id == SaleModel.product_id)
            .where(SaleModel.retailer_id == retailer.id, SaleModel.occurred_at <= as_of)
            .order_by(SaleModel.occurred_at.asc())
        )
        sales: list[SalePoint] = []
        names: dict[str, str] = {}
        for sale, product in rows.all():
            sales.append(
                SalePoint(
                    product_code=product.product_code,
                    occurred_at=sale.occurred_at,
                    quantity=float(sale.quantity),
                )
            )
            names[product.product_code] = product.name

        inventory_rows = await self.session.execute(
            select(InventoryEventModel, SfaProductModel)
            .join(SfaProductModel, SfaProductModel.id == InventoryEventModel.product_id)
            .where(
                InventoryEventModel.retailer_id == retailer.id,
                InventoryEventModel.occurred_at <= as_of,
            )
        )
        for _event, product in inventory_rows.all():
            names.setdefault(product.product_code, product.name)

        return expand_observed_history(
            retailer.retailer_ref,
            as_of,
            sales=sales,
            name=retailer.name,
            region=retailer.region,
            status=retailer.status,
            product_names=names,
        )
