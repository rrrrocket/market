from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

import httpx

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
        name="Google Trends API (alpha)",
        category="SEARCH",
        capabilities=("normalized_interest",),
        reliability="B_PLUS",
        enabled=False,
        health="LIMITED_ACCESS",
    )

    async def get_keyword_interest(
        self, keyword: str, country_iso3: str, language: str
    ) -> list[dict]:
        return []


class NullExplicitDemandProvider:
    metadata = ProviderMetadata(
        code="EXPLICIT_DEMAND",
        name="Tender and RFQ integrations",
        category="TENDER",
        capabilities=("tender", "rfq", "buyer_request"),
        reliability="A_MINUS",
        enabled=False,
        health="NOT_CONNECTED",
    )

    async def search_demands(
        self, *, hs_code: str | None, country_iso3: str | None, keyword: str | None
    ) -> list[dict]:
        return []


def _localized(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return _localized(value[0]) if value else None
    if isinstance(value, dict):
        selected = value.get("eng") or value.get("ENG")
        if selected is None and value:
            selected = next(iter(value.values()))
        return _localized(selected)
    return None


def _date_time(value: object) -> datetime | None:
    text = _localized(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _number(value: object) -> float | None:
    text = _localized(value)
    if text is None:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


class TedExplicitDemandProvider:
    """European Union Tenders Electronic Daily published-notice search."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        base_url: str = "https://api.ted.europa.eu",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.AsyncClient(timeout=45)
        self.metadata = ProviderMetadata(
            code="EXPLICIT_DEMAND",
            name="TED EU Tenders",
            category="TENDER",
            capabilities=("government_tender", "published_notices"),
            reliability="A_MINUS",
            enabled=enabled,
            health="AVAILABLE" if enabled else "DISABLED",
            rate_limit="TED Search API public limits apply",
        )

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    async def search_demands(
        self, *, hs_code: str | None, country_iso3: str | None, keyword: str | None
    ) -> list[dict]:
        if not self.metadata.enabled:
            return []
        if not keyword:
            raise ValueError("TED search requires a product keyword")
        escaped = self._escape(keyword)
        query = f'(notice-title ~ "{escaped}" OR description-proc ~ "{escaped}")'
        if country_iso3:
            query += f' AND buyer-country = "{self._escape(country_iso3.upper())}"'
        fields = [
            "publication-number",
            "notice-title",
            "buyer-name",
            "buyer-country",
            "publication-date",
            "deadline",
            "description-proc",
            "total-value",
            "total-value-cur",
        ]
        response = await self.client.post(
            f"{self.base_url}/v3/notices/search",
            json={
                "query": query,
                "fields": fields,
                "page": 1,
                "limit": 100,
                "scope": "ACTIVE",
                "checkQuerySyntax": False,
                "paginationMode": "PAGE_NUMBER",
                "onlyLatestVersions": True,
            },
        )
        response.raise_for_status()
        return [self._normalize(row, hs_code) for row in response.json().get("notices", [])]

    def _normalize(self, row: dict, hs_code: str | None) -> dict:
        identifier = str(row["publication-number"])
        countries = row.get("buyer-country") or []
        country = _localized(countries) or "UNK"
        links = row.get("links", {}).get("htmlDirect", {})
        source_url = links.get("ENG") or links.get("eng") or next(iter(links.values()), None)
        published_at = _date_time(row.get("publication-date")) or datetime.now(UTC)
        deadline = _date_time(row.get("deadline"))
        return {
            "source_type": "GOVERNMENT_TENDER",
            "source_identifier": identifier,
            "buyer_name": _localized(row.get("buyer-name")),
            "buyer_country_iso3": country.upper(),
            "title": _localized(row.get("notice-title")) or identifier,
            "description": _localized(row.get("description-proc")),
            "hs_code": hs_code,
            "quantity": None,
            "quantity_unit": None,
            "budget_min": None,
            "budget_max": _number(row.get("total-value")),
            "currency": _localized(row.get("total-value-cur")),
            "deadline": deadline.isoformat() if deadline else None,
            "published_at": published_at.isoformat(),
            "requirements": {"ted_fields": row},
            "source_url": source_url,
            "status": "ACTIVE",
            "observed_type": "OBSERVED",
            "source_reliability": "A_MINUS",
        }
