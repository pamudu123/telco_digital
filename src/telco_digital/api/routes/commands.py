"""Command adapters. Routes call application services; no SQL, Cypher, or rules."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from telco_digital.api.deps import get_uow
from telco_digital.api.errors import service_errors
from telco_digital.api.schemas import (
    EndTravelRequest,
    PurchasePlanRequest,
    RechargeRequest,
    TravelRequest,
    UsageRequest,
)
from telco_digital.application.services.plan_purchase import purchase_plan
from telco_digital.application.services.recharge import record_recharge
from telco_digital.application.services.travel import end_travel, record_travel
from telco_digital.application.services.usage import record_usage
from telco_digital.infrastructure.postgres.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/commands", tags=["commands"])
logger = logging.getLogger(__name__)


def _payload(result, *, command: str) -> dict:
    logger.info(
        "command adapter",
        extra={
            "command": command,
            "customer_id": str(result.customer_id),
            "event_id": str(result.event_id),
            "correlation_id": result.correlation_id,
        },
    )
    body = result.model_dump(mode="json")
    body["source"] = "command_adapter"
    body["command"] = command
    return body


@router.post("/recharge")
async def command_recharge(
    body: RechargeRequest,
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> dict:
    async with service_errors():
        result = await record_recharge(uow, body.to_command())
        return _payload(result, command="record_recharge")


@router.post("/travel")
async def command_travel(
    body: TravelRequest,
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> dict:
    async with service_errors():
        result = await record_travel(uow, body.to_command())
        return _payload(result, command="record_travel")


@router.post("/travel/end")
async def command_end_travel(
    body: EndTravelRequest,
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> dict:
    async with service_errors():
        result = await end_travel(uow, body.to_command())
        return _payload(result, command="end_travel")


@router.post("/plan-purchase")
async def command_plan_purchase(
    body: PurchasePlanRequest,
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> dict:
    async with service_errors():
        result = await purchase_plan(uow, body.to_command())
        return _payload(result, command="purchase_plan")


@router.post("/usage")
async def command_usage(
    body: UsageRequest,
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> dict:
    async with service_errors():
        result = await record_usage(uow, body.to_command())
        return _payload(result, command="record_usage")
