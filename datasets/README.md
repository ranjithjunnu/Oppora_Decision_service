# Existing datasets and provenance

All four existing JSON files are preserved byte-for-byte. No rows, labels,
metadata or replacement datasets were generated. The API does not load this
directory at runtime. Directory names describe existing data, not implemented
benchmark functionality.

| Previous path | Current path | Classification rationale |
| --- | --- | --- |
| source/company_directory.json | reference/company_directory.json | Unlabelled mixed company and synthetic-contact input pool |
| source/_real_anchors.json | reference/_real_anchors.json | Supplemental observations; metadata explicitly says it is not itself a test set |
| source/lead_scoring.json | benchmark/legacy/lead_scoring.json | Labelled task fixtures: 322 batch-scoring cases and one recommendation case |
| source/classification.json | benchmark/legacy/classification.json | Labelled fixtures: 172 industry, 511 email-pattern, 426 email-status and 312 delivery-failure cases |

## Reference inputs

`company_directory.json` contains 3,526 companies. Its metadata reports 157
source Oppora companies, 3,369 generated companies and 55,000 synthetic lead
identities. It intentionally includes incomplete and contradictory fields and
non-canonical labels. These are preserved provenance claims, not fresh external
verification. Neither `oppora_real` nor `synthetic` accurately names the entire
mixed file.

`_real_anchors.json` describes company observations and anonymized person
structures. It holds 11 company records, 12 lead shapes, observed data patterns
and source taxonomy observations. They are not promoted into labelled cases.

## Legacy labelled fixtures

The scoring file retains original keep/drop expectations. They are task-level
labels, not standardized criterion outcomes or final numeric lead scores.
Classification fixtures retain their expected-value, alternative-label and
graceful-degradation conventions. These tasks have different output semantics.
Review adapters and label quality before using them in a common evaluation.

Some metadata refers to historical generator scripts, runners, source files or
production modules absent from this repository. These strings remain as
provenance; they are not runnable local paths. External/manual readers must use
the new paths above. Duplicate dataset copies were not added.

Previously removed generated suites, review queues, manifests and preparation
tools remain absent. No deleted files were recovered. No benchmark or model
quality result follows from these files' presence.
