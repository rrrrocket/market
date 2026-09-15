from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import Protocol

import httpx

from app.integrations.base import ProviderMetadata


class MarketplaceProvider(Protocol):
    metadata: ProviderMetadata

    async def search_products(
        self, marketplace: str, country_iso3: str, keyword: str
    ) -> list[dict]: ...
    async def get_product(self, marketplace: str, product_ref: str) -> dict | None: ...
    async def get_keyword_metrics(
        self, marketplace: str, country_iso3: str, keyword: str
    ) -> list[dict]: ...
    async def get_category_metrics(
        self, marketplace: str, country_iso3: str, category: str
    ) -> list[dict]: ...


class NullMarketplaceProvider:
    metadata = ProviderMetadata(
        code="MARKETPLACES",
        name="eBay Browse API",
        category="MARKETPLACE",
        capabilities=("products", "keyword_metrics", "category_metrics"),
        reliability="B",
        enabled=False,
        health="AUTH_REQUIRED",
    )

    async def search_products(
        self, marketplace: str, country_iso3: str, keyword: str
    ) -> list[dict]:
        return []

    async def get_product(self, marketplace: str, product_ref: str) -> dict | None:
        return None

    async def get_keyword_metrics(
        self, marketplace: str, country_iso3: str, keyword: str
    ) -> list[dict]:
        return []

    async def get_category_metrics(
        self, marketplace: str, country_iso3: str, category: str
    ) -> list[dict]:
        return []


class HttpMarketplaceProvider:
    """Adapter for an authorized marketplace gateway owned by Matrix One.

    The gateway normalizes marketplace-specific authentication and exposes the
    stable endpoints used here. This avoids embedding Amazon/Ozon/Wildberries
    credentials or response formats in the Market service.
    """

    def __init__(
        self,
        provider_code: str,
        base_url: str,
        api_key: str,
        *,
        timeout_seconds: float = 20,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.metadata = ProviderMetadata(
            code=provider_code.upper(),
            name=f"{provider_code} marketplace gateway",
            category="MARKETPLACE",
            capabilities=("products", "keyword_metrics", "category_metrics"),
            reliability="A_MINUS",
            enabled=True,
            health="AVAILABLE",
        )

    async def _get(self, path: str, params: dict | None = None) -> dict | list:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                f"{self.base_url}{path}",
                params=params,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            return response.json()

    async def search_products(
        self, marketplace: str, country_iso3: str, keyword: str
    ) -> list[dict]:
        payload = await self._get(
            "/api/v1/products/search",
            {"marketplace": marketplace, "country_iso3": country_iso3, "q": keyword},
        )
        return payload if isinstance(payload, list) else payload.get("records", [])

    async def get_product(self, marketplace: str, product_ref: str) -> dict | None:
        payload = await self._get(f"/api/v1/products/{product_ref}", {"marketplace": marketplace})
        return payload if isinstance(payload, dict) else None

    async def get_keyword_metrics(
        self, marketplace: str, country_iso3: str, keyword: str
    ) -> list[dict]:
        payload = await self._get(
            "/api/v1/metrics/keywords",
            {"marketplace": marketplace, "country_iso3": country_iso3, "keyword": keyword},
        )
        return payload if isinstance(payload, list) else payload.get("records", [])

    async def get_category_metrics(
        self, marketplace: str, country_iso3: str, category: str
    ) -> list[dict]:
        payload = await self._get(
            "/api/v1/metrics/categories",
            {"marketplace": marketplace, "country_iso3": country_iso3, "category": category},
        )
        return payload if isinstance(payload, list) else payload.get("records", [])


class EbayMarketplaceProvider:
    """Observed listing data from the official eBay Browse API."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        base_url: str = "https://api.ebay.com",
        oauth_url: str = "https://api.ebay.com/identity/v1/oauth2/token",
        timeout_seconds: float = 20,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self.oauth_url = oauth_url
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.AsyncClient(timeout=timeout_seconds)
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self.metadata = ProviderMetadata(
            code="MARKETPLACES",
            name="eBay Browse API",
            category="MARKETPLACE",
            capabilities=("products", "keyword_metrics", "listing_observations"),
            reliability="A_MINUS",
            enabled=True,
            health="AVAILABLE",
            rate_limit="eBay Buy API application limits apply",
        )

    async def _token(self) -> str:
        now = datetime.now(UTC)
        if self._access_token and self._token_expires_at and now < self._token_expires_at:
            return self._access_token
        encoded = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        response = await self.client.post(
            self.oauth_url,
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
        )
        response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        self._token_expires_at = now + timedelta(
            seconds=max(60, payload.get("expires_in", 7200) - 60)
        )
        return self._access_token

    async def _get(self, path: str, marketplace: str, params: dict | None = None) -> dict:
        token = await self._token()
        response = await self.client.get(
            f"{self.base_url}{path}",
            params=params,
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": marketplace,
            },
        )
        response.raise_for_status()
        return response.json()

    async def search_products(
        self, marketplace: str, country_iso3: str, keyword: str
    ) -> list[dict]:
        payload = await self._get(
            "/buy/browse/v1/item_summary/search",
            marketplace,
            {"q": keyword, "limit": 50},
        )
        return payload.get("itemSummaries", [])

    async def get_product(self, marketplace: str, product_ref: str) -> dict | None:
        return await self._get(f"/buy/browse/v1/item/{product_ref}", marketplace)

    async def get_keyword_metrics(
        self, marketplace: str, country_iso3: str, keyword: str
    ) -> list[dict]:
        items = await self.search_products(marketplace, country_iso3, keyword)
        observed_at = datetime.now(UTC).isoformat()
        sellers = {
            item.get("seller", {}).get("username")
            for item in items
            if item.get("seller", {}).get("username")
        }
        return [
            {
                "observed_at": observed_at,
                "product_ref": item.get("itemId"),
                "price": item.get("price", {}).get("value"),
                "currency": item.get("price", {}).get("currency"),
                "seller_count": len(sellers) or None,
                "promotion_flag": bool(item.get("marketingPrice")),
                "stock_status": "AVAILABLE" if item.get("buyingOptions") else None,
                "observed_type": "OBSERVED",
                "confidence": 90,
            }
            for item in items
            if item.get("itemId")
        ]

    async def get_category_metrics(
        self, marketplace: str, country_iso3: str, category: str
    ) -> list[dict]:
        payload = await self._get(
            "/buy/browse/v1/item_summary/search",
            marketplace,
            {"category_ids": category, "limit": 50},
        )
        return payload.get("itemSummaries", [])
