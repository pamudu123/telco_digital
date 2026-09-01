from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request

from telco_digital.api.deps import (
    as_of_query,
    get_as_of_queries,
    get_settings_dep,
    get_uow,
)
from telco_digital.api.errors import service_errors
from telco_digital.api.stack import (
    behaviour_service,
    churn_service,
    customer_features,
    decision_engine,
    digital_twin,
    event_memory,
    fraud_service,
    recommendations,
)
from telco_digital.application.commands.commands import GetCustomerStateQuery, GetTimelineQuery
from telco_digital.application.services import showcase as showcase_service
from telco_digital.application.services.customer_intelligence import get_customer_intelligence
from telco_digital.application.services.customer_state import get_customer_state
from telco_digital.application.services.timeline import get_timeline
from telco_digital.config import Settings
from telco_digital.infrastructure.postgres.repositories import SqlPlanRepository
from telco_digital.infrastructure.postgres.showcase import PostgresShowcaseQueries
from telco_digital.infrastructure.postgres.unit_of_work import SqlAlchemyUnitOfWork
from telco_digital.intelligence.recommendations import PlanRepositoryCatalogue

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/{customer_ref}/state")
async def customer_state(
    customer_ref: str,
    as_of: datetime = Depends(as_of_query),
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> dict:
    async with service_errors():
        result = await get_customer_state(
            uow, GetCustomerStateQuery(customer_ref=customer_ref, as_of=as_of)
        )
        return result.model_dump(mode="json")


@router.get("/{customer_ref}/timeline")
async def customer_timeline(
    customer_ref: str,
    as_of: datetime = Depends(as_of_query),
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> dict:
    async with service_errors():
        entries = await get_timeline(uow, GetTimelineQuery(customer_ref=customer_ref, as_of=as_of))
        return {
            "customer_ref": customer_ref,
            "as_of": as_of,
            "source": "live_database",
            "entries": [item.model_dump(mode="json") for item in entries],
        }


@router.get("/{customer_ref}/features")
async def customer_features_route(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    as_of, queries = context
    async with service_errors():
        result = await customer_features(queries.session, settings).calculate(customer_ref, as_of)
        return result.model_dump(mode="json")


@router.get("/{customer_ref}/event-memory")
async def customer_event_memory(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    destination: str | None = Query(default=None),
) -> dict:
    as_of, queries = context
    async with service_errors():
        result = await event_memory(queries.session).recall(
            customer_ref, as_of, destination=destination
        )
        return result.model_dump(mode="json")


@router.get("/{customer_ref}/behaviour")
async def customer_behaviour(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    as_of, queries = context
    async with service_errors():
        result = await behaviour_service(queries.session, settings).evaluate(customer_ref, as_of)
        return result.model_dump(mode="json")


@router.get("/{customer_ref}/churn")
async def customer_churn(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    as_of, queries = context
    async with service_errors():
        result = await churn_service(queries.session, settings).predict(customer_ref, as_of)
        return result.model_dump(mode="json")


@router.get("/{customer_ref}/fraud")
async def customer_fraud(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    as_of, queries = context
    async with service_errors():
        result = await fraud_service(queries.session, settings).evaluate(customer_ref, as_of)
        return result.model_dump(mode="json")


@router.get("/{customer_ref}/twin")
async def customer_twin(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    settings: Settings = Depends(get_settings_dep),
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
    destination: str | None = Query(default=None),
) -> dict:
    as_of, queries = context
    async with service_errors():
        result = await digital_twin(queries.session, settings, uow).build_customer(
            customer_ref, as_of, destination=destination
        )
        return result.model_dump(mode="json")


@router.get("/{customer_ref}/recommendations")
async def customer_recommendations(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    destination: str | None = Query(default=None),
) -> dict:
    as_of, queries = context
    async with service_errors():
        result = await recommendations(queries.session).recommend(
            customer_ref, as_of, destination=destination
        )
        return result.model_dump(mode="json")


@router.get("/{customer_ref}/decision")
async def customer_decision(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    destination: str | None = Query(default=None),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    as_of, queries = context
    async with service_errors():
        result = await decision_engine(queries.session, settings).evaluate(
            customer_ref, as_of, destination=destination
        )
        return result.model_dump(mode="json")


@router.get("/{customer_ref}/360")
async def customer_360(
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> dict:
    as_of, queries = context
    async with service_errors():
        result = await showcase_service.get_customer_360(
            uow,
            queries,
            customer_ref=customer_ref,
            as_of=as_of,
            queried_at=datetime.now(tz=UTC),
        )
        return result.model_dump(mode="json")


@router.get("/{customer_ref}/intelligence")
async def customer_intelligence(
    request: Request,
    customer_ref: str,
    context: tuple[datetime, PostgresShowcaseQueries] = Depends(get_as_of_queries),
    settings: Settings = Depends(get_settings_dep),
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
    destination: str | None = Query(default=None),
) -> dict:
    as_of, queries = context
    async with service_errors():
        factory = request.app.state.session_factory
        async with (
            factory() as feature_session,
            factory() as memory_session,
            factory() as fraud_session,
        ):
            result = await get_customer_intelligence(
                customer_ref=customer_ref,
                as_of=as_of,
                destination=destination,
                queries=queries,
                uow=uow,
                features=customer_features(feature_session, settings),
                memory=event_memory(memory_session),
                catalogue=PlanRepositoryCatalogue(SqlPlanRepository(memory_session)),
                fraud=fraud_service(fraud_session, settings),
            )
        return result.model_dump(mode="json")
