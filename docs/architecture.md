# Architecture

The platform is a modular monolith: a React/Vite client calls one FastAPI application. An active dataset is shared across EDA, AI analysis, charting, feature engineering, and reporting.

## Backend layers

Dependencies point downward only. A lower layer never imports a higher one.

1. `api/routes` — validates HTTP input and delegates. Resolves the active dataset through `dependencies.ActiveDataset`.
2. `services` — coordinates application use cases. Assembles results, never calculates.
3. `graphs` — sequences one AI analysis: understand → delegate → compute → narrate.
4. `agents` — classify analytical intent and choose a tool.
5. `tools` — performs every deterministic calculation.
6. `data`, `database`, `storage` — isolate data access.
7. `reports` — renders portable output.
8. `utils`, `core` — shared sanitizers, exceptions, and configuration.

## The calculation contract

**Language models may route and explain. They never produce a figure.**

This is enforced in three places, not just documented:

- `agents/orchestrator_agent.py` validates every column the model names against the real dataframe. A hallucinated column is discarded and the keyword router takes over.
- Specialists compute exclusively through `app.tools`, which receive a dataframe and return numbers.
- `agents/insight_agent._is_grounded` compares every number in the model's narration against the verified result. Narration that introduces a new figure is dropped in favour of the deterministic sentence.

`AgentResult.verified` is `True` only on that path, and `narration_source` records whether the wording came from the model or from a template.

## Degraded mode

The platform works with no language model running. When Ollama is unreachable:

- `OrchestratorAgent.plan` falls back to `agents/fallback.build_plan`, a deterministic keyword router.
- `InsightAgent.narrate` returns the template sentence unchanged.
- `LLMClient` opens a 30-second circuit breaker so each request pays at most one failed connection.
- `GET /api/ai/health` reports `mode: "deterministic"` so the UI can say so plainly.

Answers in this mode are still fully computed and still marked `verified`.

## Serialization

Pandas produces `NaN`, `±inf`, numpy scalars, and timestamps that are not valid JSON. Everything crossing the HTTP boundary passes through `utils/dataframe_utils` (`json_records`, `finite`, `finite_series`), and Plotly figures are normalised with `PlotlyJSONEncoder`.

## Frontend layers

`app/*` pages compose `components/*`, which call `services/*` clients and read the active dataset from `store/datasetStore`. `App.tsx` is shell and routing only. The AI conversation is lifted to `App` so saved answers can feed the report builder.

## State

The MVP stores dataframes in process memory (`services/dataset_service.DatasetStore`), so a restart clears them and the app is single-process. Production should replace this with authenticated workspace metadata and object storage.
