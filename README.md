# Oppora Decision Service

**Current phase: an Oppora-style LLM baseline on DeepSeek, with every model call and decision recorded.** Hosted JEV (TypeSafe System One) is the candidate for selected bounded decisions. One decision, lead filter-and-score, can already be run with JEV as an opt-in per run; DeepSeek remains the default and JEV is not yet an approved replacement. Local Laya execution has been retired.

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

Open [the app](http://127.0.0.1:5173). The existing backend `.env` supplies LLM settings. Preserve it; `.env.example` is a reference, not a replacement. When `LLM_PROVIDER` is blank and `DEEPSEEK_API_KEY` is set, DeepSeek is used with `DEEPSEEK_MODEL` and `DEEPSEEK_BASE_URL`. The JEV key stored there is used only when a scoring run chooses JEV. Keys must never enter frontend files or Git.

**Find leads** retains the existing LLM search/scoring workflow, with an LLM/JEV choice for the scoring step. **Decision Lab** shows one LLM result per manually submitted request. Neither opening the UI nor reading configuration starts model inference.

## Decision models: LLM and JEV

Only the **lead filter-and-score** step offers a choice. `POST /v1/lead-scoring/runs` and `POST /v1/lead-scoring/lists/{list_id}/score` accept `decision_model: "llm"` (default) or `"jev"`; the scoring screen has the same toggle. Search interpretation and explanations always use the LLM, because JEV does not generate text.

| | LLM path (default) | JEV path (opt-in) |
|---|---|---|
| Code | `scoring/batch.py`, `scoring/prompts/lead_filter_oppora_v2.txt` | `scoring/jev_scoring.py`, `engines/jev_engine.py` |
| Calls | One prompt per company batch | One `/v1/systemone` query per lead, up to `JEV_CONCURRENCY` at once |
| Model output | Matching lead IDs with 0–100 scores | A probability per typed question |
| Who selects | The LLM | Code: every requirement gate must reach `JEV_MATCH_THRESHOLD` (default 0.5) |
| Score | Written by the LLM | Computed by code from JEV's 4-level fit answer |
| Why a lead failed | Not stated | The weakest requirement and each gate's probability |

On the JEV path, code builds the questions: `build_questions` turns each filter the target actually uses (role, location, excluded location, department, seniority, experience) into one yes/no question, plus an overall fit rating. JEV only answers; code decides. JEV failures mark the lead as failed and there is no automatic LLM fallback yet. `JEV_MODEL` is pinned (`jev-1.13.0`) so the threshold keeps its meaning.

**Evidence so far (19 October 2026, local prototype):** both paths were run on 200 hand-labelled people for one sales-leadership target in the US, Canada or UK. Accuracy was similar (LLM 99.4–100%, JEV 98.9–99.4%). JEV made no wrong inclusions but missed 1–2 true matches, gave the same decision on 99.5% of re-runs (LLM 97–97.5%), and selected far fewer borderline people (4 of 19 versus 12–15). This is one target, labelled by one reviewer, without department, seniority or experience data, so it does not establish general quality. Saved results are in the ignored `data/eval_*.json`; the internal report, including speed and cost estimates, is in the ignored `docs/reports/` and is shared directly rather than through Git. See [SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) for the next steps.

## AI Admin: where decisions happen

Every LLM and JEV request is recorded in an AI ledger (`llm_calls` table in `data/lead_scoring.sqlite3`) with its decision point, provider/model, tokens (including cached input), estimated cost, latency and a count of what it decided. Full prompts stay in the run, search or target that owns the call.

- `GET /v1/ai-admin/decisions` — every decision point, whether an LLM or code makes it, its Oppora equivalent and our current view of Jev fit.
- `GET /v1/ai-admin/usage?range=last_7_days` — calls, tokens, cost and latency per decision point (`last_24_hours`, `last_7_days`, `last_30_days`, `all_time`).
- `GET /v1/ai-admin/calls?decision_point=lead_filter_score&limit=50` — recent ledger entries.

Set `LLM_INPUT_COST_PER_MILLION`, `LLM_CACHED_INPUT_COST_PER_MILLION` and `LLM_OUTPUT_COST_PER_MILLION` to see estimated cost; without them cost is left blank rather than guessed.

## Folder responsibilities

| Folder | Keep it for |
|---|---|
| `app/` | Startup and API routes |
| `core/`, `models/` | Configuration and schemas |
| `engines/`, `evaluators/` | LLM and JEV transport and bounded decision interface |
| `scoring/` | Retrieval, criteria, rules, scores and local run storage |
| `frontend/` | Lead UI and Decision Lab |
| `datasets/` | Existing synthetic/reference data |
| `docs/` | Current usage and production migration |
| `scripts/` | Optional existing utilities; nothing runs automatically |
| `archive/` | Retired Laya/planner/comparison source ZIP |
| `venv/`, `data/` | Ignored local dependencies and runtime data |

Cleanup archives 18 obsolete source files and backs up changed originals under `.backups/`. It preserves `.env`, datasets, dependency manifests, the environment and stored runs. Public scoring endpoints are unchanged. The manual `/evaluate` response now contains only `llm` and shared request metadata; retired `laya`/`comparison` fields are removed together with their UI.

No tests, builds, benchmarks, live-key checks or provider calls were run for these changes, at the user's request. Runtime behavior remains unverified. This local SQLite/background-task application is not yet production-ready; do not expose it publicly or claim 10,000-user capacity.
