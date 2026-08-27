# Agents

Five agents cooperate on every question. The natural language agent reads the question and
delegates; one specialist computes; the insight agent explains.

| Agent | Owns | Intents | LLM |
|---|---|---|---|
| **Natural language** | Understands the request and delegates | routing only | optional |
| **Statistical** | Aggregations, rankings, descriptive measures, IQR outliers | `aggregation`, `ranking`, `descriptive`, `outlier` | never |
| **Pattern** | Correlation, relationships, trends, segmentation | `correlation`, `relationship`, `trend`, `segmentation` | never |
| **Predictive** | Regression, classification, forecasting | `regression`, `classification`, `forecast` | never |
| **Insight** | Dataset overviews and explaining verified results | `summary` | optional |

`agents/registry.INTENT_OWNERS` is the single source of truth for which agent owns which
intent. It is comprehended from the skills each agent declares, so there is no separate
table to keep in sync.

## The invariant

From `agents/base.py`:

> `data` is produced by deterministic pandas/scipy tools. A language model may choose
> *which* tool runs and may phrase `answer`, but it never supplies a figure.

Three mechanisms enforce it. The planner model sees column names and kinds but never a row
of data. Whatever it proposes is re-checked against the real dataframe before anything
executes. Any sentence it writes is scanned for numbers absent from the computed result and
discarded if it invents one.

The payoff is that the platform degrades instead of breaking. With no model configured,
questions are still routed, computed, and answered — only the phrasing gets blunter.

## The graph

`graphs/graph.AnalysisGraph` compiles a LangGraph state machine, one pass per request. The
topology is fixed but genuinely branching: which specialist runs depends on the plan, and a
specialist that cannot run its plan is diverted rather than allowed to fail the request.

```
                        START
                          |
                    +-----v------+
                    | understand |   LanguageAgent.plan() -> AnalysisPlan   [LLM optional]
                    +-----+------+
                    +-----v------+
                    |  delegate  |   announces the hand-off (trace only)
                    +-----+------+
          +-----------+---+-------+-----------+   choose_specialist() -> plan.agent
    +-----v-----++----v----++-----v-----++----v----+
    |statistical|| pattern ||predictive || insight |   one specialist computes
    +-----+-----++----+----++-----+-----++----+----+
          +-----------+-----+-----+-----------+       after_compute() -> error?
                      +-----v-----+
              error   |  error?   |   ok
           +----------+-----+-----+----------+
     +-----v-----+                     +-----v-----+
     |  recover  |-------------------->|  narrate  |  [LLM optional]
     +-----------+   dataset summary   +-----+-----+
                                             v
                                            END
```

Only `understand` and `narrate` ever touch a model. Nodes live in `graphs/nodes.py`, the
wiring in `graphs/graph.py`, the state in `graphs/state.py`.

### The five stages

1. **understand** — the language agent turns the question into an `AnalysisPlan`: an intent,
   the columns to use, an operation, a row limit. No calculation.
2. **delegate** — announces the hand-off in the trace. The plan already names its owning
   specialist, so this node writes a trace entry and nothing else.
3. **one specialist** — executes the plan against the dataframe and returns an `AgentResult`.
4. **recover** — reached only when the specialist raised `AnalysisError`. Rewrites the plan
   to a dataset summary and attaches a caveat, so the user gets an answer instead of a 422.
   If the summary itself was what failed, it re-raises and the API returns 422.
5. **narrate** — the insight agent offers the verified numbers to the model for rephrasing.
   If the model is off, or its sentence fails the grounding check, the deterministic
   sentence stands.

State is a `TypedDict` where `trace` carries an additive reducer, so each node appends its
own step without reading what came before:

```python
class AnalysisState(TypedDict, total=False):
    record: Any                 # DatasetRecord — carries the live dataframe
    question: str
    plan: AnalysisPlan
    result: AgentResult
    error: str                  # set by a specialist that could not run its plan
    trace: Annotated[list[dict], operator.add]
```

## The shared contract

Three types define everything the agents exchange.

### Skill — what an agent declares it can do

A frozen dataclass naming one capability: the intent it serves, the tool that computes it,
and which of the six plan slots (`group`, `metric`, `x`, `y`, `target`, `features`) must
hold which *kind* of column.

```python
Skill(
    intent="ranking",
    summary="The best or worst N categories by a numeric measure.",
    tool="tools.statistics.aggregation.aggregate",
    example="What are the top 5 products by sales?",
    required=("metric", "group"),   # both must be filled to run at all
    numeric=("metric",),            # metric must be a numeric column
    categorical=("group",),         # group must be categorical/boolean/datetime
    chart="bar",
)
```

That single declaration is the source of truth for three unrelated consumers, which is why
adding a capability is a one-place edit:

- **routing** — `registry.INTENT_OWNERS` is built from every agent's skills at import.
- **validation** — `agents/validation.validate_plan` reads it to decide which columns are legal.
- **the planner prompt** — `registry.skill_menu()` serialises it, so the model only ever
  sees intents that actually exist.

### AnalysisPlan — the routing decision

Produced by the language agent or the keyword fallback, consumed by exactly one specialist.

```python
class AnalysisPlan(BaseModel):
    intent: str = "summary"            # one of 12 routable intents
    agent: str = "insight"             # derived: owner(intent)
    columns: PlanColumns               # group / metric / x / y / target / features
    operation: Literal["sum","mean","median","min","max","count"] = "sum"
    limit: int = Field(default=5, ge=1, le=50)
    chart: str | None = None
    source: Literal["llm", "fallback"] = "fallback"
    rejected: list[str] = []           # slots the validator emptied, with reasons
```

### AgentResult — the API contract

Every specialist returns this shape, and `to_dict()` on it *is* the JSON body the client
receives. The two honesty fields matter as much as the data: `caveats` carries what the
agent knows is shaky about its own answer, and `narration_source` tells the UI whether a
human-sounding sentence came from a model or a template.

```python
@dataclass
class AgentResult:
    agent: str                  # "statistical_agent"
    intent: str                 # "ranking"
    answer: str                 # the sentence shown to the user
    data: dict[str, Any]        # every figure, always from pandas
    suggested_chart: str | None = None
    verified: bool = True
    narration_source: str = "template"   # or "llm"
    trace: list[dict] = []      # the agent hand-off trail
    caveats: list[str] = []     # dropped rows, auto-picked features, weak fits
```

`agents/base.Agent.run` dispatches on intent alone and is the only entry point the graph
ever calls:

```python
def run(self, record, plan: AnalysisPlan) -> AgentResult:
    handler = self.handlers().get(plan.intent)
    if handler is None:
        raise AnalysisError(f"The {self.title.lower()} cannot handle '{plan.intent}'")
    return handler(record, plan)
```

`record` is a `DatasetRecord` — `id`, `name`, `source`, and `frame`, the live in-memory
`pd.DataFrame`. Agents read `record.frame` and never mutate it.

---

## Natural language agent

`agents/language_agent.py` · `class LanguageAgent` · LLM optional

The delegator. The only agent that talks to a model, and the only one that is *not* an
`Agent` subclass — it declares no skills and computes nothing, so it has no handlers to
inherit. `OrchestratorAgent` remains as a backwards-compatible alias.

| | |
|---|---|
| **Input** | `plan(record, question: str)` |
| **Output** | `AnalysisPlan` — always validated, always runnable. Never raises. |
| **Tools** | `describe_columns`, `skill_menu`, `parse_structured`, `validate_plan`, `is_runnable`, `build_plan` |

What the model is shown is deliberately narrow: the skill menu, and column *metadata*.

```python
described = describe_columns(record.frame)     # names + kinds only
prompt = (
    f"Available analyses:\n{json.dumps(skill_menu())}\n\n"
    f"Dataset columns ({described['total']} total):\n"
    f"{json.dumps(described['columns'])}\n\n"
    f"Question: {question}\n\n"
    "Return the routing plan as JSON."
)
proposed = parse_structured(self.client, prompt, load_prompt("orchestrator"), LLMPlan)
plan = validate_plan(record.frame, proposed.intent, proposed.columns, ...)
```

`agents/column_resolver.describe_columns` emits `{"name": "revenue", "kind": "numeric"}` per
column, plus a distinct count for categoricals. It sorts numeric columns first and
low-cardinality categoricals next, so that when a wide frame is truncated at 60 columns the
planner still sees the ones it is most likely to need — and the truncation is reported in
the prompt rather than hidden.

Everything the model returns is treated as a suggestion.
`llm/structured_output.parse_structured` digs a JSON object out of prose or code fences and
gives the model exactly one corrective retry with the validation error attached.
`validate_plan` then checks every named column against the real dtypes and empties any slot
holding the wrong kind, recording why in `plan.rejected`. `is_runnable` asks whether the
skill's required slots survived.

The whole fallback policy is nine lines:

```python
def plan(self, record, question: str) -> AnalysisPlan:
    if self.client is not None:
        try:
            proposed = self._llm_plan(record, question)
            if is_runnable(proposed):
                return proposed
            logger.info("LLM plan for %r was not runnable (rejected: %s)", question, proposed.rejected)
        except Exception as exc:
            logger.info("LLM planning unavailable (%s); using keyword routing", exc)
    return build_plan(record, question)
```

**Failure mode:** none that reaches the user. Connection error, invalid JSON, invented
column, wrong column kind, unrunnable plan — every path lands on `agents/fallback.build_plan`.
`tests/test_agents.py::test_falls_back_when_llm_unreachable` is the guarantee that a stopped
Ollama cannot break the product.

### The keyword fallback

`agents/fallback.py` is roughly a hundred lines of ordered rules over word lists —
`PREDICT_WORDS`, `CORRELATION_WORDS`, `RANK_WORDS` and so on — first match wins, ending in
`summary` if nothing matches. Every comparison is anchored on word boundaries via
`agents/column_resolver.mentions`, because substring matching mis-routes silently: `sum`
fires inside "summary", `count` inside "country" and "discount", `id` inside "identify".

---

## Statistical agent

`agents/statistical_agent.py` · deterministic

The calculator. Owns anything that reduces a column to a number.

| | |
|---|---|
| **Input** | `run(record, plan)` — needs `plan.columns.metric` for all four intents, plus `group` for ranking |
| **Output** | `AgentResult`, or raises `AnalysisError` → the graph diverts to `recover` |

| Intent | Required slots | Tool | Chart |
|---|---|---|---|
| `aggregation` | metric (+ optional group) | `tools/statistics/aggregation.aggregate` | bar |
| `ranking` | metric, group | `tools/statistics/aggregation.aggregate` | bar |
| `descriptive` | metric | `tools/distribution.numeric_distribution` | histogram |
| `outlier` | metric | `tools/quality.iqr_outliers` | box |

The interesting code is not the arithmetic, it is the refusal to state a misleading figure.
Ranking normally reports what share of the total the top N account for — but a share is only
meaningful when the measure is non-negative and sums above zero:

```python
total = float(finite_series(frame[metric]).sum())
if total > 0 and finite_series(frame[metric]).min() >= 0:
    share = float(table[metric].sum() / total * 100)
    answer = (f"The top {len(rows)} {group} values account for {share:.1f}% "
              f"of total {metric}.")
else:
    share = None
    caveats.append(f"{metric} contains negative or zero-summing values, so a share of "
                   "the total would be misleading and is omitted.")
```

Outlier detection reports the count, the percentage, and the IQR bounds, shows up to ten
example rows, and says plainly that they are *flagged, not removed* — an outlier can be a
genuine extreme value. Descriptive analysis reports how many non-finite values it had to
exclude rather than quietly dropping them.

Output shape is exact; figures are illustrative:

```json
{
  "agent": "statistical_agent",
  "intent": "ranking",
  "answer": "The top 5 product values account for 63.4% of total sales. Widget A leads with 48,210.00.",
  "data": {
    "group": "product", "metric": "sales", "operation": "sum",
    "rows": [{"product": "Widget A", "sales": 48210.0}],
    "combined_share_percent": 63.4,
    "limit": 5
  },
  "suggested_chart": "bar",
  "caveats": []
}
```

**Failure mode:** raises `AnalysisError` with a worked example in the message — "Ranking
needs a category and a numeric measure, for example: top 5 products by revenue" — when a
slot is missing, or when the column has no usable numeric values left after dropping
non-finite entries.

---

## Pattern recognition agent

`agents/pattern_agent.py` · deterministic

Owns relationships *between* columns. Never claims causation.

| | |
|---|---|
| **Input** | `run(record, plan)` — `x`/`y` for a correlation pair, `metric` + `x` for a trend, `group` for segments |
| **Output** | `AgentResult` — correlation with no pair named returns the whole matrix instead of failing |

| Intent | Required slots | Tool | Chart |
|---|---|---|---|
| `correlation` | none — x, y optional | `tools/correlation.correlation_matrix` | scatter / heatmap |
| `relationship` | alias of correlation | same handler | scatter |
| `trend` | metric (x must be datetime) | `numpy.polyfit` over the sorted series | line |
| `segmentation` | group | `tools/statistics/aggregation.aggregate` | bar |

Correlation has two modes in one handler. Name two numeric columns and you get a single
coefficient with its strength band, direction, observation count, and an unconditional
reminder that correlation does not establish causation. Name none, and it surveys every
numeric pair in the frame, sorts by absolute strength, and returns the top twenty plus the
full matrix for a heatmap.

Strength bands come from one module so `0.7` is never hardcoded twice
(`tools/correlation/thresholds.py`):

```python
STRONG = 0.7
MODERATE = 0.4
# Above this, a "feature" is almost certainly derived from the target, not predictive of it.
LEAKAGE = 0.98
```

Trend analysis fits a least-squares line over date ordinals and reports slope per day. It
refuses to run on fewer than three points, warns below twenty observations, and states its
own limitation in the answer text: "A linear fit describes direction only, not seasonality."

Segmentation counts rows per group into a private column name and renames it at the very
end, so a dataset that genuinely contains a column called `rows` cannot collide with the
count:

```python
COUNT_COLUMN = "__segment_rows"
counts = frame.groupby(group, dropna=False).size().reset_index(name=COUNT_COLUMN)
table = table.sort_values(COUNT_COLUMN, ascending=False).rename(columns={COUNT_COLUMN: "rows"})
```

**Failure mode:** raises when a pair shares fewer than 3 complete rows, when a correlation is
undefined because a column is constant, when fewer than two numeric columns exist at all, or
when a trend is requested on a frame with no datetime column. Segments smaller than 5 rows
produce a caveat about unstable averages rather than an error.

---

## Predictive agent

`agents/predictive_agent.py` · deterministic

Fits a model on a held-out split and reports how it scored. It never presents a prediction
as fact, and it is deliberately blunt about weak models.

| | |
|---|---|
| **Input** | `run(record, plan)` — needs `target` (or `metric`); `features` optional, auto-selected when absent |
| **Output** | `AgentResult` with a full scorecard: coefficients, train/test row counts, R2, RMSE, MAE |

| Intent | Model | Reports | Minimum data |
|---|---|---|---|
| `regression` | sklearn `LinearRegression` | R2, RMSE, MAE, coefficients | 20 complete rows |
| `classification` | `LogisticRegression` + `StandardScaler` | accuracy vs majority baseline, precision, recall, F1 | 20 rows, 2–20 classes |
| `forecast` | `numpy.polyfit` linear trend | slope, fit R2, projected points | 4 observations |

All three use a 25% test split at `random_state=42`, so the same question on the same data
gives the same score twice.

### Leakage defence

When the user names no features, the agent picks them. Auto-selection is where a data
platform quietly starts lying: include a column derived from the target and R2 goes to 0.99
while the model measures nothing at all. So before selecting, it drops any candidate
correlating with the target above `LEAKAGE`:

```python
candidates = [c for c in numeric_columns(frame) if c != target]
leaked = []
if target in numeric_columns(frame):
    for column in list(candidates):
        pair = frame[[column, target]].dropna()
        if len(pair) < 3:
            continue
        value = pair[column].corr(pair[target])
        if pd.notna(value) and abs(value) >= LEAKAGE:
            candidates.remove(column)
            leaked.append(column)
```

The docstring immediately above it admits what the check cannot catch:

> This check is pairwise, so it catches linear duplicates only. It cannot see a
> multiplicative identity such as `revenue = units * price`: neither factor is strongly
> correlated with the product on its own, yet together they reconstruct it exactly. That is
> why auto-selection always emits a caveat — a high R2 from features the user did not choose
> deserves a second look, not celebration.

The bluntness is enforced in the answer text too. A classifier that fails to beat the
majority-class baseline does not get a soft landing:

```python
caveats.append("Always predicting the most common class would score as well. "
               "That is a real finding about the data, not a model failure.")
```

Regression below R2 = 0.3 attaches: "Treat this as evidence against the relationship, not a
tuning problem."

**Failure mode:** the tools raise plain `ValueError` for guardrail violations — too few rows,
a single-valued target, more than 20 classes, a class with only one row. A `_compute`
wrapper converts those into `AnalysisError` so they surface as a 422 with a readable message
instead of a 500.

---

## Insight generation agent

`agents/insight_agent.py` · LLM optional

The only agent with two distinct jobs, and the only specialist the graph can reach twice in
one request.

| | |
|---|---|
| **Input — job 1** | `run(record, plan=None)` — answers "tell me about this data"; also the landing spot for `recover` |
| **Output — job 1** | `AgentResult`: row/column counts, dtype split, duplicates, gaps, strongest correlations |
| **Input — job 2** | `narrate(result, question, client)` — a result another agent already computed |
| **Output — job 2** | the same object, `answer` possibly rephrased, `narration_source` flipped to `"llm"` |

Job one is a dataset overview built from `tools/quality.missing_summary`,
`tools/quality.duplicate_summary`, and the correlation matrix. Job two is the second place a
model touches the pipeline, and it is fenced on three sides.

**Fence one — the model is handed finished numbers.** The prompt contains the question, the
intent, the verified data payload, the deterministic sentence, and any caveats it must
preserve. It is never asked to derive anything.

**Fence two — the payload is shrunk.** Bulky keys (`matrix`, `points`, `histogram`) are
dropped outright rather than truncated into the prompt, and long lists are cut to ten rows
with the original length recorded, so the model can see that truncation happened.

**Fence three — the sentence is checked before it is accepted.** Every number in the
narration must already exist in the verified result, within 1% for rounding. One invented
figure and the whole sentence is discarded:

```python
def _is_grounded(narration: str, result: AgentResult) -> bool:
    """Reject narration that introduces a figure absent from the verified result.

    The last line of defence behind the prompt: the model may phrase, never compute.
    """
    if not narration or len(narration) < 10:
        return False
    source = json.dumps(result.data, default=str) + " " + result.answer + " " + " ".join(result.caveats)
    allowed = [v for v in (_as_float(t) for t in _tokens(source)) if v is not None]
    for token in _tokens(narration):
        value = _as_float(token)
        if value is None:
            return False
        tolerance = max(abs(value) * ROUNDING_TOLERANCE, ROUNDING_TOLERANCE)
        if not any(abs(value - candidate) <= tolerance for candidate in allowed):
            return False
    return True
```

**Failure mode:** there is no failure path out of `narrate`. No client, an exception
mid-request, an ungrounded sentence, an empty reply — every one of them returns the original
result untouched, with `narration_source` still reading `"template"`.

---

## The tools the agents call

Agents hold no maths of their own. Everything lives under `app/tools/` as plain functions
taking a dataframe or series and returning primitives — which is what makes them testable
without an agent, a graph, or a model.

| Package | Function | Built on | Called by |
|---|---|---|---|
| `statistics` | `aggregate` | pandas groupby | statistical, pattern |
| `statistics` | `describe_numeric`, `independent_t_test` | pandas, scipy | EDA endpoints |
| `distribution` | `numeric_distribution` | pandas, scipy skew | statistical |
| `distribution` | `categorical_distribution` | pandas value_counts | EDA endpoints |
| `quality` | `iqr_outliers` | pandas quantiles | statistical |
| `quality` | `missing_summary`, `duplicate_summary` | pandas | insight |
| `quality` | `datatype_summary`, `datatype_issues` | pandas inference | EDA endpoints |
| `correlation` | `correlation_matrix`, `pair_relationship` | pandas corr | pattern, insight |
| `correlation` | `strength`, `direction` | the shared thresholds | pattern, insight, predictive |
| `prediction` | `train_regression` | sklearn LinearRegression | predictive |
| `prediction` | `train_classifier`, `majority_baseline` | sklearn LogisticRegression | predictive |
| `prediction` | `trend_forecast`, `naive_forecast` | numpy polyfit | predictive |
| `visualization` | bar, line, scatter, box, pie, histogram, heatmap | plotly express | visualization endpoints |
| `feature_engineering` | `standardize`, `one_hot_encode`, `datetime_parts`, … | pandas, sklearn | feature endpoints |

Every arrow points the same way: `agents -> tools`, never `agents -> services`. That is what
keeps the agent layer importable from a test without booting FastAPI.

## The LLM boundary

`llm/client.py` wraps two providers selected by the `LLM_PROVIDER` environment variable:
`ollama` for local, `cloudflare` for hosted Workers AI. It uses `urllib` only, so it adds no
dependency. Two details are worth knowing:

- **A circuit breaker.** After a connection failure the client refuses to retry for 30
  seconds. Without it, every question during an outage pays a fresh connection timeout
  before falling back.
- **Configuration errors skip the breaker.** A missing `CLOUDFLARE_ACCOUNT_ID` is reported
  immediately and does not trip the cooldown — waiting will never fix a blank setting, and
  the real cause is more useful to see.

Copy `.env.example` to `.env` and set `OLLAMA_MODEL` to a model you have pulled locally.
Prompts live in `llm/prompts/*.md`: `orchestrator.md` carries the routing contract with five
worked examples, `insight.md` the narration rules. `GET /api/ai/health` reports whether
routing and narration are available.

## One request, end to end

`POST /api/datasets/{id}/ai-analysis` with `{"question": "What are the top 5 products by
sales?"}`, on a dataset with `product` (categorical) and `sales` (numeric), no model
configured:

| Stage | What happens | State after |
|---|---|---|
| `understand` | `client is None`, so `build_plan` runs. `RANK_WORDS` matches "top", the `LIMIT` regex extracts 5. | plan = ranking |
| ↳ | `validate_plan` confirms `sales` is numeric and `product` categorical; sets `agent = owner("ranking")`. | rejected = [] |
| `delegate` | Writes one trace entry naming the specialist and the columns. | trace: 2 steps |
| `statistical` | `aggregate(frame, "sales", "sum", "product").nlargest(5, "sales")`, then the share calculation. | result set |
| ↳ | `after_compute` sees no error. | → narrate |
| `narrate` | `client is None` → returns the result untouched. | narration_source = template |

The trace array the UI renders as the hand-off trail, numbered at the end so it never
depends on node execution order:

```json
"trace": [
  {"step": 1, "stage": "understand", "agent": "language_agent",
   "detail": "Interpreted the question as 'ranking' using keyword routing."},
  {"step": 2, "stage": "delegate",   "agent": "language_agent",
   "detail": "Delegated to the statistical agent with product, sales."},
  {"step": 3, "stage": "compute",    "agent": "statistical_agent",
   "detail": "Computed the ranking result with pandas."},
  {"step": 4, "stage": "narrate",    "agent": "insight_agent",
   "detail": "Used the deterministic explanation."}
]
```

Had the statistical agent raised — say `sales` turned out to be entirely non-finite — step 3
would read "Could not complete that analysis: …", a fifth `recover` step would appear, and
the response would carry a dataset summary plus the caveat explaining the substitution. The
client still gets 200.

## Adding a sixth agent

1. Write the class: subclass `Agent`, declare `skills`, implement `handlers()` returning one
   callable per intent.
2. Add one line to `build_agents()` in `agents/registry.py`.
3. Optionally add keyword rules to `agents/fallback.py` so the new intents are reachable
   without a model.

Nothing else changes. `INTENT_OWNERS`, `SKILLS`, `VALID_INTENTS`, and the planner prompt all
rebuild themselves from the skill declarations at import; and because `SPECIALIST_NODES` is
derived from the registry rather than hand-listed, the graph grows its node and both
conditional edges automatically:

```python
# One node per computing specialist. The keys are both node names and the values
# choose_specialist returns, so they must match the registry's agent keys.
SPECIALIST_NODES: tuple[str, ...] = tuple(AGENTS)
```
