# API

Interactive OpenAPI documentation is available at `/docs` while the backend runs. All paths are prefixed `/api`.

## System

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/ai/health` | Whether LLM routing and narration are available. Analysis works either way. |

## Data source

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/datasets/upload` | Multipart CSV, XLSX, or XLS upload (100 MB limit) |
| `POST` | `/datasets/database` | Load via a read-only `SELECT` against PostgreSQL or MySQL |
| `GET` | `/datasets` | List loaded datasets |
| `GET` | `/datasets/{id}?limit=20` | Dataset summary with a row preview |

## Exploratory analysis

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/datasets/{id}/eda/overview` | Row/column counts, memory, per-column profile |
| `GET` | `/datasets/{id}/eda/statistics` | Numeric stats, categorical stats, per-column histograms |
| `GET` | `/datasets/{id}/eda/quality` | Missing values, duplicates, IQR outliers, datatype issues, score |
| `GET` | `/datasets/{id}/eda/correlation?method=pearson` | Matrix plus pairs at \|r\| ≥ 0.7. Accepts `pearson`, `spearman`, `kendall`. |
| `GET` | `/datasets/{id}/eda/distribution?column=X` | Numeric: histogram, box quartiles, interpretation. Categorical: counts and proportions. |

## Feature engineering

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/datasets/{id}/features` | Calculated column from an arithmetic expression |
| `POST` | `/datasets/{id}/features/transform` | `standardize`, `min_max`, `log`, `bin`, `one_hot`, `frequency`, `datetime_parts` |

Expressions are parsed into a restricted AST supporting column names, numbers, and `+ - * / ** %`. Python's `eval` is never used.

## AI analysis

`POST /datasets/{id}/ai-analysis` with `{"question": "..."}` returns:

```json
{
  "agent": "statistical_agent",
  "intent": "ranking",
  "answer": "The top 5 product values account for 62.4% of total revenue…",
  "data": { "group": "product", "metric": "revenue", "rows": [] },
  "suggested_chart": "bar",
  "verified": true,
  "narration_source": "template",
  "trace": [{ "step": 1, "stage": "understand", "agent": "orchestrator_agent", "detail": "…" }]
}
```

`verified` is `true` when every figure in `data` came from pandas. `narration_source` is `"llm"` when a model phrased the answer and `"template"` when the deterministic sentence was used.

## Visualization

`POST /datasets/{id}/charts` accepts `chart_type` (`bar`, `line`, `scatter`, `histogram`, `box`, `pie`, `heatmap`), `x`, `y`, `aggregation` (`none`, `sum`, `mean`, `count`, `min`, `max`), `color`, and `title`. Returns a Plotly figure as JSON.

## Reports

`POST /datasets/{id}/reports` accepts `title`, `sections`, `format` (`html`, `markdown`, `pdf`), and `insights`. Returns the file as an attachment.

Sections: `executive_summary`, `overview`, `quality`, `statistics`, `correlation`, `distribution`, `insights`. They render in that order regardless of request order.

## Errors

| Status | Meaning |
|---|---|
| `404` | `DatasetNotFoundError` — unknown dataset id |
| `422` | `AnalysisError` — the request was understood but cannot be computed (unknown column, unusable expression, dataset too small for a model) |

Both carry a human-readable `detail` string intended for display.
