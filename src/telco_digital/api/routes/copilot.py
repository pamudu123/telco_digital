from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from telco_digital.api.deps import get_settings_dep, parse_as_of, require_showcase
from telco_digital.api.stack import copilot_service
from telco_digital.application.services.common import NotFoundError
from telco_digital.config import Settings

router = APIRouter(
    prefix="/copilot",
    tags=["copilot"],
    dependencies=[Depends(require_showcase)],
)


class CopilotAskBody(BaseModel):
    question: str = Field(min_length=1)
    customer_ref: str = Field(min_length=1)
    as_of: str | None = None
    destination: str | None = None


@router.post("/ask")
async def copilot_ask(
    body: CopilotAskBody,
    request: Request,
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    as_of = parse_as_of(body.as_of)
    factory = request.app.state.session_factory
    try:
        async with factory() as session:
            result = await copilot_service(session, settings).answer(
                body.question,
                body.customer_ref,
                as_of,
                destination=body.destination,
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
        raise HTTPException(status_code=503, detail="PostgreSQL is unreachable") from exc
