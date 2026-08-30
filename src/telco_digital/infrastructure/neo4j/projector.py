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
    wallets: list[dict[str, Any]]
    merchants: list[dict[str, Any]]
    transactions: list[dict[str, Any]]
    distributors: list[dict[str, Any]]
    retailers: list[dict[str, Any]]
    sales_agents: list[dict[str, Any]]
    products: list[dict[str, Any]]
    sales: list[dict[str, Any]]
    inventory_events: list[dict[str, Any]]


class GraphProjector:
    def __init__(self, repository: GraphRepository) -> None:
        self.repository = repository

    def rebuild(self, snapshot: GraphSnapshot, *, reset_managed: bool = True) -> dict[str, int]:
        """Idempotently merge a complete authoritative PostgreSQL snapshot."""
        self.repository.ensure_constraints()
        if reset_managed:
            self.repository.clear_managed_projection()
        self.repository.project_customers(snapshot.customers)
        self.repository.project_accounts(snapshot.accounts)
        self.repository.project_devices(snapshot.devices)
        self.repository.project_customer_devices(snapshot.customer_devices)
        self.repository.project_plans(snapshot.plans)
        self.repository.project_subscriptions(snapshot.subscriptions)
        self.repository.project_wallets(snapshot.wallets)
        self.repository.project_merchants(snapshot.merchants)
        self.repository.project_transactions(snapshot.transactions)
        self.repository.project_distributors(snapshot.distributors)
        self.repository.project_retailers(snapshot.retailers)
        self.repository.project_sales_agents(snapshot.sales_agents)
        self.repository.project_products(snapshot.products)
        self.repository.project_sales(snapshot.sales)
        self.repository.project_inventory_events(snapshot.inventory_events)
        return self.repository.counts()
