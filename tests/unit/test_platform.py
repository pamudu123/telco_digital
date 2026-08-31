from uuid import uuid4

from fastapi.testclient import TestClient
from tests.helpers import utc

from telco_digital.api.app import create_app
from telco_digital.application.clock import FixedClock
from telco_digital.application.queries.platform import OutboxLagSnapshot
from telco_digital.application.services.platform import (
    API_SLICE,
    assemble_projection_lag,
    assemble_readiness,
    get_model_catalog,
    liveness,
    snapshot_from_events,
)
from telco_digital.config import Settings
from telco_digital.domain.entities import OutboxEvent
from telco_digital.domain.enums import EventType, OutboxStatus


def test_liveness_reports_capability_12_slice() -> None:
    body = liveness(environment="test")
    assert body["status"] == "ok"
    assert body["slice"] == API_SLICE
    assert body["environment"] == "test"


def test_readiness_is_unavailable_when_postgres_is_down() -> None:
    document = assemble_readiness(environment="test", postgres="unavailable", neo4j="ok")
    assert document.status == "unavailable"
    assert document.slice == API_SLICE


def test_readiness_is_degraded_when_only_neo4j_is_down() -> None:
    document = assemble_readiness(environment="test", postgres="ok", neo4j="unavailable")
    assert document.status == "degraded"


def test_projection_lag_is_zero_when_the_outbox_is_caught_up() -> None:
    now = utc("2026-08-20T12:00:00+00:00")
    lag = assemble_projection_lag(OutboxLagSnapshot(processed=10), now=now)
    assert lag.lag_seconds == 0.0
    assert lag.pending_count == 0
    assert lag.source == "live_database"


def test_projection_lag_uses_oldest_pending_event() -> None:
    now = utc("2026-08-20T12:00:00+00:00")
    event = OutboxEvent(
        event_id=uuid4(),
        event_type=EventType.RECHARGE_RECORDED.value,
        aggregate_type="account",
        aggregate_id=uuid4(),
        payload={},
        created_at=utc("2026-08-20T11:59:00+00:00"),
        status=OutboxStatus.PENDING,
    )
    snapshot = snapshot_from_events([event])
    lag = assemble_projection_lag(snapshot, now=now)
    assert lag.pending_count == 1
    assert lag.lag_seconds == 60.0


def test_projection_lag_is_unknown_while_events_are_processing() -> None:
    now = utc("2026-08-20T12:00:00+00:00")
    lag = assemble_projection_lag(OutboxLagSnapshot(processing=2), now=now)
    assert lag.processing_count == 2
    assert lag.lag_seconds is None


def test_model_catalog_serves_churn_and_forecast_versions() -> None:
    catalog = get_model_catalog(clock=FixedClock(utc("2026-08-20T12:00:00+00:00")))
    by_name = {item.name: item for item in catalog.models}
    assert by_name["churn"].version == "churn-lr-v1"
    assert by_name["churn"].served is True
    assert by_name["sfa_forecast"].version == "sfa-forecast-v1"
    assert by_name["sfa_forecast"].served is True
    assert by_name["fraud_rules"].kind == "rules"
    assert catalog.source == "served_artifacts"


def test_models_endpoint_returns_catalog() -> None:
    with TestClient(create_app(Settings(showcase_enabled=True, api_environment="test"))) as client:
        response = client.get("/api/v1/models")
        assert response.status_code == 200
        body = response.json()
        versions = {item["name"]: item["version"] for item in body["models"]}
        assert versions["churn"] == "churn-lr-v1"
        assert versions["sfa_forecast"] == "sfa-forecast-v1"
