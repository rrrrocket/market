# Architecture

Matrix One Market is a modular monolith with a FastAPI service, a Next.js UI, and one PostgreSQL database. This keeps deployment and consistency simple while preserving explicit module boundaries.

```text
External / Internal Providers
            ↓
      Source Snapshot        (immutable raw)
            ↓
Canonical Observations       (trade, tariff, macro, supply)
            ↓
       Demand Signal         (source-aware shared semantics)
            ↓
     Market Opportunity      (product × country × channel × time)
            ↓
Supply Fit + Economics + Risk
            ↓
 Distribution Opportunity   (only when critical inputs exist)
            ↓
 Decision → ERP → Outcome
```

Raw provider payloads are immutable. Canonical observations keep product, year, reporter, partner, and flow independent. Intelligence objects can be regenerated from the canonical layer and a score version. BackgroundTasks provides the initial in-process job runner; `analysis_runs` is the durable job record.

External systems are adapters. Business services depend on `TradeDataProvider` and `SupplierNetworkClient`, never an SDK or another service's database.

## Boundaries and runtime

- Supplier Network answers what China can supply through an authorized API. Market never reads or mutates its database.
- Market owns external demand evidence, matching context, and opportunity intelligence.
- ERP receives a Distribution Plan and owns listing, pricing, procurement, inventory, orders, and transactions.
- The Demand Graph is a relational business model in PostgreSQL; no graph database is required.

`ProviderRegistry` exposes capabilities, reliability, enablement, health, sync time, and rate-limit notes. Live, fixture, and null implementations share contracts, so unavailable sources remain explicit without branching throughout business services.

The deployment remains a single three-service Docker Compose application: Next.js web, FastAPI API, and PostgreSQL. Docker is the only deployment mode, so hosts require no machine-specific Python or Node.js setup and there are no environment-specific Compose variants. `data_jobs` provides durable state for ingestion, normalization, scoring, refresh, backfill, and matching jobs.

The public origin is `https://market.matrix-one.tech`. Next.js owns that origin and proxies same-origin `/api/*` traffic to FastAPI over the private Docker network at `api:8000`; PostgreSQL is never exposed publicly.
