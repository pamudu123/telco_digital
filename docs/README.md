# Omobio Intelligence POC — documentation

**Architecture status: LOCKED** (2026-08-27). Implementation follows these documents. Do not treat this folder as brainstorming notes.

| Document | Contents |
|---|---|
| [LOCKED-ARCHITECTURE.md](./LOCKED-ARCHITECTURE.md) | Core idea, target diagram, technology choices, hard rules, write path, temporal integrity |
| [SHARED-INTELLIGENCE.md](./SHARED-INTELLIGENCE.md) | How this POC supports Omobio shared intelligence across applications |
| [DATA-MODEL.md](./DATA-MODEL.md) | PostgreSQL schemas/tables, ledgers, events, outbox, Neo4j projection |
| [INTELLIGENCE.md](./INTELLIGENCE.md) | State, features, episodes, twins, ML, recommendations, decisions, copilot |
| [MILESTONES.md](./MILESTONES.md) | Milestone 1–15 gates |
| [BUILD-SEQUENCE.md](./BUILD-SEQUENCE.md) | Coding order 01–62 |
| [TESTING.md](./TESTING.md) | Unit / integration / scenario tests |
| [CONNECTION.md](./CONNECTION.md) | Local Docker, Supabase Postgres, Neo4j / Aura env setup |
| [VERCEL-DEPLOYMENT.md](./VERCEL-DEPLOYMENT.md) | Single-project deployment for the static UI and FastAPI backend |
| [POC-UI.md](./POC-UI.md) | Intelligence Showcase UI for the existing Omobio/NG applications |
| [EXISTING-APP.md](./EXISTING-APP.md) | Mapping from shared-intelligence capabilities to existing Omobio applications |
| [features/README.md](./features/README.md) | Verified capability status, evidence and implementation documents |
| [features/00-read-only-showcase.md](./features/00-read-only-showcase.md) | Early read-only UI showcase for capability-00 evidence (not FastAPI/simulator complete) |
| [features/03-event-memory.md](./features/03-event-memory.md) | Capability 03 travel episode extraction and similar-event matching |
| [features/04-behaviour-intelligence.md](./features/04-behaviour-intelligence.md) | Capability 04 derived behaviour traits and notebook clustering |
| [features/05-churn-prediction.md](./features/05-churn-prediction.md) | Capability 05 notebook-trained churn score |
| [features/07-graph-fraud.md](./features/07-graph-fraud.md) | Capability 07 graph fraud rules and combined scorer |

Start here: [LOCKED-ARCHITECTURE.md](./LOCKED-ARCHITECTURE.md).  
Code next: steps 01–33 in [BUILD-SEQUENCE.md](./BUILD-SEQUENCE.md).
