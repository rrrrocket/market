from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from app.integrations.base import ProviderMetadata

WORLD_BANK_INDICATORS = {
    "gdp_usd": "NY.GDP.MKTP.CD",
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",
    "gdp_per_capita": "NY.GDP.PCAP.CD",
    "population": "SP.POP.TOTL",
    "household_consumption": "NE.CON.PRVT.CD",
    "internet_penetration": "IT.NET.USER.ZS",
    "imports_percent_gdp": "NE.IMP.GNFS.ZS",
    "trade_percent_gdp": "NE.TRD.GNFS.ZS",
    "urbanization": "SP.URB.TOTL.IN.ZS",
    "inflation": "FP.CPI.TOTL.ZG",
}


@dataclass(frozen=True)
class CountryMetricRecord:
    country_iso3: str
    metric_key: str
    value: float | None
    unit: str | None
    period_year: int
    source_identifier: str


class MacroDataProvider(Protocol):
    metadata: ProviderMetadata

    async def get_country_metrics(
        self, country_iso3: str, year: int | None = None
    ) -> list[CountryMetricRecord]: ...


class WorldBankProvider:
    base_url = "https://api.worldbank.org/v2"

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        enabled: bool = True,
    ) -> None:
        self.client = client or httpx.AsyncClient(timeout=30)
        self.metadata = ProviderMetadata(
            code="WORLD_BANK",
            name="World Bank Indicators",
            category="MACRO",
            capabilities=tuple(WORLD_BANK_INDICATORS),
            reliability="A",
            enabled=enabled,
            health="AVAILABLE" if enabled else "DISABLED",
            rate_limit="Public API policy",
        )

    async def get_country_metrics(
        self, country_iso3: str, year: int | None = None
    ) -> list[CountryMetricRecord]:
        if not self.metadata.enabled:
            return []
        records: list[CountryMetricRecord] = []
        for metric_key, indicator in WORLD_BANK_INDICATORS.items():
            params = {"format": "json", "per_page": 20}
            if year is not None:
                params["date"] = str(year)
            response = await self.client.get(
                f"{self.base_url}/country/{country_iso3}/indicator/{indicator}",
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
            rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
            row = next((item for item in rows if item.get("value") is not None), None)
            if row:
                records.append(
                    CountryMetricRecord(
                        country_iso3=country_iso3.upper(),
                        metric_key=metric_key,
                        value=float(row["value"]),
                        unit=None,
                        period_year=int(row["date"]),
                        source_identifier=f"World Bank {indicator}",
                    )
                )
        return records


class FixtureMacroProvider:
    metadata = ProviderMetadata(
        code="WORLD_BANK_FIXTURE",
        name="World Bank fixture",
        category="MACRO",
        capabilities=("gdp_usd", "population"),
        reliability="A",
        enabled=True,
        health="TEST_DATA",
    )

    async def get_country_metrics(
        self, country_iso3: str, year: int | None = None
    ) -> list[CountryMetricRecord]:
        if country_iso3.upper() != "TUR":
            return []
        period_year = year or 2025
        return [
            CountryMetricRecord("TUR", "gdp_usd", 1_320_000_000_000, "USD", period_year, "fixture:world_bank"),
            CountryMetricRecord("TUR", "population", 87_700_000, "PERSON", period_year, "fixture:world_bank"),
        ]
