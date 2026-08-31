from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from telco_digital.api.deps import get_lag_queries, get_settings_dep
from telco_digital.api.errors import service_errors
from telco_digital.application.services.platform import (
    assemble_readiness,
    get_model_catalog,
    get_projection_lag,
    liveness,
)
from telco_digital.config import Settings
from telco_digital.infrastructure.neo4j.health import ping_neo4j
from telco_digital.infrastructure.postgres.platform import PostgresProjectionLagQueries
from telco_digital.infrastructure.postgres.session import check_database_connection

router = APIRouter(tags=["platform"])


@router.get("/health")
async def health(settings: Settings = Depends(get_settings_dep)) -> dict[str, str]:
    return liveness(environment=settings.api_environment)


@router.get("/ready")
async def ready(request: Request, settings: Settings = Depends(get_settings_dep)) -> JSONResponse:
    postgres = "ok"
    try:
        await check_database_connection(request.app.state.engine)
    except Exception:
        postgres = "unavailable"
    neo4j = "ok" if await ping_neo4j(settings) else "unavailable"
    document = assemble_readiness(
        environment=settings.api_environment,
        postgres=postgres,
        neo4j=neo4j,
    )
    status_code = 503 if document.status == "unavailable" else 200
    return JSONResponse(status_code=status_code, content=document.model_dump(mode="json"))


@router.get("/projection/lag")
async def projection_lag(
    queries: PostgresProjectionLagQueries = Depends(get_lag_queries),
) -> dict:
    async with service_errors():
        result = await get_projection_lag(queries)
        return result.model_dump(mode="json")


@router.get("/models")
async def models() -> dict:
    result = get_model_catalog()
    return result.model_dump(mode="json")
