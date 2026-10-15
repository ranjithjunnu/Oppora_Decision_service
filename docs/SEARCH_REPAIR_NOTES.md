# Search repair: people-search-v2

The earlier interpreter could add department/seniority restrictions from a role.
Retrieval treated missing metadata as a contradiction, compared equivalent labels
literally and read the wrong experience field. The UI also browsed all people
before a request was submitted. This repair addresses those shared problems.

## Use after installation

1. Restart the backend and refresh the frontend. The UI checks the backend's
   `people_search_version` and explains when a restart is still needed.
2. Enter a role/location request and choose **Find people**. No people are shown
   until the model returns a supported, source-backed interpretation.
3. Inspect the applied filters and **How the search decision was made**. The
   details include any discarded assumptions, retrieval counts and model calls.
4. Use the default results or explicitly inspect **Location needs review**.
   Unverified geography is not silently treated as matching geography.
5. Save selected people to a named list, then choose **Score this list**.
6. Open a result and **AI activity** to see what the LLM received and returned.
   The LLM still selects matching leads and assigns their scores. Retrieval notes
   are not supplied to scoring or explanation models as evidence about people.

Targets interpreted by the earlier engine must be applied again before new UI
scoring requests. Historical runs/list snapshots are not rewritten. The raw
datasets remain unchanged and continue to contain generated people and deliberate
data-quality defects. The repair does not add web discovery, a live Oppora
connection, Laya execution, model evaluations or benchmark results.

## Boundaries for later model evaluation

- LLM: interpret the request and propose close title variants, with literal source
  quotes for active requirements. A source/schema validation failure can trigger
  one repair call; all attempts in a successful search are recorded.
- Backend: remove additional inferred restrictions, normalize labels, retrieve
  candidates and report missing/contradicting facts. Source-quote checks do not
  establish that every interpretation is semantically correct.
- LLM: assess saved candidate batches and assign numeric scores.
- Backend: validate returned IDs, duplicates and score ranges, save the run and
  sort the model's scores. No calibrated probability is implied.

This makes the inputs, decisions and outcomes inspectable before introducing
Laya into any of these boundaries. Decision Lab remains separate.

No tests, builds, live AI requests or benchmarks were run during implementation,
following the user's instruction. Runtime/model behavior remains for manual
verification; this document is not evidence that every natural-language query
will succeed or that the generated dataset contains every requested audience.
