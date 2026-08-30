# Data model (locked)

PostgreSQL is the system of record. Do not dump everything into `public`.

Logical schemas:

| Schema | Purpose |
|---|---|
| `core` | Relatively stable entities |
| `telco` | Usage, recharge, travel, service, balance ledger |
| `marketing` | Loyalty, campaigns |
| `money` | Wallets, merchants, transactions |
| `sfa` | Distributors, retailers, agents, products, sales, inventory |
| `activity` | Universal immutable event history |
| `intelligence` | Derived snapshots, predictions, recommendations (not facts) |
| `integration` | Outbox for Neo4j (and later other) projections |

Later on Supabase, keep internal schemas outside the exposed API surface. Use dedicated API schemas and explicit grants for anything exposed.

All primary keys are UUID unless noted. Timestamps are `TIMESTAMPTZ`.

---

## `core` schema

### `core.customer`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| customer_ref | VARCHAR UNIQUE | e.g. `U0001` / `U001` |
| home_country | VARCHAR | e.g. `LK` or display name used by seed |
| account_type | VARCHAR | `PREPAID` / `POSTPAID` |
| status | VARCHAR | `ACTIVE` / … |
| customer_since | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

Example: `U0001`, Sri Lanka, `PREPAID`, `ACTIVE`.

### `core.account`

| Column | Type |
|---|---|
| id | UUID PK |
| customer_id | FK → customer |
| account_ref | VARCHAR |
| account_type | VARCHAR |
| currency | VARCHAR |
| status | VARCHAR |
| created_at | TIMESTAMPTZ |

Do not rely solely on a mutable balance column. Use `telco.balance_ledger`.

### `core.sim`

| Column | Type |
|---|---|
| id | UUID PK |
| sim_ref | VARCHAR |
| customer_id | FK |
| msisdn | VARCHAR |
| activated_at | TIMESTAMPTZ |
| deactivated_at | TIMESTAMPTZ nullable |
| status | VARCHAR |

### `core.device`

| Column | Type |
|---|---|
| id | UUID PK |
| device_ref | VARCHAR |
| device_type | VARCHAR |
| model | VARCHAR |
| fingerprint | VARCHAR |
| first_seen_at | TIMESTAMPTZ |

### `core.customer_device`

Important for graph intelligence. Device use can change over time.

| Column | Type |
|---|---|
| id | UUID PK |
| customer_id | FK |
| device_id | FK |
| valid_from | TIMESTAMPTZ |
| valid_to | TIMESTAMPTZ nullable |

Graph view: `U0001 -USES→ D001` is a time-bounded fact.

### `core.plan`

| Column | Type |
|---|---|
| id | UUID PK |
| plan_code | VARCHAR UNIQUE |
| name | VARCHAR |
| plan_type | VARCHAR | `LOCAL` / `ROAMING` / `ADD_ON` |
| data_mb | INTEGER |
| validity_days | INTEGER |
| price | NUMERIC |
| currency | VARCHAR |
| country_code | VARCHAR nullable |
| country_group | VARCHAR nullable |
| active | BOOLEAN |
| created_at | TIMESTAMPTZ |

### `core.subscription`

| Column | Type |
|---|---|
| id | UUID PK |
| customer_id | FK |
| plan_id | FK |
| started_at | TIMESTAMPTZ |
| ended_at | TIMESTAMPTZ nullable |
| status | VARCHAR |
| source_event_id | UUID nullable |

Enables: *What package did User 1 have on March 10?*

---

## Ledgers (`telco.balance_ledger`)

| Column | Type |
|---|---|
| id | UUID PK |
| account_id | FK |
| customer_id | FK |
| entry_type | VARCHAR | `RECHARGE`, `PLAN_BUY`, … |
| amount | NUMERIC | signed |
| currency | VARCHAR |
| occurred_at | TIMESTAMPTZ |
| source_event_id | UUID nullable |

Example: `RECHARGE +500`, `PLAN_BUY -300`, `RECHARGE +100`.

```
balance at time T = SUM(entries WHERE occurred_at <= T)
```

---

## `telco.usage_event`

| Column | Type |
|---|---|
| id | UUID PK |
| customer_id | FK |
| occurred_at | TIMESTAMPTZ |
| usage_type | VARCHAR | e.g. `STREAMING` |
| data_mb | NUMERIC |
| country_code | VARCHAR |
| network_type | VARCHAR nullable |
| source_event_id | UUID nullable |

Feeds: usage 1d / 7d / 30d, daily average, usage change, streaming affinity.

---

## `telco.recharge`

| Column | Type |
|---|---|
| id | UUID PK |
| customer_id | FK |
| account_id | FK |
| amount | NUMERIC |
| currency | VARCHAR |
| occurred_at | TIMESTAMPTZ |
| channel | VARCHAR nullable |
| source_event_id | UUID nullable |

Repeated small amounts (100, 100, 100, …) support frequent-small-recharge behaviour.

---

## `telco.travel`

| Column | Type |
|---|---|
| id | UUID PK |
| customer_id | FK |
| country_code | VARCHAR |
| started_at | TIMESTAMPTZ |
| ended_at | TIMESTAMPTZ nullable |
| source | VARCHAR nullable |
| start_event_id | UUID nullable |
| end_event_id | UUID nullable |

`ended_at = NULL` means trip duration is **UNKNOWN** — required for uncertainty-aware recommendations.

---

## `telco.service_interaction`

| Column | Type |
|---|---|
| id | UUID PK |
| customer_id | FK |
| interaction_type | VARCHAR | `COMPLAINT`, `NETWORK_ISSUE`, `BILLING_ISSUE`, `PACKAGE_ISSUE` |
| occurred_at | TIMESTAMPTZ |
| category | VARCHAR nullable |
| severity | VARCHAR nullable |
| status | VARCHAR |
| resolved_at | TIMESTAMPTZ nullable |
| source_event_id | UUID nullable |

---

## Marketing

### `marketing.loyalty_account`

id, customer_id, joined_at, status

### `marketing.loyalty_ledger`

id, loyalty_account_id, customer_id, entry_type (`EARN` / `REDEEM`), points, reward_id nullable, occurred_at, source_event_id

Historical loyalty balance = SUM(earned) − SUM(redeemed).

### `marketing.campaign`

id, campaign_code, name, category, target_plan_id, starts_at, ends_at, status

### `marketing.campaign_interaction`

id, campaign_id, customer_id, interaction_type (`RECEIVED`, `OPENED`, `CLICKED`, `CONVERTED`, `IGNORED`), occurred_at, source_event_id

---

## Mobile money

### `money.wallet`

id, wallet_ref, customer_id, status, created_at

### `money.merchant`

id, merchant_ref, name, category, country_code, status

### `money.transaction`

id, transaction_ref, source_wallet_id, destination_wallet_id nullable, merchant_id nullable, customer_id, device_id, amount, currency, transaction_type, country_code, occurred_at, status, source_event_id

Later powers graph fraud detection.

---

## SFA

- `sfa.distributor` — distributor_ref, name, region
- `sfa.retailer` — retailer_ref, distributor_id, name, region, latitude, longitude, status
- `sfa.sales_agent` — agent_ref, distributor_id, name, status
- `sfa.product` — product_code, name, category (POC: can reference plans/SIM products)
- `sfa.sale` — retailer_id, product_id, quantity, amount, occurred_at, sales_agent_id, source_event_id
- `sfa.inventory_event` — retailer_id, product_id, event_type (`STOCK_IN`, `SALE`, `ADJUSTMENT`), quantity, occurred_at, source_event_id

Inventory at time T is reconstructed from events.

---

## Universal event history — `activity.event`

This is **not** full event sourcing. Structured relational tables remain the primary business model.

| Column | Type |
|---|---|
| id | UUID PK |
| entity_type | VARCHAR |
| entity_id | UUID |
| customer_id | UUID nullable |
| event_type | VARCHAR |
| occurred_at | TIMESTAMPTZ |
| recorded_at | TIMESTAMPTZ |
| source | VARCHAR |
| correlation_id | VARCHAR nullable |
| idempotency_key | VARCHAR UNIQUE nullable |
| payload | JSONB |

Provides: timeline, auditability, temporal history, episodic memory, projection triggers, simulation playback.

Events are immutable. Corrections are new events.

---

## Outbox — `integration.outbox_event`

| Column | Type |
|---|---|
| id | UUID PK |
| event_id | UUID |
| event_type | VARCHAR |
| aggregate_type | VARCHAR |
| aggregate_id | UUID |
| payload | JSONB |
| created_at | TIMESTAMPTZ |
| processed_at | TIMESTAMPTZ nullable |
| attempt_count | INTEGER |
| last_error | TEXT nullable |
| status | VARCHAR | `PENDING` / `PROCESSING` / `PROCESSED` / `FAILED` |

POC worker: read pending → lock batch → project to Neo4j → mark `PROCESSED`. Later: `FOR UPDATE SKIP LOCKED` for concurrent workers. One worker is enough for the POC.

---

## Intelligence tables (derived)

### `intelligence.feature_snapshot`

id, entity_type, entity_id, as_of, feature_set_version, features JSONB, created_at

### `intelligence.model_prediction`

id, entity_type, entity_id, model_name, model_version, as_of, score, label, feature_snapshot_id, explanation JSONB, created_at

Every ML result includes `model_name`, `model_version`, feature version, `as_of`, `created_at`. Never store `churn = 0.72` without knowing which model produced it.

### `intelligence.recommendation`

id, customer_id, as_of, decision_mode, recommended_action, recommended_item_id, score, confidence, evidence JSONB, unknowns JSONB, created_at

### `intelligence.recommendation_outcome`

recommendation_id, selected_option, accepted, occurred_at, outcome JSONB

### `intelligence.twin_snapshot` (later, optional cache)

Derived snapshots for audit / performance / demo playback. Source remains PostgreSQL + Neo4j.

### `intelligence.warning`

Deterministic warnings are separate from ML: `IMPOSSIBLE_TRAVEL`, `DUPLICATE_DEVICE`, `UNUSUAL_RECHARGE`, `OVERLAPPING_TRAVEL`, `ABNORMAL_TRANSACTION_VELOCITY`, `STOCKOUT_RISK`, `FREQUENT_SMALL_RECHARGE_PATTERN`.

Suspicious events remain stored; they are marked, not rejected.

---

## Neo4j projection (not source of truth)

### Nodes

Customer, Account, SIM, Device, Plan, Wallet, Merchant, Campaign, Reward, Retailer, Distributor, SalesAgent, Location

### Relationships (start set)

```
(:Customer)-[:OWNS]->(:SIM)
(:Customer)-[:USES]->(:Device)
(:Customer)-[:HAS_ACCOUNT]->(:Account)
(:Customer)-[:SUBSCRIBES_TO]->(:Plan)
(:Customer)-[:OWNS]->(:Wallet)
(:Wallet)-[:PAID]->(:Merchant)
(:Wallet)-[:TRANSFERRED_TO]->(:Wallet)
(:Customer)-[:INTERACTED_WITH]->(:Campaign)
(:Customer)-[:REDEEMED]->(:Reward)
(:Retailer)-[:SUPPLIED_BY]->(:Distributor)
(:SalesAgent)-[:VISITED]->(:Retailer)
(:Retailer)-[:SOLD]->(:Plan)
```

Projection uses `MERGE` and parameterized Cypher only.
