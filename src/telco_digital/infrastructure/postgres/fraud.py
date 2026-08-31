"""PostgreSQL outgoing-transaction features for graph fraud scoring."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telco_digital.infrastructure.postgres.models import CustomerModel, MoneyTransactionModel
from telco_digital.intelligence.fraud.features import TransactionRiskFeatures


class PostgresTransactionRiskQueries:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def calculate(self, customer_ref: str, as_of: datetime) -> TransactionRiskFeatures:
        customer = await self.session.scalar(
            select(CustomerModel).where(CustomerModel.customer_ref == customer_ref)
        )
        if customer is None:
            raise LookupError(f"Unknown customer: {customer_ref}")
        window_start = as_of - timedelta(days=90)
        rows = list(
            (
                await self.session.execute(
                    select(MoneyTransactionModel).where(
                        MoneyTransactionModel.customer_id == customer.id,
                        MoneyTransactionModel.occurred_at >= window_start,
                        MoneyTransactionModel.occurred_at <= as_of,
                    )
                )
            ).scalars()
        )
        transfers = [row for row in rows if row.transaction_type == "TRANSFER"]
        merchants = [row for row in rows if row.merchant_id is not None]
        amounts = [float(row.amount or Decimal(0)) for row in rows]
        age = (as_of - customer.customer_since).days if customer.customer_since <= as_of else None
        return TransactionRiskFeatures(
            customer_id=customer.id,
            customer_ref=customer.customer_ref,
            as_of=as_of,
            account_age_days=age,
            transaction_count_90d=len(rows),
            transfer_count_90d=len(transfers),
            merchant_payment_count_90d=len(merchants),
            spend_90d=round(sum(amounts), 4),
            max_amount_90d=round(max(amounts), 4) if amounts else 0.0,
            unique_merchants_90d=len({row.merchant_id for row in merchants}),
            unique_devices_90d=len({row.device_id for row in rows if row.device_id is not None}),
        )
