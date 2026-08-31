"""Stable retailer query adapters wrapping application / intelligence services."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from telco_digital.api.deps import get_as_of_queries
from telco_digital.api.errors import service_errors
from telco_digital.api.stack import forecasting_service
from telco_digital.application.services import showcase as showcase_service
from telco_digital.infrastructure.postgres.showcase import PostgresShowcaseQueries
from telco_digital.intelligence.digital_twin import assemble_retailer_twin

router = APIRouter(prefix="/retailers", tags=["retailers"])


@router.get("/{retailer_ref}/forecast")
async def retailer_forecast(
    retailer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    horizon_days: int = 7,
) -> dict:
    as_of, queries = context
    async with service_errors():
        result = await forecasting_service(queries.session).forecast(
            retailer_ref,
            as_of,
            horizon_days=horizon_days,
        )
        return result.model_dump(mode="json")


@router.get("/{retailer_ref}/twin")
async def retailer_twin(
    retailer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
) -> dict:
    as_of, queries = context
    async with service_errors():
        facts = await showcase_service.get_retailer_360(
            queries,
            retailer_ref=retailer_ref,
            as_of=as_of,
            queried_at=datetime.now(tz=UTC),
        )
        return assemble_retailer_twin(facts).model_dump(mode="json")
