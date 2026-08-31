from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

from telco_digital.api.deps import get_as_of_queries, get_settings_dep, get_uow, require_showcase
from telco_digital.application.services import showcase as showcase_service
from telco_digital.application.services.common import NotFoundError
from telco_digital.config import Settings
from telco_digital.infrastructure.neo4j.features import Neo4jFeatureQueries
from telco_digital.infrastructure.neo4j.fraud import Neo4jGraphFraudQueries
from telco_digital.infrastructure.postgres.event_memory import PostgresEventMemoryQueries
from telco_digital.infrastructure.postgres.features import PostgresTemporalFeatureQueries
from telco_digital.infrastructure.postgres.fraud import PostgresTransactionRiskQueries
from telco_digital.infrastructure.postgres.showcase import PostgresShowcaseQueries
from telco_digital.infrastructure.postgres.unit_of_work import SqlAlchemyUnitOfWork
from telco_digital.intelligence.behaviour import BehaviourService
from telco_digital.intelligence.churn import ChurnService
from telco_digital.intelligence.event_memory import EventMemoryService
from telco_digital.intelligence.features import (
    CustomerFeatureService,
    GraphFeatureService,
    TemporalFeatureService,
)
from telco_digital.intelligence.fraud import FraudService

router = APIRouter(
    prefix="/customers",
    tags=["customers"],
    dependencies=[Depends(require_showcase)],
)


@router.get("/{customer_ref}/features")
async def customer_features(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    as_of, queries = context
    service = CustomerFeatureService(
        TemporalFeatureService(PostgresTemporalFeatureQueries(queries.session)),
        GraphFeatureService(Neo4jFeatureQueries(settings)),
    )
    try:
        result = await service.calculate(customer_ref, as_of)
        return result.model_dump(mode="json")
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL is unreachable") from exc


@router.get("/{customer_ref}/event-memory")
async def customer_event_memory(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    destination: str | None = Query(default=None),
) -> dict:
    as_of, queries = context
    service = EventMemoryService(PostgresEventMemoryQueries(queries.session))
    try:
        result = await service.recall(customer_ref, as_of, destination=destination)
        return result.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL is unreachable") from exc


@router.get("/{customer_ref}/behaviour")
async def customer_behaviour(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    as_of, queries = context
    features = CustomerFeatureService(
        TemporalFeatureService(PostgresTemporalFeatureQueries(queries.session)),
        GraphFeatureService(Neo4jFeatureQueries(settings)),
    )
    memory = EventMemoryService(PostgresEventMemoryQueries(queries.session))
    try:
        result = await BehaviourService(features, memory).evaluate(customer_ref, as_of)
        return result.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL is unreachable") from exc


@router.get("/{customer_ref}/churn")
async def customer_churn(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    as_of, queries = context
    features = CustomerFeatureService(
        TemporalFeatureService(PostgresTemporalFeatureQueries(queries.session)),
        GraphFeatureService(Neo4jFeatureQueries(settings)),
    )
    try:
        result = await ChurnService(features).predict(customer_ref, as_of)
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
        raise HTTPException(status_code=503, detail="PostgreSQL is unreachable") from exc


@router.get("/{customer_ref}/fraud")
async def customer_fraud(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    as_of, queries = context
    service = FraudService(
        PostgresTransactionRiskQueries(queries.session),
        Neo4jGraphFraudQueries(settings),
    )
    try:
        result = await service.evaluate(customer_ref, as_of)
        return result.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL is unreachable") from exc


@router.get("/{customer_ref}/360")
async def customer_360(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> dict:
    as_of, queries = context
    try:
        result = await showcase_service.get_customer_360(
            uow,
            queries,
            customer_ref=customer_ref,
            as_of=as_of,
            queried_at=datetime.now(tz=UTC),
        )
        return result.model_dump(mode="json")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail={"source": "unavailable", "detail": "PostgreSQL is unreachable"},
        ) from exc
