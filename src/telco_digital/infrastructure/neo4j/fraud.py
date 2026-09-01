"""Read-only Cypher queries for capability-07 graph fraud features."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from neo4j import GraphDatabase

from telco_digital.config import Settings
from telco_digital.intelligence.fraud.features import (
    KNOWN_FRAUD_CUSTOMER_REFS,
    GraphFraudFeatures,
    distance_to_known_fraud,
    graph_unavailable,
    suspicious_neighbors,
)


class Neo4jGraphFraudQueries:
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

    async def calculate(self, customer_ref: str, as_of: datetime) -> GraphFraudFeatures:
        return await asyncio.to_thread(self._calculate, customer_ref, as_of)

    def _calculate(self, customer_ref: str, as_of: datetime) -> GraphFraudFeatures:
        query = """
        MATCH (c:Customer {customer_ref: $customer_ref, projection: 'poc-v1'})
        OPTIONAL MATCH (c)-[uses:USES]->(device:Device)<-[other:USES]-(peer:Customer)
        WHERE datetime(uses.valid_from) <= datetime($as_of)
          AND (uses['valid_to'] IS NULL OR datetime(uses['valid_to']) > datetime($as_of))
          AND datetime(other.valid_from) <= datetime($as_of)
          AND (other['valid_to'] IS NULL OR datetime(other['valid_to']) > datetime($as_of))
        WITH c, collect(DISTINCT peer.customer_ref) AS device_peers
        OPTIONAL MATCH (sender:Customer)-[:INITIATED]->(inbound:Transaction)
                       -[:TO_WALLET]->(:Wallet)<-[:OWNS_WALLET]-(c)
        WHERE datetime(inbound.occurred_at) >= datetime($window_start)
          AND datetime(inbound.occurred_at) <= datetime($as_of)
        WITH c, device_peers, collect(DISTINCT sender.customer_ref) AS inbound_refs
        OPTIONAL MATCH (c)-[:INITIATED]->(outbound:Transaction)
                       -[:TO_WALLET]->(:Wallet)<-[:OWNS_WALLET]-(recv:Customer)
        WHERE datetime(outbound.occurred_at) >= datetime($window_start)
          AND datetime(outbound.occurred_at) <= datetime($as_of)
        WITH c, device_peers, inbound_refs, collect(DISTINCT recv.customer_ref) AS outbound_refs
        OPTIONAL MATCH (c)-[:INITIATED]->(out_circ:Transaction)
                       -[:TO_WALLET]->(:Wallet)<-[:OWNS_WALLET]-(other:Customer)
        WHERE datetime(out_circ.occurred_at) >= datetime($window_start)
          AND datetime(out_circ.occurred_at) <= datetime($as_of)
        OPTIONAL MATCH (other)-[:INITIATED]->(back:Transaction)
                       -[:TO_WALLET]->(:Wallet)<-[:OWNS_WALLET]-(c)
        WHERE datetime(back.occurred_at) >= datetime($window_start)
          AND datetime(back.occurred_at) <= datetime($as_of)
        WITH c, device_peers, inbound_refs, outbound_refs,
             collect(DISTINCT CASE WHEN back IS NULL THEN NULL ELSE other.customer_ref END)
             AS circular_refs
        OPTIONAL MATCH (c)-[:INITIATED]->(pay:Transaction)-[:AT_MERCHANT]->(merchant:Merchant)
        WHERE datetime(pay.occurred_at) >= datetime($window_start)
          AND datetime(pay.occurred_at) <= datetime($as_of)
        WITH c, device_peers, inbound_refs, outbound_refs, circular_refs,
             collect(DISTINCT merchant) AS merchants
        UNWIND CASE WHEN size(merchants) = 0 THEN [NULL] ELSE merchants END AS merchant
        OPTIONAL MATCH (other_pay:Customer)-[:INITIATED]->(opay:Transaction)
                       -[:AT_MERCHANT]->(merchant)
        WHERE merchant IS NOT NULL
          AND datetime(opay.occurred_at) >= datetime($window_start)
          AND datetime(opay.occurred_at) <= datetime($as_of)
        WITH device_peers, inbound_refs, outbound_refs, circular_refs, merchants,
             merchant, count(DISTINCT other_pay) AS merchant_customers,
             count(DISTINCT opay) AS merchant_degree
        RETURN device_peers, inbound_refs, outbound_refs, circular_refs,
               size([m IN merchants WHERE m IS NOT NULL]) AS merchant_count,
               max(merchant_customers) AS merchant_customer_count,
               max(merchant_degree) AS merchant_degree
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
            return graph_unavailable("Customer is absent from the managed Neo4j projection.")

        device_peers = _refs(record["device_peers"])
        inbound_refs = _refs(record["inbound_refs"])
        outbound_refs = _refs(record["outbound_refs"])
        circular_refs = _refs(record["circular_refs"])
        wallet_neighbors = tuple(dict.fromkeys([*inbound_refs, *outbound_refs]))
        neighbor_refs = tuple(dict.fromkeys([*device_peers, *wallet_neighbors]))
        transfer_edges = len(inbound_refs) + len(outbound_refs)
        neighbor_count = max(1, len(neighbor_refs))
        density = round(min(1.0, transfer_edges / max(1, neighbor_count * (neighbor_count - 1))), 4)
        return GraphFraudFeatures(
            available=True,
            shared_device_customer_count=len(device_peers),
            shared_wallet_count=len(wallet_neighbors),
            incoming_transfer_counterparty_count=len(inbound_refs),
            outgoing_transfer_counterparty_count=len(outbound_refs),
            circular_transfer_count=len(circular_refs),
            merchant_degree=int(record["merchant_degree"] or 0),
            merchant_customer_count=int(record["merchant_customer_count"] or 0),
            suspicious_neighbor_count=suspicious_neighbors(
                customer_ref, wallet_neighbors, inbound_refs, KNOWN_FRAUD_CUSTOMER_REFS
            ),
            distance_to_known_fraud=distance_to_known_fraud(
                customer_ref, wallet_neighbors, KNOWN_FRAUD_CUSTOMER_REFS
            ),
            connected_component_size=1 + len(neighbor_refs),
            transaction_cluster_density=density,
            neighbor_refs=neighbor_refs,
        )


def _refs(values: list | None) -> tuple[str, ...]:
    return tuple(ref for ref in (values or []) if ref)
