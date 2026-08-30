from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from telco_digital.domain.value_objects import display_country


class ObservedCustomerState(BaseModel):
    model_config = ConfigDict(frozen=True)

    customer_id: UUID
    customer_ref: str
    as_of: datetime
    home_country: str
    home_country_name: str
    country: str
    country_name: str
    country_source: str
    current_plan_code: str | None
    balance_amount: Decimal
    currency: str
    loyalty_points: int = 0
    device_ref: str | None = None
    active_complaints: int = 0
    active_travel_id: UUID | None = None
    trip_duration_known: bool = True
    warnings: list[str] = Field(default_factory=list)

    @classmethod
    def country_name_for(cls, code: str) -> str:
        return display_country(code)


class TimelineEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: UUID
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    payload: dict[str, Any]


class CommandResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    customer_id: UUID
    event_id: UUID
    correlation_id: str
    warnings: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)
