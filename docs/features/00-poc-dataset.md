# Capability 00 — Expanded POC dataset

## 1. POC objective

Prove that the locked PostgreSQL model can hold reproducible, temporally ordered
signals from telco, marketing, loyalty, mobile money, service, and SFA domains.
The dataset is designed to support later intelligence demonstrations without
claiming that synthetic behavior represents a real population.

## 2. Demonstrated scenario

The loader preserves U001–U005, adds golden personas U006–U010, and adds 1,000
background customers across seven repeatable personas. Each material generated
fact receives a matching immutable activity event and pending outbox event in the
same database transaction.

## 3. Data inputs and outputs

Inputs are fixed seed `20260831`, dataset version `poc-v1`, and the interval
2025-09-01 through 2026-08-31. Outputs use the existing `core`, `telco`,
`marketing`, `money`, `sfa`, `activity`, and `integration` schemas.

Reference outputs include 8 plans, 20 merchants, 10 campaigns, 5 distributors,
25 retailers, 10 sales agents, and 12 SFA products. The default generated output
contains 1,005 new customers and correlated subscriptions, recharges, ledger
entries, usage, travel, service, loyalty, campaign, money, sales, and inventory
facts.

## 4. Architecture and data flow

```text
Deterministic builder
        ↓
DatasetBundle (rows + metrics)
        ↓
One SQLAlchemy transaction
        ↓
Facts + activity events + outbox events
        ↓
Validation report
        ↓
Executed analysis notebook + plots
```

Deterministic UUIDv5 identifiers and PostgreSQL `ON CONFLICT DO NOTHING` make
loading repeatable. Reset uses the same generated identifiers and deletes only
rows owned by `poc-v1`.

## 5. Public services and types

- `build_dataset(background_customers=1000) -> DatasetBundle`
- `load_dataset(engine, bundle)`
- `validate_dataset(engine, expected_counts)`
- `reset_dataset(engine, bundle)`
- `scripts/generate_poc_dataset.py {load|validate|reset}`

## 6. Notebook and execution command

Notebook: `notebooks/00_dataset/00_dataset.ipynb`

```powershell
python -m poetry install --extras "dev notebooks"
python -m poetry run jupyter nbconvert --execute --inplace notebooks/00_dataset/00_dataset.ipynb
```

The notebook is read-only and consumes `outputs/metrics.json` created by the
loader/validator.

## 7. Results, metrics and plots

The live Supabase load committed 68,410 deterministic generated rows. Validation
confirmed 1,005 new customers, 1,010 customers including U001–U005, and exact
parity between 19,772 generated activity events and 19,772 generated outbox
events. A second load produced the same counts, proving idempotent reruns.

Selected generated counts are 6,030 usage events, 4,020 recharges, 4,020 balance
ledger entries, 2,010 loyalty entries, 2,010 money transactions, 1,200 sales,
1,200 inventory events, 144 travel episodes, and 143 service interactions.

The validation report also records persona counts and monthly usage, recharge,
mobile-money, and SFA series. The executed notebook produces:

- `outputs/plots/table_row_counts.png`
- `outputs/plots/persona_distribution.png`
- `outputs/plots/monthly_activity_trends.png`

Final live validation results are recorded in `outputs/metrics.json`; the
notebook executed successfully with all plots embedded and saved.

## 8. How to run and verify it

```powershell
python -m poetry run alembic upgrade head
python -m poetry run python scripts/generate_poc_dataset.py load
python -m poetry run python scripts/generate_poc_dataset.py validate
python -m poetry run pytest tests/unit/test_demo_dataset.py -q
```

Reset is explicit and affects only deterministic `poc-v1` rows:

```powershell
python -m poetry run python scripts/generate_poc_dataset.py reset
```

## 9. What is implemented

- Deterministic golden and background population generation.
- Existing-schema reference catalogues and cross-domain facts.
- Correlated persona behavior and temporally ordered timestamps.
- Fact/activity/outbox parity for material generated operations.
- Idempotent loading, dataset-owned reset, validation report, notebook, and plots.
- Query indexes for temporal, outbox, money, and SFA workloads.

## 10. What is not implemented

- Automatic Neo4j projection of the new outbox records; that belongs to capability 01.
- Temporal/graph features, event memory, behavior models, churn, recommendations,
  fraud scoring, forecasting, twins, decisioning, Copilot, API, and UI.
- A general production data-ingestion or orchestration platform.

## 11. POC limitations

- Synthetic distributions are deliberately scenario-shaped.
- Background activity is smaller and cleaner than real telecom event volumes.
- Reference catalogues are representative, not commercial product master data.
- Loading uses a single controlled process rather than distributed ingestion.
- The dataset does not demonstrate production scale, accuracy, security, or availability.

## 12. Production improvements required later

Real deployment would require governed source mappings, data contracts, privacy
controls, consent and retention policies, schema evolution, streaming/batch
orchestration, quality monitoring, lineage, reconciliation, partitioning, and
realistic capacity testing.

## 13. Dependency for the next capability

Capability 01 consumes the generated activity/outbox data to complete reliable
PostgreSQL-to-Neo4j projection, replay, reconciliation, and graph analysis.
