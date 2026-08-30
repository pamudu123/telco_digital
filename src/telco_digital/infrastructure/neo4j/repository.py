"""Neo4j projection adapter with fixed, parameterized Cypher mappings."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from neo4j import Driver


class GraphRepository:
    """Own all Cypher used to build and query the graph projection."""

    def __init__(self, driver: Driver) -> None:
        self.driver = driver

    def ensure_constraints(self) -> None:
        statements = (
            "CREATE CONSTRAINT customer_id IF NOT EXISTS "
            "FOR (n:Customer) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT account_id IF NOT EXISTS "
            "FOR (n:Account) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT device_id IF NOT EXISTS "
            "FOR (n:Device) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT plan_id IF NOT EXISTS "
            "FOR (n:Plan) REQUIRE n.id IS UNIQUE",
        )
        with self.driver.session() as session:
            for statement in statements:
                session.run(statement).consume()

    def project_customers(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write(
            """
            UNWIND $rows AS row
            MERGE (n:Customer {id: row.id})
            SET n.customer_ref = row.customer_ref,
                n.home_country = row.home_country,
                n.account_type = row.account_type,
                n.status = row.status,
                n.customer_since = datetime(row.customer_since)
            """,
            rows,
        )

    def project_accounts(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write(
            """
            UNWIND $rows AS row
            MATCH (customer:Customer {id: row.customer_id})
            MERGE (account:Account {id: row.id})
            SET account.account_ref = row.account_ref,
                account.account_type = row.account_type,
                account.currency = row.currency,
                account.status = row.status
            MERGE (customer)-[:HAS_ACCOUNT]->(account)
            """,
            rows,
        )

    def project_devices(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write(
            """
            UNWIND $rows AS row
            MERGE (device:Device {id: row.id})
            SET device.device_ref = row.device_ref,
                device.device_type = row.device_type,
                device.model = row.model,
                device.fingerprint = row.fingerprint
            """,
            rows,
        )

    def project_customer_devices(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write(
            """
            UNWIND $rows AS row
            MATCH (customer:Customer {id: row.customer_id})
            MATCH (device:Device {id: row.device_id})
            MERGE (customer)-[relationship:USES {id: row.id}]->(device)
            SET relationship.valid_from = datetime(row.valid_from),
                relationship.valid_to = CASE
                    WHEN row.valid_to IS NULL THEN NULL
                    ELSE datetime(row.valid_to)
                END
            """,
            rows,
        )

    def project_plans(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write(
            """
            UNWIND $rows AS row
            MERGE (plan:Plan {id: row.id})
            SET plan.plan_code = row.plan_code,
                plan.name = row.name,
                plan.plan_type = row.plan_type,
                plan.data_mb = row.data_mb,
                plan.validity_days = row.validity_days,
                plan.price = row.price,
                plan.currency = row.currency,
                plan.country_code = row.country_code,
                plan.active = row.active
            """,
            rows,
        )

    def project_subscriptions(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write(
            """
            UNWIND $rows AS row
            MATCH (customer:Customer {id: row.customer_id})
            MATCH (plan:Plan {id: row.plan_id})
            MERGE (customer)-[relationship:SUBSCRIBES_TO {id: row.id}]->(plan)
            SET relationship.started_at = datetime(row.started_at),
                relationship.ended_at = CASE
                    WHEN row.ended_at IS NULL THEN NULL
                    ELSE datetime(row.ended_at)
                END,
                relationship.status = row.status
            """,
            rows,
        )

    def counts(self) -> dict[str, int]:
        query = """
        MATCH (n)
        WITH labels(n)[0] AS kind, count(*) AS total
        RETURN kind, total
        UNION ALL
        MATCH ()-[r]->()
        RETURN type(r) AS kind, count(*) AS total
        """
        with self.driver.session() as session:
            return {record["kind"]: record["total"] for record in session.run(query)}

    def _write(self, query: str, rows: Iterable[Mapping[str, Any]]) -> None:
        materialized = list(rows)
        if not materialized:
            return
        with self.driver.session() as session:
            session.run(query, rows=materialized).consume()
