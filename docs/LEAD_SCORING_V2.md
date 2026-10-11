# Lead scoring v2 — first implementation milestone

This implements an offering-aware, single-lead workflow inspired by the visible
Oppora workflow. It does not claim to reproduce Oppora's private scoring algorithm.

## Flow

1. Describe the seller's offering and target buyer persona.
2. Enter company and person criteria, or generate an editable ICP draft.
3. Review the criteria and enter known lead facts, including role responsibilities
   when available. Missing information stays unknown.
4. Structured fields use exact rules. One LLM call evaluates the supplied semantic
   criteria against source text and offering/buyer context.
5. Validate the output schema, criterion IDs, completion status, and exact source
   quotes. Invalid evidence becomes unknown; provider/schema failures become errors.
6. Calculate fit, intent, coverage and priority in code. Apply the recommendation
   policy in `scoring/policy.py`.
7. Display Yes, No or Needs review, reasons, eligibility, factors, source excerpts,
   model usage and versions. Download the submitted request and result as JSON.

Seller context is a requirement, not evidence about a lead. A title does not prove
budget authority or purchase intent. Model decisions and explanations can be wrong;
quote validation verifies attribution, not semantic correctness.

## Recommendation policy

The policy is deliberately conservative and versioned as `lead-score-v2`:

| Condition, in evaluation order | Recommendation |
| --- | --- |
| A mandatory structured requirement explicitly fails | No, even if another evaluation fails |
| Evaluation failure, unresolved mandatory rule, missing offering/persona, missing company criteria, missing semantic person criterion, or any unknown criterion | Needs review |
| Explicit mismatch on a person criterion | No |
| Partial person match | Needs review |
| Insufficient fit evidence | Needs review |
| Fit below the profile's warm threshold | No |
| Fit below its hot threshold | Needs review |
| All preceding checks pass | Yes |

Eligibility reports only mandatory-rule status: eligible, ineligible or unknown.
Eligible does not by itself mean Yes. With no mandatory rules, eligibility is
eligible. A semantic person criterion is a job-title or responsibilities criterion.
The LLM must assess that criterion against both offering and persona context.

Thresholds are business settings, not calibrated conversion probabilities. Their
defaults remain 55 and 80. The same thresholds label priority bands; recommendation
thresholds use **fit**, so intent cannot manufacture buyer relevance.

## Arithmetic and compatibility changes

- Outcomes: match 1, partial 0.5, miss 0, unknown 0.5. Importance: high 3,
  medium 2, low 1. Mandatory rules have no numeric weight.
- Coverage is known weighted criteria / total weight. Both overall coverage and
  fit coverage must meet `min_coverage` before numeric scores are returned.
- Each axis is its weighted mean multiplied by 100. Priority combines axes using
  `alpha_fit`; without configured intent criteria, priority equals fit.
- Configured but missing intent stays neutral at 50, retains its configured
  weight and reports zero intent coverage. It is not an observed intent score.
- Known signals decay toward neutral: `0.5 + (value - 0.5) * 0.5 ** (age / 30)`.
  Funding recency is first advanced to the scoring date for the threshold check.
- Factor impacts add to a neutral baseline of 50 before rounding. A mandatory
  failure suppresses priority; otherwise-valid fit/intent scores remain diagnostic.
- Old requests remain valid: offering, buyer persona and person summary are
  optional. A legacy request without buyer context produces Needs review.
- New response fields: `recommendation`, `recommendation_reasons`, `eligibility`,
  `fit_coverage` and nullable `intent_coverage`.
- Request fingerprints include context and versions. Model and prompt versions
  are recorded, but the same request is not guaranteed to produce identical LLM output.

## Files and responsibilities

| File | Responsibility |
| --- | --- |
| `models/scoring.py` | Request, profile, evidence and result contracts |
| `scoring/catalog.py` | Supported fields and policy/prompt versions |
| `scoring/llm.py` | Semantic prompt, provider call and response validation |
| `scoring/service.py` | Field checks, evidence attribution, arithmetic and orchestration |
| `scoring/policy.py` | Provider-independent recommendation policy and axis coverage |
| `app/api/scoring.py` | Configuration, profile drafting and scoring endpoints |
| `app/main.py` | LLM-only default startup; opt-in legacy Decision Lab |
| `frontend/src/pages/LeadScoringConsole.tsx` | Reviewed profile and lead input workflow |
| `frontend/src/components/ScorePanel.tsx` | Recommendation, evidence and score display |
| `tests/test_llm_scoring.py` | Offline API, provider-contract and policy regressions |

## Run and verify

From the project root in PowerShell:

```powershell
& .\venv\Scripts\python.exe -B -m unittest discover -s tests -v
& .\venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Run `npm run dev` from `frontend` in another terminal. For a production frontend
build, run `npm run build` there. Provider credentials stay in the backend `.env`.
The tests mock provider responses and do not assess live model quality.

Default startup does not import Laya or Torch. To use the existing Decision Lab,
set `$env:ENABLE_DECISION_LAB = 'true'` before starting the backend. This optional
setting is read from the process environment, not the `.env` file, and requires
the existing local runtime dependencies. It is not a scoring benchmark adapter.

## Next milestones

This milestone does not add database persistence, bulk jobs, company deduplication,
people caps or a Laya scoring adapter. Next, assemble human-reviewed lead cases
with expected criterion outcomes and recommendations. Run the LLM baseline, inspect
false positives and abstentions, then implement a Laya adapter that returns the
same criterion decisions. Compare decision quality, evidence validity, errors,
latency and cost under the same policy. LLM agreement alone is not ground truth.
