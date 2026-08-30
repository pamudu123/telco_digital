"""Neo4j projection adapters.

Cypher lives only here. Application services must not import this package
until Milestone 3. Projection is idempotent MERGE from the Postgres outbox.
"""

from __future__ import annotations


class GraphRepository:
    """Infrastructure owner of parameterized Cypher. Not yet wired."""

    def project_customer(self, *args, **kwargs) -> None:
        raise NotImplementedError("Milestone 3")

    def project_device(self, *args, **kwargs) -> None:
        raise NotImplementedError("Milestone 3")

    def project_transaction(self, *args, **kwargs) -> None:
        raise NotImplementedError("Milestone 3")

    def customer_neighborhood(self, *args, **kwargs) -> None:
        raise NotImplementedError("Milestone 3")

    def fraud_connections(self, *args, **kwargs) -> None:
        raise NotImplementedError("Milestone 3")
