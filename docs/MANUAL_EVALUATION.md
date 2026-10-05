# Manual evaluation

## Run locally (PowerShell)

From `E:\laya_decision_service`:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd E:\laya_decision_service\frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Node 22.12+ is supported. Backend startup loads and
warms up the existing model; wait for startup completion. Existing application
commands and imports remain supported. `npm run build` produces `frontend/dist`;
`npm run preview` serves it locally on port 4173 with the same API proxy.

Add `GROQ_API_KEY=your-key` to the existing backend `.env` without overwriting
other settings. `.env.example` lists optional settings. Never put secrets in
frontend files or `VITE_*` variables. OS environment values override `.env`.
Settings are read per request; refresh the console configuration after edits.

Defaults: provider `groq`, model `openai/gpt-oss-120b`, strict `json_schema`,
60-second HTTP timeout, 2048 output tokens, task `gtm_intent`. These are starting
configuration choices, not measured model recommendations. A different model
must support the selected output format. For another compatible API, set
`LLM_PROVIDER=openai_compatible`, `LLM_MODEL`, `LLM_BASE_URL`, and optional
`LLM_API_KEY`. `json_object` is available for servers without strict schemas;
responses are still validated locally.

The frontend proxies `/api` to port 8000. Optional `BACKEND_URL` changes its proxy
target; `VITE_API_BASE_URL` can configure a public API URL. Neither is a key.

## Contracts and API

`POST /evaluate` accepts `query` plus optional `request_id`, `context`,
`structured_input` (JSON object) and `criterion` (`id`, `instructions`, `choices`).
The default criterion classifies the query into the six existing GTM intents.
The console uses that default; custom criteria are currently API-only. Set
`EVALUATION_TASK=custom` to require an explicit criterion in every API request.

Example request, not a recorded model result:

```json
{"query":"Find IT services companies in India"}
```

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/evaluate `
  -ContentType 'application/json' `
  -Body '{"query":"Find IT services companies in India"}'
```

The response contains `request_id`, `query`, `evaluated_at`, `semantic_input`,
`laya`, `llm`, and `comparison`. Each model result contains:

| Fields | Meaning |
| --- | --- |
| evaluator, provider, model, status | Model identity and success/error status |
| decision, confidence, confidence_source | Selected label and nullable score with provenance |
| probabilities | Original Laya distribution when available; null for LLM |
| reasoning, evidence | Nullable LLM rationale and unverified input quotations |
| latency_ms, queue_ms | Adapter duration and separately recorded Laya lock wait |
| input_tokens, output_tokens | Provider-reported usage when available |
| cost_usd, cost_source | Optional configured estimate; null when unavailable |
| raw_model_output | Original model response where serializable; safe diagnostic otherwise |
| input_fingerprint | SHA256 of the shared semantic input |
| error | Nullable structured code, message and retryable flag |

Both adapters receive identical query, context, structured input, criterion,
choice menu and semantic instructions. The LLM receives additional output-format
instructions. Request IDs are excluded from model inputs. The shared input and
raw results are inspectable in the UI. No planner corrections are applied.

The Laya adapter preserves existing confidence parsing and probabilities.
The LLM score is self-reported, not a calibrated probability. Neither is accuracy.
No rationale or evidence is invented for Laya when it does not provide them.
The two latency values measure their respective adapter calls, including remote
network time for the LLM; Laya queue wait is separate. They are not benchmark
measurements. Parallel execution does not make the model architectures equivalent.

Comparison formulas when both models succeed:

- `same_decision`: exact label equality.
- `confidence_difference`: LLM minus Laya, using fractions; null if either is missing.
- `latency_difference_ms`: LLM minus Laya.
- `latency_ratio`: Laya divided by LLM; null for a zero/missing denominator.

If either model fails, comparison values are null and the other result remains
available. Invalid requests return 422. Model/configuration failures appear as
structured per-model errors in a 200 response. Missing Groq configuration does
not fabricate an LLM answer. `GET /evaluate/config` exposes safe readiness and
configuration details without API keys. Swagger provides the full schemas.

Cost is null unless usage and both configured per-million rates are available.
Configured rates produce an estimate, not an invoice; prices are not hard-coded.
LLM evidence is displayed for human inspection without verification.

## UI and scope

The console offers query examples, optional context and JSON input, side-by-side
results, Laya probability bars, latency/usage/cost, raw JSON and last-30-request
history. History is in browser memory and disappears on reload. There is no
database, automatic dataset collection or file export. Stopping the browser wait
does not guarantee cancellation of model work already running.

The manual Laya adapter uses a thread and a bounded lock wait. This lock does
not cover legacy endpoints; avoid overlapping legacy/manual inference during
manual inspection. Existing startup model configuration and legacy handlers,
regexes, thresholds, workflows and confidence calculations are preserved.

No datasets, scoring engine, evidence verifier, confidence calibration,
benchmark runner, restored tests or deployment setup are included.

## Verification and next phase

Completed before handoff: React production build, backend import/route loading,
cached local model warmup and browser configuration/empty-state loading. Groq
was not configured during these checks; a live Groq result and an end-to-end
two-model evaluation have not been verified. Further browser/testing work was
stopped at the user's request. No model results or quality claims are fabricated.

Next: configure the Groq key, manually submit representative queries and inspect
both raw results. Agree the lead/criterion semantics and human review criteria
before adding approved tests, benchmarking, evidence checks, calibration or
score aggregation in a separate phase.
