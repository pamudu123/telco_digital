#!/usr/bin/env python3
"""Project one outbox batch and checkpoint it after Neo4j succeeds."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telco_digital.infrastructure.workers.outbox_worker import run_once


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=25_000)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    processed = asyncio.run(run_once(batch_size=args.batch_size))
    print({"processed": processed})
