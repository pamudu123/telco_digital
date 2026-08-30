# Capability 02 — Temporal and Graph Feature Layer

## 1. POC objective

Prove that reusable customer features can be reconstructed at an explicit point in time from authoritative PostgreSQL facts and a rebuildable Neo4j projection.

## 2. Demonstrated scenario

For a golden customer, the showcase returns bounded usage, recharge, wallet, plan, travel, service, loyalty and campaign evidence together with graph context. Moving `as_of` backward excludes later evidence.

## 3. Data inputs and outputs

Inputs are the capability-00 facts and capability-01 managed graph. The output is a typed `customer-features-v1` document containing temporal groups, graph values, provenance, explicit unknowns, `as_of` and `computed_at`. PostgreSQL remains authoritative.

## 4. Architecture and data flow

`PostgreSQL facts -> PostgresTemporalFeatureQueries -> TemporalFeatureService`

`Neo4j projection -> Neo4jFeatureQueries -> GraphFeatureService`

`CustomerFeatureService -> read-only API or explicit materialization command`

SQL and Cypher stay in their infrastructure adapters. Normal GET requests do not persist data.

## 5. Public services and types

- `TemporalFeatureService.calculate(customer_ref, as_of)`
- `GraphFeatureService.calculate(customer_ref, as_of)`
- `CustomerFeatureService.calculate(customer_ref, as_of)`
- `CustomerFeatures`, `FeatureGroup` and `GraphFeatures`
- `snapshot_id(customer_id, as_of, feature_version)`

All services reject timezone-naive `as_of` values.

## 6. Notebook and execution command

The retained notebook is `notebooks/02_features/02_features.ipynb`.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/02_features/02_features.ipynb
```

## 7. Results, metrics and plots

The notebook retains compact metrics, leakage checks, feature profiles, distributions, missingness, correlations, temporal comparisons and graph distributions under `notebooks/02_features/outputs/`. These are POC evidence over synthetic fixtures, not estimates of a real population.

## 8. How to run and verify it

```bash
poetry run python scripts/materialize_features.py
poetry run pytest tests/unit/test_features.py -q
poetry run pytest
poetry run ruff check .
```

Read live results at `/api/v1/customers/U001/features?as_of=2026-08-31T23:59:00Z`, `/api/v1/showcase/graph/summary?as_of=...`, and `/api/v1/showcase/graph/customers/U001?as_of=...`.

## 9. What is implemented

- Versioned 30/90-day temporal features and previous-window change.
- Recharge, wallet, plan, travel, service, loyalty and campaign groups.
- Temporally bounded graph degree, shared-device, counterparty, merchant and transaction context.
- Explicit graph-unavailable behavior, provenance and unknowns.
- Idempotent, deterministic feature snapshot materialization.
- Read-only API and amber/purple Customer 360 and Graph Explorer UI treatments.

## 10. What is not implemented

Event memory, clustering, churn/fraud prediction, recommendations, training, automated refresh, online feature serving and production feature-store infrastructure are not implemented.

## 11. POC limitations

The definitions and thresholds are demonstrative. The data are synthetic; the POC does not establish real-world accuracy, production scalability, high availability, multi-tenant isolation, certified security, full observability, orchestration, monitoring or drift response.

## 12. Production improvements that would be required later

Approve feature definitions with domain owners, introduce governed feature lineage and registry controls, incremental computation, workload isolation, service objectives, access controls, monitoring, backfills and independent reconciliation alerts.

## 13. Dependency for the next capability

Capability 03 may consume these versioned snapshots for travel episode matching. It remains not started and no event-memory behavior is included here.
