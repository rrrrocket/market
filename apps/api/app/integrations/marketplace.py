from __future__ import annotations

from typing import Protocol

from app.integrations.base import ProviderMetadata


class MarketplaceProvider(Protocol):
    metadata: ProviderMetadata

    async def search_products(self, marketplace: str, country_iso3: str, keyword: str) -> list[dict]: ...
    async def get_product(self, marketplace: str, product_ref: str) -> dict | None: ...
    async def get_keyword_metrics(self, marketplace: str, country_iso3: str, keyword: str) -> list[dict]: ...
    async def get_category_metrics(self, marketplace: str, country_iso3: str, category: str) -> list[dict]: ...


class NullMarketplaceProvider:
    metadata = ProviderMetadata(
        code="NULL_MARKETPLACE",
        name="Marketplace integrations",
        category="MARKETPLACE",
        capabilities=("products", "keyword_metrics", "category_metrics"),
        reliability="B",
        enabled=False,
        health="NOT_CONNECTED",
    )

    async def search_products(self, marketplace: str, country_iso3: str, keyword: str) -> list[dict]:
        return []

    async def get_product(self, marketplace: str, product_ref: str) -> dict | None:
        return None

    async def get_keyword_metrics(self, marketplace: str, country_iso3: str, keyword: str) -> list[dict]:
        return []

    async def get_category_metrics(self, marketplace: str, country_iso3: str, category: str) -> list[dict]:
        return []
