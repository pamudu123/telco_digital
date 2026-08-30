"""Outbox → Neo4j projector. Rebuild must be possible from Postgres alone."""

from __future__ import annotations


class GraphProjector:
    def project_event(self, outbox_event) -> None:
        raise NotImplementedError("Milestone 3: MERGE nodes/relationships from outbox")
