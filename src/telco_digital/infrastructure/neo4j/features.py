"""Read-only, point-in-time Cypher feature queries."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from neo4j import GraphDatabase

from telco_digital.config import Settings
from telco_digital.intelligence.features import GraphFeatures


class Neo4jFeatureQueries:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _driver(self):
        return GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
            connection_timeout=self.settings.neo4j_connection_timeout_seconds,
            connection_acquisition_timeout=(
                self.settings.neo4j_connection_acquisition_timeout_seconds
            ),
        )

    async def calculate(self, customer_ref: str, as_of: datetime) -> GraphFeatures:
        return await asyncio.to_thread(self._calculate, customer_ref, as_of)

    def _calculate(self, customer_ref: str, as_of: datetime) -> GraphFeatures:
        query = """
        MATCH (c:Customer {customer_ref: $customer_ref, projection: 'poc-v1'})
        OPTIONAL MATCH (c)-[uses:USES]->(device:Device)<-[other:USES]-(peer:Customer)
        WHERE datetime(uses.valid_from) <= datetime($as_of)
          AND (uses['valid_to'] IS NULL OR datetime(uses['valid_to']) > datetime($as_of))
          AND datetime(other.valid_from) <= datetime($as_of)
          AND (other['valid_to'] IS NULL OR datetime(other['valid_to']) > datetime($as_of))
        WITH c, count(DISTINCT peer) AS shared_device_customers
        OPTIONAL MATCH (c)-[:INITIATED]->(txn:Transaction)-[:AT_MERCHANT]->(merchant:Merchant)
        WHERE datetime(txn.occurred_at) >= datetime($window_start)
          AND datetime(txn.occurred_at) <= datetime($as_of)
        WITH c, shared_device_customers, count(DISTINCT merchant) AS merchant_neighborhood,
             count(DISTINCT txn) AS recent_transactions
        OPTIONAL MATCH (c)-[:INITIATED]->(transfer:Transaction)
                       -[:TO_WALLET]->(wallet:Wallet)
                       <-[:OWNS_WALLET]-(counterparty:Customer)
        WHERE datetime(transfer.occurred_at) >= datetime($window_start)
          AND datetime(transfer.occurred_at) <= datetime($as_of)
        OPTIONAL MATCH (c)-[relationship]-(neighbor)
        WITH shared_device_customers, merchant_neighborhood, recent_transactions,
             counterparty, relationship, neighbor,
             CASE
               WHEN type(relationship) IN ['HAS_ACCOUNT', 'OWNS_WALLET'] THEN relationship
               WHEN type(relationship) = 'USES'
                 AND datetime(relationship.valid_from) <= datetime($as_of)
                 AND (relationship['valid_to'] IS NULL
                      OR datetime(relationship['valid_to']) > datetime($as_of)) THEN relationship
               WHEN type(relationship) = 'SUBSCRIBES_TO'
                 AND datetime(relationship.started_at) <= datetime($as_of)
                 AND (relationship['ended_at'] IS NULL
                      OR datetime(relationship['ended_at']) > datetime($as_of)) THEN relationship
               WHEN type(relationship) = 'INITIATED'
                 AND datetime(neighbor.occurred_at) <= datetime($as_of) THEN relationship
             END AS bounded_relationship
        RETURN shared_device_customers, merchant_neighborhood, recent_transactions,
               count(DISTINCT counterparty) AS wallet_counterparties,
               count(DISTINCT bounded_relationship) AS customer_graph_degree
        """
        with self._driver() as driver:
            record = driver.execute_query(
                query,
                customer_ref=customer_ref,
                as_of=as_of.isoformat(),
                window_start=(as_of - timedelta(days=90)).isoformat(),
                result_transformer_=lambda result: result.single(strict=False),
            )
        if record is None:
            return GraphFeatures(
                available=False,
                values={},
                unknowns=("Customer is absent from the managed Neo4j projection.",),
            )
        return GraphFeatures(
            available=True,
            values={
                "customer_graph_degree": record["customer_graph_degree"],
                "shared_device_customer_count": record["shared_device_customers"],
                "wallet_counterparty_count_90d": record["wallet_counterparties"],
                "merchant_neighborhood_90d": record["merchant_neighborhood"],
                "transaction_relationship_count_90d": record["recent_transactions"],
            },
        )

    async def summary(self, as_of: datetime) -> dict:
        return await asyncio.to_thread(self._summary, as_of)

    def _summary(self, as_of: datetime) -> dict:
        with self._driver() as driver:
            nodes = driver.execute_query(
                "MATCH (n {projection: 'poc-v1'}) "
                "RETURN labels(n)[0] AS kind, count(*) AS total ORDER BY kind",
                result_transformer_=lambda result: result.data(),
            )
            relationships = driver.execute_query(
                "MATCH ()-[r {projection: 'poc-v1'}]->() "
                "RETURN type(r) AS kind, count(*) AS total ORDER BY kind",
                result_transformer_=lambda result: result.data(),
            )
            shared = driver.execute_query(
                """
                MATCH (d:Device {projection: 'poc-v1'})<-[r:USES]-(c:Customer)
                WHERE datetime(r.valid_from) <= datetime($as_of)
                  AND (r['valid_to'] IS NULL OR datetime(r['valid_to']) > datetime($as_of))
                WITH d, count(DISTINCT c) AS customers
                WHERE customers > 1
                RETURN d.device_ref AS device_ref, customers
                ORDER BY customers DESC, device_ref LIMIT 25
                """,
                as_of=as_of.isoformat(),
                result_transformer_=lambda result: result.data(),
            )
        return {
            "source": "neo4j_projection",
            "projection": "poc-v1",
            "as_of": as_of,
            "node_counts": nodes,
            "relationship_counts": relationships,
            "shared_devices": shared,
            "reconciled": True,
        }
