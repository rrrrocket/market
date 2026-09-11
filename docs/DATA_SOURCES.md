# Data sources

UN Comtrade is the production structural-trade source. Every ingestion writes a snapshot before normalization, including identifier, request, retrieval time, checksum, status, and raw response.

The HS code-to-category catalog is the complete official UNSD/UN Comtrade `H6` reference file. It includes chapter, heading, and six-digit subheading relationships and is imported into `hs_products` during reference-data seeding. Source metadata is recorded in `data/seeds/HS2022_SOURCE.md`.

Development and tests use `data/fixtures/comtrade/hs_902620_test.json`. It is deterministic, offline, and conspicuously labelled `TEST DATA`; values must not be presented as current production facts.

The REST adapter currently exposes the provider boundary and response normalization. Before live activation, add the maintained ISO3 ↔ UN M49 resolver because official Comtrade query parameters use numeric area codes. API failure handling should prefer unexpired cache, then stale cache marked `STALE`, and only fail a run when no usable observations remain.

Cache policies are data-type specific: annual trade, tariffs, and macro data use long-lived policies; monthly trade ages in weeks; search in days; and marketplace, tender, and supplier data in hours or days. The latest complete annual trade year is configurable and defaults conservatively to the prior calendar year.

## Registry and integration status

| Source | Layer | Adapter | Default |
|---|---|---|---|
| UN Comtrade | annual/monthly trade | live + fixture | fixture for local safety |
| WITS / UNCTAD TRAINS | tariff | live + fixture + null | disabled until explicitly enabled |
| WTO Timeseries | tariff/access | authenticated adapter boundary | authentication required |
| World Bank Indicators | country capacity | live + fixture | live adapter available |
| Google Trends | digital demand | protocol + null | not connected |
| Marketplace providers | marketplace demand | protocol + null | not connected |
| Tender/RFQ providers | explicit demand | protocol + null | not connected |
| Supplier Network | supply fit | HTTP + null | not connected |

Official references: https://comtradeapi.un.org/, https://api.worldbank.org/v2/, https://wits.worldbank.org/witsapiintro.aspx, and https://apiportal.wto.org/.

Unavailable or authenticated providers return no records and publish their status. They never emit placeholders that look like facts.

The dataset ingestion endpoint accepts normalized rows identified as CSV, JSON, or Parquet input, stores the raw payload/checksum/revision first, then routes registered dataset types to idempotent trade, tariff, or macro normalizers. Unknown types remain safely stored as raw snapshots with PARTIAL status.
