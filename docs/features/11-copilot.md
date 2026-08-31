# Capability 11 — OpenRouter GLM Copilot

## 1. POC objective

Prove that Copilot is a presentation layer over structured intelligence. It
answers from a decision document and never creates facts, discounts or
invented plans.

## 2. Demonstrated scenario

“Why is U001 receiving this recommendation?” is answered from the March
Singapore episode (6 days / 11.4 GB / `ROAM_15`), duration unknown, and
catalogue alternatives `ROAM_5` and `ROAM_30`.

## 3. Data inputs and outputs

Inputs are capability-03/06/10 documents only. The output is a typed
`customer-copilot-v1` answer with source (`deterministic_fallback` or
`openrouter_glm`), used facts, unknowns and an optional fallback reason.
Answers are derived and not persisted. PostgreSQL remains authoritative.

## 4. Architecture and data flow

`DecisionEngine -> context pack -> CopilotService`

A deterministic template is always available. Optional OpenRouter GLM is used
only when `OPENROUTER_API_KEY` is set. Failed calls or ungrounded model text
return the fallback.

## 5. Public services and types

- `CopilotService.answer(question, customer_ref, as_of, destination=None)`
- `answer_from_decision`, `render_fallback`, `is_ungrounded`
- `CopilotAnswer`

Settings (environment only): `openrouter_api_key`, `openrouter_model`
(default `z-ai/glm-4.5-flash`). The key is never placed in frontend files.

## 6. Notebook and execution command

The retained notebook is `notebooks/11_copilot/11_copilot.ipynb`.

```bash
poetry run jupyter nbconvert --execute --to notebook --inplace notebooks/11_copilot/11_copilot.ipynb
```

The notebook shows the fallback answer for the U001 question. A live
OpenRouter cell is skipped without a key.

## 7. Results, metrics and plots

Retained evidence lives under `notebooks/11_copilot/outputs/`:

- `metrics.json`
- `tables/u001_fallback.json`

These are POC evidence over synthetic fixtures.

## 8. How to run and verify it

```bash
poetry run pytest tests/unit/test_copilot.py tests/scenarios/scenario_decision.py -q
poetry run pytest tests/unit tests/scenarios -q
poetry run ruff check src/telco_digital/copilot tests/unit/test_copilot.py
```

Ask live at `POST /api/v1/copilot/ask` with
`{question, customer_ref, as_of, destination}`.

## 9. What is implemented

- Structured context pack from the decision document.
- Deterministic fallback that names only catalogue plans in context.
- Optional OpenRouter GLM with ungrounded-output rejection.
- Read-only Copilot API and a live Copilot page with Fallback / Model badges.

## 10. What is not implemented

Command writes, conversation history, FastAPI-complete and the simulator are
not implemented.

## 11. POC limitations

The optional model is a presentation layer. Missing keys or unsupported claims
always fall back. The demo question is synthetic.

## 12. Production improvements that would be required later

Govern prompts, log provenance, keep the fallback as the safety path, and
never let the model write facts.

## 13. Dependency for the next capability

Capability 12 is the complete FastAPI surface. See
[12-fastapi.md](./12-fastapi.md). Copilot does not complete that milestone by
itself; it remains a presentation layer over structured intelligence.
