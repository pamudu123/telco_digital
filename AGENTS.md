# Agent Instructions

Company shared-intelligence POC (`telco-digital`). PostgreSQL is source of truth; Neo4j is a rebuildable projection. Architecture is locked — follow `docs/`, do not invert the stack.

## What's Included

### Docs (`docs/`)
| File | Role |
|------|------|
| `LOCKED-ARCHITECTURE.md` | Source of truth: stack, write path, hard rules |
| `SHARED-INTELLIGENCE.md` | Cross-app intelligence framing |
| `DATA-MODEL.md` | Postgres schemas, ledgers, outbox, Neo4j projection |
| `INTELLIGENCE.md` | Features, twins, ML, recommendations, decisions |
| `MILESTONES.md` | Milestone 1–15 gates |
| `BUILD-SEQUENCE.md` | Coding order 01–62 |
| `TESTING.md` | Unit / integration / scenario strategy |
| `PROBLEM-STATEMENT.md` | POC scope and success criteria |

### Package (`src/telco_digital/`)
| Package | Contents |
|---------|----------|
| `domain/` | Entities, enums, value objects, domain rules (travel, recharge) |
| `application/` | Commands, queries, UoW protocol, services (customer, recharge, plan, usage, travel, timeline, state, catalog) |
| `infrastructure/postgres/` | SQLAlchemy models, session, repositories, UoW |
| `infrastructure/neo4j/` | Projector, repository, Cypher mappings |
| `infrastructure/workers/` | Outbox worker |
| `intelligence/` | Scaffolds: state, features, event_memory, behaviour, churn, fraud, forecasting, recommendations, digital_twin |
| `decisioning/` | Scaffolds: candidates, ranking, uncertainty, explanations, rules |
| `api/`, `copilot/` | Scaffold only |
| `config/` | Settings from env |

### Other
- `alembic/` — migration `0001_locked_schema`
- `scripts/` — seed, synthetic data, train models, rebuild graph
- `tests/` — unit, integration (Postgres), scenarios (travel, recharge, fraud, churn, reconstruction)
- `docker-compose.yml` — Postgres + Neo4j

## Package Manager
Use **Poetry** (`python -m poetry` if `poetry` is not on PATH):

```bash
poetry install --extras "dev"
poetry run pytest
poetry run alembic upgrade head
```

Extras: `dev` (pytest, ruff, mypy, pre-commit), `api` (FastAPI), `ml` (sklearn, pandas).

## File-Scoped Commands
| Task | Command |
|------|---------|
| Lint file | `poetry run ruff check path/to/file.py` |
| Format file | `poetry run ruff format path/to/file.py` |
| Pre-commit | `poetry run pre-commit run --all-files` |
| One test | `poetry run pytest tests/unit/test_travel_rules.py -q` |
| Scenario | `poetry run pytest tests/scenarios/test_impossible_travel.py -q` |

## Key Conventions
- Business rules in `domain/` / `application/` — never put Cypher or SQL there
- Cypher only under `infrastructure/neo4j/`; SQL only under `infrastructure/postgres/`
- Digital twins and predictions are derived, not authoritative tables
- Do not connect an LLM before Milestone 12 (`docs/MILESTONES.md`)
- Implement in `BUILD-SEQUENCE.md` order; later packages may be scaffolds only
- Temporal queries use `as_of` / event history; reconstruct state from facts

## Commit Attribution
AI commits MUST include:
```
Co-Authored-By: (the agent model's name and attribution byline)
```
