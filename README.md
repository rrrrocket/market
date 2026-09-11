# Matrix One Market

Global Demand Intelligence answers one practical question: given a Chinese product, which destination markets deserve attention first, and why?

The current connected layer ranks countries using observed import size, structural growth, momentum, and stability. It deliberately does **not** predict sales or invent logistics, tariffs, certification, marketplace competition, supplier fit, or economics when those sources are absent.

## Architecture

- `apps/api`: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL
- `apps/web`: Next.js, TypeScript, Tailwind, ECharts, and a local GeoJSON/SVG market map
- `data/fixtures`: deterministic offline development data marked `TEST DATA`
- `data/seeds/hs2022.json`: complete official UN HS 2022 catalog (6,939 application rows)
- raw snapshots, canonical observations, and intelligence results are stored separately

The system flow is: provider registry → raw snapshot → canonical observations → demand signals → versioned opportunity → evidence → API/UI. Supply Fit, Economics, Risk, Decision, and ERP Outcome use the same nullable, auditable model rather than a separate phase architecture.

## Local start

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -e 'apps/api[dev]'
cd apps/web && npm install && cd ../..
make migrate
make seed
```

Start the API and web app in separate terminals using the commands printed by `make dev`. Open `http://localhost:3000` and analyze HS `902620`.

Without `.env`, the API uses local SQLite for convenience. Docker and `.env.example` use PostgreSQL as required for the deployed system.

## Docker

```bash
docker compose up --build
```

This starts PostgreSQL on the internal network, the API at `:7891`, and the web app at `:7890` (the standard `3000`/`8000` ports are intentionally left free for the existing workspace services).

## Fixture and Comtrade configuration

`TRADE_DATA_PROVIDER=fixture` is the safe default and supports the full offline acceptance flow. The included HS 902620 fixture contains five years, twelve destinations, world imports, bilateral imports from China, and supplier-country shares. It must never be described as current production data. Tariff and macro fixtures are likewise marked TEST DATA; disconnected providers return no data.

The live adapter is isolated in `apps/api/app/integrations/trade.py`. Set `TRADE_DATA_PROVIDER=comtrade` and `COMTRADE_API_KEY`, then switch the provider only after configuring the official reporter/partner numeric-code resolver described in `docs/DATA_SOURCES.md`.

`LATEST_COMPLETE_TRADE_YEAR` can pin the analysis year. When empty, the service uses the previous calendar year rather than treating the current partial year as complete.

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
