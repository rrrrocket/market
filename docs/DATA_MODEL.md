# Data model

The raw layer is `source_snapshots`. It stores request, response, checksum, retrieval time, and status.

The canonical layer contains `countries`, `hs_products`, `trade_observations`, `market_access_metrics`, `country_metrics`, and `supply_fit`. A trade observation is unique by classification + HS code + period type/start + reporter + partner + flow, so monthly records do not collide with annual records.

The signal layer is `demand_signals`. Structural, digital, marketplace, explicit, macro, and access observations share period, provenance, observed type, reliability, freshness, and confidence semantics.

The intelligence layer contains `market_metrics`, `market_opportunities`, `distribution_economics`, `opportunity_risks`, `opportunity_events`, `opportunity_outcomes`, `evidence`, and job/run records. Opportunities retain the legacy HS-origin-destination-year uniqueness key while adding product scope, channel, period boundaries, independent layer scores, coverage, and confidence.

`supply_product_links` reserves a human-confirmed HS mapping boundary. AI or rules may propose a mapping but cannot mark it confirmed.

`product_entities`, `product_identifiers`, and `product_hs_mappings` separate real products, supplier products, brands/models, and marketplace identifiers from HS classifications. `hs_classifications` and `hs_correspondence` prevent silent joins across HS revisions and preserve one-to-many/many-to-one mapping confidence.

`data_sources` and `metric_definitions` are administrator-managed registries. `watchlists` store monitoring targets; events and outcomes close the future decision-feedback loop.
