# POC capability status

This index tracks verified POC capabilities. `POC complete` means the documented
scenario works in the shared demo environment; it does not mean production ready.

| # | Capability | Status | Document |
|---|---|---|---|
| 00 | Expanded POC dataset | POC complete | [00-poc-dataset.md](./00-poc-dataset.md) |
| 01 | Outbox and Neo4j projection | POC complete | [01-neo4j-projection.md](./01-neo4j-projection.md) |
| 02 | Temporal and graph features | POC complete | [Feature layer](./02-feature-layer.md) |
| 03 | Event memory | POC complete | [03-event-memory.md](./03-event-memory.md) |
| 04 | Behaviour intelligence | POC complete | [04-behaviour-intelligence.md](./04-behaviour-intelligence.md) |
| 05 | Churn prediction | POC complete | [05-churn-prediction.md](./05-churn-prediction.md) |
| 06 | Recommendations and uncertainty | POC complete | [06-recommendations-uncertainty.md](./06-recommendations-uncertainty.md) |
| 07 | Graph fraud | POC complete | [07-graph-fraud.md](./07-graph-fraud.md) |
| 08 | SFA forecasting | POC complete | [08-sfa-forecasting.md](./08-sfa-forecasting.md) |
| 09 | Digital twins | POC complete | [09-digital-twins.md](./09-digital-twins.md) |
| 10 | Decision engine and explanations | POC complete | [10-decision-engine.md](./10-decision-engine.md) |
| 11 | OpenRouter GLM Copilot | POC complete | [11-copilot.md](./11-copilot.md) |
| 12 | FastAPI | Not started | — |
| 13 | POC simulator | Not started | — |

Capabilities are implemented and accepted sequentially. Capabilities 00–11 are
POC complete. Graph fraud, SFA forecasting and twins stay as separate live
panels from the decision engine. Later package scaffolds must not be interpreted
as implemented behavior.

The planned presentation of these capabilities inside the existing Omobio/NG
application family is documented in [POC-UI.md](../POC-UI.md). UI labels must
use this status table and must not present planned capabilities as live output.

An early **read-only showcase** for capability-00 evidence is documented in
[00-read-only-showcase.md](./00-read-only-showcase.md). That slice does not
change the status of capabilities 12 or 13.
