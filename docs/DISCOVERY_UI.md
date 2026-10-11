# Discovery workspace

The main page now starts with Companies and People search. The technical criterion
editor and manual lead-entry form have been removed from this page. Decision Lab
remains visible in the sidebar; its optional backend setting is unchanged.

## Using it

1. Open Companies or People and search a name, industry, role or location.
2. Select View people on a company to browse the people attached to it.
3. Open a person to see company/role information and Check fit with AI.
4. Add Your targeting: your offering, optional ideal company description, and
   target buyer. There are no mandatory-country filters, weight selectors or
   review checkboxes in this workflow.
5. Inspect the recommendation and source evidence in the person detail panel.

Search uses case-insensitive text matching against the existing local directory;
it does not use the LLM to invent search results. AI is called only for an explicit
fit check. Fit requests use two equally weighted semantic criteria with no hard
requirements. Backend evidence validation and missing-data handling still apply.
Targeting and fit results stay in memory while switching to Decision Lab and back.
Reloading clears them; Download result preserves a scored request and its output.

## Data source

The source is `datasets/company_directory.json`. Its metadata identifies 3,526
companies, including saved and generated companies, and 55,000 generated people.
All people are synthetic test identities, including those attached to saved
company records. The UI labels this explicitly and does not expose synthetic
email, phone or social profile links. This is a local preview, not live prospecting.
Employee-count ranges remain unknown for scoring; no midpoint is invented.

`GET /v1/discovery/companies` and `GET /v1/discovery/people` accept `query`,
`location`, `offset`, `limit` (1–50) and optional `company_id` for people.
The directory is cached in process; restart the backend after replacing it.

## Start

From `E:\laya_decision_service`, run:

```powershell
.\venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

From `E:\laya_decision_service\frontend`, run `npm run dev`, then open
http://127.0.0.1:5173. Restart an existing backend to load the discovery endpoints.

Verification: offline API/policy tests, frontend TypeScript and production build,
and browser checks of company-to-people navigation, person details, targeting,
search, Decision Lab navigation and mobile layout. No live provider call is
included in those checks. Connecting a real discovery provider is separate work.
