from dataclasses import dataclass
from typing import Protocol

import httpx

from app.integrations.base import ProviderMetadata


@dataclass
class SupplySummary:
    hs_code: str
    supplier_count: int = 0
    product_count: int = 0
    active_offer_count: int = 0
    min_price: float | None = None
    median_price: float | None = None
    currency: str | None = None
    moq_min: float | None = None
    moq_median: float | None = None
    stock_total: float | None = None
    lead_time_min: float | None = None
    lead_time_median: float | None = None
    certified_supplier_count: int | None = None
    dropship_supplier_count: int | None = None
    historical_delivery_score: float | None = None
    quality_score: float | None = None
    available: bool = False


class SupplierNetworkClient(Protocol):
    metadata: ProviderMetadata

    async def get_supply_summary(self, hs_code: str) -> SupplySummary: ...
    async def get_products(self, hs_code: str) -> list[dict]: ...
    async def get_offers(self, hs_code: str) -> list[dict]: ...
    async def get_capability_summary(self, hs_code: str) -> dict | None: ...


class NullSupplierNetworkClient:
    metadata = ProviderMetadata(
        code="SUPPLIER_NETWORK",
        name="Matrix One Supplier Network",
        category="SUPPLY",
        capabilities=("summary", "products", "offers", "capabilities"),
        reliability="A",
        enabled=False,
        health="AUTH_REQUIRED",
    )

    async def get_supply_summary(self, hs_code: str) -> SupplySummary:
        return SupplySummary(hs_code=hs_code)

    async def get_products(self, hs_code: str) -> list[dict]:
        return []

    async def get_offers(self, hs_code: str) -> list[dict]:
        return []

    async def get_capability_summary(self, hs_code: str) -> dict | None:
        return None


class HttpSupplierNetworkClient:
    def __init__(self, base_url: str, api_key: str, *, timeout_seconds: float = 20) -> None:
        self.base_url, self.api_key = base_url.rstrip("/"), api_key
        self.timeout_seconds = timeout_seconds
        self.metadata = ProviderMetadata(
            code="SUPPLIER_NETWORK",
            name="Matrix One Supplier Network",
            category="SUPPLY",
            capabilities=("summary", "products", "offers", "capabilities"),
            reliability="A",
            enabled=True,
            health="AVAILABLE",
        )

    async def _get(self, path: str) -> dict | list:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            return response.json()

    async def get_supply_summary(self, hs_code: str) -> SupplySummary:
        payload = await self._get(f"/api/v1/supply/summary/{hs_code}")
        assert isinstance(payload, dict)
        values = dict(payload)
        values["hs_code"] = hs_code
        values["available"] = True
        return SupplySummary(**values)

    async def get_products(self, hs_code: str) -> list[dict]:
        payload = await self._get(f"/api/v1/supply/products?hs_code={hs_code}")
        return payload if isinstance(payload, list) else []

    async def get_offers(self, hs_code: str) -> list[dict]:
        payload = await self._get(f"/api/v1/supply/offers?hs_code={hs_code}")
        return payload if isinstance(payload, list) else []

    async def get_capability_summary(self, hs_code: str) -> dict | None:
        payload = await self._get(f"/api/v1/supply/capabilities?hs_code={hs_code}")
        return payload if isinstance(payload, dict) else None
