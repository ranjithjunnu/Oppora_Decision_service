# Oppora Decision Service

**Current phase: an Oppora-style LLM baseline on DeepSeek, with every LLM call and decision recorded.** Hosted JEV is the future candidate for selected decisions. It is not connected or called in this phase. Local Laya execution has been retired.

Start with [SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) for our goal and ordered changes. Use [OPPORA_LEAD_SCORING_FLOW.md](docs/OPPORA_LEAD_SCORING_FLOW.md) for the lead workflow and [MANUAL_EVALUATION.md](docs/MANUAL_EVALUATION.md) for Decision Lab.

## Local startup — when ready

Python 3.11+ and a Node version compatible with the locked Vite dependency are needed. The existing `venv/` remains local tooling. Install declared dependencies only when needed; no dependencies were upgraded during cleanup.

```powershell
cd D:\Oppora_Decision_service-main
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, after installing the frontend dependencies with `npm ci` when needed:

```powershell
cd D:\Oppora_Decision_service-main\frontend
npm run dev
```

Open [the app](http://127.0.0.1:5173). The existing backend `.env` supplies LLM settings. Preserve it; `.env.example` is a reference, not a replacement. When `LLM_PROVIDER` is blank and `DEEPSEEK_API_KEY` is set, DeepSeek is used with `DEEPSEEK_MODEL` and `DEEPSEEK_BASE_URL`. The JEV key stored there is unused. Keys must never enter frontend files or Git.

**Find leads** retains the existing LLM search/scoring workflow. **Decision Lab** shows one LLM result per manually submitted request. Neither opening the UI nor reading configuration starts model inference.

## AI Admin: where decisions happen

Every LLM request is recorded in an AI ledger (`llm_calls` table in `data/lead_scoring.sqlite3`) with its decision point, provider/model, tokens (including cached input), estimated cost, latency and a count of what it decided. Full prompts stay in the run, search or target that owns the call.

- `GET /v1/ai-admin/decisions` — every decision point, whether an LLM or code makes it, its Oppora equivalent and our current view of Jev fit.
- `GET /v1/ai-admin/usage?range=last_7_days` — calls, tokens, cost and latency per decision point (`last_24_hours`, `last_7_days`, `last_30_days`, `all_time`).
- `GET /v1/ai-admin/calls?decision_point=lead_filter_score&limit=50` — recent ledger entries.

Set `LLM_INPUT_COST_PER_MILLION`, `LLM_CACHED_INPUT_COST_PER_MILLION` and `LLM_OUTPUT_COST_PER_MILLION` to see estimated cost; without them cost is left blank rather than guessed.

## Folder responsibilities

| Folder | Keep it for |
|---|---|
| `app/` | Startup and API routes |
| `core/`, `models/` | Configuration and schemas |
| `engines/`, `evaluators/` | LLM transport and bounded decision interface |
| `scoring/` | Retrieval, criteria, rules, scores and local run storage |
| `frontend/` | Lead UI and Decision Lab |
| `datasets/` | Existing synthetic/reference data |
| `docs/` | Current usage and production migration |
| `scripts/` | Optional existing utilities; nothing runs automatically |
| `archive/` | Retired Laya/planner/comparison source ZIP |
| `venv/`, `data/` | Ignored local dependencies and runtime data |

Cleanup archives 18 obsolete source files and backs up changed originals under `.backups/`. It preserves `.env`, datasets, dependency manifests, the environment and stored runs. Public scoring endpoints are unchanged. The manual `/evaluate` response now contains only `llm` and shared request metadata; retired `laya`/`comparison` fields are removed together with their UI.

No tests, builds, benchmarks, live-key checks or provider calls were run for these changes, at the user's request. Runtime behavior remains unverified. This local SQLite/background-task application is not yet production-ready; do not expose it publicly or claim 10,000-user capacity.
