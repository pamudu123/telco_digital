"""PostgreSQL reads for the capability-00 showcase. SQL stays in this module."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from telco_digital.application.demo_dataset import (
    DATASET_VERSION,
    END_AT,
    GOLDEN_CUSTOMER_REFS,
    GOLDEN_PERSONAS,
    START_AT,
    persona_for_ref,
)
from telco_digital.application.queries.dtos import ObservedCustomerState
from telco_digital.application.queries.showcase import (
    DOMAIN_COVERAGE,
    Customer360,
    EvidenceSeries,
    FactRecord,
    OverviewCounts,
    PersonaSummary,
    ProvenanceBlock,
    Retailer360,
    SeriesPoint,
    display_persona,
)
from telco_digital.infrastructure.postgres.demo_dataset import TABLES
from telco_digital.infrastructure.postgres.models import (
    AccountModel,
    ActivityEventModel,
    BalanceLedgerModel,
    CampaignInteractionModel,
    CampaignModel,
    CustomerDeviceModel,
    CustomerModel,
    DeviceModel,
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

GENERATED_CUSTOMER_FILTER = or_(
    CustomerModel.customer_ref.in_(tuple(GOLDEN_PERSONAS)),
    CustomerModel.customer_ref.like("BG%"),
)


def _generated_customer_ids() -> Select[tuple[UUID]]:
    return select(CustomerModel.id).where(GENERATED_CUSTOMER_FILTER)


def _generated_retailer_ids() -> Select[tuple[UUID]]:
    return select(RetailerModel.id).where(RetailerModel.retailer_ref.like("RET-%"))


def _provenance(as_of: datetime, table: str) -> ProvenanceBlock:
    return ProvenanceBlock(
        source="live_database",
        as_of=as_of,
        dataset_version=DATASET_VERSION,
        table=table,
    )


async def _scalar_count(session: AsyncSession, statement: Select[tuple[int]]) -> int:
    result = await session.execute(statement)
    return int(result.scalar_one() or 0)


async def count_generated_rows(session: AsyncSession) -> dict[str, int]:
    """Count poc-v1 owned rows. This is not SUM(*) across tables."""
    generated_customers = _generated_customer_ids()
    generated_retailers = _generated_retailer_ids()
    statements: dict[str, Select[tuple[int]]] = {
        "plans": select(func.count())
        .select_from(PlanModel)
        .where(PlanModel.plan_code.like("POC_%")),
        "campaigns": select(func.count())
        .select_from(CampaignModel)
        .where(CampaignModel.campaign_code.like("POC-%")),
        "merchants": select(func.count())
        .select_from(MerchantModel)
        .where(MerchantModel.name.like("POC Merchant%")),
        "distributors": select(func.count())
        .select_from(TABLES["distributors"])
        .where(TABLES["distributors"].c.distributor_ref.like("DIST-%")),
        "sfa_products": select(func.count())
        .select_from(SfaProductModel)
        .where(SfaProductModel.product_code.like("POC-PROD-%")),
        "customers": select(func.count())
        .select_from(CustomerModel)
        .where(GENERATED_CUSTOMER_FILTER),
        "accounts": select(func.count())
        .select_from(AccountModel)
        .where(AccountModel.customer_id.in_(generated_customers)),
        "devices": select(func.count())
        .select_from(DeviceModel)
        .where(DeviceModel.device_ref.like("DEV-%")),
        "customer_devices": select(func.count())
        .select_from(CustomerDeviceModel)
        .where(CustomerDeviceModel.customer_id.in_(generated_customers)),
        "wallets": select(func.count())
        .select_from(WalletModel)
        .where(WalletModel.customer_id.in_(generated_customers)),
        "loyalty_accounts": select(func.count())
        .select_from(LoyaltyAccountModel)
        .where(LoyaltyAccountModel.customer_id.in_(generated_customers)),
        "retailers": select(func.count())
        .select_from(RetailerModel)
        .where(RetailerModel.retailer_ref.like("RET-%")),
        "sales_agents": select(func.count())
        .select_from(SalesAgentModel)
        .where(SalesAgentModel.agent_ref.like("AGENT-%")),
        "subscriptions": select(func.count())
        .select_from(SubscriptionModel)
        .where(SubscriptionModel.customer_id.in_(generated_customers)),
        "recharges": select(func.count())
        .select_from(RechargeModel)
        .where(RechargeModel.customer_id.in_(generated_customers)),
        "balance_ledger": select(func.count())
        .select_from(BalanceLedgerModel)
        .where(BalanceLedgerModel.customer_id.in_(generated_customers)),
        "usage_events": select(func.count())
        .select_from(UsageEventModel)
        .where(UsageEventModel.customer_id.in_(generated_customers)),
        "travels": select(func.count())
        .select_from(TravelModel)
        .where(TravelModel.customer_id.in_(generated_customers)),
        "service_interactions": select(func.count())
        .select_from(ServiceInteractionModel)
        .where(ServiceInteractionModel.customer_id.in_(generated_customers)),
        "loyalty_ledger": select(func.count())
        .select_from(LoyaltyLedgerModel)
        .where(LoyaltyLedgerModel.customer_id.in_(generated_customers)),
        "campaign_interactions": select(func.count())
        .select_from(CampaignInteractionModel)
        .where(CampaignInteractionModel.customer_id.in_(generated_customers)),
        "money_transactions": select(func.count())
        .select_from(MoneyTransactionModel)
        .where(MoneyTransactionModel.customer_id.in_(generated_customers)),
        "sales": select(func.count())
        .select_from(SaleModel)
        .where(SaleModel.retailer_id.in_(generated_retailers)),
        "inventory_events": select(func.count())
        .select_from(InventoryEventModel)
        .where(InventoryEventModel.retailer_id.in_(generated_retailers)),
        "activity_events": select(func.count())
        .select_from(ActivityEventModel)
        .where(ActivityEventModel.source == DATASET_VERSION),
        "outbox_events": select(func.count())
        .select_from(OutboxEventModel)
        .where(OutboxEventModel.payload["dataset_version"].astext == DATASET_VERSION),
    }
    counts: dict[str, int] = {}
    for name, statement in statements.items():
        counts[name] = await _scalar_count(session, statement)
    return counts


async def count_table_totals(session: AsyncSession) -> dict[str, int]:
    totals: dict[str, int] = {}
    for name, table in TABLES.items():
        totals[name] = await _scalar_count(session, select(func.count()).select_from(table))
    return totals


class PostgresShowcaseQueries:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def overview(self, *, as_of: datetime, queried_at: datetime) -> OverviewCounts:
        generated = await count_generated_rows(self.session)
        totals = await count_table_totals(self.session)
        total_customers = await _scalar_count(
            self.session, select(func.count()).select_from(CustomerModel)
        )
        background = await _scalar_count(
            self.session,
            select(func.count())
            .select_from(CustomerModel)
            .where(CustomerModel.customer_ref.like("BG%")),
        )
        golden = await _scalar_count(
            self.session,
            select(func.count())
            .select_from(CustomerModel)
            .where(CustomerModel.customer_ref.in_(GOLDEN_CUSTOMER_REFS)),
        )
        activity = generated["activity_events"]
        outbox = generated["outbox_events"]
        return OverviewCounts(
            source="live_database",
            as_of=as_of,
            dataset_version=DATASET_VERSION,
            queried_at=queried_at,
            generated_rows=sum(generated.values()),
            total_database_rows=sum(totals.values()),
            total_customers=total_customers,
            background_customers=background,
            golden_personas=golden,
            activity_events=activity,
            outbox_events=outbox,
            event_outbox_parity=activity == outbox,
            period_start=START_AT,
            period_end=END_AT,
            generated_row_counts=generated,
            domain_coverage=DOMAIN_COVERAGE,
        )

    async def evidence(self, *, as_of: datetime, queried_at: datetime) -> EvidenceSeries:
        generated = await count_generated_rows(self.session)
        refs = await self.session.execute(
            select(CustomerModel.customer_ref).where(GENERATED_CUSTOMER_FILTER)
        )
        personas: dict[str, int] = {}
        for (customer_ref,) in refs.all():
            code = persona_for_ref(customer_ref) or "UNKNOWN"
            personas[code] = personas.get(code, 0) + 1
        month_expr = func.to_char(ActivityEventModel.occurred_at, "YYYY-MM")
        monthly = await self.session.execute(
            select(month_expr, func.count())
            .where(
                ActivityEventModel.source == DATASET_VERSION,
                ActivityEventModel.occurred_at <= as_of,
            )
            .group_by(month_expr)
            .order_by(month_expr)
        )
        return EvidenceSeries(
            source="live_database",
            as_of=as_of,
            dataset_version=DATASET_VERSION,
            queried_at=queried_at,
            generated_rows_by_table=tuple(
                SeriesPoint(label=name, value=float(count))
                for name, count in sorted(generated.items(), key=lambda item: item[1], reverse=True)
            ),
            persona_distribution=tuple(
                SeriesPoint(label=display_persona(name), value=float(count))
                for name, count in sorted(personas.items())
            ),
            monthly_activity=tuple(
                SeriesPoint(label=month, value=float(count)) for month, count in monthly.all()
            ),
        )

    async def list_personas(self) -> tuple[PersonaSummary, ...]:
        present = {
            row[0]
            for row in (
                await self.session.execute(
                    select(CustomerModel.customer_ref).where(
                        CustomerModel.customer_ref.in_(GOLDEN_CUSTOMER_REFS)
                    )
                )
            ).all()
        }
        summaries: list[PersonaSummary] = []
        for customer_ref in GOLDEN_CUSTOMER_REFS:
            code = persona_for_ref(customer_ref) or "UNKNOWN"
            summaries.append(
                PersonaSummary(
                    customer_ref=customer_ref,
                    persona=code,
                    label=f"{display_persona(code)} — {customer_ref}",
                    golden=True,
                    present=customer_ref in present,
                )
            )
        return tuple(summaries)

    async def customer_facts(
        self,
        observed: ObservedCustomerState,
        *,
        queried_at: datetime,
    ) -> Customer360:
        customer_id = observed.customer_id
        as_of = observed.as_of
        customer = await self.get_customer_row(observed.customer_ref)
        if customer is None:
            raise LookupError(f"Unknown customer: {observed.customer_ref}")
        usage_rows = await self.session.execute(
            select(UsageEventModel)
            .where(UsageEventModel.customer_id == customer_id, UsageEventModel.occurred_at <= as_of)
            .order_by(UsageEventModel.occurred_at.desc())
            .limit(50)
        )
        recharge_rows = await self.session.execute(
            select(RechargeModel)
            .where(RechargeModel.customer_id == customer_id, RechargeModel.occurred_at <= as_of)
            .order_by(RechargeModel.occurred_at.desc())
            .limit(50)
        )
        travel_rows = await self.session.execute(
            select(TravelModel)
            .where(TravelModel.customer_id == customer_id, TravelModel.started_at <= as_of)
            .order_by(TravelModel.started_at.desc())
        )
        service_rows = await self.session.execute(
            select(ServiceInteractionModel)
            .where(
                ServiceInteractionModel.customer_id == customer_id,
                ServiceInteractionModel.occurred_at <= as_of,
            )
            .order_by(ServiceInteractionModel.occurred_at.desc())
        )
        loyalty_rows = await self.session.execute(
            select(LoyaltyLedgerModel)
            .where(
                LoyaltyLedgerModel.customer_id == customer_id,
                LoyaltyLedgerModel.occurred_at <= as_of,
            )
            .order_by(LoyaltyLedgerModel.occurred_at.desc())
        )
        campaign_rows = await self.session.execute(
            select(CampaignInteractionModel, CampaignModel)
            .join(CampaignModel, CampaignModel.id == CampaignInteractionModel.campaign_id)
            .where(
                CampaignInteractionModel.customer_id == customer_id,
                CampaignInteractionModel.occurred_at <= as_of,
            )
            .order_by(CampaignInteractionModel.occurred_at.desc())
        )
        wallet_rows = await self.session.execute(
            select(MoneyTransactionModel, MerchantModel)
            .outerjoin(MerchantModel, MerchantModel.id == MoneyTransactionModel.merchant_id)
            .where(
                MoneyTransactionModel.customer_id == customer_id,
                MoneyTransactionModel.occurred_at <= as_of,
            )
            .order_by(MoneyTransactionModel.occurred_at.desc())
            .limit(50)
        )
        device_rows = await self.session.execute(
            select(CustomerDeviceModel, DeviceModel)
            .join(DeviceModel, DeviceModel.id == CustomerDeviceModel.device_id)
            .where(
                CustomerDeviceModel.customer_id == customer_id,
                CustomerDeviceModel.valid_from <= as_of,
                or_(
                    CustomerDeviceModel.valid_to.is_(None),
                    CustomerDeviceModel.valid_to > as_of,
                ),
            )
        )
        timeline_rows = await self.session.execute(
            select(ActivityEventModel)
            .where(
                ActivityEventModel.customer_id == customer_id,
                ActivityEventModel.occurred_at <= as_of,
            )
            .order_by(ActivityEventModel.occurred_at.desc())
            .limit(40)
        )
        plan_row = await self.session.execute(
            select(SubscriptionModel, PlanModel)
            .join(PlanModel, PlanModel.id == SubscriptionModel.plan_id)
            .where(
                SubscriptionModel.customer_id == customer_id,
                SubscriptionModel.started_at <= as_of,
                or_(
                    SubscriptionModel.ended_at.is_(None),
                    SubscriptionModel.ended_at > as_of,
                ),
            )
            .order_by(SubscriptionModel.started_at.desc())
            .limit(1)
        )
        subscription = plan_row.first()
        loyalty_total = await self.session.execute(
            select(func.coalesce(func.sum(LoyaltyLedgerModel.points), 0)).where(
                LoyaltyLedgerModel.customer_id == customer_id,
                LoyaltyLedgerModel.occurred_at <= as_of,
            )
        )
        ledger_balance = await self.session.execute(
            select(func.coalesce(func.sum(BalanceLedgerModel.amount), 0)).where(
                BalanceLedgerModel.customer_id == customer_id,
                BalanceLedgerModel.occurred_at <= as_of,
            )
        )
        account = (
            await self.session.execute(
                select(AccountModel).where(AccountModel.customer_id == customer_id).limit(1)
            )
        ).scalar_one_or_none()

        unknowns: list[str] = []
        trip_duration_known = observed.trip_duration_known
        if trip_duration_known is False:
            unknowns.append("Active trip duration is unknown at this as_of.")
        if observed.current_plan_code is None and subscription is None:
            unknowns.append("No active subscription at this as_of.")

        plan_code = observed.current_plan_code
        plan_name = None
        sub_status = None
        sub_started = None
        if subscription is not None:
            sub, plan = subscription
            plan_code = plan.plan_code
            plan_name = plan.name
            sub_status = sub.status
            sub_started = sub.started_at

        persona = persona_for_ref(customer.customer_ref)
        return Customer360(
            source="live_database",
            as_of=as_of,
            dataset_version=DATASET_VERSION,
            queried_at=queried_at,
            customer_ref=customer.customer_ref,
            persona=persona,
            home_country=customer.home_country,
            account_type=customer.account_type,
            status=customer.status,
            customer_since=customer.customer_since,
            observed_country=observed.country,
            observed_country_source=observed.country_source,
            current_plan_code=plan_code,
            current_plan_name=plan_name,
            subscription_status=sub_status,
            subscription_started_at=sub_started,
            balance_amount=Decimal(ledger_balance.scalar_one()),
            currency=account.currency if account else observed.currency,
            loyalty_points=int(loyalty_total.scalar_one() or 0),
            device_ref=observed.device_ref,
            active_complaints=observed.active_complaints,
            trip_duration_known=trip_duration_known,
            unknowns=tuple(unknowns),
            usage=tuple(
                FactRecord(
                    kind="usage",
                    occurred_at=row.occurred_at,
                    summary=f"{row.usage_type} {row.data_mb} MB in {row.country_code}",
                    detail={
                        "usage_type": row.usage_type,
                        "data_mb": str(row.data_mb),
                        "country_code": row.country_code,
                        "network_type": row.network_type,
                    },
                    provenance=_provenance(as_of, "telco.usage_event"),
                )
                for row in usage_rows.scalars()
            ),
            recharges=tuple(
                FactRecord(
                    kind="recharge",
                    occurred_at=row.occurred_at,
                    summary=f"{row.amount} {row.currency} via {row.channel or 'unknown'}",
                    detail={
                        "amount": str(row.amount),
                        "currency": row.currency,
                        "channel": row.channel,
                    },
                    provenance=_provenance(as_of, "telco.recharge"),
                )
                for row in recharge_rows.scalars()
            ),
            travels=tuple(
                FactRecord(
                    kind="travel",
                    occurred_at=row.started_at,
                    summary=(
                        f"{row.country_code} from {row.started_at.date()}"
                        + (
                            f" to {row.ended_at.date()}"
                            if row.ended_at is not None and row.ended_at <= as_of
                            else " (end unknown at as_of)"
                        )
                    ),
                    detail={
                        "country_code": row.country_code,
                        "started_at": row.started_at.isoformat(),
                        "ended_at": (
                            row.ended_at.isoformat()
                            if row.ended_at is not None and row.ended_at <= as_of
                            else None
                        ),
                    },
                    provenance=_provenance(as_of, "telco.travel"),
                )
                for row in travel_rows.scalars()
            ),
            service_interactions=tuple(
                FactRecord(
                    kind="service_interaction",
                    occurred_at=row.occurred_at,
                    summary=f"{row.interaction_type} ({row.status})",
                    detail={
                        "interaction_type": row.interaction_type,
                        "category": row.category,
                        "severity": row.severity,
                        "status": row.status,
                    },
                    provenance=_provenance(as_of, "telco.service_interaction"),
                )
                for row in service_rows.scalars()
            ),
            loyalty=tuple(
                FactRecord(
                    kind="loyalty",
                    occurred_at=row.occurred_at,
                    summary=f"{row.entry_type} {row.points} points",
                    detail={"entry_type": row.entry_type, "points": row.points},
                    provenance=_provenance(as_of, "marketing.loyalty_ledger"),
                )
                for row in loyalty_rows.scalars()
            ),
            campaigns=tuple(
                FactRecord(
                    kind="campaign",
                    occurred_at=interaction.occurred_at,
                    summary=f"{interaction.interaction_type} — {campaign.name}",
                    detail={
                        "interaction_type": interaction.interaction_type,
                        "campaign_code": campaign.campaign_code,
                        "campaign_name": campaign.name,
                    },
                    provenance=_provenance(as_of, "marketing.campaign_interaction"),
                )
                for interaction, campaign in campaign_rows.all()
            ),
            wallet=tuple(
                FactRecord(
                    kind="wallet",
                    occurred_at=txn.occurred_at,
                    summary=(
                        f"{txn.transaction_type} {txn.amount} {txn.currency}"
                        + (f" at {merchant.name}" if merchant is not None else "")
                    ),
                    detail={
                        "transaction_ref": txn.transaction_ref,
                        "transaction_type": txn.transaction_type,
                        "amount": str(txn.amount),
                        "currency": txn.currency,
                        "status": txn.status,
                        "merchant": merchant.name if merchant is not None else None,
                    },
                    provenance=_provenance(as_of, "money.transaction"),
                )
                for txn, merchant in wallet_rows.all()
            ),
            devices=tuple(
                FactRecord(
                    kind="device",
                    occurred_at=link.valid_from,
                    summary=f"{device.device_ref} ({device.model})",
                    detail={
                        "device_ref": device.device_ref,
                        "model": device.model,
                        "device_type": device.device_type,
                    },
                    provenance=_provenance(as_of, "core.customer_device"),
                )
                for link, device in device_rows.all()
            ),
            timeline=tuple(
                FactRecord(
                    kind="activity",
                    occurred_at=event.occurred_at,
                    summary=event.event_type,
                    detail={"entity_type": event.entity_type, "source": event.source},
                    provenance=_provenance(as_of, "activity.event"),
                )
                for event in timeline_rows.scalars()
            ),
        )

    async def retailer_facts(
        self, retailer_ref: str, *, as_of: datetime, queried_at: datetime
    ) -> Retailer360 | None:
        retailer = (
            await self.session.execute(
                select(RetailerModel).where(RetailerModel.retailer_ref == retailer_ref)
            )
        ).scalar_one_or_none()
        if retailer is None:
            return None
        sales = await self.session.execute(
            select(SaleModel, SfaProductModel)
            .join(SfaProductModel, SfaProductModel.id == SaleModel.product_id)
            .where(SaleModel.retailer_id == retailer.id, SaleModel.occurred_at <= as_of)
            .order_by(SaleModel.occurred_at.desc())
            .limit(50)
        )
        inventory = await self.session.execute(
            select(InventoryEventModel, SfaProductModel)
            .join(SfaProductModel, SfaProductModel.id == InventoryEventModel.product_id)
            .where(
                InventoryEventModel.retailer_id == retailer.id,
                InventoryEventModel.occurred_at <= as_of,
            )
            .order_by(InventoryEventModel.occurred_at.desc())
            .limit(50)
        )
        return Retailer360(
            source="live_database",
            as_of=as_of,
            dataset_version=DATASET_VERSION,
            queried_at=queried_at,
            retailer_ref=retailer.retailer_ref,
            name=retailer.name,
            region=retailer.region,
            status=retailer.status,
            sales=tuple(
                FactRecord(
                    kind="sale",
                    occurred_at=sale.occurred_at,
                    summary=f"{product.name}: {sale.quantity} units, {sale.amount}",
                    detail={
                        "product_code": product.product_code,
                        "quantity": sale.quantity,
                        "amount": str(sale.amount),
                    },
                    provenance=_provenance(as_of, "sfa.sale"),
                )
                for sale, product in sales.all()
            ),
            inventory=tuple(
                FactRecord(
                    kind="inventory",
                    occurred_at=event.occurred_at,
                    summary=f"{product.name}: {event.event_type} {event.quantity}",
                    detail={
                        "product_code": product.product_code,
                        "event_type": event.event_type,
                        "quantity": event.quantity,
                    },
                    provenance=_provenance(as_of, "sfa.inventory_event"),
                )
                for event, product in inventory.all()
            ),
        )

    async def get_customer_row(self, customer_ref: str) -> CustomerModel | None:
        result = await self.session.execute(
            select(CustomerModel).where(CustomerModel.customer_ref == customer_ref)
        )
        return result.scalar_one_or_none()
