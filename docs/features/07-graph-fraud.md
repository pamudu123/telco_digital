# Capability 07 — Graph fraud

## 1. POC objective

Prove that a customer can be scored at an explicit `as_of` from outgoing
PostgreSQL money activity **and** rebuildable Neo4j relationship evidence, and
that the two scores can diverge. Deterministic rules fire first. Graph ML is
not served.

## 2. Demonstrated scenario

U009 is a seeded wallet-funnel hub. Transaction-only risk stays moderate
because the account only initiates a small number of transfers. Graph risk is
**HIGH** because incoming counterparties, seeded-fraud membership and cluster
density are visible on the projection. U003 stays **LOW** on both scores. U005
shares device D001 with U001; that overlap is evidence, not a write-path block.

Capability 06 (recommendations) remains not started and is not required to
score fraud.

## 3. Data inputs and outputs

Inputs are outgoing `money.transaction` rows with `occurred_at <= as_of` and
time-bounded Neo4j `USES` / `INITIATED` / `TO_WALLET` / `AT_MERCHANT`
relationships. Known-fraud membership is the documented seed set `{U005, U009}`,
not an authoritative table. The output is a typed `customer-fraud-v1` document
containing transaction risk, graph risk, combined risk, risk band, fired rules,
drivers and a feature snapshot. Scores are derived and not persisted.

## 4. Architecture and data flow

`PostgresTransactionRiskQueries -> transaction-only risk`

`Neo4jGraphFraudQueries -> graph fraud features`

`FraudRuleService + FraudScorer -> FraudService.evaluate`

SQL stays in `infrastructure/postgres`. Cypher stays in `infrastructure/neo4j`.
Rules and scoring stay in `intelligence/fraud`.

## 5. Public services and types

- `FraudService.evaluate(customer_ref, as_of)`
- `score_fraud`, `score_transaction_risk`, `score_graph_risk`, `evaluate_rules`
- `CustomerFraud`, `FraudRule`, `TransactionRiskFeatures`, `GraphFraudFeatures`

Rules: `SHARED_DEVICE`, `KNOWN_FRAUD_WITHIN_2_HOPS`, `WALLET_FUNNEL`,
`CIRCULAR_TRANSFERS`, `ABNORMAL_CREATION`, `ABNORMAL_TRANSACTION_VELOCITY`.
Known-fraud distance uses wallet/transfer hops only. Device sharing is a
separate rule so U001 is not treated as a two-hop fraud neighbor.

All services reject timezone-naive `as_of` values. Missing Neo4j evidence is an
unknown; graph risk is not assumed to be zero.

## 6. Notebook and execution command

The retained notebook is `notebooks/07_graph_fraud/07_graph_fraud.ipynb`.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/07_graph_fraud/07_graph_fraud.ipynb
```

The notebook is the analysis surface. It scores synthetic golden fixtures with
the runtime scorer, writes compact tables and plots, and does not export a
trained model. Runtime services stay in `src/telco_digital`.

## 7. Results, metrics and plots

Retained evidence lives under `notebooks/07_graph_fraud/outputs/`:

- `metrics.json`
- `tables/golden_scores.json`
- `tables/u009_rules.json`
- `tables/transaction_vs_graph.json`
- `plots/transaction_vs_graph.png`
- `plots/rule_firings.png`

These are POC evidence over synthetic fixtures, not estimates of a real fraud
population.

## 8. How to run and verify it

```bash
poetry run pytest tests/unit/test_fraud.py tests/scenarios/scenario_graph_fraud.py -q
poetry run pytest tests/unit tests/scenarios -q
poetry run ruff check .
```

Read live results at
`/api/v1/customers/U009/fraud?as_of=2026-08-21T00:00:00Z`.

## 9. What is implemented

- Point-in-time transaction-only and graph fraud features.
- Deterministic rules and a combined scorer that keeps both scores visible.
- Read-only fraud API and Customer 360 / Money risk panel.
- Notebook comparison of transaction-only versus graph risk.

## 10. What is not implemented

Graph ML embeddings, a persisted prediction store, review-queue actions,
write-path blocking, recommendations, twins and Copilot are not implemented.

## 11. POC limitations

The watchlist is a documented seed list. The wallet funnel is synthetic.
Hold-out metrics are not claimed. Capability 06 is intentionally still not
started.

## 12. Production improvements that would be required later

Approve an outcome definition with risk owners, replace the seed watchlist
with a governed case table, evaluate rules against labelled history, add
graph embeddings only after the rule baseline is monitored, and only then
persist prediction records.

## 13. Dependency for the next sequential capability

Capability 06 remains not started and may later consume this score as one
input to candidate ranking. Capability 08 (SFA forecasting) does not depend
on this scorer.
