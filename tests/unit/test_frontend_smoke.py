from pathlib import Path

ROOT = Path("frontend")


def test_shell_has_landmarks_and_vendored_chart() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'lang="en"' in html
    assert "css/variables.css" in html
    assert "Company Intelligence POC" in html
    assert "omobio" not in html.lower()
    assert "vendor/chart.umd.min.js" in html
    assert "js/app.js" in html
    assert (ROOT / "vendor" / "chart.umd.min.js").stat().st_size > 10_000

    app_js = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
    assert "Synthetic data" in app_js or "synthetic" in app_js.lower()
    assert 'className: "banner"' not in app_js
    assert "COMPANY INTELLIGENCE" in app_js
    assert "omobio" not in app_js.lower()
    assert "Customer 360" in app_js
    assert "POC planned" in app_js
    assert "Graph Explorer" in app_js
    assert "Copilot" in app_js
    assert 'import { renderGraph } from "./graph.js"' in app_js
    assert "customerFeatures" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "customerBehaviour" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "customerChurn" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "customerFraud" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "customerRecommendations" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "retailerForecast" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "customerTwin" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "retailerTwin" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "customerDecision" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "copilotAsk" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "projectionLag" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "customerState" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "OPENROUTER" not in (ROOT / "js" / "config.js").read_text(encoding="utf-8")
    assert "badge-recommend" in (ROOT / "css" / "components.css").read_text(encoding="utf-8")
    assert "Derived features" in (ROOT / "js" / "customer-360.js").read_text(encoding="utf-8")
    assert "Digital twin" in (ROOT / "js" / "customer-360.js").read_text(encoding="utf-8")
    assert "Behaviour traits" in (ROOT / "js" / "customer-360.js").read_text(encoding="utf-8")
    assert "Churn prediction" in (ROOT / "js" / "customer-360.js").read_text(encoding="utf-8")
    assert "Graph fraud" in (ROOT / "js" / "customer-360.js").read_text(encoding="utf-8")
    assert "recommendationPanel" in (ROOT / "js" / "customer-360.js").read_text(encoding="utf-8")
    assert "Demand forecast" in (ROOT / "js" / "customer-360.js").read_text(encoding="utf-8")
    assert "Decision" in (ROOT / "js" / "customer-360.js").read_text(encoding="utf-8")
    assert "decisionPanel" in (ROOT / "js" / "journey.js").read_text(encoding="utf-8")
    assert "Fallback" in (ROOT / "js" / "copilot.js").read_text(encoding="utf-8")
    assert 'className: "question-field"' in (ROOT / "js" / "copilot.js").read_text(encoding="utf-8")
    assert ".toolbar .question-field" in (ROOT / "css" / "components.css").read_text(
        encoding="utf-8"
    )
    assert "Digital twins" in (ROOT / "js" / "models.js").read_text(encoding="utf-8")
    assert "badge-prediction" in (ROOT / "css" / "components.css").read_text(encoding="utf-8")
    assert "badge-forecast" in (ROOT / "css" / "components.css").read_text(encoding="utf-8")
    assert "FastAPI platform" in (ROOT / "js" / "status.js").read_text(encoding="utf-8")
    assert "projectionLag" in (ROOT / "js" / "status.js").read_text(encoding="utf-8")


def test_status_links_all_submitted_capability_evidence() -> None:
    status_js = (ROOT / "js" / "status.js").read_text(encoding="utf-8")
    assert "SOURCE_REPOSITORY_URL" in status_js
    assert 'el("th", { text: "Live evidence" })' in status_js
    assert 'target: "_blank"' in status_js
    assert "item.evidence" in status_js
    assert "Retained capability-00 artifacts" not in status_js
    assert 'badge("Not connected", "unknown")' in status_js
    assert 'errorBox(lag, "Projection lag unavailable.")' not in status_js


def test_as_of_controls_accept_dates_without_a_time_component() -> None:
    for filename in ("customer-360.js", "journey.js", "models.js", "copilot.js"):
        source = (ROOT / "js" / filename).read_text(encoding="utf-8")
        assert 'text: "As of date (optional)"' in source
        assert 'type: "date"' in source
        assert "ISO-8601" not in source

    api_js = (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "T23:59:59Z" in api_js


def test_frontend_does_not_assign_untrusted_inner_html() -> None:
    for path in (ROOT / "js").glob("*.js"):
        source = path.read_text(encoding="utf-8")
        assert "innerHTML" not in source


def test_frontend_renders_temporal_provenance_in_utc() -> None:
    dom_js = (ROOT / "js" / "dom.js").read_text(encoding="utf-8")
    assert 'timeZone: "UTC"' in dom_js
    assert "} UTC`" in dom_js


def test_nav_distinguishes_live_and_planned_pages() -> None:
    app_js = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
    assert '["journey", "Journey and Event Memory", "live"]' in app_js
    assert 'import { renderJourney } from "./journey.js"' in app_js
    assert "eventMemory" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    journey_js = (ROOT / "js" / "journey.js").read_text(encoding="utf-8")
    customer_js = (ROOT / "js" / "customer-360.js").read_text(encoding="utf-8")
    assert "Recall episodes" in journey_js
    assert "customerRecommendations" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "SCENARIO_BASED" in journey_js or "recommendationPanel" in journey_js
    assert "Recommend" in journey_js
    assert 'params.get("destination") || "SG"' not in journey_js
    assert 'params.get("destination") || ""' in journey_js
    assert "duration_known" in customer_js
    assert "duration unknown" in customer_js
    assert "formatEpisodeSummary" in customer_js
    assert '["overview", "Overview", "live"]' in app_js
    assert '["models", "Models and Decisions", "live"]' in app_js
    assert '["copilot", "Copilot", "live"]' in app_js
    assert "00–12" in app_js
    assert "renderCopilot" in app_js
    assert "renderModels" in app_js


def test_customer_360_does_not_paint_stale_loads() -> None:
    app_js = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
    api_js = (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    customer_js = (ROOT / "js" / "customer-360.js").read_text(encoding="utf-8")

    assert "AbortController" in app_js
    assert "active.abort()" in app_js
    assert "isAbortError" in api_js
    assert "AbortError" in api_js
    assert "page-results" in customer_js
    assert "Promise.allSettled" in customer_js
    assert "results.replaceChildren" in customer_js
    assert "Recorded facts remain live" in customer_js
    assert "root.append(renderFacts" not in customer_js
    assert "root.append(errorBox" not in customer_js
