# Company Intelligence POC — Locked Architecture

**Status:** LOCKED — this is the initial plan and the source of truth for implementation.  
**Date locked:** 2026-08-27  
**POC package:** `telco-digital` (`telco_digital`)

This document locks the architecture. Code follows this design. Do not invert the stack (for example: putting predictions in Neo4j as facts, putting Cypher in domain services, or treating a Digital Twin as an authoritative table).

---

## Core idea

PostgreSQL is the system of record.  
Neo4j is the relationship intelligence projection.  
Events preserve history.  
Temporal features describe behaviour.  
Digital Twins combine facts, inference and predictions.  
ML predicts.  
The Decision Engine determines what to do.

This supports company **shared intelligence**: multiple applications contribute signals to reusable intelligence rather than maintaining isolated AI inside each application. See [SHARED-INTELLIGENCE.md](./SHARED-INTELLIGENCE.md).

---

## 1. Target architecture

```
                     FUTURE UI
                        │
                        ▼
                APPLICATION LAYER
                        │
          Commands │ Queries │ Decisions
                        │
                        ▼
                   DOMAIN LAYER
                        │
                   Business Rules
                        │
                        ▼
              ┌─────────────────────┐
              │     POSTGRESQL      │
              │   SOURCE OF TRUTH   │
              └──────────┬──────────┘
                         │
           ┌─────────────┼──────────────┐
           │             │              │
           ▼             ▼              ▼
     Domain Data      Event Log       Outbox
           │             │              │
           │             │              ▼
           │             │       GRAPH PROJECTOR
           │             │              │
           │             │              ▼
           │             │           NEO4J
           │             │              │
           └─────────────┼──────────────┘
                         ▼
                INTELLIGENCE LAYER
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
 Temporal Features   Graph Features   Event Memory
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
                  CUSTOMER CONTEXT
                         │
                         ▼
                   DIGITAL TWIN
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      Behaviour        Churn        Recommendation
                                           │
                  Fraud ◄────── Graph ─────┤
                                           │
                     SFA Forecasting ◄──────┘
                         │
                         ▼
                  DECISION ENGINE
                         │
                  ┌──────┴──────┐
                  ▼             ▼
              Warnings      Actions/NBA
                         │
                         ▼
                    EXPLANATION
                         │
                         ▼
                    AI COPILOT
```

---

## 2. Technology choices (backend POC)

| Component | Choice |
|---|---|
| Language | Python |
| API later | FastAPI |
| ORM / SQL | SQLAlchemy 2.x |
| PostgreSQL driver | asyncpg |
| Migrations | Alembic |
| Validation | Pydantic |
| Relational DB | PostgreSQL |
| Future relational deployment | Supabase |
| Graph DB | Neo4j |
| Graph driver | Neo4j Python Driver |
| ML | scikit-learn + XGBoost/LightGBM where needed |
| Data processing | Polars or pandas |
| Tests | pytest |
| Lint/format | Ruff |
| Containers | Docker Compose |

SQLAlchemy 2.x: use `AsyncSession` and `async_sessionmaker`. Pass sessions explicitly. Do not rely on global scoped session state.

---

## 3. Hard placement rules

- Do **not** put ML logic inside route files.
- Do **not** put Cypher inside business services.
- Do **not** put SQL queries randomly around the application.
- Do **not** hide transactional outbox writes inside ORM event hooks. Use explicit application services.
- Do **not** place predictions into the graph as facts.
- Do **not** mix raw facts, derived features, inferences, predictions, decisions, and explanations into one table.
- The API contains almost no business logic. Routes are adapters.
- The Copilot is a presentation layer over structured intelligence. It does not create facts or predictions.

---

## 4. Separation of concerns

| Kind | Example | Where it lives |
|---|---|---|
| Fact | U001 used 1.8 GB | PostgreSQL domain tables + `activity.event` |
| Derived feature | 7-day usage increased 31% | Intelligence feature engine (`as_of` bounded) |
| Inference | Heavy Data User | Behaviour intelligence |
| Prediction | Upgrade probability 82% | ML models + `intelligence.model_prediction` |
| Decision | Recommend ROAM_15 | Decision Engine |
| Explanation | Because recent usage and previous travel support it | Explanation layer |

Neo4j stores **relationships that happened**, not **scores that might change**.

Avoid:

```
(:Customer)-[:IS_CHURNING]->(...)
```

Churn, fraud risk, and price sensitivity are predictions. Keep them in the intelligence layer.

---

## 5. Transactional write path

Whenever the application performs an important operation, **one PostgreSQL transaction** must include:

1. Domain write
2. Activity event
3. Outbox event

Example: user purchases a plan.

```
BEGIN
  Insert subscription
  Insert balance ledger entry
  Insert activity event
  Insert outbox event
COMMIT
```

If any operation fails: **ROLLBACK EVERYTHING**.

This prevents:

- Plan exists in Postgres but Neo4j never learns about it
- Or the reverse

Events are **immutable**. Do not overwrite `TRAVEL_STARTED`. If it was wrong, write `TRAVEL_CORRECTED`.

Every event has:

- `occurred_at` — when the real activity happened
- `recorded_at` — when this system received it

---

## 6. Temporal integrity rule

This rule exists everywhere in the intelligence layer:

> **No intelligence calculation can use information after `as_of`.**

Applies to: features, churn, recommendations, fraud, digital twin, event memory.

Otherwise you introduce future leakage.

Ledger balances, subscriptions, device usage, travel, and loyalty are reconstructed as:

```
value at time T = fold(facts where occurred_at <= T)
```

Do not rely solely on a mutable balance column if historical reconstruction is required.

---

## 7. Graph projection

Neo4j must not receive arbitrary direct writes from the UI.

```
POSTGRESQL → Outbox → Graph Projector Worker → NEO4J
```

The graph is reproducible. If Neo4j is corrupted:

```
Clear Neo4j → Replay Postgres data/events → Rebuild graph
```

Projection must be **idempotent** (`MERGE`). Processing the same event twice must not create duplicate nodes.

Use parameterized Cypher only. One infrastructure service (`GraphRepository`) owns Cypher.

---

## 8. Intelligence stack (order of construction)

1. **Point-in-time state** (`CustomerStateService`) — observed facts at `as_of`
2. **Temporal features** — windows that respect `occurred_at <= as_of`
3. **Event memory** — episodes derived from events (travel first)
4. **Similar event retrieval** — personal history first, then similar customers, then population
5. **Graph features** — for fraud and relationship context
6. **Behaviour** — rules + clustering, with evidence
7. **Churn** — supervised model, auditable predictions
8. **Recommendations** — candidate generation from real catalogue, scoring, uncertainty, decision modes
9. **Fraud** — Postgres transaction features + Neo4j graph features; start with deterministic rules
10. **SFA forecasting** — retailer/product demand; naive baseline before boosting
11. **Digital Twin** — computed, not authoritative; Observed / Recent / Historical / Relationships / Inferred / Predicted / Unknown / Recommended
12. **Decision Engine** — predictions do not make business decisions directly
13. **Explanation** — What / Why / Evidence / Confidence / Unknowns / Alternatives
14. **AI Copilot** — only after structured intelligence works
15. **API** — adapters over application services
16. **UI simulator**
17. **Supabase** — same domain; local Postgres → Supabase Postgres. Keep Neo4j separately deployed.

---

## 9. What “done” looks like for the temporal core

The most important proof is:

1. Create a user
2. Add activities at arbitrary timestamps
3. Reconstruct the correct historical state
4. Detect a contradictory event such as Singapore → USA (`IMPOSSIBLE_TRAVEL`) while still storing the event

Once that works, Neo4j, ML, Digital Twins and recommendations are intelligence layers — not compensation for a weak data architecture.

See [BUILD-SEQUENCE.md](./BUILD-SEQUENCE.md) for the exact coding order and [MILESTONES.md](./MILESTONES.md) for gated delivery.
