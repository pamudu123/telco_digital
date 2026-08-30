# Intelligence, decisioning, and copilot (locked)

## Point-in-time state

`CustomerStateService(customer_id, as_of) → ObservedCustomerState`

Example:

```
Customer: U0001
As of: 2026-08-26 10:00
Country              Singapore
Current plan         PLAN_A
Balance              LKR 850
Loyalty points       3,200
Device               D001
Active complaints    1
```

Everything respects `occurred_at <= as_of`.

## Temporal features

Windows for usage, recharge, behaviour change, campaigns, loyalty, service, travel. Persist `intelligence.feature_snapshot` during development for reproducibility (“why did model v1 predict churn 0.74?”).

## Event memory

Transform events into episodes. POC starts with **travel only**. Later: `DATA_EXHAUSTION`, `NETWORK_PROBLEM`, `CHURN_WARNING`, `LOYALTY_REDEMPTION`, `CAMPAIGN_RESPONSE`, `PACKAGE_UPGRADE`.

```
TRAVEL EPISODE
Destination       Singapore
Start             10 Mar
End               16 Mar
Duration          6 days
Plan selected     ROAM_15
Usage             11.4 GB
Outcome           No additional package required
```

Episode shape: `type`, `start_at`, `end_at`, `context`, `actions`, `outcome`, `metrics`.  
Do not persist episodes at first; generate from events.

## Similar event retrieval

Priority:

1. Same customer's same situation  
2. Same customer's similar situation  
3. Similar customers in similar situation  
4. Population behaviour  

Personal history is strongest.

## Graph features (fraud)

`shared_device_customer_count`, `shared_wallet_count`, `merchant_degree`, `merchant_customer_count`, `suspicious_neighbor_count`, `distance_to_known_fraud`, `connected_component_size`, `transaction_cluster_density`.

Example: Postgres transaction risk 0.32 + graph risk 0.91 → **HIGH RISK**.

## Behaviour

Start with rules + clustering. Traits such as Heavy Data User, Frequent Traveller, Promotion Responsive, Price Sensitive, High Value, Declining Engagement, Streaming Heavy.

Every trait carries confidence and evidence:

```json
{
  "trait": "PRICE_SENSITIVE",
  "confidence": 0.81,
  "evidence": {
    "small_recharge_frequency": "high",
    "discount_campaign_response": "high"
  }
}
```

## Churn

Inputs: usage/recharge/spend trends, network issues, complaints, campaign and loyalty engagement, tenure, plan changes.  
Compare logistic regression vs gradient boosted trees. Do not choose the most complex model automatically.

Store: probability, risk band, drivers, model version, feature snapshot, prediction timestamp, `as_of`.

## Recommendations

Do not build `model → plan`.

```
Customer Context
  ├── Current State
  ├── Recent Behaviour
  ├── Long-term Behaviour
  ├── Event Memory
  ├── Similar Customers
  ├── Graph Context
  └── Predictions
         ↓
   Candidate Generator   (real catalogue only)
         ↓
   Candidate Scorer
         ↓
   Business Constraints
         ↓
   Uncertainty Assessment
         ↓
   Recommendation
```

Decision modes: `SINGLE_RECOMMENDATION`, `RANKED_OPTIONS`, `SCENARIO_BASED`, `ASK_FOR_INFORMATION`, `NO_RECOMMENDATION`.

Uncertainty tracks known / inferred / predicted / unknown (e.g. destination known, trip duration unknown).

Travel example: previous Singapore trip 6 days / 11.4 GB / ROAM_15 → recommend ROAM_15; alternatives ROAM_5 (1–3 days) and ROAM_30 (8–14 days).

Record outcomes: what AI suggested, what the user chose, what happened.

## Digital Twin (computed)

```
DIGITAL TWIN
Observed      Facts directly supported by data
Recent        What has changed recently
Historical    Long-term behaviour and episodes
Relationships Graph context
Inferred      Behavioural traits
Predicted     Churn / fraud / demand / propensity
Unknown       Important missing information
Recommended   Current actions
```

`DigitalTwinService.build(entity_id, as_of)` combines state, features, event memory, graph, prediction, and recommendation services. Retailer twins are first-class, not customer-only.

`CustomerContext` is the object consumed by recommendation and decisioning.

## Decision Engine

`churn = 0.78` does not automatically mean `20% discount`. The engine evaluates churn risk, customer value, cause, network state, price sensitivity, available rewards, recommendation scores, uncertainty, and business rules → Next Best Action + reason codes.

## Explanation

Every prediction/decision exposes: What, Why, Evidence, Confidence, Unknowns, Alternatives.

## Copilot

Queries structured intelligence and generates natural language. Example: “Why is U0001 receiving this recommendation?” is answered from episodes, usage, unknowns, and ranked candidates — not from the model inventing facts.

## Warnings (deterministic, separate from ML)

`IMPOSSIBLE_TRAVEL`, `DUPLICATE_DEVICE`, `UNUSUAL_RECHARGE`, `OVERLAPPING_TRAVEL`, `ABNORMAL_TRANSACTION_VELOCITY`, `STOCKOUT_RISK`, `FREQUENT_SMALL_RECHARGE_PATTERN`.

Singapore 09:00 then USA 10:00: record both events; emit `IMPOSSIBLE_TRAVEL`.
