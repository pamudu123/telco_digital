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
| `scenario_impossible_travel.py` | Event stored; `IMPOSSIBLE_TRAVEL` warning |
| `scenario_churn.py` | Usage decline + complaints + falling engagement → HIGH score and drivers |
| `scenario_decision.py` | U001 PRESENT_OFFER ROAM_15; U004 SUPPORT_FOLLOW_UP with no discount; Copilot fallback names ROAM_15 and duration unknown |
| `scenario_graph_fraud.py` | Shared device + suspicious merchant → graph risk + evidence |
| `scenario_retailer_stockout.py` | Inventory 18, 7d demand 47 → stockout risk + restock |

### Travel

Given user historically travelled Singapore for 6 days, used 11.4 GB, selected ROAM_15.  
When user travels to Singapore again.  
Then historical event is retrieved, ROAM_15 ranks highest, alternatives appear, trip duration remains unknown, and the decision is PRESENT_OFFER ROAM_15.

### Impossible travel

Given U001 Singapore at 09:00.  
When USA travel is entered at 10:00.  
Then event remains stored and `IMPOSSIBLE_TRAVEL` is generated.

### Churn / fraud / retailer

As specified in the locked plan (Milestone 6 / 8 / 9). The first implementation slice proves reconstruction + impossible travel + frequent small recharge. Later scenarios land with those milestones.
