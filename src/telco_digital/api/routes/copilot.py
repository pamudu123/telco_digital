from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from telco_digital.api.deps import get_settings_dep, parse_as_of
from telco_digital.api.errors import service_errors
from telco_digital.api.stack import copilot_service
from telco_digital.config import Settings

router = APIRouter(prefix="/copilot", tags=["copilot"])


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
    async with service_errors():
        async with factory() as session:
            result = await copilot_service(session, settings).answer(
                body.question,
                body.customer_ref,
                as_of,
                destination=body.destination,
            )
            return result.model_dump(mode="json")
