# Matrix One Market

Global Demand Intelligence answers one practical question: given a Chinese product, which destination markets deserve attention first, and why?

Production URL: `https://market.matrix-one.tech`

The current connected layer ranks countries using observed import size, structural growth, momentum, and stability. It deliberately does **not** predict sales or invent logistics, tariffs, certification, marketplace competition, supplier fit, or economics when those sources are absent.

## Architecture

- `apps/api`: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL
- `apps/web`: Next.js, TypeScript, Tailwind, ECharts, and a local GeoJSON/SVG market map
- `data/fixtures`: deterministic offline development data marked `TEST DATA`
- `data/seeds/hs2022.json`: complete official UN HS 2022 catalog (6,939 application rows)
- raw snapshots, canonical observations, and intelligence results are stored separately

The system flow is: provider registry → raw snapshot → canonical observations → demand signals → versioned opportunity → evidence → API/UI. Supply Fit, Economics, Risk, Decision, and ERP Outcome use the same nullable, auditable model rather than a separate phase architecture.

`/catalog` is the complete six-digit HS market-analysis directory. It shows catalog-wide coverage and, for each HS, its latest real-data analysis, number of covered markets, top destination, and score. Entries without verified source observations remain visibly unanalysed.

`/intelligence` adds the local UN Comtrade pipeline view. It reports download, import, and analysis progress before exposing completed HS results in the catalog.

## Docker deployment

Docker is the only supported deployment mode on every machine. There are no development/production Compose variants or machine-specific runtime steps.

```bash
./start.sh
```

The command builds and starts the single `market` Compose project: PostgreSQL, FastAPI on port `7891`, and Next.js on port `7890`. It waits until the same-origin API path is ready before returning.

Point `market.matrix-one.tech` at port `7890`. Browser requests use same-origin `/api/*`, and Next.js proxies them to `api:8000` over the Docker network.

## Data-source configuration

Docker defaults to `TRADE_DATA_PROVIDER=comtrade`. The included HS 902620 fixture is used only by automated tests, which explicitly override the provider. It contains deterministic offline acceptance data and must never be displayed as a deployed source or described as current production data.

Copy `.env.example` to `.env`, add the credentials you own, and start Docker. API keys stay in environment configuration and are never written to source snapshots. The live Comtrade adapter includes ISO3 ↔ UN M49 conversion, retry control, bounded concurrency, annual/monthly periods, raw snapshots, and idempotent canonical imports.

The shortest activation order is Comtrade → World Bank → WITS → TED EU Tenders → Supplier API → eBay Browse API. TED needs no key; eBay and Supplier credentials are read from `.env`. The sync endpoints and upstream contracts are documented in `docs/DATA_SOURCES.md`.

`LATEST_COMPLETE_TRADE_YEAR` can pin the analysis year. When empty, the service uses the previous calendar year rather than treating the current partial year as complete.

## Local all-HS pipeline

The Free API pipeline requests 25 HS codes per batch, downloads 2022–2026 annual imports for all reporters and the `WLD`/`CHN` partner scopes, and stores each response as an atomic gzip file under the ignored `data/comtrade/raw` directory. `data/comtrade/manifest.json` contains checksums and resume state. The 2026 period is treated as partial; 2025 is the ranking year.

Run the complete sequence in the foreground:

```bash
make pipeline
```

The stages can also be run independently and safely resumed:

```bash
make pipeline-download
make pipeline-import
make pipeline-analyze
make pipeline-status
```

Credentials are sent to UN Comtrade in the subscription header and are never written to URLs, manifests, raw files, database snapshots, or application logs.

## Commands

```bash
make test       # pytest
make lint       # Ruff and frontend lint
make migrate    # Alembic migration
make seed       # reference countries and HS products
make build      # Next.js production build
```

The scoring implementation is in `apps/api/app/scoring/engine.py`; `market_attractiveness_v1` remains an immutable internal version identifier. Confidence is independent, and Distribution Opportunity stays null until verified demand, supply, and economics inputs exist.

## Supplier integration

Market never accesses the Supplier database. `SupplierNetworkClient` provides null and HTTP implementations for supply summaries, products, offers, and capabilities. Supply Fit stays null until the authorized Supplier API is connected.
