# telco-digital

Shared intelligence POC: PostgreSQL is the system of record, Neo4j is the relationship projection, and digital twins are computed from facts, inference, and predictions.

Python project managed with [Poetry](https://python-poetry.org/). Architecture is locked in [docs/LOCKED-ARCHITECTURE.md](docs/LOCKED-ARCHITECTURE.md).

## Layout

Business logic lives in `src/telco_digital/application` and `src/telco_digital/domain`.  
SQL stays in PostgreSQL repositories. Cypher stays in the Neo4j infrastructure package.

## Local

```bash
docker compose up -d
cp .env.example .env
poetry install --extras dev
poetry run alembic upgrade head
poetry run python scripts/seed_demo_data.py
poetry run pytest
```

If Docker is not running, `pytest` still covers the temporal core against an in-memory unit of work.
