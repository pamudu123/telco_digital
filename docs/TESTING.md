# Testing strategy (locked)

Three levels.

## Unit tests

Feature calculations, anomaly rules, candidate scoring, uncertainty logic, episode building.

## Integration tests

Postgres repositories, outbox, Neo4j projection, graph queries.

## Scenario tests (especially important for the POC)

| File | Intent |
|---|---|
| `scenario_travel_recommendation.py` | Historical Singapore trip retrieved; ROAM_15 ranks highest; duration unknown; no invented plan |
| `scenario_digital_twin.py` | U001 twin composes episode + ROAM_15; RET-001 Predicted/Recommended stay unknown |
| `scenario_impossible_travel.py` | Event stored; `IMPOSSIBLE_TRAVEL` warning |
| `scenario_churn.py` | Usage decline + complaints + falling engagement → HIGH score and drivers (NBA stays later) |
| `scenario_graph_fraud.py` | Shared device + wallet funnel → graph risk exceeds transaction-only risk |
| `scenario_retailer_stockout.py` | Inventory 18, 7d demand 47 → stockout risk + restock |

### Travel

Given user historically travelled Singapore for 6 days, used 11.4 GB, selected ROAM_15.  
When user travels to Singapore again.  
Then historical event is retrieved, ROAM_15 ranks highest, alternatives appear, trip duration remains unknown.

### Impossible travel

Given U001 Singapore at 09:00.  
When USA travel is entered at 10:00.  
Then event remains stored and `IMPOSSIBLE_TRAVEL` is generated.

### Churn / fraud / retailer

Churn (capability 05) and graph fraud (capability 07) land with their milestones. The first implementation slice proves reconstruction + impossible travel + frequent small recharge.
