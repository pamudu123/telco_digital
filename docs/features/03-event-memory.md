# Capability 03 — Event memory

## 1. POC objective

Prove that travel events can be reconstructed into episodes at an explicit
`as_of`, and that a current situation retrieves similar historical episodes
with personal history ranked above peers.

## 2. Demonstrated scenario

U001's March 2026 Singapore trip is reconstructed as 6 days, 11.4 GB,
`ROAM_15`, and "No additional package required". When the same customer is
queried for Singapore again after that trip, the March episode is the top
match. An open later trip keeps duration unknown.

## 3. Data inputs and outputs

Inputs are capability-00 travel, usage and subscription facts. The output is a
typed `travel-episodes-v1` `CustomerContext` containing the current situation,
historical episodes, ranked matches, provenance and explicit unknowns.
Episodes are derived and not persisted. PostgreSQL remains authoritative.

## 4. Architecture and data flow

`PostgreSQL facts -> PostgresEventMemoryQueries -> EventMemoryService`

`UnitOfWork repositories -> UnitOfWorkEventMemoryQueries -> EventMemoryService`

SQL stays in the PostgreSQL adapter. Extraction, outcome rules and similarity
ranking stay in `intelligence/event_memory`.

## 5. Public services and types

- `EventMemoryService.recall(customer_ref, as_of, destination=None)`
- `extract_travel_episodes`, `situation_from_facts`, `match_episodes`
- `CustomerContext`, `TravelEpisode`, `TravelSituation`, `EpisodeMatch`
- Match ranks: `SAME_CUSTOMER_SAME_SITUATION`, `SAME_CUSTOMER_SIMILAR_SITUATION`,
  `SIMILAR_CUSTOMERS`, `POPULATION`

All services reject timezone-naive `as_of` values. Future `ended_at` values are
treated as unknown at `as_of`.

## 6. Notebook and execution command

The retained notebook is `notebooks/03_event_memory/03_event_memory.ipynb`.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/03_event_memory/03_event_memory.ipynb
```

The notebook is the experiment surface. It reconstructs seed facts in memory,
writes compact tables and plots under `outputs/`, and does not require
database credentials. Runtime services stay in `src/telco_digital`.

## 7. Results, metrics and plots

Retained evidence lives under `notebooks/03_event_memory/outputs/`:

- `metrics.json`
- `tables/u001_march_episode.json`
- `tables/match_ranks.json`
- `tables/future_leakage_validation.json`
- `plots/episode_similarity.png`
- `plots/match_priority.png`

These are POC evidence over synthetic fixtures, not estimates of a real
population.

## 8. How to run and verify it

```bash
poetry run pytest tests/unit/test_event_memory.py tests/scenarios/scenario_travel_recommendation.py -q
poetry run pytest
poetry run ruff check .
```

Read live results at
`/api/v1/customers/U001/event-memory?as_of=2026-08-20T12:00:00Z&destination=SG`.

## 9. What is implemented

- Point-in-time travel episode extraction with usage, plan and outcome.
- Similar-event matching with personal-history priority.
- `CustomerContext` for the current situation plus retrieved episodes.
- Explicit destination and duration unknowns.
- Read-only API and a live Journey page. Recommendations stay planned.

## 10. What is not implemented

Non-travel episode types, a persisted episode store, vector search, learned
similarity, recommendation ranking, twins and Copilot are not implemented.

## 11. POC limitations

Episode definitions are demonstrative. The journeys are synthetic. The POC does
not establish real-world retrieval quality, production scale, or a durable
memory store.

## 12. Production improvements that would be required later

Approve episode contracts with domain owners, add more episode types, introduce
governed lineage, incremental extraction, evaluation against labelled retrieval
sets, and a versioned episode store only if product owners require persistence.

## 13. Dependency for the next capability

Capability 04 consumes these episodes as optional evidence for behaviour traits.
