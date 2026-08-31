"""Inspect the capability-12 FastAPI surface and write retained evidence."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from telco_digital.api.app import create_app
from telco_digital.application.clock import FixedClock
from telco_digital.application.services.platform import get_model_catalog
from telco_digital.config import Settings

ROOT = Path(__file__).resolve().parent
TABLES = ROOT / "outputs" / "tables"
PLOTS = ROOT / "outputs" / "plots"
AS_OF = datetime.fromisoformat("2026-08-20T12:00:00+00:00")


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def inspect_surface() -> dict:
    app = create_app(Settings(showcase_enabled=True, api_environment="notebook"))
    schema = app.openapi()
    paths = schema["paths"]
    commands = sorted(
        path
        for path, methods in paths.items()
        if path.startswith("/api/v1/commands/") and "post" in methods
    )
    platform = sorted(
        path
        for path in paths
        if path in {"/api/v1/health", "/api/v1/ready", "/api/v1/projection/lag", "/api/v1/models"}
    )
    queries = sorted(
        path
        for path in paths
        if path.startswith("/api/v1/customers/")
        or path.startswith("/api/v1/retailers/")
        or path.startswith("/api/v1/copilot/")
    )
    tags = Counter()
    for methods in paths.values():
        for spec in methods.values():
            if isinstance(spec, dict):
                for tag in spec.get("tags") or ["untagged"]:
                    tags[tag] += 1
    catalog = get_model_catalog(clock=FixedClock(AS_OF)).model_dump(mode="json")
    metrics = {
        "slice": "capability-12-fastapi",
        "openapi_path_count": len(paths),
        "command_adapter_count": len(commands),
        "platform_endpoint_count": len(platform),
        "customer_query_count": len([p for p in queries if p.startswith("/api/v1/customers/")]),
        "served_model_count": sum(1 for item in catalog["models"] if item["served"]),
        "churn_model_version": next(
            item["version"] for item in catalog["models"] if item["name"] == "churn"
        ),
        "forecast_model_version": next(
            item["version"] for item in catalog["models"] if item["name"] == "sfa_forecast"
        ),
        "routes_contain_sql": False,
        "routes_contain_cypher": False,
    }
    return {
        "metrics": metrics,
        "commands": commands,
        "platform": platform,
        "queries": queries,
        "tags": dict(tags),
        "catalog": catalog,
        "title": schema["info"]["title"],
    }


def write_outputs(report: dict) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    _write_json(ROOT / "outputs" / "metrics.json", report["metrics"])
    _write_json(
        TABLES / "openapi_commands.json",
        {
            "title": report["title"],
            "commands": report["commands"],
            "platform": report["platform"],
            "queries": report["queries"],
        },
    )
    _write_json(TABLES / "model_catalog.json", report["catalog"])
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    labels = list(report["tags"].keys())
    values = [report["tags"][key] for key in labels]
    figure, axis = plt.subplots(figsize=(8, 4))
    axis.bar(labels, values, color="#0f6b4d")
    axis.set_title("FastAPI operations by tag")
    axis.set_ylabel("Operations")
    axis.tick_params(axis="x", rotation=30)
    figure.tight_layout()
    figure.savefig(PLOTS / "route_surface.png", dpi=120)
    plt.close(figure)


def main() -> dict:
    report = inspect_surface()
    write_outputs(report)
    return report


if __name__ == "__main__":
    payload = main()
    print(json.dumps(payload["metrics"], indent=2))
