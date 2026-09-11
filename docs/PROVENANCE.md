# Provenance

All ingested data records where it came from, when it was retrieved, how it entered the system, and which source revision produced it.

1. `data_sources` identifies the provider, category, reliability, terms, and update policy.
2. `source_snapshots` stores the immutable request, raw response, checksum, retrieval status, and source revision.
3. Canonical observations reference the raw snapshot or source.
4. `evidence` links entity metrics to numeric/text/JSON values, units, currency, period, source URL, reliability, observed type, snapshot, and confidence.
5. `demand_signals` link to evidence and carry normalized values without overwriting the original fact.

Reimporting the same canonical key updates that canonical record while preserving a new raw snapshot and job record. This makes provider revisions visible without duplicating analytical observations.
