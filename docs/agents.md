# Agents

Five agents cooperate on every question. The orchestrator reads the question; a specialist computes; the insight agent explains.

| Agent | Owns | Intents |
|---|---|---|
| **Orchestrator** | Understands the request and delegates | routing only |
| **Statistical** | Aggregations, rankings, descriptive measures, IQR outliers | `aggregation`, `ranking`, `descriptive`, `outlier` |
| **Pattern** | Correlation, relationships, trends, segmentation | `correlation`, `relationship`, `trend`, `segmentation` |
| **Predictive** | Regression, classification, forecasting | `regression`, `classification`, `forecast` |
| **Insight** | Dataset overviews and explaining verified results | `summary` |

`agents/base.INTENT_OWNERS` is the single source of truth for which agent owns which intent.

## The pipeline

`graphs/graph.AnalysisGraph` runs four nodes and records a trace the UI displays:

1. **understand** — `OrchestratorAgent.plan` produces an `AnalysisPlan`.
2. **delegate** — `graphs/routing.select` maps the intent to a specialist.
3. **compute** — the specialist calls `app.tools`. Every figure originates here.
4. **narrate** — `InsightAgent.narrate` optionally rephrases the verified numbers.

## Planning

With a model available, the orchestrator sends the question plus **column names and types only — never row values** — and asks for a JSON routing plan. `llm/structured_output.parse_structured` extracts the JSON, validates it against a Pydantic model, and gives the model one corrective retry.

The plan is then checked against reality:

- Any column not present in the dataframe is set to `None`.
- An unrecognised intent becomes `summary`.
- An invalid operation or chart type falls back to a default.
- A plan that names no usable column defers to the keyword router.

Any failure at any step — connection error, malformed JSON, invalid plan — routes to `agents/fallback.build_plan`. This is covered by `tests/test_agents.py`; `test_falls_back_when_llm_unreachable` is the guarantee that a stopped Ollama cannot break the product.

## Narration guard

`InsightAgent._is_grounded` extracts every number from the model's sentence and compares it against the numbers in the verified result, tolerating rounding within 1%. A sentence containing an invented figure is discarded and the deterministic sentence is kept, with `narration_source` left as `"template"`.

## Configuration

`app/llm/client.py` is the Ollama boundary and reads all connection and generation settings from environment variables. Copy `.env.example` to `.env` and set `OLLAMA_MODEL` to a model you have pulled locally. Prompts live in `app/llm/prompts/*.md`, one per agent.
