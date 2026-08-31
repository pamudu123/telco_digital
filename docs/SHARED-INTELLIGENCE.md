# Shared intelligence (company)

This POC implements the shared intelligence concept already defined for the company: **multiple applications contribute signals to reusable intelligence**, rather than each product maintaining isolated AI.

Referenced product framing: *Digital Service Solutions*. The PDF is not checked into this repository; this document records the architectural implication that the locked plan must support.

## What shared intelligence means here

Telco, marketing, mobile money, SFA, and service activity are **signal sources**. They write facts into PostgreSQL (system of record) and emit immutable activity events. A single intelligence layer then derives:

- temporal behaviour
- relationship/graph context
- event memory / episodes
- predictions (churn, fraud, demand, propensity)
- next-best actions

Applications **consume** twins, warnings, recommendations, and explanations. They do not each train a private model over a private copy of the customer.

## Implications that this architecture locks

| Isolated AI (avoid) | Shared intelligence (this POC) |
|---|---|
| Each app has its own customer 360 | One `CustomerContext` / Digital Twin computed at `as_of` |
| Balance is a mutable column in one app | Ledgers + events reconstruct history for every consumer |
| Graph writes from each UI | Outbox projection; graph is a rebuildable view |
| Model scores stored as graph facts | Predictions stay in the intelligence layer with model version + feature snapshot |
| Copilot invents answers | Copilot explains structured evidence from twins, episodes, graph, and decisions |

## Signal domains in this POC

- **core** — customer, account, SIM, device, plan, subscription
- **telco** — recharge, usage, travel, service interactions, balance ledger
- **marketing** — loyalty, campaigns
- **money** — wallets, merchants, transactions
- **sfa** — distributors, retailers, agents, sales, inventory
- **activity** — universal event history
- **integration** — outbox for projections
- **intelligence** — feature snapshots, model predictions, recommendations, outcomes (derived, not source of truth)

New company applications should add facts and events into these schemas (or a new bounded schema) and reuse the same intelligence pipeline.
