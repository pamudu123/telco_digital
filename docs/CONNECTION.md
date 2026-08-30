# Service connections

How to connect PostgreSQL (local or Supabase), Neo4j, and related tooling for this POC.

For the project-specific hosted PostgreSQL setup, migration commands, and the
reason this repository does not use the Supabase Python client, see
[SUPABASE-CONNECTION.md](./SUPABASE-CONNECTION.md).

PostgreSQL is the system of record. Neo4j is a rebuildable projection. Domain code does not change when you swap local Postgres for Supabase — only env and deploy config change. See [LOCKED-ARCHITECTURE.md](./LOCKED-ARCHITECTURE.md) and Milestone 15 in [MILESTONES.md](./MILESTONES.md).

---

## Required services

| Service | Role | Local default | Cloud / shared |
|---|---|---|---|
| PostgreSQL | Source of truth (schemas `core`, `telco`, `activity`, `integration`, …) | Docker Compose `:5432` | **Supabase** Postgres |
| Neo4j | Relationship projection (Bolt) | Docker Compose `:7687` / Browser `:7474` | Neo4j Aura or self-hosted (not Supabase) |
| App env | `DATABASE_URL`, Neo4j credentials | `.env` from `.env.example` | Same vars; secrets in host / CI / Supabase |

Optional later: FastAPI (`poetry install --extras api`), ML (`--extras ml`). No LLM until Milestone 12.

---

## 1. Local (Docker Compose)

```bash
docker compose up -d
cp .env.example .env
poetry install --extras dev
poetry run alembic upgrade head
poetry run python scripts/seed_demo_data.py
```

### Defaults (`.env.example`)

```env
DATABASE_URL=postgresql+asyncpg://poc:poc@localhost:5432/intelligence_poc
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
LOG_LEVEL=INFO
```

| Check | URL / command |
|---|---|
| Postgres | `localhost:5432`, db `intelligence_poc`, user/pass `poc`/`poc` |
| Neo4j Browser | http://localhost:7474 |
| Neo4j Bolt | `bolt://localhost:7687` |
| Health | `docker compose ps` |

SQLAlchemy loads settings from `.env` via `telco_digital.config.Settings` (`database_url`, `neo4j_*`).

---

## 2. Supabase (PostgreSQL)

Supabase replaces only the PostgreSQL host. The domain, application,
SQLAlchemy, Alembic, and outbox architecture does not change, and Neo4j remains
separately deployed.

Use a direct `postgresql+asyncpg://` database URI for migrations and the initial
POC runtime. Do not use the project URL or publishable key as database
credentials, and do not expose internal schemas through Supabase REST.

Follow [SUPABASE-CONNECTION.md](./SUPABASE-CONNECTION.md) for the exact `.env`,
migration, verification, pooling, and troubleshooting procedure.

---

## 3. Neo4j

Neo4j is **not** hosted by Supabase. Deploy it next to the app (Docker, VM, or [Neo4j Aura](https://neo4j.com/cloud/aura/)).

### Local

Already covered by `docker compose` (see above). Credentials: `neo4j` / `password`.

### Aura (or remote)

```env
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=[AURA_PASSWORD]
```

| URI scheme | When |
|---|---|
| `bolt://` | Local / unencrypted Bolt |
| `neo4j://` | Routed driver (cluster) |
| `neo4j+s://` / `bolt+s://` | Aura / TLS required |

Graph data must remain **rebuildable from Postgres** (outbox → projector). After connecting a fresh Neo4j:

```bash
poetry run python scripts/rebuild_graph.py
```

Do not treat Neo4j as a second source of truth.

---

## 4. Env checklist

Copy `.env.example` → `.env` and fill:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://…` — local Docker or Supabase |
| `NEO4J_URI` | Yes (for graph) | `bolt://…` or `neo4j+s://…` |
| `NEO4J_USER` | Yes (for graph) | Usually `neo4j` |
| `NEO4J_PASSWORD` | Yes (for graph) | Match Compose / Aura |
| `LOG_LEVEL` | No | Default `INFO` |

Settings class: `src/telco_digital/config/settings.py`.

---

## 5. Typical topologies

**Dev machine**

```text
App (Poetry) → localhost:5432 (Compose Postgres)
             → localhost:7687 (Compose Neo4j)
```

**POC on Supabase + Aura**

```text
App / CI → Supabase Postgres (DATABASE_URL)
        → Neo4j Aura (NEO4J_*)
Outbox worker → reads Postgres → projects to Neo4j
```

**Wrong**

```text
Browser → Supabase REST on internal domain tables   # bypasses transactional write path
Predictions stored as Neo4j “facts”                   # forbidden by locked architecture
```

---

## 6. Troubleshooting

| Symptom | Likely fix |
|---|---|
| `Connection refused` on 5432 / 7687 | `docker compose up -d`; wait for healthchecks |
| Supabase `Tenant or user not found` / auth fail | Wrong project ref, password, or user (`postgres` vs `postgres.[ref]` for pooler) |
| SSL errors to Supabase | Add `?ssl=require` or use the dashboard’s URI as given |
| Alembic fails via pooler | Use **direct** `:5432` URL for migrations only |
| asyncpg + transaction pooler weirdness | Prefer session mode or direct connection for this POC |
| Neo4j empty after Postgres seed | Run outbox worker / `scripts/rebuild_graph.py` |
| Integration tests skipped | Export `DATABASE_URL` (or load `.env`) before `pytest` |

---

## Related docs

- [SUPABASE-CONNECTION.md](./SUPABASE-CONNECTION.md) — hosted PostgreSQL setup and verification  
- [DATA-MODEL.md](./DATA-MODEL.md) — schemas and tables  
- [BUILD-SEQUENCE.md](./BUILD-SEQUENCE.md) — step 62 Supabase deploy  
- [TESTING.md](./TESTING.md) — when Postgres/Neo4j are required for tests  
- [README.md](../README.md) — quick local start  
