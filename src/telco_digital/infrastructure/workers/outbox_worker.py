"""Graph projection worker.

POC loop: read pending outbox events → lock batch → project to Neo4j → mark PROCESSED.
Later: SELECT ... FOR UPDATE SKIP LOCKED. One worker is enough for the POC.
"""

from __future__ import annotations


async def run_once() -> int:
    raise NotImplementedError("Milestone 3")
