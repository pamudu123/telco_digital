"""Platform DTOs for health, projection lag, and served model versions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OutboxLagSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    pending: int = 0
    processing: int = 0
    failed: int = 0
    processed: int = 0
    oldest_pending_at: datetime | None = None
    newest_processed_at: datetime | None = None


class ProjectionLag(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = "live_database"
    pending_count: int
    processing_count: int
    failed_count: int
    processed_count: int
    oldest_pending_at: datetime | None = None
    newest_processed_at: datetime | None = None
    lag_seconds: float | None = None
    queried_at: datetime


class ModelVersion(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    kind: str
    served: bool
    artifact: str | None = None
    algorithm: str | None = None
    notes: str = ""


class ModelCatalog(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = "served_artifacts"
    queried_at: datetime
    models: tuple[ModelVersion, ...] = Field(default_factory=tuple)


class Readiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    environment: str
    slice: str
    postgres: str
    neo4j: str
