# Current Architecture Audit

## Scope

This audit records the system state before the Global Distribution Intelligence expansion. The existing product-to-country analysis remains a supported compatibility surface; the upgrade extends it rather than replacing it.

## Existing models

- `countries`: ISO reference data and regional grouping.
- `hs_products`: HS 2022 hierarchy and descriptions.
- `source_snapshots`: immutable provider request/response snapshots with checksum and retrieval status.
- `trade_observations`: annual importer-reported trade observations by HS, reporter, partner, and flow.
- `market_metrics`: derived import size, growth, China share, unit value, and volatility.
- `market_opportunities`: product-country market-attractiveness results and component scores.
- `evidence`: metric-level traceability for each opportunity.
- `analysis_runs`: asynchronous analysis execution state.
- `supply_product_links`: external product-to-HS mapping review records.

## Existing APIs

- Product search and country reference endpoints.
- Analysis creation and status polling.
- Opportunity ranking and detail.
- Trade history and supplier-country breakdown.
- Basic source/run administration status.

## Existing providers

- `FixtureTradeDataProvider`: deterministic offline HS 902620 dataset, explicitly test data.
- `ComtradeTradeDataProvider`: live annual UN Comtrade adapter.
- `NullSupplierNetworkClient` and `HttpSupplierNetworkClient`: supplier-system boundary.

Provider selection is currently embedded in the analysis service and there is no shared provider metadata/health registry.

## Existing scoring

`market_attractiveness_v1` combines market size, three-year structural growth, latest momentum, and stability. Missing components are reweighted and separately reduce coverage. The score is reproducible and must remain immutable.

It is not a distribution-opportunity score: supply fit, economics, market access, and risk are not currently available.

## Existing pages

- Overview/product search.
- Product-to-country global explorer with map and ranking.
- Country opportunity evidence detail.
- Methodology.
- Basic data administration.

## Gap to the target architecture

| Target capability | Current state | Upgrade approach |
|---|---|---|
| Data Source Registry | Missing | Add an administrator-managed source table and runtime Provider Registry. |
| Raw → Canonical → Signal → Intelligence | Raw, canonical, and intelligence exist | Add the shared `demand_signals` layer and provenance links. |
| Reliability / observed type / freshness | Informal source labels only | Add explicit enums/fields and source-specific freshness policies. |
| Monthly trade | Annual-only schema | Add period type/start/end without removing `period_year`. |
| HS version correspondence | Classification string only | Add classification and correspondence registries. |
| Product identity graph | One external link table | Add product entities, identifiers, HS mappings, and relationships. |
| Tariff / macro | Missing | Add provider protocols, live adapters, fixture/null adapters, canonical tables, and endpoints. |
| Search / marketplace / explicit demand | Missing | Add stable protocols and null adapters; unavailable layers remain null/not connected. |
| Supply fit | Summary client only | Expand the API contract and persist structured nullable supply-fit data. |
| Economics / risk | Missing | Add auditable nullable calculation and risk records. |
| Distribution Opportunity | Market attractiveness only | Extend `market_opportunities`; never synthesize the final score without supply and economics. |
| Confidence | Conflated with coverage | Add independent confidence calculation and label. |
| Watchlist / events / outcomes | Missing | Add persistent models and APIs. |
| Data Quality | Basic counts | Add provider health, coverage, staleness, failures, mappings, and reliability view. |

## Compatible migration plan

1. Add new registry and canonical tables without dropping or renaming existing tables.
2. Add nullable period, provenance, and multidimensional score columns to existing tables.
3. Backfill annual period boundaries and trustworthy source semantics from existing records.
4. Seed source, classification, freshness, and metric definitions idempotently.
5. Continue serving existing ranking/list shapes while enriching opportunity detail with additive fields.
6. Keep `market_attractiveness_v1` reproducible; introduce new score versions only beside it.

## Compatibility guarantees

- Existing HS search, analysis, ranking, trade, and evidence endpoints remain available.
- Existing annual records and opportunities remain valid after migration.
- Missing layers return `null` or `NOT_CONNECTED`, never zero or invented values.
- Supplier data remains API-only; Market never reads or mutates the Supplier database.
- ERP integration produces plans/events only and does not execute listings, pricing, procurement, or orders.
