# Datum — Data Analysis Platform

Datum is a full-stack analytics workspace for a data science team. One loaded dataset stays active across data profiling, deterministic EDA, a multi-agent AI analyst, interactive charts, feature engineering, and report export.

## The five modules

**1. Data source** — CSV, XLSX, and XLS upload up to 100 MB, or PostgreSQL/MySQL through a read-only `SELECT`. Credentials are used for the request and never stored.

**2. Exploratory analysis** — six tabs:
- *Overview* — size, memory, and a per-column profile of type, completeness, and cardinality
- *Statistics* — numeric summaries, categorical breakdowns, and a histogram per numeric column
- *Data quality* — missing values, duplicate rows, IQR outliers, datatype consistency, and a 0–100 score
- *Correlation* — Pearson/Spearman/Kendall matrix as a heatmap, plus every pair at |r| ≥ 0.7
- *Distribution* — histogram, box plot, and interpretation for numeric columns; bar chart and pie proportions for categorical ones
- *Feature engineering* — calculated columns from arithmetic, plus standardize, min–max, log, quantile bins, one-hot, frequency encoding, and date-part extraction

**3. AI analysis** — ask in plain language. Five agents cooperate: an orchestrator reads the question and delegates; statistical, pattern, and predictive agents compute; an insight agent explains. Each answer shows the agent trail that produced it.

**4. Interactive visualization** — bar, line, scatter, histogram, box, pie, and correlation heatmap, with selectable X, Y, aggregation, group-by colour, and title.

**5. Automated reports** — choose your sections and export as **HTML, PDF, or Markdown**.

## How the AI works

> **The language model routes and explains. Pandas computes. Every figure originates from a deterministic tool.**

The orchestrator sends the model your question and the column names — never row values — and asks for a routing plan. That plan is validated against the real dataframe before anything runs: a column the model invented is discarded. A specialist then computes the answer in pandas, and the insight agent is given the finished numbers to phrase. If it states a figure that is not in the verified result, its wording is thrown away and the deterministic sentence stands.

**Two providers, picked by `LLM_PROVIDER`:** `ollama` runs locally and is the official service; `cloudflare` uses Cloudflare Workers AI and is there for testing. One is active at a time — there is no automatic failover between them.

**Both are optional.** With neither reachable, questions route through a keyword classifier and answers use deterministic explanations. Every number is still computed and still marked `verified`. `GET /api/ai/health` reports which mode is live, and the UI says so plainly.

## Run locally

Backend (PowerShell):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend, in a second terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open http://localhost:5173 and upload [sample-data/sales.csv](sample-data/sales.csv) — 263 rows with deliberate missing values, duplicates, outliers, and a strong age/income correlation, so every tab has something to show. The API is at http://localhost:8000/docs.

For the AI agents, copy `.env.example` to `.env` (and `backend/.env.example` to `backend/.env` when running the backend directly). For Ollama, set `OLLAMA_MODEL` to a model you have pulled; with Docker Desktop use `OLLAMA_BASE_URL=http://host.docker.internal:11434`. To test against Cloudflare instead, set `LLM_PROVIDER=cloudflare` and fill in `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`.

Alternatively `docker compose up --build`, then open http://localhost:3000.

## Verify

```powershell
cd backend
python -m pytest tests -q

cd ..\frontend
npm.cmd run build
```

## Project organization

Backend layers run `api/routes → services → graphs → agents → tools`, with `data`, `database`, `storage`, `reports`, `utils`, and `core` alongside. Frontend pages in `app/` compose `components/`, calling typed `services/` clients over a shared `store/`.

**Start with [docs/system-overview.md](docs/system-overview.md)** — a full walkthrough of the architecture, the technology used for each component, and the design decisions behind them. Then:

- [docs/architecture.md](docs/architecture.md) — layer dependency rules
- [docs/agents.md](docs/agents.md) — the five-agent pipeline
- [docs/api.md](docs/api.md) — every endpoint
- [docs/database.md](docs/database.md) — SQL sources

## Production roadmap

The MVP keeps datasets in process memory, so a restart clears them and it runs single-process. Production should add authenticated workspaces, encrypted secret management, object storage, PostgreSQL metadata, Redis/job workers, row and column limits, query timeouts, audit logs, and persisted chart and report artifacts.
