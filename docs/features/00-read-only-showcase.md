# Capability-00 early read-only showcase

This is a **sequencing exception**, not capabilities 12 or 13.

The accepted order remains `00 → 01 … → 11 → 12 FastAPI → 13 Simulator`.
This slice only presents verified capability-00 PostgreSQL facts in a
framework-free UI so stakeholders can inspect the dataset without waiting for
graph, models, Copilot, the full API, or the simulator.

## Status impact

| Capability | Status after this slice |
|---|---|
| 00 Expanded POC dataset | POC complete |
| 12 FastAPI | **POC complete** (see [12-fastapi.md](./12-fastapi.md); this slice did not complete it) |
| 13 POC simulator | **Not started** |

A few read endpoints did not complete FastAPI. Capability 12 now exposes the
stable application services, health, projection lag, model versions and
command adapters. The simulator document name remains `13-poc-simulator.md`
when that capability is implemented.

## What visitors can do

- Open Overview, Customer 360, application fact lenses, walkthroughs, and POC Status.
- See live counts from PostgreSQL with explicit `source: live_database`.
- See live Models (NBA only; twins stay planned) and Copilot with a Fallback or Model badge.
- Open Journey and Event Memory for derived travel-episode matches and decisions.

## What they cannot do

- Issue writes or run the simulator.
- Query Neo4j from the browser.
- See digital twins, fraud scores or forecasts as live output.
- Treat notebook plots as live metric cards.

## Public services

- `GET /api/v1/health`
- `GET /api/v1/showcase/overview`
- `GET /api/v1/showcase/evidence`
- `GET /api/v1/showcase/personas`
- `GET /api/v1/showcase/status` (structured manifest, not Markdown parsing)
- `GET /api/v1/showcase/walkthroughs`
- `GET /api/v1/customers/{ref}/360?as_of=`
- `GET /api/v1/customers/{ref}/decision?as_of=&destination=`
- `POST /api/v1/copilot/ask`
- `GET /api/v1/showcase/sfa/retailers/{ref}?as_of=`

Routes 404 unless `SHOWCASE_ENABLED` is true. Invalid `as_of` returns 422.
Unknown refs return 404. PostgreSQL failure returns 503 with
`source: unavailable` and does not substitute notebook JSON.

Generated-row counts use `poc-v1` ownership, not `SUM(*)` of every table.

## How to run

```powershell
python -m poetry install --extras "dev api"
$env:SHOWCASE_ENABLED = "true"
python -m poetry run uvicorn telco_digital.api.app:app --reload
```

Open `http://127.0.0.1:8000/`. Configure `frontend/js/config.js` if the API is
hosted separately. Do not put database, Neo4j, or OpenRouter credentials in
frontend files.

If this UI is deployed beyond localhost, protect it (Vercel deployment
protection, basic-auth gateway, or a restricted preview). All records are
synthetic and the banner must remain visible.

## Verification

```powershell
python -m poetry run pytest tests/unit/test_capability_status.py tests/unit/test_showcase_dtos.py tests/unit/test_api_showcase.py tests/unit/test_frontend_smoke.py -q
```

PostgreSQL `as_of` and generated-row reconciliation:

```powershell
python -m poetry run pytest tests/integration/test_showcase_queries.py -q
```
