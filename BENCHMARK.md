# Planned decision benchmark

Status: design documentation only. No runner, LLM adapter, metric pipeline,
calibration, evidence verifier, score aggregator or UI is implemented.

## Purpose

Compare Laya decisions, LLM decisions and reviewed ground truth on identical
eligible inputs. Retain raw confidence/probability provenance, latency, cost,
evidence, disagreements and failure cases. An engine predicts; an evaluator
interprets a lead and criterion; a benchmark compares evaluations; a scorer
deterministically aggregates accepted outcomes. The GTM planner stays separate.

## Decisions needed before implementation

- Lead, criterion and ICP contracts, including missing data and source references.
- Standard criterion outcomes and meanings; legacy keep/drop labels do not
  establish a future criterion schema or weighting policy.
- Confidence/probability provenance distinct from later calibration.
- Evidence and verification semantics; an explanation is not verified evidence.
- Failure/abstention representation; failures must not silently become labels.
- Versioned case/label policies, review status, model configuration and partitions.
- Latency measurement boundaries and cost basis; local inference is not
  automatically zero cost.

These are open decisions, not implemented defaults.

## Planned components

| Location | Future responsibility |
| --- | --- |
| models/ | Approved lead, criterion, evaluation and benchmark contracts |
| engines/ | Existing Laya engine plus a future LLM prediction adapter |
| evaluators/ | Criterion routing and structured/Laya/LLM evaluation |
| evidence/ | Source extraction and evidence verification |
| benchmark/runner.py | Run eligible cases through selected evaluators |
| benchmark/comparison.py | Align cases and retain disagreements |
| benchmark/metrics.py | Agreed quality, coverage, failure, latency and cost metrics |
| benchmark/calibration.py | Later calibration with appropriate separate data |
| benchmark/reports.py | Reproducible comparison artifacts |
| scoring/ | Separately owned deterministic aggregation and weighting |
| app/api/benchmark.py | HTTP access after comparison services exist |
| ui/ | Future side-by-side inspection and review |

No empty files were created at these planned locations. The existing
`datasets/benchmark/legacy/` contains fixtures only.

## Data eligibility and next phase

See [datasets/README.md](datasets/README.md). The mixed reference pool is not
labelled ground truth. Historical scoring/classification labels have distinct
contracts and need reviewed adapters. Expected labels and review metadata must
not be supplied to a future model as input. Grouping, duplicates, review and
evaluation splits need agreement on actual selected cases; no new partitions
or datasets were generated here.

First agree a narrow initial task and a standardized evaluation contract. Then
restore or add approved regression/adapter coverage in the testing phase.
Implement one evaluator against that contract before the comparison runner and
additional providers. Evidence policy, scoring weights, calibration and UI each
need their own agreed scope. Organization establishes no accuracy, speed, cost
savings or production-readiness claim.
