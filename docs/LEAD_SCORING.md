# LLM-first AI Lead Scoring

> Historical v1 design. The current implementation and changed scoring policy are
> documented in [Lead scoring v2](LEAD_SCORING_V2.md).

Current phase: build and validate AI Lead Scoring using the configured larger
LLM. Laya/Jev integration is deferred until this baseline establishes what the
product needs and which decisions might benefit from a smaller model.

## Working flow

1. Enter ICP criteria or use the configured LLM to generate an editable draft.
2. Review the criteria and supply one lead's known facts.
3. The UI submits `{lead, profile, as_of}` to `POST /v1/scores`.
4. Python evaluates exact fields with rules. Missing facts remain unknown.
5. All semantic criteria with supplied text are sent together in one LLM request.
6. Validate JSON, exact criterion IDs, outcome labels, source IDs and quoted text.
7. Aggregate accepted outcomes and show scores, factors, evidence and model usage.

Only the semantic requirement, criterion ID, source-field ID and that field's
text are sent for scoring. Other lead fields, credentials, datasets and CRM
records are not added to this request. Draft generation sends the ICP description
and supported field catalog. No third-party source or CRM data is fetched.

The model returns match, partial, miss or unknown, with a short reason and a
verbatim quote for known outcomes. A missing, empty, invented or wrong-field
quote downgrades the factor to unknown. Quote attribution is checked; semantic
support and model explanations are not independently verified. No confidence
percentage is fabricated for the LLM.

Malformed, duplicate/missing/extra criterion IDs, truncated responses, provider
errors and timeouts make the semantic factors fail and suppress numeric scores.
There is no fallback to Laya and no automatic retry. Missing provider configuration
returns HTTP 503 for requests containing semantic criteria. Rules-only requests
remain possible without a provider. Stopping the browser wait does not guarantee
cancellation of work already accepted by the provider.

## Scoring policy: lead-score-v1

The provider migration preserves the existing arithmetic and product policy:

- Weights: high 3, medium 2, low 1. Hard requirements have zero numeric weight.
- Outcomes: match 1, partial 0.5, miss 0, unknown 0.5.
- Each axis is `100 × sum(weight × value) / sum(weight)`.
- Known intent values decay with a 30-day half-life from their observation date.
- Priority blends fit and intent using `alpha_fit` (default 0.7); without known
  intent it uses fit alone. Scores round once using half-up rounding.
- Coverage is known non-hard weight divided by all non-hard weight. Default
  minimum coverage is 0.5. Insufficient coverage or an unresolved hard gate
  suppresses scores, unless another hard gate already proves disqualification.
- Hard misses set `band=disqualified` without replacing arithmetic scores.
  Consumers must honor disqualification. Errors suppress numeric scores.
- Default hot/warm cutoffs are 80/55. The score is not a purchase probability.

The previously identified coverage, unknown-intent and signal-aging tradeoffs
remain policy follow-up work; switching providers does not validate those choices.

## Provenance and usage

Results include profile/policy/weight/prompt versions, LLM provider/model, input
fingerprint, scoring date, total latency and `llm_usage`. Model usage shows request
count, provider latency, input/output tokens and estimated cost only when both
token counts and configured token prices are available. Missing cost is null,
not zero. These metrics cover the scoring call, excluding optional ICP drafting.
Provider/model aliases are not immutable model revision identifiers.

## Runtime and files

- `app/main.py`, `app/__init__.py`: scoring-only startup; no Laya import or warmup.
- `app/api/scoring.py`: config, draft and async scoring routes.
- `scoring/service.py`: field rules, evidence attribution and aggregation.
- `scoring/llm.py`: one batched semantic request and strict response normalization.
- `engines/llm_engine.py`: existing compatible provider transport.
- `engines/structured_output.py`: strict JSON schema preparation.
- `models/scoring.py`: request, model-output, factor and usage contracts.
- `frontend/src/main.tsx`: Lead Scoring workspace only.
- `tests/test_llm_scoring.py`: provider-independent regression checks.

Use the existing backend environment and provider settings in `.env`; do not put
keys in the browser. Start with `venv\Scripts\python.exe -m uvicorn app:app
--host 127.0.0.1 --port 8000` and `npm run dev` in `frontend`.
`GET /health` reports liveness/configuration, not a successful provider handshake.

Historical Laya and Decision Lab source remains on disk for later evaluation.
The active runtime and base dependency list do not depend on Laya. No datasets,
model weights or environment secrets were removed or changed.

The app is still a local single-lead prototype: no persistence, tenant boundary,
bulk jobs, production workflow execution, calibrated model quality or automatic
enrichment. This migration establishes the LLM baseline, not production readiness.
