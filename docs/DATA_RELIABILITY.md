# Data reliability

Every source and key metric carries explicit semantics.

## Reliability grades

- A+: verified Matrix One transaction outcomes.
- A: official statistics/tariffs and confirmed supplier offers or inventory.
- A−: official marketplace APIs.
- B+/B: official behavior signals and direct public observations.
- C: third-party estimates.
- D: weak sources and AI-derived conclusions.

Grades are defaults in `data_sources`, not hardcoded truth. Administrators may adjust them with documented rationale.

## Observed type

`REPORTED`, `OBSERVED`, `ESTIMATED`, `INFERRED`, and `AI_GENERATED` are never interchangeable. AI output without evidence IDs is a HYPOTHESIS, not a fact.

## Freshness

Each source category defines its own TTL and maps retrieval age to `FRESH`, `AGING`, `STALE`, or `UNKNOWN`. A stale record may remain visible with a warning; it is never silently presented as current.

## Missing data

Missing values remain null. Scoring functions reweight only their allowed optional inputs and expose coverage. Critical Distribution Opportunity inputs are not optional, so their absence prevents the final score.
