# Data sources

UN Comtrade is the production structural-trade source. Every ingestion writes a snapshot before normalization, including identifier, request, retrieval time, checksum, status, and raw response.

The HS code-to-category catalog is the complete official UNSD/UN Comtrade `H6` reference file. It includes chapter, heading, and six-digit subheading relationships and is imported into `hs_products` during reference-data seeding. Source metadata is recorded in `data/seeds/HS2022_SOURCE.md`.

Automated tests use `data/fixtures/comtrade/hs_902620_test.json`. It is deterministic and offline, is selected explicitly by the test configuration, and is not registered in the deployed provider list.

The live REST adapter converts ISO3 country codes to official UN M49 query codes and converts numeric response codes back to ISO3. It supports annual and monthly periods, bounded concurrency, retry/backoff, raw snapshots, and canonical imports. Analysis uses fresh cache first, then stale cache from the same source type; fixture data is never used as a live-source fallback.

Cache policies are data-type specific: annual trade, tariffs, and macro data use long-lived policies; monthly trade ages in weeks; search in days; and marketplace, tender, and supplier data in hours or days. The latest complete annual trade year is configurable and defaults conservatively to the prior calendar year.

## Registry and integration status

| Source | Layer | Adapter | Default |
|---|---|---|---|
| UN Comtrade | annual/monthly trade | live; fixture in tests only | live by default |
| WITS / UNCTAD TRAINS | tariff | live SDMX | enabled |
| WTO Timeseries | tariff/access | authenticated adapter boundary | authentication required |
| World Bank Indicators | country capacity | live | enabled |
| Google Trends API alpha | digital demand | access boundary | limited-access application required |
| eBay Browse API | marketplace demand | direct OAuth adapter | Client ID/Secret required |
| TED EU Tenders | explicit demand | live Search API v3 | enabled; no key required |
| Supplier Network | supply fit | normalized HTTP + null | credentials required |

Official references: https://comtradeapi.un.org/, https://api.worldbank.org/v2/, https://wits.worldbank.org/witsapiintro.aspx, https://apiportal.wto.org/, https://developers.google.com/search/apis/trends, https://developer.ebay.com/develop/api/buy, and https://docs.ted.europa.eu/api/latest/search.html.

Unavailable or authenticated providers return no records and publish their status. They never emit placeholders that look like facts.

The dataset ingestion endpoint accepts normalized rows identified as CSV, JSON, or Parquet input, stores the raw payload/checksum/revision first, then routes registered dataset types to idempotent trade, tariff, or macro normalizers. Unknown types remain safely stored as raw snapshots with PARTIAL status.

## Activation

Copy `.env.example` to `.env`. Keep credentials only in `.env`; request snapshots contain query parameters and normalized responses, never authorization headers or API keys.

The shortest usable sequence is:

```bash
curl -X POST http://localhost:7890/api/v1/admin/sync/comtrade \
  -H 'Content-Type: application/json' \
  -d '{"hs_code":"902620","origin_iso3":"CHN","countries":["TUR"],"years":[2022,2023,2024]}'

curl -X POST http://localhost:7890/api/v1/admin/sync/world-bank \
  -H 'Content-Type: application/json' \
  -d '{"countries":["TUR"],"year":2024}'

curl -X POST http://localhost:7890/api/v1/admin/sync/wits \
  -H 'Content-Type: application/json' \
  -d '{"hs_code":"902620","origin_iso3":"CHN","countries":["TUR"],"year":2022}'
```

Comtrade preview access may work without a key for small requests; configure `COMTRADE_API_KEY` for production quotas. World Bank and WITS do not require keys. Set `TRADE_DATA_PROVIDER=comtrade` before running an analysis that should consume live trade data.

## All-HS analysis catalog

`GET /api/v1/catalog/hs` exposes the complete active six-digit HS 2022 catalog with pagination, search, analysis state, covered-market count, and top market. The web interface is available at `/catalog`. Only opportunities backed by non-fixture evidence count toward coverage.

The preview Comtrade endpoint is capped at 500 records and is not suitable for building all 5,613 analyses. Configure `COMTRADE_API_KEY`; authenticated calls automatically use `COMTRADE_FINAL_API_BASE_URL` (`https://comtradeapi.un.org/data/v1/get`) and the official `subscription-key` parameter. Until real observations have been processed, catalog entries remain `NOT ANALYZED` instead of displaying fabricated results.

## Supplier contract

Configure `SUPPLIER_API_BASE_URL` and `SUPPLIER_API_KEY`. Market calls `GET /api/v1/supply/summary/{hs_code}` with a bearer token. The JSON response may contain `supplier_count`, `product_count`, `active_offer_count`, `min_price`, `median_price`, `currency`, MOQ, stock, lead-time, certification, dropship, delivery, and quality fields. Omitted values stay null; no value is inferred.

Trigger it with:

```bash
curl -X POST http://localhost:7890/api/v1/admin/sync/supplier \
  -H 'Content-Type: application/json' \
  -d '{"hs_code":"902620"}'
```

## eBay marketplace

Configure `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` from an eBay production application. Market obtains an application access token through the official client-credentials flow and reads observed listings from the Browse API. It stores only fields actually returned by eBay; product ratings, sales estimates, and other absent values remain null.

```bash
curl -X POST http://localhost:7890/api/v1/admin/sync/marketplace \
  -H 'Content-Type: application/json' \
  -d '{"marketplace":"EBAY_DE","country_iso3":"DEU","keyword":"pressure sensor"}'
```

## Optional marketplace gateway

Configure `MARKETPLACE_PROVIDER_CODE`, `MARKETPLACE_API_BASE_URL`, and `MARKETPLACE_API_KEY`. The gateway owns marketplace-specific authentication and exposes these normalized bearer-token endpoints:

- `GET /api/v1/products/search`
- `GET /api/v1/products/{product_ref}`
- `GET /api/v1/metrics/keywords`
- `GET /api/v1/metrics/categories`

Keyword metrics accept `marketplace`, `country_iso3`, and `keyword`. Each record may contain `observed_at`, `product_ref`, price, rating, reviews, rank, seller count, stock, promotion, estimated sales, confidence, and observed type. Repeating the same product/timestamp sync updates the canonical row instead of duplicating it.

## TED explicit demand

TED is the official EU procurement notice service. Its published-notice Search API is public and requires no key. The adapter stores buyer, destination, title, description, dates, reported value/currency, original fields, and the official notice URL. HS association comes only from the keyword/HS request that produced the match and is not inferred from CPV.

```bash
curl -X POST http://localhost:7890/api/v1/admin/sync/explicit-demand \
  -H 'Content-Type: application/json' \
  -d '{"hs_code":"902620","country_iso3":"DEU","keyword":"pressure instrument"}'
```

## Google Trends

The official Google Trends API remains a limited-access alpha. Apply at https://developers.google.com/search/apis/trends. Until access and its issued API contract are available, the provider reports `LIMITED ACCESS` and returns no data; the service does not use unofficial scraping as production evidence.

## Verified economics

Economics is intentionally not guessed from incomplete sources. Submit explicit, verified costs to `POST /api/v1/economics`. The payload requires EXW, freight, insurance, tariff rate, marketplace commission, fulfillment, payment, return allowance, target sale price, currency, `input_source`, and `verified: true`. Distribution Opportunity remains null until both Supply Fit and verified Economics exist.
