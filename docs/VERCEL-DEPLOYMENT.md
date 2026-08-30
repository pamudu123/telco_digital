# Single-project Vercel deployment

This POC deploys the framework-free frontend and FastAPI backend as one Vercel
project and one public origin:

```text
https://telco-intelligence.vercel.app/             frontend
https://telco-intelligence.vercel.app/api/v1/...   FastAPI
https://telco-intelligence.vercel.app/docs          OpenAPI UI
```

This is a POC deployment. It does not add authentication, multi-tenant
isolation, production observability, high availability or enterprise security
certification.

## How the single project works

Vercel discovers the root `app.py`, which exports the existing FastAPI
application. FastAPI registers `/api/v1` routes first and then mounts
`frontend/` at `/`. The frontend therefore keeps the same-origin API setting:

```javascript
export const API_BASE_URL = "/api/v1";
```

`vercel.json` includes `frontend/**` in the Python function bundle and prevents
live API responses from being cached. No database or Neo4j credential is sent
to the browser.

## Required Vercel environment variables

Configure these in Project Settings -> Environment Variables for Production and
the preview environments that should use the shared POC data:

```env
DATABASE_URL=postgresql+asyncpg://postgres.[PROJECT_REF]:[URL_ENCODED_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
DATABASE_POOL_MODE=transaction
NEO4J_URI=neo4j+s://[INSTANCE].databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=[AURA_PASSWORD]
API_ENVIRONMENT=poc
SHOWCASE_ENABLED=true
LOG_LEVEL=INFO
```

Copy the transaction-pooler URI from Supabase Dashboard -> Connect. Do not
construct the hostname or region from memory. Vercel is serverless, so this
runtime uses Supavisor transaction mode. The application selects SQLAlchemy
`NullPool` and disables asyncpg statement caching when
`DATABASE_POOL_MODE=transaction`.

Do not add the direct migration URI, OpenRouter key, Supabase secret key or
Neo4j password to frontend JavaScript.

## Migrations

Do not execute Alembic during function startup. Before deploying a revision,
run migrations once from a trusted local or CI environment with the direct
Supabase connection:

```env
DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
DATABASE_POOL_MODE=direct
```

```powershell
python -m poetry run alembic upgrade head
python -m poetry run alembic current
```

The current expected revision is `0002_poc_query_indexes`.

## Deploy from the Vercel dashboard

1. Push the repository to the Git provider connected to Vercel.
2. Select Add New -> Project and import the repository.
3. Keep Root Directory at the repository root.
4. Use the detected FastAPI framework preset.
5. Leave Build Command and Output Directory unset.
6. Add the server-side environment variables above.
7. Enable Deployment Protection while the POC has no application authentication.
8. Deploy.

The normal runtime dependencies include FastAPI and Uvicorn, so Vercel does not
need a Poetry extras flag to install the backend.

## Deploy with the CLI

Use Vercel CLI 48.1.8 or newer:

```powershell
npm install --global vercel
vercel login
vercel link
vercel deploy
vercel deploy --prod
```

Do not paste secrets into CLI arguments. Add them through the dashboard or
`vercel env add` prompts.

## Verification

After deployment, verify the same origin:

```text
GET /
GET /api/v1/health
GET /api/v1/showcase/overview
GET /api/v1/showcase/status
GET /api/v1/customers/U001/360
```

Expected behavior:

- `/` renders the Intelligence Overview shell.
- Overview counts come from Supabase and identify `live_database` as the source.
- Customer 360 shows recorded facts and UTC provenance.
- Capabilities 12 and 13 remain `Not started`.
- Database failure produces an unavailable state; notebook artifacts are not
  silently substituted.
- Frontend assets and API responses share the same Vercel domain.

Run the repository gates before deployment:

```powershell
python -m poetry run pytest -q
python -m poetry run ruff check .
python -m poetry check --lock
```

## POC operational limitations

- Static assets are bundled with and served by the FastAPI function rather than
  being a separately optimized frontend deployment.
- Cold starts and serverless execution limits apply.
- The read-only health endpoint does not yet prove projection lag or model
  availability.
- The outbox is not yet operated as a durable production worker on Vercel.
- Vercel deployment protection is not a replacement for application auth.
- Production deployment needs monitoring, alerting, backups, rate limits and a
  deliberate worker/queue design.

