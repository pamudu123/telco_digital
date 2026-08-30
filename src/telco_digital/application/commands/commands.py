from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from telco_digital.domain.enums import AccountType, CustomerStatus, UsageType
from telco_digital.domain.value_objects import normalize_country


class CreateCustomerCommand(BaseModel):
    customer_ref: str
    home_country: str
    account_type: AccountType = AccountType.PREPAID
    status: CustomerStatus = CustomerStatus.ACTIVE
    customer_since: datetime
    currency: str = "LKR"
    device_ref: str | None = None
    device_type: str = "HANDSET"
    device_model: str | None = None
    device_fingerprint: str | None = None
    correlation_id: str | None = None
    source: str = "simulator"

    def normalized_country(self) -> str:
        return normalize_country(self.home_country)


class RecordRechargeCommand(BaseModel):
    customer_ref: str
    amount: Decimal
    occurred_at: datetime
    currency: str | None = None
    channel: str | None = "APP"
    correlation_id: str | None = None
    source: str = "simulator"


class PurchasePlanCommand(BaseModel):
    customer_ref: str
    plan_code: str
    occurred_at: datetime
    correlation_id: str | None = None
    source: str = "simulator"


class RecordUsageCommand(BaseModel):
    customer_ref: str
    occurred_at: datetime
    data_mb: Decimal
    usage_type: UsageType = UsageType.STREAMING
    country: str | None = None
    network_type: str | None = None
    correlation_id: str | None = None
    source: str = "simulator"


class RecordTravelCommand(BaseModel):
    customer_ref: str
    country: str
    started_at: datetime
    ended_at: datetime | None = None
    correlation_id: str | None = None
    source: str = "simulator"

    def normalized_country(self) -> str:
        return normalize_country(self.country)


class EndTravelCommand(BaseModel):
    customer_ref: str
    ended_at: datetime
    travel_id: UUID | None = None
    correlation_id: str | None = None
    source: str = "simulator"


class CreatePlanCommand(BaseModel):
    plan_code: str
    name: str
    plan_type: str
    data_mb: int
    validity_days: int
    price: Decimal
    currency: str = "LKR"
    country_code: str | None = None
    country_group: str | None = None
    created_at: datetime


class RecordServiceInteractionCommand(BaseModel):
    customer_ref: str
    interaction_type: str
    occurred_at: datetime
    category: str | None = None
    severity: str | None = None
    status: str = "OPEN"
    correlation_id: str | None = None
    source: str = "simulator"


class GetCustomerStateQuery(BaseModel):
    customer_ref: str
    as_of: datetime


class GetTimelineQuery(BaseModel):
    customer_ref: str
    as_of: datetime | None = None
