# Oppora-style lead scoring

This implementation reproduces the observed background `lead_scoring` contract:
company context + people filters + a batch of people → LLM-selected IDs and
LLM-authored 0–100 scores. It is an adaptation of the inspected AI Admin prompt,
not a claim of complete equivalence to Oppora's backend or its `judge_leads` tool.

## Use the application

Restart the backend after installing the changes and use the existing frontend
development server. Open **Find & score leads**.

1. In **People**, enter a natural-language request such as **Find software engineers in India**.
2. Choose **Find people**. AI extracts person filters and close title variants. The backend searches the local directory using the relevant fields. The search supplies the initial scoring target automatically.
3. Select people across pages and choose **Save selected to list**, or **Save all** for all returned results. Name a new list or append to an existing list.
4. Open the saved list and choose **Score this list**. Optionally edit the scoring target above first. Lists hold up to 1,000 people; large searches explicitly show when only their first 1,000 matches are available.
5. Results update as batches finish. Matches are ordered by descending score.
6. Open a person and request an optional AI explanation.
7. Open **AI activity** for exact instructions, inputs, returned JSON and validation.
8. Use **Lists** to rename lists, add/remove members and score again. Use **Run history** to reopen assessments or **Download run** to export a snapshot.

People search uses an LLM to interpret the request, then deterministic field-specific local retrieval. Role words are matched against titles, not combined company/department text. Token boundaries prevent VP from matching SVP and India from matching Indiana. Close title variants are proposed by the LLM; this is candidate retrieval, not a guarantee of semantic equivalence. Company browsing remains literal local search. Neither path searches the web. The directory contains generated people and is visibly labelled.

The initial screen shows no records. People retrieval starts only after the submitted query has been interpreted and its source-backed requirements validated. Editing the query clears previous results so rows from an earlier request cannot appear under new text. Company browsing also waits for a submitted keyword or location.

The interpreter must quote the user's own words for each active requirement. The backend drops department/seniority assumptions inferred from a job title rather than requested separately. It attempts one interpretation repair when required source quotes are absent or the response JSON is unusable; transport failures are not retried automatically. Unclear/unsupported requests produce an actionable error, not a misleading zero-match result. These source and schema checks do not independently prove semantic correctness.

Known contradictions in explicit requirements exclude a candidate. Missing department, seniority or experience remains unknown with a visible note. VP/Vice President and country abbreviations are normalized for comparison; raw source labels stay in snapshots. Both `years_experience` and `experience_years` map into the canonical experience field, and textual missing markers such as Unknown/null/N/A become missing values. The directory cache refreshes when the source file changes.

Requested geography has two result pools. Location-matching candidates appear by default. Role candidates whose person location cannot establish the requirement appear separately under **Location needs review**. Missing location is never filled from company headquarters. Review candidates must be explicitly selected to save them; **Save all** saves the default result pool only. Known incompatible locations are excluded from both pools. Each pool exposes at most 1,000 rows with truncation stated in the UI. Scoring still uses the observed benefit-of-the-doubt policy, and a high fit score does not verify a missing location.

Search details show record counts after company scope, role, geography and explicit metadata checks, along with removed assumptions and recorded model calls. These are retrieval diagnostics, not accuracy measurements. Editing the scoring target does not silently change the search or list membership.

## Supported targeting

Job titles, person countries/locations, excluded locations, departments,
management levels and minimum/maximum years of experience. Unknown or
unrepresentable constraints produce an actionable targeting error instead of
being silently dropped. Company selection is performed in the directory.
The optional objective only breaks ties; it does not create an extra filter. Natural-language people search also supports explicitly named employing companies as a retrieval scope. Other unsupported constraints produce an error instead of disappearing from the request.

## Decision ownership

- People search and standalone target interpretation: LLM, `people-search-v2`; both paths use the same validated interpreter. The search stores prompts, outputs, title variants, validation repairs and retrieval diagnostics. Pagination reuses a saved search without a model call.
- Named lists, duplicate-ID checks and membership edits: backend.
- Candidate lookup and company grouping: backend. As in Oppora, each company gets its own call; a company with more people than `LEAD_SCORING_BATCH_SIZE` (default 50) is split into numbered batches, and up to `LEAD_SCORING_CONCURRENCY` (default 4) batches run at once. Oppora was observed sending about 90 people per call; our default is smaller to stay within the output token limit.
- Inclusion/exclusion and scores: LLM, `oppora-filter-v1`.
- Response JSON, numeric ranges, unique IDs, membership in the input: backend.
- Explanation: separate optional LLM request, `lead-explanation-v1`; its cited
  quotations are checked against saved source fields. Prose correctness is not
  independently proven by quote checking. An unavailable or invalid explanation
  falls back to a labelled factual result summary and can be retried.
- Final ranking: backend sorts the model's numbers without recalculating them.

A successful empty scoring response means no matching people were selected. A timeout,
invalid response or invalid ID marks every person in that chunk as failed; it
does not fabricate zero scores or treat them as rejected. Failed people can be
retried in a new run using the original targeting. Successful responses can
still contain semantic errors: schema validation is not an accuracy test.

The model receives no emails or phone numbers. Missing person location is not
replaced with company headquarters. Title/headline can support inclusion with
the benefit of the doubt, matching the observed policy. A high score does not
verify missing data or represent a probability of conversion.

## Storage and execution

Named lists, search snapshots and scoring runs share the existing SQLite store. Lists save member facts, their original search and targeting, and membership versions. Duplicate IDs are ignored when appending. Prior list revisions are retained internally; no revision-restore UI is provided. Membership edits use optimistic version checks so a stale page cannot overwrite a newer list.

Scoring a list pins its member facts and list version into a new run. Later edits do not change that run. A retry uses the original failed people's saved facts, even if the directory or list changes. Lists and runs are distinct: a list is a reusable audience; a run is one recorded assessment.

The configured provider is reused (DeepSeek when `DEEPSEEK_API_KEY` is set and `LLM_PROVIDER` is blank, matching Oppora). Every call is also written to the AI ledger; see the AI Admin section of the README.
`LLM_TIMEOUT_SECONDS`, `LLM_MAX_OUTPUT_TOKENS` and optional pricing configuration
continue to apply. No model calls occur merely by opening the page or starting
the backend. Natural-language people search, applying targeting, scoring and requesting explanations make calls. Saving, editing and reopening lists do not call an LLM.

Immutable targeting snapshots and scoring runs are stored in
`data/lead_scoring.sqlite3`, excluded from Git. Each run records its targeting,
lead facts, provider/model, prompt version, input fingerprint, usage and call
outputs. New scoring requests make new runs; scores are not silently reused.
Stored targeting lives on the backend; the browser remembers the last applied
target and last run. A browser refresh can reconnect to a running assessment.

This is a **single-process local service**, using FastAPI background tasks,
two concurrent scoring runs and parallel batches within each run. Run one backend worker. It is not a distributed
queue or a tenant-isolated production deployment. On backend restart, unfinished
people are marked as failed/interrupted and can be retried. Closing a browser
does not cancel a submitted scoring run. Use run history after an ambiguous
network response before submitting the same work again.

Data remains local to this backend except selected facts sent to the configured
LLM provider. There is no live Oppora integration or external discovery provider.
History shows the most recent 30 runs; an older run remains retrievable by ID.

## API

- `POST /v1/lead-scoring/targeting` — `{description, objective}`.
- `POST /v1/lead-scoring/searches` — `{description, objective, company_id?}`.
- `GET /v1/lead-scoring/searches/{search_id}?offset=0&limit=20&pool=confirmed` — saved search page; `pool=review` retrieves candidates with unknown geography.
- `GET /v1/lead-scoring/lists` — saved list summaries.
- `POST /v1/lead-scoring/lists` — `{name, search_id?, lead_ids?, targeting_id?}`; omit lead_ids with search_id to save all returned candidates.
- `GET /v1/lead-scoring/lists/{list_id}` — saved member facts and list version.
- `POST /v1/lead-scoring/lists/{list_id}/members` — append with `{expected_version, search_id?, lead_ids?}`.
- `POST /v1/lead-scoring/lists/{list_id}/edit` — `{expected_version, name?, remove_ids?}`.
- `POST /v1/lead-scoring/lists/{list_id}/score` — `{expected_version, targeting_id?}`; scores saved member snapshots, up to 1,000 people.
- `POST /v1/lead-scoring/runs` — `{targeting_id, lead_ids}`, returns 202 and a saved run.
- `GET /v1/lead-scoring/runs` — recent run summaries.
- `GET /v1/lead-scoring/runs/{run_id}` — results, progress and recorded AI activity.
- `POST /v1/lead-scoring/runs/{run_id}/retry` — retry failed people using their saved facts.
- `POST /v1/lead-scoring/runs/{run_id}/explanation` — `{lead_id}`.

The original `/v1/scores` criterion-based scorer remains available to existing
callers. It is a different scoring method. Decision Lab and its evaluator paths
are separate. Decision Lab is LLM-only in the current cleanup phase. JEV integration and dynamic tool execution are not enabled.

No tests, builds, live scoring calls or benchmarks were run during implementation,
as requested. Runtime and model evaluation are left to the user.

