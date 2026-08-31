"""Compose health, projection-lag, and model-version documents.

SQL and Cypher stay in infrastructure. This module only assembles typed DTOs
from query snapshots and packaged artifacts.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from telco_digital.application.clock import Clock, SystemClock
from telco_digital.application.queries.platform import (
    ModelCatalog,
    ModelVersion,
    OutboxLagSnapshot,
    ProjectionLag,
    Readiness,
)
from telco_digital.decisioning import DECISION_SET_VERSION
from telco_digital.domain.entities import OutboxEvent
from telco_digital.domain.enums import OutboxStatus
from telco_digital.intelligence.churn import MODEL_VERSION as CHURN_MODEL_VERSION
from telco_digital.intelligence.churn import load_artifact as load_churn_artifact
from telco_digital.intelligence.churn.model import default_artifact_path as churn_artifact_path
from telco_digital.intelligence.features import FEATURE_SET_VERSION
from telco_digital.intelligence.forecasting import MODEL_VERSION as FORECAST_MODEL_VERSION
from telco_digital.intelligence.forecasting.models import (
    default_artifact_path as forecast_artifact_path,
)
from telco_digital.intelligence.forecasting.models import load_artifact as load_forecast_artifact
from telco_digital.intelligence.fraud.features import SCORER_VERSION

API_SLICE = "capability-12-fastapi"


class ProjectionLagQueries(Protocol):
    async def snapshot(self) -> OutboxLagSnapshot: ...


def snapshot_from_events(events: Sequence[OutboxEvent]) -> OutboxLagSnapshot:
    pending = [item for item in events if item.status == OutboxStatus.PENDING]
    processing = [item for item in events if item.status == OutboxStatus.PROCESSING]
    failed = [item for item in events if item.status == OutboxStatus.FAILED]
    processed = [item for item in events if item.status == OutboxStatus.PROCESSED]
    oldest_pending = min((item.created_at for item in pending), default=None)
    newest_processed = max(
        (item.processed_at for item in processed if item.processed_at is not None),
        default=None,
    )
    return OutboxLagSnapshot(
        pending=len(pending),
        processing=len(processing),
        failed=len(failed),
        processed=len(processed),
        oldest_pending_at=oldest_pending,
        newest_processed_at=newest_processed,
    )


def assemble_projection_lag(
    snapshot: OutboxLagSnapshot,
    *,
    now: datetime,
    source: str = "live_database",
) -> ProjectionLag:
    if snapshot.oldest_pending_at is not None:
        lag_seconds = max(0.0, (now - snapshot.oldest_pending_at).total_seconds())
    elif snapshot.pending == 0:
        lag_seconds = 0.0
    else:
        lag_seconds = None
    return ProjectionLag(
        source=source,
        pending_count=snapshot.pending,
        processing_count=snapshot.processing,
        failed_count=snapshot.failed,
        processed_count=snapshot.processed,
        oldest_pending_at=snapshot.oldest_pending_at,
        newest_processed_at=snapshot.newest_processed_at,
        lag_seconds=lag_seconds,
        queried_at=now,
    )


async def get_projection_lag(
    queries: ProjectionLagQueries,
    *,
    clock: Clock | None = None,
) -> ProjectionLag:
    clock = clock or SystemClock()
    return assemble_projection_lag(await queries.snapshot(), now=clock.now())


def _relative_artifact(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path(__file__).resolve().parents[4]))
    except ValueError:
        return path.name


def _artifact_entry(
    *,
    name: str,
    version: str,
    kind: str,
    load: Callable[[], dict[str, Any]],
    path: Callable[[], Path],
    algorithm: str | None = None,
    notes: str = "",
) -> ModelVersion:
    artifact = _relative_artifact(path())
    try:
        payload = load()
        served = True
        version = str(payload.get("model_version") or version)
        algorithm = algorithm or payload.get("model_type")
    except FileNotFoundError:
        served = False
    return ModelVersion(
        name=name,
        version=version,
        kind=kind,
        served=served,
        artifact=artifact,
        algorithm=str(algorithm) if algorithm else None,
        notes=notes,
    )


def get_model_catalog(*, clock: Clock | None = None) -> ModelCatalog:
    clock = clock or SystemClock()
    models = (
        _artifact_entry(
            name="churn",
            version=CHURN_MODEL_VERSION,
            kind="prediction",
            load=load_churn_artifact,
            path=churn_artifact_path,
            notes="Notebook-trained logistic regression. Not a live outcome table.",
        ),
        _artifact_entry(
            name="sfa_forecast",
            version=FORECAST_MODEL_VERSION,
            kind="forecast",
            load=load_forecast_artifact,
            path=forecast_artifact_path,
            notes="Notebook-trained retailer demand artifact.",
        ),
        ModelVersion(
            name="features",
            version=FEATURE_SET_VERSION,
            kind="feature_contract",
            served=True,
            notes="Point-in-time temporal and graph feature contract.",
        ),
        ModelVersion(
            name="fraud_rules",
            version=SCORER_VERSION,
            kind="rules",
            served=True,
            notes="Deterministic graph-fraud scorer. Not a trained embedding.",
        ),
        ModelVersion(
            name="decision",
            version=DECISION_SET_VERSION,
            kind="decision_contract",
            served=True,
            notes="Next-best-action document version. Predictions are not discounts.",
        ),
    )
    return ModelCatalog(queried_at=clock.now(), models=models)


def assemble_readiness(
    *,
    environment: str,
    postgres: str,
    neo4j: str,
) -> Readiness:
    if postgres != "ok":
        status = "unavailable"
    elif neo4j != "ok":
        status = "degraded"
    else:
        status = "ok"
    return Readiness(
        status=status,
        environment=environment,
        slice=API_SLICE,
        postgres=postgres,
        neo4j=neo4j,
    )


def liveness(*, environment: str) -> dict[str, str]:
    return {
        "status": "ok",
        "environment": environment,
        "slice": API_SLICE,
    }
