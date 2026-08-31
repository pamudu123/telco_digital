from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from telco_digital.api.deps import (
    as_of_query,
    get_as_of_queries,
    get_queries,
    get_settings_dep,
    require_showcase,
)
from telco_digital.application.services import showcase as showcase_service
from telco_digital.application.services.common import NotFoundError
from telco_digital.config import Settings
from telco_digital.infrastructure.neo4j.features import Neo4jFeatureQueries
from telco_digital.infrastructure.postgres.forecasting import PostgresRetailerDemandQueries
from telco_digital.infrastructure.postgres.showcase import PostgresShowcaseQueries
from telco_digital.intelligence.digital_twin import assemble_retailer_twin
from telco_digital.intelligence.forecasting import ForecastingService

router = APIRouter(
    prefix="/showcase",
    tags=["showcase"],
    dependencies=[Depends(require_showcase)],
)


@router.get("/graph/summary")
async def graph_summary(
    as_of: datetime = Depends(as_of_query),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    try:
        return await Neo4jFeatureQueries(settings).summary(as_of)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Neo4j projection is unreachable") from exc


@router.get("/graph/customers/{customer_ref}")
async def graph_customer(
    customer_ref: str,
    as_of: datetime = Depends(as_of_query),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    try:
        result = await Neo4jFeatureQueries(settings).calculate(customer_ref, as_of)
        return {"customer_ref": customer_ref, "as_of": as_of, **result.model_dump(mode="json")}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Neo4j projection is unreachable") from exc


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _unavailable(exc: SQLAlchemyError) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"source": "unavailable", "detail": "PostgreSQL is unreachable"},
    )


@router.get("/overview")
async def overview(
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
) -> dict:
    as_of, queries = context
    try:
        result = await showcase_service.get_overview(queries, as_of=as_of, queried_at=_now())
        return result.model_dump(mode="json")
    except SQLAlchemyError as exc:
        raise _unavailable(exc) from exc


@router.get("/evidence")
async def evidence(
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
) -> dict:
    as_of, queries = context
    try:
        result = await showcase_service.get_evidence(queries, as_of=as_of, queried_at=_now())
        return result.model_dump(mode="json")
    except SQLAlchemyError as exc:
        raise _unavailable(exc) from exc


@router.get("/personas")
async def personas(queries: PostgresShowcaseQueries = Depends(get_queries)) -> dict:
    try:
        items = await showcase_service.list_personas(queries)
        return {
            "source": "live_database",
            "personas": [item.model_dump(mode="json") for item in items],
        }
    except SQLAlchemyError as exc:
        raise _unavailable(exc) from exc


@router.get("/status")
async def status() -> dict:
    manifest = showcase_service.capability_manifest()
    return {
        "source": "capability_manifest",
        "notes": manifest.notes,
        "capabilities": [item.model_dump(mode="json") for item in manifest.capabilities],
        "artifacts": list(showcase_service.artifact_links()),
    }


@router.get("/walkthroughs")
async def walkthroughs() -> dict:
    return {
        "source": "capability_manifest",
        "walkthroughs": [item.model_dump(mode="json") for item in showcase_service.walkthroughs()],
    }


@router.get("/sfa/retailers/{retailer_ref}/forecast")
async def retailer_forecast(
    retailer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    horizon_days: int = 7,
) -> dict:
    as_of, queries = context
    try:
        result = await ForecastingService(PostgresRetailerDemandQueries(queries.session)).forecast(
            retailer_ref,
            as_of,
            horizon_days=horizon_days,
        )
        return result.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise _unavailable(exc) from exc


@router.get("/sfa/retailers/{retailer_ref}")
async def retailer(
    retailer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
) -> dict:
    as_of, queries = context
    try:
        result = await showcase_service.get_retailer_360(
            queries, retailer_ref=retailer_ref, as_of=as_of, queried_at=_now()
        )
        return result.model_dump(mode="json")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise _unavailable(exc) from exc


@router.get("/sfa/retailers/{retailer_ref}/twin")
async def retailer_twin(
    retailer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
) -> dict:
    as_of, queries = context
    try:
        facts = await showcase_service.get_retailer_360(
            queries, retailer_ref=retailer_ref, as_of=as_of, queried_at=_now()
        )
        return assemble_retailer_twin(facts).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise _unavailable(exc) from exc
