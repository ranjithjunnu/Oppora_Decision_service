# Current project instructions

Read `README.md` and `docs/SYSTEM_DESIGN.md` before changes. They describe intent and observed code, not proof of model quality or production readiness.

- Current phase is LLM-first cleanup. JEV is a future candidate, not an active replacement. Laya source is archived.
- User instruction on 17 October 2026: do not run tests, builds for verification, benchmarks, provider/key checks or model calls until explicitly requested again. Report unverified behavior honestly.
- Preserve the existing `.env`, including its JEV key. Do not print secrets or copy them into frontend code, logs, docs or archives.
- Keep discovery, semantic judgments, deterministic scoring and generation separate. JEV replacements require reviewed bounded tasks; do not invent evidence or calibrated confidence.
- Target is 1,000–10,000 simultaneous users, not a measured result. Follow the ordered production plan; do not enable multi-worker SQLite/background-task execution.
- Prefer small changes and preserve scoring APIs. Archive verified obsolete source with a recovery path; do not remove datasets, environments or runtime data as clutter.
- Production deployment, external actions and bulk live provider traffic are not authorized by cleanup work.
