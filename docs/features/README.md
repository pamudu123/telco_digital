# POC capability status

This index tracks verified POC capabilities. `POC complete` means the documented
scenario works in the shared demo environment; it does not mean production ready.

| # | Capability | Status | Document |
|---|---|---|---|
| 00 | Expanded POC dataset | POC complete | [00-poc-dataset.md](./00-poc-dataset.md) |
| 01 | Outbox and Neo4j projection | Not started | — |
| 02 | Temporal and graph features | Not started | — |
| 03 | Event memory | Not started | — |
| 04 | Behaviour intelligence | Not started | — |
| 05 | Churn prediction | Not started | — |
| 06 | Recommendations and uncertainty | Not started | — |
| 07 | Graph fraud | Not started | — |
| 08 | SFA forecasting | Not started | — |
| 09 | Digital twins | Not started | — |
| 10 | Decision engine and explanations | Not started | — |
| 11 | OpenRouter GLM Copilot | Not started | — |
| 12 | FastAPI | Not started | — |
| 13 | POC simulator | Not started | — |

Capabilities are implemented and accepted sequentially. Later package scaffolds
must not be interpreted as implemented behavior.

The planned presentation of these capabilities inside the existing Omobio/NG
application family is documented in [POC-UI.md](../POC-UI.md). UI labels must
use this status table and must not present planned capabilities as live output.
