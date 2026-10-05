# Project map

Status: existing functionality reorganized. Future evaluation/scoring layers are
documented, not implemented. No deleted files or replacement datasets were added.

## Final source tree

```text
laya_decision_service/
├── app/
│   ├── __init__.py              # Old app:app export
│   ├── main.py                  # FastAPI construction and startup
│   └── api/
│       ├── __init__.py
│       ├── health.py
│       ├── decision.py
│       └── planning.py
├── engines/
│   ├── __init__.py
│   └── laya_engine.py
├── agents/
│   ├── __init__.py
│   └── gtm_agent.py
├── models/
│   ├── __init__.py
│   ├── decision.py
│   ├── planning.py
│   └── health.py
├── taxonomy/
│   ├── __init__.py              # Original catalog exports
│   ├── titles.py
│   ├── industries.py
│   └── geography.py
├── workflows/
│   ├── __init__.py
│   └── catalog.py
├── scripts/
│   ├── __init__.py
│   ├── demo_client.py
│   └── choice_probe.py
├── datasets/
│   ├── README.md
│   ├── reference/
│   │   ├── company_directory.json
│   │   └── _real_anchors.json
│   └── benchmark/
│       └── legacy/
│           ├── classification.json
│           └── lead_scoring.json
├── docs/
│   └── architecture-legacy.png
├── app.py                      # Compatibility script launcher
├── engine.py                   # Compatibility module alias
├── gtm_agent.py                # Compatibility module alias
├── contracts.py                # Compatibility class exports
├── demo_client.py              # Compatibility demo launcher/exports
├── test_choice.py              # Compatibility manual-probe entry point
├── .gitignore
├── requirements.txt
├── sample_responses.json
├── README.md
├── ARCHITECTURE.md
├── BENCHMARK.md
└── PROJECT_MAP.md
```

Existing `.env`, `.git/`, `venv/` and ignored `__pycache__/` are unchanged and omitted
from the source tree. Package initializers identify existing packages; they are
not speculative feature stubs.

## Component -> responsibility -> dependencies -> status -> future role

| Component | Responsibility | Dependencies | Status | Future role |
| --- | --- | --- | --- | --- |
| API application | Construction, middleware, lifecycle and routing | FastAPI, existing routers, engine/planner startup | Implemented | Add evaluation routes after services exist |
| API handlers | Existing HTTP validation and responses | Models, engine or agent | Implemented | Transport boundary; no model/scoring logic |
| Laya engine | Local prediction, warmup, parsing and timing | Laya, models/decision | Implemented | Reused by a future Laya evaluator; remains an engine |
| GTM agent | Classifications, explicit rules and workflow proposals | Engine, contracts, target taxonomy, workflow catalog | Implemented | Remain a separate planning component |
| Decision/planning/health models | Existing request/response validation | Pydantic; planning uses decision contracts | Implemented | Add separate evaluation models after agreement |
| Target taxonomy | Current role, industry and geography menus/patterns | Literal catalogs | Implemented | Extend only through intentional behavior changes |
| Workflow catalog | GTM intents, tool descriptions and ordered blueprints | Literal catalogs | Implemented | Planning policy; not an ICP or scoring policy |
| Developer scripts | In-process demo and manual raw prediction | Agent/models or Laya directly | Implemented | Keep separate from future automated tests |
| Reference data | Unlabelled input pool and reference observations | Existing source provenance | Preserved, relocated | Candidate inputs after eligibility review |
| Legacy fixtures | Existing labelled task examples | Original task-specific label conventions | Preserved, relocated | Reviewed adapters before common benchmarking |
| Evaluators/evidence/benchmark/scoring/UI | Future evaluation pipeline | Contracts and policies to agree | Planned in documentation only | See ARCHITECTURE.md and BENCHMARK.md |

Canonical imports do not depend on root wrappers. Compatibility exports retain
the old module entry points without duplicating their implementations.

## Every existing file: destination and reason

| Original file | Current destination | Treatment and reason |
| --- | --- | --- |
| app.py | app/main.py; app/api/health.py, decision.py, planning.py | Split construction/startup from HTTP handlers; root launcher retained |
| engine.py | engines/laya_engine.py | Move inference responsibility intact; root alias preserves imports/state |
| gtm_agent.py | agents/gtm_agent.py | Move planning intact; root alias preserves imports/state |
| contracts.py | models/decision.py, planning.py, health.py | Split by actual existing contract role; root re-exports retained |
| taxonomy.py | taxonomy/titles.py, industries.py, geography.py; workflows/catalog.py | Separate target categories from GTM workflow policy; taxonomy package retains old exports |
| demo_client.py | scripts/demo_client.py | Developer demo, not an HTTP integration test; root launcher retained |
| test_choice.py | scripts/choice_probe.py | Rename canonical implementation to identify a manual probe; root compatibility entry retained |
| architecture.png | docs/architecture-legacy.png | Preserve the historical image and identify its status |
| sample_responses.json | Same root path | Preserve historical responses byte-for-byte |
| requirements.txt | Same root path | Preserve dependency declarations byte-for-byte |
| .gitignore | Same root path | Preserve ignore rules byte-for-byte |
| .env | Same root path | Preserve existing local file; no configuration changes |
| README.md | Same root path | Update commands, compatibility, data paths and current scope |
| ARCHITECTURE.md | Same root path | Document implemented versus planned boundaries and preserved limitations |
| datasets/README.md | Same path | Document inspected provenance, classification and migration |
| datasets/source/company_directory.json | datasets/reference/company_directory.json | Mixed unlabelled input pool; bytes preserved |
| datasets/source/_real_anchors.json | datasets/reference/_real_anchors.json | Reference observations explicitly not a test set; bytes preserved |
| datasets/source/lead_scoring.json | datasets/benchmark/legacy/lead_scoring.json | Existing task-level labelled fixtures; bytes preserved |
| datasets/source/classification.json | datasets/benchmark/legacy/classification.json | Existing labelled classification fixtures; bytes preserved |

All 19 original files have a recorded destination above. BENCHMARK.md and this map are new documentation requested
for this phase. New Python files only contain relocated code, compatibility
exports, existing router wiring or package documentation.

## Preserved behavior and verification scope

Existing startup commands, public project imports, HTTP paths, generated API
schema, handler semantics, model default, warmup, confidence calculation,
threshold, regexes, fixed workflows and class validation are preserved. Engine
and planner singleton state is shared between old and new module imports.

Organization checks compare executable source definitions, complete OpenAPI and
middleware configuration, import identities and dataset/asset hashes against a
snapshot of the files actually present before restructuring. These checks do
not constitute a regression suite, model benchmark or calibration analysis.
Deleted tests remain deleted; no test suite is added for this phase.

Dataset file paths change as shown above; external/manual readers must update
those paths. Compatibility promises cover the existing application commands
and Python imports, not arbitrary hard-coded old data or image paths.

## Problems and next phase

The existing planner ignores context and has known scope/negation limitations;
tool selection is fixed and a scoring label does not supply a scorer. Raw
prediction validation, inference concurrency and operational boundaries also
need deliberate later work. These are documented in ARCHITECTURE.md and have
not been silently changed.

The manual evaluation phase now adds a shared decision contract, Laya/Groq
adapters and a React console. The organization migration table above records
the earlier phase. See docs/MANUAL_EVALUATION.md for the current additions and
next steps; existing datasets and legacy planner behavior remain unchanged.

Do not change raw dataset contents, historical sample responses, model settings,
confidence policy, regexes or workflow behavior solely for organization.
Previously deleted files and speculative future implementations remain absent.

## Manual evaluation additions

```text
core/config.py                 Backend-only environment configuration
models/evaluation.py           Shared request, case, result and comparison contracts
engines/llm_engine.py           Replaceable compatible HTTP transport
evaluators/base.py              Evaluator interface and common input preparation
evaluators/laya.py              Existing-engine adapter and raw-output capture
evaluators/llm.py               Structured LLM response normalization
evaluators/service.py           Concurrent evaluation and comparison
app/api/evaluation.py           /evaluate and /evaluate/config
frontend/                      React/TypeScript console and Vite proxy
docs/MANUAL_EVALUATION.md        Setup, contracts and implementation boundaries
.env.example                   Backend configuration template; no credentials
```

Modified: app/main.py registers the new router; engines/laya_engine.py adds
an optional raw-output observer; requirements.txt adds HTTPX/python-dotenv;
.gitignore excludes frontend artifacts and local environment files; README.md,
ARCHITECTURE.md and this map describe the current phase. No existing source
files are relocated in this phase. Full applied file list: docs/MANUAL_EVALUATION_FILES.md.
