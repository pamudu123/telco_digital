# Supabase PostgreSQL connection

This project uses Supabase as hosted PostgreSQL. It does **not** use the
`supabase` Python client as its domain data layer.

PostgreSQL remains the source of truth, and the existing SQLAlchemy, asyncpg,
Alembic, repository, and unit-of-work stack remains unchanged. FastAPI will be
added later as a thin API adapter over application services.

See [CONNECTION.md](./CONNECTION.md) for the complete local, PostgreSQL, and
Neo4j service overview. The architectural rules are defined in
[LOCKED-ARCHITECTURE.md](./LOCKED-ARCHITECTURE.md).

## Why the Flask and Supabase client example is not used

The common Supabase quickstart uses `SUPABASE_URL`, a publishable key, and the
`supabase` Python client to query a public table through Supabase's data API.
That is not the correct integration for this repository because it would:

- bypass the SQLAlchemy repositories and application services;
- make the domain write, activity event, and outbox harder to guarantee in one
  PostgreSQL transaction;
- encourage exposing internal domain schemas through the data API; and
- add Flask even though FastAPI is the locked future API framework.

The project URL and publishable key are therefore not database credentials.
They are not required for the current backend connection. Do not add
`SUPABASE_URL`, `SUPABASE_KEY`, or a service-role key for this milestone.

## Obtain the database URI

In Supabase Dashboard, open the project and choose **Connect** or
**Project Settings -> Database**. Copy the direct database connection URI. It
has this general form:

```text
postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
```

The known project reference for this POC is `gxkiadapfjjcqeubotcd`. The database
password is separate from the publishable key. Reset the database password in
the dashboard if it is not available.

Convert the URI for this repository by changing only the scheme:

```env
DATABASE_URL=postgresql+asyncpg://postgres:[URL_ENCODED_PASSWORD]@db.gxkiadapfjjcqeubotcd.supabase.co:5432/postgres
```

If the password contains reserved URI characters such as `@`, `#`, `%`, `/`,
or `:`, URL-encode it. Put the real URI in the gitignored `.env`; never put it
in `.env.example`, documentation, source code, chat logs, or commits.

## Direct connection versus pooler

| Workload | Connection | Guidance |
|---|---|---|
| Alembic and administrative scripts | Direct, port `5432` | Required default for schema migration and long-lived DDL |
| Initial POC runtime | Direct, port `5432` | Simplest option while concurrency is low |
| Later serverless or high-concurrency runtime | Supavisor pooler, commonly port `6543` | Use the exact dashboard pooler URI and validate asyncpg behavior |

Do not use a transaction-pooler URI for Alembic. If runtime pooling is added
later, keep a separate direct migration secret in the deployment environment.

## Configure and migrate

From the repository root:

```powershell
Copy-Item .env.example .env
```

Replace `DATABASE_URL` in `.env` with the converted direct URI. Leave the
Neo4j variables pointed at Docker Compose or replace them with Neo4j Aura
credentials. Supabase hosts PostgreSQL only; Neo4j stays separate.

Install the existing project dependencies and apply the locked schema:

```powershell
python -m poetry install --extras "dev"
python -m poetry run alembic upgrade head
```

The migration creates the internal schemas and tables defined by the locked
data model. Do not reproduce them manually in the Supabase SQL editor. Demo
data is intentionally not seeded as part of connection setup.

## Verify without exposing credentials

Run the codebase connection check. It executes `SELECT 1` and prints only the
parsed host, port, and database name:

```powershell
python -m poetry run python scripts/check_postgres_connection.py
```

Then verify the migration and tests:

```powershell
python -m poetry run alembic current
$env:DATABASE_URL = (Get-Content .env | Where-Object { $_ -like 'DATABASE_URL=*' } | ForEach-Object { $_.Substring(13) })
python -m poetry run pytest tests/integration -m integration -q
python -m poetry run pytest -q
python -m poetry run ruff check .
```

`alembic current` must report `0001_locked_schema (head)`. In Supabase, confirm
that `public.alembic_version` contains `0001_locked_schema` and that the locked
internal schemas exist.

## Security rules

- Keep `.env`, database passwords, publishable keys, and service-role keys out
  of Git.
- The browser must not read or write the internal domain schemas directly.
- Future frontend access must go through FastAPI application services, or a
  deliberately designed API schema with explicit grants and RLS.
- Preserve the transactional write path: domain write + activity event +
  outbox event in one PostgreSQL transaction.
- Treat Neo4j as a rebuildable projection, never as a second source of truth.
- Enable backups and point-in-time recovery before using non-disposable data.

## Troubleshooting

| Symptom | Action |
|---|---|
| Password authentication failed | Use the database password, not the publishable or service-role key |
| Host cannot be reached | Copy the current direct or pooler URI from Dashboard -> Connect; direct IPv6 connectivity may not be available on every network |
| Password with special characters fails | URL-encode the password portion of the URI |
| SSL error | Start from the dashboard URI and add driver-compatible SSL options only if required |
| Alembic fails through port `6543` | Switch to the direct port `5432` URI |
| Pooler reports tenant or user not found | Use the exact pooler hostname and username shown by Supabase |
| Integration tests are skipped | Ensure `DATABASE_URL` is available to the test process and contains no placeholder |
