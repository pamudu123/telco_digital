from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

SCHEMAS = (
    "core",
    "telco",
    "marketing",
    "money",
    "sfa",
    "activity",
    "intelligence",
    "integration",
)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class CustomerModel(Base):
    __tablename__ = "customer"
    __table_args__ = {"schema": "core"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    customer_ref: Mapped[str] = mapped_column(String(64), unique=True)
    home_country: Mapped[str] = mapped_column(String(8))
    account_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    customer_since: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AccountModel(Base):
    __tablename__ = "account"
    __table_args__ = {"schema": "core"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    account_ref: Mapped[str] = mapped_column(String(64))
    account_type: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SimModel(Base):
    __tablename__ = "sim"
    __table_args__ = {"schema": "core"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    sim_ref: Mapped[str] = mapped_column(String(64))
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    msisdn: Mapped[str] = mapped_column(String(32))
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))


class DeviceModel(Base):
    __tablename__ = "device"
    __table_args__ = {"schema": "core"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    device_ref: Mapped[str] = mapped_column(String(64), unique=True)
    device_type: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    fingerprint: Mapped[str] = mapped_column(String(128))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CustomerDeviceModel(Base):
    __tablename__ = "customer_device"
    __table_args__ = {"schema": "core"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    device_id: Mapped[UUID] = mapped_column(ForeignKey("core.device.id"))
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlanModel(Base):
    __tablename__ = "plan"
    __table_args__ = {"schema": "core"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    plan_code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    plan_type: Mapped[str] = mapped_column(String(32))
    data_mb: Mapped[int] = mapped_column(Integer)
    validity_days: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(8))
    country_code: Mapped[str | None] = mapped_column(String(8))
    country_group: Mapped[str | None] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SubscriptionModel(Base):
    __tablename__ = "subscription"
    __table_args__ = {"schema": "core"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("core.plan.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))
    source_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class BalanceLedgerModel(Base):
    __tablename__ = "balance_ledger"
    __table_args__ = {"schema": "telco"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("core.account.id"))
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    entry_type: Mapped[str] = mapped_column(String(32))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(8))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class UsageEventModel(Base):
    __tablename__ = "usage_event"
    __table_args__ = {"schema": "telco"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usage_type: Mapped[str] = mapped_column(String(32))
    data_mb: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    country_code: Mapped[str] = mapped_column(String(8))
    network_type: Mapped[str | None] = mapped_column(String(32))
    source_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class RechargeModel(Base):
    __tablename__ = "recharge"
    __table_args__ = {"schema": "telco"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    account_id: Mapped[UUID] = mapped_column(ForeignKey("core.account.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(8))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    channel: Mapped[str | None] = mapped_column(String(64))
    source_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class TravelModel(Base):
    __tablename__ = "travel"
    __table_args__ = {"schema": "telco"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    country_code: Mapped[str] = mapped_column(String(8))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str | None] = mapped_column(String(64))
    start_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    end_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class ServiceInteractionModel(Base):
    __tablename__ = "service_interaction"
    __table_args__ = {"schema": "telco"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    interaction_type: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    category: Mapped[str | None] = mapped_column(String(64))
    severity: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class LoyaltyAccountModel(Base):
    __tablename__ = "loyalty_account"
    __table_args__ = {"schema": "marketing"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))


class LoyaltyLedgerModel(Base):
    __tablename__ = "loyalty_ledger"
    __table_args__ = {"schema": "marketing"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    loyalty_account_id: Mapped[UUID] = mapped_column(ForeignKey("marketing.loyalty_account.id"))
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    entry_type: Mapped[str] = mapped_column(String(32))
    points: Mapped[int] = mapped_column(Integer)
    reward_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class CampaignModel(Base):
    __tablename__ = "campaign"
    __table_args__ = {"schema": "marketing"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    campaign_code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))
    target_plan_id: Mapped[UUID | None] = mapped_column(ForeignKey("core.plan.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))


class CampaignInteractionModel(Base):
    __tablename__ = "campaign_interaction"
    __table_args__ = {"schema": "marketing"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("marketing.campaign.id"))
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    interaction_type: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class WalletModel(Base):
    __tablename__ = "wallet"
    __table_args__ = {"schema": "money"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    wallet_ref: Mapped[str] = mapped_column(String(64), unique=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MerchantModel(Base):
    __tablename__ = "merchant"
    __table_args__ = {"schema": "money"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    merchant_ref: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))
    country_code: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(32))


class MoneyTransactionModel(Base):
    __tablename__ = "transaction"
    __table_args__ = {"schema": "money"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    transaction_ref: Mapped[str] = mapped_column(String(64), unique=True)
    source_wallet_id: Mapped[UUID] = mapped_column(ForeignKey("money.wallet.id"))
    destination_wallet_id: Mapped[UUID | None] = mapped_column(ForeignKey("money.wallet.id"))
    merchant_id: Mapped[UUID | None] = mapped_column(ForeignKey("money.merchant.id"))
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    device_id: Mapped[UUID | None] = mapped_column(ForeignKey("core.device.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(8))
    transaction_type: Mapped[str] = mapped_column(String(32))
    country_code: Mapped[str] = mapped_column(String(8))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))
    source_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class DistributorModel(Base):
    __tablename__ = "distributor"
    __table_args__ = {"schema": "sfa"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    distributor_ref: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    region: Mapped[str] = mapped_column(String(64))


class RetailerModel(Base):
    __tablename__ = "retailer"
    __table_args__ = {"schema": "sfa"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    retailer_ref: Mapped[str] = mapped_column(String(64), unique=True)
    distributor_id: Mapped[UUID] = mapped_column(ForeignKey("sfa.distributor.id"))
    name: Mapped[str] = mapped_column(String(128))
    region: Mapped[str] = mapped_column(String(64))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    status: Mapped[str] = mapped_column(String(32))


class SalesAgentModel(Base):
    __tablename__ = "sales_agent"
    __table_args__ = {"schema": "sfa"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    agent_ref: Mapped[str] = mapped_column(String(64), unique=True)
    distributor_id: Mapped[UUID] = mapped_column(ForeignKey("sfa.distributor.id"))
    name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))


class SfaProductModel(Base):
    __tablename__ = "product"
    __table_args__ = {"schema": "sfa"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    product_code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))


class SaleModel(Base):
    __tablename__ = "sale"
    __table_args__ = {"schema": "sfa"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    retailer_id: Mapped[UUID] = mapped_column(ForeignKey("sfa.retailer.id"))
    product_id: Mapped[UUID] = mapped_column(ForeignKey("sfa.product.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sales_agent_id: Mapped[UUID | None] = mapped_column(ForeignKey("sfa.sales_agent.id"))
    source_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class InventoryEventModel(Base):
    __tablename__ = "inventory_event"
    __table_args__ = {"schema": "sfa"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    retailer_id: Mapped[UUID] = mapped_column(ForeignKey("sfa.retailer.id"))
    product_id: Mapped[UUID] = mapped_column(ForeignKey("sfa.product.id"))
    event_type: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[int] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class ActivityEventModel(Base):
    __tablename__ = "event"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_activity_event_idempotency_key"),
        {"schema": "activity"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    customer_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    event_type: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(64))
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class OutboxEventModel(Base):
    __tablename__ = "outbox_event"
    __table_args__ = {"schema": "integration"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    event_type: Mapped[str] = mapped_column(String(64))
    aggregate_type: Mapped[str] = mapped_column(String(64))
    aggregate_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))


class FeatureSnapshotModel(Base):
    __tablename__ = "feature_snapshot"
    __table_args__ = {"schema": "intelligence"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    feature_set_version: Mapped[str] = mapped_column(String(32))
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ModelPredictionModel(Base):
    __tablename__ = "model_prediction"
    __table_args__ = {"schema": "intelligence"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    model_name: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(32))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    score: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    label: Mapped[str | None] = mapped_column(String(64))
    feature_snapshot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("intelligence.feature_snapshot.id")
    )
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RecommendationModel(Base):
    __tablename__ = "recommendation"
    __table_args__ = {"schema": "intelligence"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decision_mode: Mapped[str] = mapped_column(String(64))
    recommended_action: Mapped[str] = mapped_column(String(128))
    recommended_item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    score: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    unknowns: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RecommendationOutcomeModel(Base):
    __tablename__ = "recommendation_outcome"
    __table_args__ = {"schema": "intelligence"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    recommendation_id: Mapped[UUID] = mapped_column(ForeignKey("intelligence.recommendation.id"))
    selected_option: Mapped[str | None] = mapped_column(String(128))
    accepted: Mapped[bool] = mapped_column(Boolean)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class WarningModel(Base):
    __tablename__ = "warning"
    __table_args__ = {"schema": "intelligence"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("core.customer.id"))
    warning_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    related_event_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
