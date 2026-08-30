"""PostgreSQL snapshot to Neo4j projection orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from telco_digital.infrastructure.neo4j.repository import GraphRepository


@dataclass(frozen=True)
class GraphSnapshot:
    customers: list[dict[str, Any]]
    accounts: list[dict[str, Any]]
    devices: list[dict[str, Any]]
    customer_devices: list[dict[str, Any]]
    plans: list[dict[str, Any]]
    subscriptions: list[dict[str, Any]]


class GraphProjector:
    def __init__(self, repository: GraphRepository) -> None:
        self.repository = repository

    def rebuild(self, snapshot: GraphSnapshot) -> dict[str, int]:
        """Idempotently merge a complete authoritative PostgreSQL snapshot."""
        self.repository.ensure_constraints()
        self.repository.project_customers(snapshot.customers)
        self.repository.project_accounts(snapshot.accounts)
        self.repository.project_devices(snapshot.devices)
        self.repository.project_customer_devices(snapshot.customer_devices)
        self.repository.project_plans(snapshot.plans)
        self.repository.project_subscriptions(snapshot.subscriptions)
        return self.repository.counts()
