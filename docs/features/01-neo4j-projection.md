# Capability 01 — Outbox and Neo4j projection

## 1. POC objective

Prove that PostgreSQL remains authoritative while a useful cross-domain Neo4j
graph can be rebuilt, reconciled, and checkpointed through the transactional
outbox. This is deliberately a single-worker POC, not a distributed projection
platform.

## 2. Demonstrated scenario

The worker reads pending PostgreSQL outbox rows, marks a locked batch as
processing, rebuilds the `poc-v1` graph, and marks the batch processed only after
Neo4j succeeds. A failed write records a bounded error and returns the row to
pending until the third attempt, after which it is marked failed.

The graph connects customers to accounts, devices, plans and wallets; money
transactions to source/destination wallets, merchants and devices; and SFA
retailers and agents to distributors, products, sales and inventory events.

## 3. Data inputs and outputs

Inputs are the existing `core`, `telco`, `money`, `sfa`, and `integration`
PostgreSQL schemas. Outputs are Neo4j nodes and relationships carrying
`projection: "poc-v1"`, plus outbox `status`, `attempt_count`, `processed_at`,
and `last_error` updates in PostgreSQL.

No Neo4j value is promoted back into PostgreSQL. The graph is disposable and
rebuildable.

## 4. Architecture and data flow

```text
PostgreSQL facts + pending outbox
              ↓ locked batch
Authoritative snapshot loader
              ↓
Managed Neo4j transaction retries
              ↓
poc-v1 graph rebuild and reconciliation
              ↓ success only
PostgreSQL outbox PROCESSED checkpoint
```

Rebuild deletion is restricted to nodes marked `projection: "poc-v1"`.
Unrelated Neo4j data is outside the operation's scope.

## 5. Public services and types

- `GraphSnapshot` — serializable authoritative graph input.
- `load_graph_snapshot(engine)` — PostgreSQL snapshot reader with connection retries.
- `GraphProjector.rebuild(snapshot, reset_managed=True)` — managed projection rebuild.
- `GraphRepository` — the only owner of Cypher mappings.
- `process_batch(session_factory, project)` — outbox claim, retry, and checkpoint flow.
- `scripts/rebuild_graph.py` — explicit snapshot rebuild.
- `scripts/project_outbox.py` — one projection/checkpoint batch.

## 6. Notebook and execution command

Notebook: `notebooks/01_graph_projection/01_graph_projection.ipynb`

```powershell
python -m poetry install --extras "dev notebooks"
python -m poetry run jupyter nbconvert --execute --inplace --ExecutePreprocessor.timeout=300 notebooks/01_graph_projection/01_graph_projection.ipynb
```

The notebook reads credentials only from the gitignored `.env` and fails the
command if any cell fails.

## 7. Results, metrics and plots

The live projection reconciled all authoritative node categories with zero
difference. Selected counts are 1,010 customers, 967 devices, 1,005 wallets,
2,010 transactions, 20 merchants, 25 retailers, 1,200 sales and 1,200 inventory
events. PostgreSQL reports 19,811 processed outbox rows and no pending rows.

The graph contains 22 shared-device patterns. Transaction context includes
2,010 source-wallet and device relationships, 1,988 merchant relationships and
22 destination-wallet transfers.

Retained evidence:

- `outputs/metrics.json`
- `outputs/tables/reconciliation.json`
- `outputs/tables/customer_degrees.json`
- `outputs/tables/shared_devices.json`
- `outputs/plots/projection_graph_summary.png`
- `outputs/plots/source_projection_reconciliation.png`

## 8. How to run and verify it

```powershell
python -m poetry run python scripts/rebuild_graph.py
python -m poetry run python scripts/project_outbox.py --batch-size 25000
python -m poetry run pytest tests/unit/test_graph_projection.py -q
```

In Neo4j Query, inspect only the managed projection:

```cypher
MATCH (n {projection: 'poc-v1'})
RETURN labels(n)[0] AS kind, count(*) AS total
ORDER BY kind;
```

```cypher
MATCH (d:Device {projection: 'poc-v1'})<-[:USES]-(c:Customer)
WITH d, count(c) AS customers
WHERE customers > 1
RETURN d.device_ref, customers
ORDER BY customers DESC;
```

## 9. What is implemented

- Idempotent projection for core, telco, money, transaction and SFA context.
- Projection-owned reset that preserves unrelated graph data.
- Neo4j constraints, parameterized Cypher, and managed transaction retries.
- Single-worker outbox claiming, attempts, errors, success checkpointing and terminal failure.
- Source/projection reconciliation, degree and shared-device analysis.
- Executed notebook, compact tables, metrics and plots.
- Live Supabase-to-Neo4j rebuild and outbox verification.

## 10. What is not implemented

- Distributed worker coordination, scheduling, dead-letter queues or replay UI.
- Change-level Cypher per event; the POC worker rebuilds the authoritative snapshot.
- Continuous projection-lag monitoring, alerting or operational dashboards.
- Multi-tenant graph isolation or production access controls.
- Temporal/graph feature computation, graph fraud scores or recommendations.

## 11. POC limitations

- One controlled worker is assumed.
- A full snapshot rebuild is intentionally simpler but less efficient than incremental projection.
- Retry policy is fixed and has no exponential backoff or dead-letter operator workflow.
- Synthetic relationships demonstrate graph feasibility, not real fraud or social-network truth.
- This does not demonstrate production scalability, availability, security certification or 24/7 operations.

## 12. Production improvements required later

Production would require event-specific idempotent mappings, durable worker
hosting, leases/heartbeats, exponential backoff, dead-letter replay, lag SLOs,
metrics and alerts, capacity tests, schema/version compatibility, access
controls, audit trails and disaster-recovery procedures.

## 13. Dependency for the next capability

Capability 02 can now calculate versioned temporal features from PostgreSQL and
graph-context features from the reconciled Neo4j projection at an explicit
`as_of`, with future-leakage tests.
