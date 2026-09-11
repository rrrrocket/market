# Integration roadmap

The architecture already exposes the final provider, signal, opportunity, evidence, decision, and outcome boundaries. Remaining work is additive source connectivity rather than phase-based redesign.

Priority for live data coverage:

1. Harden annual and monthly UN Comtrade ingestion, including ISO/M49 resolution and HS correspondence.
2. Activate WITS/WTO tariff ingestion and verified non-tariff measures.
3. Schedule World Bank country-capacity refreshes.
4. Connect localized Google Trends keywords without treating interest as search volume.
5. Add official or authorized Ozon, Wildberries, Amazon, tender/RFQ, Supplier Network, logistics, and regulatory providers.
6. Add Distribution Plan delivery to ERP and verified outcome feedback.

Every activation requires provider health reporting, raw snapshots, idempotent normalization, provenance, reliability, freshness, fixtures, and failure tests.
