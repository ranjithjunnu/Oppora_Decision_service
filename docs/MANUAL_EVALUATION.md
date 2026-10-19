# Decision Lab — LLM baseline

This phase uses the existing configured LLM only. Laya has been archived; JEV remains a later replacement candidate. No testing or benchmarking is currently requested. This guide documents how the feature can be used when the user is ready.

## Configuration

See [README](../README.md) for startup. Existing server-side settings remain: `LLM_PROVIDER`, `LLM_MODEL`, `GROQ_API_KEY` or compatible-provider credentials, response format, timeout and token limit. Read `.env.example` for defaults. Never overwrite the existing `.env`; the user's JEV key stays there unused.

`ENABLE_DECISION_LAB=true` exposes the manual interface. `EVALUATION_TASK=gtm_intent` uses the historical GTM category menu; `custom` requires a criterion in each API request. No local model is imported or downloaded by this path.

## Contract

`POST /evaluate` accepts `query` and optional `request_id`, `context`, `structured_input`, and `criterion` (`id`, `instructions`, `choices`). The result contains `request_id`, `query`, `evaluated_at`, `semantic_input`, and `llm`.

**Migration:** the retired `laya` and `comparison` response fields, and `laya` config field, were removed. The frontend changes accompany the backend. External callers using those fields must migrate. Lead-scoring contracts are unchanged.

The LLM result includes its selected label, self-reported confidence, rationale, unverified citations, latency, usage, optional configured cost estimate, raw output and structured error. Confidence is not measured accuracy; evidence quotes still need validation. Session history is browser memory only.

The UI uses the default GTM task. Custom criteria are available through the API for later focused work, for example:

```json
{
  "query": "The company sells payroll software to small businesses.",
  "criterion": {
    "id": "b2b_software",
    "instructions": "Does the text establish that this company sells software to businesses?",
    "choices": {
      "match": "Explicit support for selling software to businesses.",
      "miss": "Explicit support for a different business model.",
      "unknown": "Insufficient or conflicting evidence."
    }
  }
}
```

This is an illustrative request, not a recorded result. The default six-label GTM menu lacks an out-of-scope option and must not execute real workflows. Future JEV work should start from reviewed bounded criteria, preserving the same facts/options and a clear unknown outcome.
