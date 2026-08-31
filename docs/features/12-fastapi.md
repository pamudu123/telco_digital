# Capability 12 — FastAPI

## 1. POC objective

Prove that FastAPI is a thin adapter over locked application services. Routes
do not contain SQL, Cypher, ML or business rules. PostgreSQL remains the
source of truth. Neo4j stays a rebuildable projection.

## 2. Demonstrated scenario

The stable `/api/v1` surface exposes:

- `GET /health` — process liveness with `slice: capability-12-fastapi`
- `GET /ready` — PostgreSQL and Neo4j probes (`unavailable` / `degraded` / `ok`)
- `GET /projection/lag` — pending / processed outbox counts and lag seconds
- `GET /models` — served churn and SFA forecast versions plus rule contracts
- Command adapters: recharge, travel, end-travel, plan purchase, usage
- Query adapters: customer state, timeline, twin, churn, recommendations,
  fraud, retailer forecast

A command writes fact + activity event + outbox event in one UnitOfWork
transaction and returns `correlation_id` and `event_id`.

## 3. Data inputs and outputs

Inputs are existing application commands and queries. Outputs are the existing
Pydantic documents (`CommandResult`, `ObservedCustomerState`, intelligence
payloads). Nothing is persisted except through the locked write path. Digital
twins and predictions remain derived.

## 4. Architecture and data flow

```text
HTML / CSS / JavaScript frontend
        |
        v
FastAPI read and command adapters
        |
        v
Application services and SQLAlchemy transaction boundary
        |
        +--> PostgreSQL (source of truth)
        |
        +--> Neo4j (read-only rebuildable projection)
```

Writes preserve:

```text
HTTP command -> FastAPI -> application service -> SQLAlchemy transaction
             -> domain fact + activity event + outbox event
```

## 5. Public services and types

Command adapters (`source=api`):

- `POST /api/v1/commands/recharge` → `record_recharge`
- `POST /api/v1/commands/travel` → `record_travel`
- `POST /api/v1/commands/travel/end` → `end_travel`
- `POST /api/v1/commands/plan-purchase` → `purchase_plan`
- `POST /api/v1/commands/usage` → `record_usage`

Query adapters:

- `GET /api/v1/customers/{ref}/state?as_of=`
- `GET /api/v1/customers/{ref}/timeline?as_of=`
- Existing intelligence reads (features, event-memory, behaviour, churn,
  fraud, twin, recommendations, decision, Copilot, retailer forecast)

Platform:

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `GET /api/v1/projection/lag`
- `GET /api/v1/models`

Unknown refs return 404. Invalid timestamps return 422. PostgreSQL failure
returns 503. Duplicate customer commands that already exist return 409.

## 6. Notebook and execution command

The retained notebook is `notebooks/12_fastapi/12_fastapi.ipynb`.

```bash
poetry run python notebooks/12_fastapi/generate_outputs.py
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/12_fastapi/12_fastapi.ipynb
```

The notebook inspects OpenAPI, the model catalog and command wrappers. It does
not train a model. Runtime adapters stay in `src/telco_digital/api`.

## 7. Results, metrics and plots

Retained evidence lives under `notebooks/12_fastapi/outputs/`:

- `metrics.json`
- `tables/openapi_commands.json`
- `tables/model_catalog.json`
- `plots/route_surface.png`

These are POC evidence of the HTTP surface, not production SLA numbers.

## 8. How to run and verify it

```bash
poetry run pytest tests/unit/test_api_showcase.py tests/unit/test_api_commands.py tests/unit/test_platform.py tests/scenarios/scenario_api.py -q
poetry run pytest tests/unit tests/scenarios -q
poetry run ruff check src/telco_digital/api src/telco_digital/application/services/platform.py tests/unit/test_api_commands.py
```

```powershell
python -m poetry install --extras "dev api"
$env:SHOWCASE_ENABLED = "true"
python -m poetry run uvicorn telco_digital.api.app:app --reload
```

Open `http://127.0.0.1:8000/docs` for OpenAPI. The POC Status page shows live
health, projection lag and model versions.

## 9. What is implemented

- Thin adapters over application services.
- Command adapters that preserve the locked write path.
- Health, readiness, projection lag and model versions.
- GetCustomerState and GetTimeline plus the existing intelligence reads.
- Canonical retailer forecast and twin routes alongside the showcase aliases.

## 10. What is not implemented

The UI simulator write path, authentication, and outcome recording are not
implemented. Capability 13 remains not started.

## 11. POC limitations

This is a POC HTTP surface. It is not production auth, multi-tenant isolation,
or an SLA. Command adapters exist so the simulator can call them later; they
are not a browser simulator.

## 12. Production improvements that would be required later

Add authentication, idempotency keys, rate limits, structured audit logs,
request tracing, and a dedicated API schema if the surface is exposed beyond
the POC origin.

## 13. Dependency for the next capability

Capability 13 is the framework-free POC simulator. It should call these
command adapters rather than writing SQL or Cypher from the browser.
