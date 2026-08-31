from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from telco_digital.api.deps import attach_runtime
from telco_digital.api.routes import commands, copilot, customers, health, retailers, showcase
from telco_digital.config import Settings, get_settings


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    attach_runtime(application, application.state.settings)
    try:
        yield
    finally:
        engine = getattr(application.state, "engine", None)
        if engine is not None:
            await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(
        title="Omobio Intelligence POC — FastAPI",
        version="0.1.0",
        description=(
            "Thin HTTP adapters over application services. PostgreSQL is the source "
            "of truth. Routes contain no SQL, Cypher, or ML. The simulator write UI "
            "is capability 13."
        ),
        lifespan=lifespan,
    )
    application.state.settings = settings

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @application.exception_handler(SQLAlchemyError)
    async def database_unavailable(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "source": "unavailable",
                "detail": "PostgreSQL is unreachable",
            },
        )

    application.include_router(health.router, prefix="/api/v1")
    application.include_router(commands.router, prefix="/api/v1")
    application.include_router(customers.router, prefix="/api/v1")
    application.include_router(retailers.router, prefix="/api/v1")
    application.include_router(copilot.router, prefix="/api/v1")
    application.include_router(showcase.router, prefix="/api/v1")

    frontend = repo_root() / "frontend"
    if frontend.is_dir():
        application.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")

    return application


app = create_app()
