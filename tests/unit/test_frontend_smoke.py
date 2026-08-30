from pathlib import Path

ROOT = Path("frontend")


def test_shell_has_landmarks_banner_and_vendored_chart() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'lang="en"' in html
    assert "css/variables.css" in html
    assert "vendor/chart.umd.min.js" in html
    assert "js/app.js" in html
    assert (ROOT / "vendor" / "chart.umd.min.js").stat().st_size > 10_000

    app_js = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
    assert "Synthetic data" in app_js or "synthetic" in app_js.lower()
    assert "Customer 360" in app_js
    assert "POC planned" in app_js
    assert "Graph Explorer" in app_js
    assert "Copilot" in app_js
    assert 'import { renderGraph } from "./graph.js"' in app_js
    assert "customerFeatures" in (ROOT / "js" / "api.js").read_text(encoding="utf-8")
    assert "Derived features" in (ROOT / "js" / "customer-360.js").read_text(encoding="utf-8")
    assert "Graph projection" in (ROOT / "js" / "graph.js").read_text(encoding="utf-8")


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
    assert '["journey", "Journey and Event Memory", "planned"]' in app_js
    assert '["overview", "Overview", "live"]' in app_js
    assert "No LLM answers" in app_js or "not connected" in app_js
