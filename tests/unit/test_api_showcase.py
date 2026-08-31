from fastapi.testclient import TestClient

from telco_digital.api.app import create_app
from telco_digital.config import Settings


def test_health_and_status_do_not_mark_api_complete() -> None:
    with TestClient(create_app(Settings(showcase_enabled=True, api_environment="test"))) as client:
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["slice"] == "capability-00-read-only-showcase"

        status = client.get("/api/v1/showcase/status")
        assert status.status_code == 200
        body = status.json()
        by_number = {item["number"]: item for item in body["capabilities"]}
        assert by_number["00"]["status"] == "POC complete"
        assert by_number["12"]["status"] == "Not started"
        assert by_number["13"]["status"] == "Not started"
        assert body["source"] == "capability_manifest"
        for artifact in body["artifacts"]:
            assert artifact["source"] == "capability_00_artifact"


def test_showcase_disabled_returns_404_but_health_remains() -> None:
    with TestClient(create_app(Settings(showcase_enabled=False, api_environment="test"))) as client:
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/showcase/status").status_code == 404
        assert client.get("/api/v1/showcase/walkthroughs").status_code == 404


def test_invalid_as_of_returns_422() -> None:
    with TestClient(create_app(Settings(showcase_enabled=True, api_environment="test"))) as client:
        response = client.get("/api/v1/showcase/overview", params={"as_of": "yesterday"})
        assert response.status_code == 422


def test_capability_02_routes_are_registered() -> None:
    with TestClient(create_app(Settings(showcase_enabled=True, api_environment="test"))) as client:
        paths = client.get("/openapi.json").json()["paths"]
        assert "/api/v1/customers/{customer_ref}/features" in paths
        assert "/api/v1/customers/{customer_ref}/event-memory" in paths
        assert "/api/v1/customers/{customer_ref}/behaviour" in paths
        assert "/api/v1/customers/{customer_ref}/churn" in paths
        assert "/api/v1/customers/{customer_ref}/fraud" in paths
        assert "/api/v1/showcase/graph/summary" in paths
        assert "/api/v1/showcase/graph/customers/{customer_ref}" in paths


def test_frontend_index_is_served() -> None:
    with TestClient(create_app(Settings(showcase_enabled=True, api_environment="test"))) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "capabilities 00–05, 07 showcase" in response.text
        assert "vendor/chart.umd.min.js" in response.text
        assert "js/app.js" in response.text


def test_walkthroughs_are_metadata_not_predictions() -> None:
    with TestClient(create_app(Settings(showcase_enabled=True, api_environment="test"))) as client:
        body = client.get("/api/v1/showcase/walkthroughs").json()
        assert body["source"] == "capability_manifest"
        assert len(body["walkthroughs"]) == 6
        for item in body["walkthroughs"]:
            planned = [step for step in item["steps"] if not step["live"]]
            assert planned
            assert any(
                "infer" in step["title"].lower() or "recommend" in step["title"].lower()
                for step in planned
            )
