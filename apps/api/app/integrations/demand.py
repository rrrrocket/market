from __future__ import annotations

from typing import Protocol

from app.integrations.base import ProviderMetadata


class SearchDemandProvider(Protocol):
    metadata: ProviderMetadata

    async def get_keyword_interest(
        self, keyword: str, country_iso3: str, language: str
    ) -> list[dict]: ...


class ExplicitDemandProvider(Protocol):
    metadata: ProviderMetadata

    async def search_demands(
        self, *, hs_code: str | None, country_iso3: str | None, keyword: str | None
    ) -> list[dict]: ...


class NullSearchDemandProvider:
    metadata = ProviderMetadata(
        code="GOOGLE_TRENDS",
        name="Google Trends",
        category="SEARCH",
        capabilities=("normalized_interest",),
        reliability="B_PLUS",
        enabled=False,
        health="NOT_CONNECTED",
    )

    async def get_keyword_interest(self, keyword: str, country_iso3: str, language: str) -> list[dict]:
        return []


class NullExplicitDemandProvider:
    metadata = ProviderMetadata(
        code="NULL_EXPLICIT_DEMAND",
        name="Tender and RFQ integrations",
        category="TENDER",
        capabilities=("tender", "rfq", "buyer_request"),
        reliability="A_MINUS",
        enabled=False,
        health="NOT_CONNECTED",
    )

    async def search_demands(self, *, hs_code: str | None, country_iso3: str | None, keyword: str | None) -> list[dict]:
        return []
