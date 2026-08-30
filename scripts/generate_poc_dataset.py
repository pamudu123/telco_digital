#!/usr/bin/env python3
"""Load, validate, or reset the deterministic capability-00 POC dataset."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telco_digital.application.demo_dataset import build_dataset
from telco_digital.infrastructure.postgres.demo_dataset import (
    load_dataset,
    reset_dataset,
    validate_dataset,
)
from telco_digital.infrastructure.postgres.session import create_engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("load", "validate", "reset"))
    parser.add_argument("--background-customers", type=int, default=1000)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("notebooks/00_dataset/outputs/metrics.json"),
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.background_customers < 0:
        raise ValueError("--background-customers must be non-negative")
    bundle = build_dataset(args.background_customers)
    engine = create_engine()
    try:
        operation: dict[str, object]
        if args.action == "load":
            operation = {"attempted_rows": await load_dataset(engine, bundle)}
        elif args.action == "reset":
            operation = {"deleted_rows": await reset_dataset(engine, bundle)}
        else:
            operation = {}
        validation = await validate_dataset(engine, bundle.metrics["row_counts"])
    finally:
        await engine.dispose()

    report = dict(bundle.metrics)
    report["operation"] = args.action
    report["operation_result"] = operation
    report["validation"] = validation
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(validation, indent=2))
    if args.action != "reset" and not validation["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
