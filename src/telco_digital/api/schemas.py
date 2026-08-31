"""HTTP request bodies for command adapters. Validation only; no domain rules."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from telco_digital.application.commands.commands import (
    EndTravelCommand,
    PurchasePlanCommand,
    RecordRechargeCommand,
    RecordTravelCommand,
    RecordUsageCommand,
)
from telco_digital.domain.enums import UsageType


def _require_aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{field} must be a timezone-aware ISO-8601 timestamp")
    return value


class RechargeRequest(BaseModel):
    customer_ref: str = Field(min_length=1)
    amount: Decimal
    occurred_at: datetime
    currency: str | None = None
    channel: str | None = "APP"
    correlation_id: str | None = None

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_aware(cls, value: datetime) -> datetime:
        return _require_aware(value, "occurred_at")

    def to_command(self) -> RecordRechargeCommand:
        return RecordRechargeCommand(
            customer_ref=self.customer_ref,
            amount=self.amount,
            occurred_at=self.occurred_at,
            currency=self.currency,
            channel=self.channel,
            correlation_id=self.correlation_id,
            source="api",
        )


class TravelRequest(BaseModel):
    customer_ref: str = Field(min_length=1)
    country: str = Field(min_length=1)
    started_at: datetime
    ended_at: datetime | None = None
    correlation_id: str | None = None

    @field_validator("started_at")
    @classmethod
    def started_at_aware(cls, value: datetime) -> datetime:
        return _require_aware(value, "started_at")

    @field_validator("ended_at")
    @classmethod
    def ended_at_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _require_aware(value, "ended_at")

    def to_command(self) -> RecordTravelCommand:
        return RecordTravelCommand(
            customer_ref=self.customer_ref,
            country=self.country,
            started_at=self.started_at,
            ended_at=self.ended_at,
            correlation_id=self.correlation_id,
            source="api",
        )


class EndTravelRequest(BaseModel):
    customer_ref: str = Field(min_length=1)
    ended_at: datetime
    travel_id: UUID | None = None
    correlation_id: str | None = None

    @field_validator("ended_at")
    @classmethod
    def ended_at_aware(cls, value: datetime) -> datetime:
        return _require_aware(value, "ended_at")

    def to_command(self) -> EndTravelCommand:
        return EndTravelCommand(
            customer_ref=self.customer_ref,
            ended_at=self.ended_at,
            travel_id=self.travel_id,
            correlation_id=self.correlation_id,
            source="api",
        )


class PurchasePlanRequest(BaseModel):
    customer_ref: str = Field(min_length=1)
    plan_code: str = Field(min_length=1)
    occurred_at: datetime
    correlation_id: str | None = None

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_aware(cls, value: datetime) -> datetime:
        return _require_aware(value, "occurred_at")

    def to_command(self) -> PurchasePlanCommand:
        return PurchasePlanCommand(
            customer_ref=self.customer_ref,
            plan_code=self.plan_code,
            occurred_at=self.occurred_at,
            correlation_id=self.correlation_id,
            source="api",
        )


class UsageRequest(BaseModel):
    customer_ref: str = Field(min_length=1)
    occurred_at: datetime
    data_mb: Decimal
    usage_type: UsageType = UsageType.STREAMING
    country: str | None = None
    network_type: str | None = None
    correlation_id: str | None = None

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_aware(cls, value: datetime) -> datetime:
        return _require_aware(value, "occurred_at")

    def to_command(self) -> RecordUsageCommand:
        return RecordUsageCommand(
            customer_ref=self.customer_ref,
            occurred_at=self.occurred_at,
            data_mb=self.data_mb,
            usage_type=self.usage_type,
            country=self.country,
            network_type=self.network_type,
            correlation_id=self.correlation_id,
            source="api",
        )
