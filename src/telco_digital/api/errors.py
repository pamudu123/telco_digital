"""Map application exceptions to HTTP. Routes must not contain domain rules."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from telco_digital.application.services.common import AlreadyExistsError, NotFoundError


@asynccontextmanager
async def service_errors() -> AsyncIterator[None]:
    try:
        yield
    except HTTPException:
        raise
    except AlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL is unreachable") from exc
