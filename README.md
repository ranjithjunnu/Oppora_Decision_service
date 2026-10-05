# Laya decision service

Local PyTorch Laya inference and GTM workflow planning, organized for future
Oppora.ai decision evaluation. The service returns choice predictions and
workflow proposals. Model behavior, confidence calculations, thresholds,
regexes, workflow templates and API response contracts are preserved.

## Run the service

From PowerShell in `E:\laya_decision_service`, using the existing environment:

```powershell
.\venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

The explicit application path also works:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`python app.py` remains compatible. Restart after code changes; the normal
command does not enable reload. Swagger: <http://127.0.0.1:8000/docs>, API 1.1.0.
For a fresh environment, create `venv` and install `requirements.txt` first.
The manual console adds HTTPX and python-dotenv dependencies. This uses PyTorch Laya, not MLX. Startup loads and
warms up `typed-decisions`; failed warmup prevents startup. Initial provisioning
may download model weights. Existing routes use local inference. The new manual evaluation route also calls the configured Groq model when a key is provided.

| Endpoint | Existing behavior |
| --- | --- |
| GET `/health` | Model and engine readiness |
| POST `/decision` | Raw Laya choices, model scores and inference latency |
| POST `/agent/plan` | GTM plan, sources, original predictions, status and clarification |

Example body for `/agent/plan`:

```json
{"prompt": "Find IT services companies in India"}
```

Check `status == "planned"` before using steps. Scores are nullable and are not
verified accuracy. Rules and fixed mappings have null confidence. Without an
explicit intent rule, the existing 0.5 threshold governs clarification.
`context` is accepted but unused. Tools are proposed, not executed; the scoring
tool label does not compute a lead score.

## Developer commands and compatibility

```powershell
.\venv\Scripts\python.exe -m scripts.demo_client
.\venv\Scripts\python.exe -m scripts.choice_probe
```

The demo runs six requests directly through the planner. The probe prints one
raw Router prediction. Both run real local inference; neither is an automated
test. Existing `python demo_client.py` and `python test_choice.py` commands work
through compatibility entry points. The latter retains import-time execution:
importing it loads a model. Its name does not imply an automated test suite.


Existing `engine`, `gtm_agent`, `contracts` and `taxonomy` imports remain
available. New code should use the canonical packages in PROJECT_MAP.md.
Engine/planner aliases share singleton state. `taxonomy` is now a package
exporting the original catalog names. No deleted regression tests were restored;
there is currently no automated regression suite in this working tree.

## Data and documentation

The four existing dataset JSON files are preserved byte-for-byte. Reference
inputs live in `datasets/reference/`, and labelled fixtures in
`datasets/benchmark/legacy/`. The service does not load them at runtime. No
replacement datasets were generated. Dataset paths changed; external/manual
readers should use the migration table in the dataset README.

- [ARCHITECTURE.md](ARCHITECTURE.md): current flow, boundaries, limitations and planned layers.
- [PROJECT_MAP.md](PROJECT_MAP.md): tree, file migration, dependencies and status.
- [BENCHMARK.md](BENCHMARK.md): future design only; no runner exists.
- [datasets/README.md](datasets/README.md): classification and provenance.
- [sample_responses.json](sample_responses.json): unchanged historical responses, not a fresh benchmark.
- [Historical diagram](docs/architecture-legacy.png): preserved image; current source locations are documented in the project map.

## Manual evaluation console

The React console compares one query using the existing Laya engine and a
configurable Groq LLM. Both receive the same decision task and input. The default
task uses the six existing GTM intent labels without planner corrections.

See [Manual evaluation guide](docs/MANUAL_EVALUATION.md) for setup, API contracts,
file responsibilities, limitations and the next phase.

New routes: `GET /evaluate/config` and `POST /evaluate`.
Evidence verification, calibration, deterministic scoring, benchmarking,
persistent storage and deployment remain future work.
