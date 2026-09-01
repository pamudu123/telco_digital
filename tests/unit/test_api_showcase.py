from fastapi.testclient import TestClient

from telco_digital.api.app import create_app
from telco_digital.config import Settings


def test_health_and_status_mark_fastapi_complete() -> None:
    with TestClient(create_app(Settings(showcase_enabled=True, api_environment="test"))) as client:
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["slice"] == "capability-12-fastapi"

        status = client.get("/api/v1/showcase/status")
        assert status.status_code == 200
        body = status.json()
        by_number = {item["number"]: item for item in body["capabilities"]}
        assert by_number["00"]["status"] == "POC complete"
        assert by_number["12"]["status"] == "POC complete"
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
        assert "/api/v1/customers/{customer_ref}/intelligence" in paths
        assert "/api/v1/customers/{customer_ref}/event-memory" in paths
        assert "/api/v1/customers/{customer_ref}/behaviour" in paths
        assert "/api/v1/customers/{customer_ref}/churn" in paths
        assert "/api/v1/customers/{customer_ref}/fraud" in paths
        assert "/api/v1/customers/{customer_ref}/recommendations" in paths
        assert "/api/v1/showcase/sfa/retailers/{retailer_ref}/forecast" in paths
        assert "/api/v1/customers/{customer_ref}/twin" in paths
        assert "/api/v1/showcase/sfa/retailers/{retailer_ref}/twin" in paths
        assert "/api/v1/customers/{customer_ref}/decision" in paths
        assert "/api/v1/customers/{customer_ref}/state" in paths
        assert "/api/v1/customers/{customer_ref}/timeline" in paths
        assert "/api/v1/commands/recharge" in paths
        assert "/api/v1/commands/travel" in paths
        assert "/api/v1/commands/plan-purchase" in paths
        assert "/api/v1/commands/usage" in paths
        assert "/api/v1/projection/lag" in paths
        assert "/api/v1/models" in paths
        assert "/api/v1/ready" in paths
        assert "/api/v1/retailers/{retailer_ref}/forecast" in paths
        assert "/api/v1/copilot/ask" in paths
        assert "/api/v1/showcase/graph/summary" in paths
        assert "/api/v1/showcase/graph/customers/{customer_ref}" in paths


def test_copilot_invalid_as_of_returns_422() -> None:
    with TestClient(create_app(Settings(showcase_enabled=True, api_environment="test"))) as client:
        response = client.post(
            "/api/v1/copilot/ask",
            json={
                "question": "Why is U001 receiving this recommendation?",
                "customer_ref": "U001",
                "as_of": "yesterday",
            },
        )
        assert response.status_code == 422


def test_frontend_index_is_served() -> None:
    with TestClient(create_app(Settings(showcase_enabled=True, api_environment="test"))) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "capabilities 00–12 FastAPI" in response.text
        assert "vendor/chart.umd.min.js" in response.text
        assert "js/app.js" in response.text


def test_walkthroughs_are_metadata_not_predictions() -> None:
    with TestClient(create_app(Settings(showcase_enabled=True, api_environment="test"))) as client:
        body = client.get("/api/v1/showcase/walkthroughs").json()
        assert body["source"] == "capability_manifest"
        assert len(body["walkthroughs"]) == 6
        for item in body["walkthroughs"]:
            planned = [step for step in item["steps"] if not step["live"]]
            if item["id"] in {
                "singapore-travel",
                "retailer-stock",
                "declining-usage",
                "small-recharges",
            }:
                assert any(
                    step["live"] and "recommend" in step["title"].lower() for step in item["steps"]
                )
                if item["id"] == "singapore-travel":
                    assert "outcome" in item["later_intelligence"].lower()
                if item["id"] == "declining-usage":
                    assert any("support" in step["summary"].lower() for step in item["steps"])
                    assert any("discount" in step["summary"].lower() for step in item["steps"])
                continue
            assert planned
            assert any(
                "infer" in step["title"].lower() or "recommend" in step["title"].lower()
                for step in planned
            )
