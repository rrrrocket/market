from __future__ import annotations

import asyncio
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
WORLD_BANK_UNITS = {
    "gdp_usd": "USD",
    "gdp_growth": "PERCENT",
    "gdp_per_capita": "USD_PER_PERSON",
    "population": "PERSON",
    "household_consumption": "USD",
    "internet_penetration": "PERCENT",
    "imports_percent_gdp": "PERCENT",
    "trade_percent_gdp": "PERCENT",
    "urbanization": "PERCENT",
    "inflation": "PERCENT",
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
        base_url: str = "https://api.worldbank.org/v2",
    ) -> None:
        self.client = client or httpx.AsyncClient(timeout=30)
        self.base_url = base_url.rstrip("/")
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

    async def get_countries_metrics(
        self,
        country_iso3_codes: list[str],
        *,
        start_year: int,
        end_year: int,
        chunk_size: int = 50,
    ) -> list[CountryMetricRecord]:
        """Fetch the latest reported value per indicator/country in batched calls."""
        if not self.metadata.enabled:
            return []
        requested = {code.upper() for code in country_iso3_codes}
        country_response = await self.client.get(
            f"{self.base_url}/country",
            params={"format": "json", "per_page": 400},
        )
        country_response.raise_for_status()
        country_payload = country_response.json()
        country_rows = (
            country_payload[1]
            if isinstance(country_payload, list) and len(country_payload) > 1
            else []
        )
        supported = {
            str(row.get("id") or "").upper()
            for row in country_rows
            if row.get("region", {}).get("value") != "Aggregates"
        }
        requested &= supported
        chunks = [
            sorted(requested)[offset : offset + chunk_size]
            for offset in range(0, len(requested), chunk_size)
        ]
        semaphore = asyncio.Semaphore(5)

        async def fetch(metric_key: str, indicator: str, countries: list[str]):
            async with semaphore:
                response = await self.client.get(
                    f"{self.base_url}/country/{';'.join(countries)}/indicator/{indicator}",
                    params={
                        "format": "json",
                        "date": f"{start_year}:{end_year}",
                        "per_page": max(1000, len(countries) * (end_year - start_year + 1)),
                    },
                )
                response.raise_for_status()
                payload = response.json()
                rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
                latest: dict[str, dict] = {}
                for row in rows:
                    iso3 = str(row.get("countryiso3code") or "").upper()
                    if iso3 not in requested or row.get("value") is None:
                        continue
                    if iso3 not in latest or int(row["date"]) > int(latest[iso3]["date"]):
                        latest[iso3] = row
                return [
                    CountryMetricRecord(
                        country_iso3=iso3,
                        metric_key=metric_key,
                        value=float(row["value"]),
                        unit=WORLD_BANK_UNITS.get(metric_key),
                        period_year=int(row["date"]),
                        source_identifier=f"World Bank {indicator}",
                    )
                    for iso3, row in latest.items()
                ]

        batches = await asyncio.gather(
            *(
                fetch(metric_key, indicator, chunk)
                for metric_key, indicator in WORLD_BANK_INDICATORS.items()
                for chunk in chunks
            )
        )
        return [record for batch in batches for record in batch]


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
            CountryMetricRecord(
                "TUR", "gdp_usd", 1_320_000_000_000, "USD", period_year, "fixture:world_bank"
            ),
            CountryMetricRecord(
                "TUR", "population", 87_700_000, "PERSON", period_year, "fixture:world_bank"
            ),
        ]
