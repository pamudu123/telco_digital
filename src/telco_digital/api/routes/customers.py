from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from telco_digital.api.deps import get_as_of_queries, get_uow, require_showcase
from telco_digital.application.services import showcase as showcase_service
from telco_digital.application.services.common import NotFoundError
from telco_digital.infrastructure.postgres.showcase import PostgresShowcaseQueries
from telco_digital.infrastructure.postgres.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(
    prefix="/customers",
    tags=["customers"],
    dependencies=[Depends(require_showcase)],
)


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
