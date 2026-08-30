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
            "CREATE CONSTRAINT wallet_id IF NOT EXISTS FOR (n:Wallet) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT merchant_id IF NOT EXISTS FOR (n:Merchant) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT transaction_id IF NOT EXISTS "
            "FOR (n:Transaction) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT distributor_id IF NOT EXISTS "
            "FOR (n:Distributor) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT retailer_id IF NOT EXISTS FOR (n:Retailer) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT agent_id IF NOT EXISTS FOR (n:SalesAgent) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (n:Product) REQUIRE n.id IS UNIQUE",
        )
        with self.driver.session() as session:
            for statement in statements:
                session.execute_write(
                    lambda transaction, query=statement: transaction.run(query).consume()
                )

    def clear_managed_projection(self) -> None:
        with self.driver.session() as session:
            session.execute_write(
                lambda transaction: transaction.run(
                    "MATCH (n {projection: $projection}) DETACH DELETE n",
                    projection="poc-v1",
                ).consume()
            )

    def project_customers(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write(
            """
            UNWIND $rows AS row
            MERGE (n:Customer {id: row.id})
            SET n.customer_ref = row.customer_ref,
                n.projection = 'poc-v1',
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
                account.projection = 'poc-v1',
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
                device.projection = 'poc-v1',
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
                relationship.projection = 'poc-v1',
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
                plan.projection = 'poc-v1',
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
                relationship.projection = 'poc-v1',
                relationship.ended_at = CASE
                    WHEN row.ended_at IS NULL THEN NULL
                    ELSE datetime(row.ended_at)
                END,
                relationship.status = row.status
            """,
            rows,
        )

    def project_wallets(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write("""
            UNWIND $rows AS row
            MATCH (customer:Customer {id: row.customer_id})
            MERGE (wallet:Wallet {id: row.id})
            SET wallet.wallet_ref = row.wallet_ref, wallet.status = row.status,
                wallet.created_at = datetime(row.created_at), wallet.projection = 'poc-v1'
            MERGE (customer)-[:OWNS_WALLET {projection: 'poc-v1'}]->(wallet)
            """, rows)

    def project_merchants(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write("""
            UNWIND $rows AS row MERGE (merchant:Merchant {id: row.id})
            SET merchant.merchant_ref = row.merchant_ref, merchant.name = row.name,
                merchant.category = row.category, merchant.country_code = row.country_code,
                merchant.status = row.status, merchant.projection = 'poc-v1'
            """, rows)

    def project_transactions(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write("""
            UNWIND $rows AS row
            MATCH (customer:Customer {id: row.customer_id})
            MATCH (source:Wallet {id: row.source_wallet_id})
            MERGE (transaction:Transaction {id: row.id})
            SET transaction.transaction_ref = row.transaction_ref,
                transaction.amount = row.amount, transaction.currency = row.currency,
                transaction.transaction_type = row.transaction_type,
                transaction.country_code = row.country_code,
                transaction.occurred_at = datetime(row.occurred_at),
                transaction.status = row.status, transaction.projection = 'poc-v1'
            MERGE (customer)-[:INITIATED {projection: 'poc-v1'}]->(transaction)
            MERGE (transaction)-[:FROM_WALLET {projection: 'poc-v1'}]->(source)
            WITH row, transaction
            OPTIONAL MATCH (destination:Wallet {id: row.destination_wallet_id})
            FOREACH (_ IN CASE WHEN destination IS NULL THEN [] ELSE [1] END |
                MERGE (transaction)-[:TO_WALLET {projection: 'poc-v1'}]->(destination))
            WITH row, transaction
            OPTIONAL MATCH (merchant:Merchant {id: row.merchant_id})
            FOREACH (_ IN CASE WHEN merchant IS NULL THEN [] ELSE [1] END |
                MERGE (transaction)-[:AT_MERCHANT {projection: 'poc-v1'}]->(merchant))
            WITH row, transaction
            OPTIONAL MATCH (device:Device {id: row.device_id})
            FOREACH (_ IN CASE WHEN device IS NULL THEN [] ELSE [1] END |
                MERGE (transaction)-[:USED_DEVICE {projection: 'poc-v1'}]->(device))
            """, rows)

    def project_distributors(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write("""
            UNWIND $rows AS row MERGE (n:Distributor {id: row.id})
            SET n.distributor_ref = row.distributor_ref, n.name = row.name,
                n.region = row.region, n.projection = 'poc-v1'
            """, rows)

    def project_retailers(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write("""
            UNWIND $rows AS row MATCH (d:Distributor {id: row.distributor_id})
            MERGE (n:Retailer {id: row.id})
            SET n.retailer_ref = row.retailer_ref, n.name = row.name, n.region = row.region,
                n.status = row.status, n.latitude = row.latitude, n.longitude = row.longitude,
                n.projection = 'poc-v1'
            MERGE (n)-[:SUPPLIED_BY {projection: 'poc-v1'}]->(d)
            """, rows)

    def project_sales_agents(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write("""
            UNWIND $rows AS row MATCH (d:Distributor {id: row.distributor_id})
            MERGE (n:SalesAgent {id: row.id})
            SET n.agent_ref = row.agent_ref, n.name = row.name, n.status = row.status,
                n.projection = 'poc-v1'
            MERGE (n)-[:WORKS_FOR {projection: 'poc-v1'}]->(d)
            """, rows)

    def project_products(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write("""
            UNWIND $rows AS row MERGE (n:Product {id: row.id})
            SET n.product_code = row.product_code, n.name = row.name,
                n.category = row.category, n.projection = 'poc-v1'
            """, rows)

    def project_sales(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write("""
            UNWIND $rows AS row MATCH (r:Retailer {id: row.retailer_id})
            MATCH (p:Product {id: row.product_id})
            MERGE (r)-[sale:SOLD {id: row.id}]->(p)
            SET sale.quantity = row.quantity, sale.amount = row.amount,
                sale.occurred_at = datetime(row.occurred_at),
                sale.sales_agent_id = row.sales_agent_id, sale.projection = 'poc-v1'
            """, rows)

    def project_inventory_events(self, rows: Iterable[Mapping[str, Any]]) -> None:
        self._write("""
            UNWIND $rows AS row MATCH (r:Retailer {id: row.retailer_id})
            MATCH (p:Product {id: row.product_id})
            MERGE (r)-[event:INVENTORY_EVENT {id: row.id}]->(p)
            SET event.event_type = row.event_type, event.quantity = row.quantity,
                event.occurred_at = datetime(row.occurred_at), event.projection = 'poc-v1'
            """, rows)

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
            records = session.execute_read(lambda transaction: list(transaction.run(query)))
            return {record["kind"]: record["total"] for record in records}

    def _write(self, query: str, rows: Iterable[Mapping[str, Any]]) -> None:
        materialized = list(rows)
        if not materialized:
            return
        with self.driver.session() as session:
            session.execute_write(
                lambda transaction: transaction.run(query, rows=materialized).consume()
            )
