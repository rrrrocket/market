from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from app.integrations.base import ProviderMetadata


@dataclass(frozen=True)
class TariffRecord:
    hs_code: str
    reporter_iso3: str
    partner_code: str
    year: int
    mfn_tariff: float | None
    preferential_tariff: float | None
    tariff_type: str | None
    nomenclature: str | None
    source_identifier: str


class TariffProvider(Protocol):
    metadata: ProviderMetadata

    async def get_tariff(
        self, hs_code: str, reporter: str, partner: str, year: int
    ) -> list[TariffRecord]: ...

    async def get_ntm(
        self, hs_code: str, reporter: str, year: int
    ) -> list[dict]: ...


class NullTariffProvider:
    metadata = ProviderMetadata(
        code="NULL_TARIFF",
        name="Tariff integration",
        category="TARIFF",
        capabilities=("tariff", "ntm"),
        reliability="A",
        enabled=False,
        health="NOT_CONNECTED",
    )

    async def get_tariff(self, hs_code: str, reporter: str, partner: str, year: int) -> list[TariffRecord]:
        return []

    async def get_ntm(self, hs_code: str, reporter: str, year: int) -> list[dict]:
        return []


class WitsTariffProvider:
    base_url = "https://wits.worldbank.org/API/V1/SDMX/V21"

    def __init__(self, client: httpx.AsyncClient | None = None, *, enabled: bool = False) -> None:
        self.client = client or httpx.AsyncClient(timeout=45)
        self.metadata = ProviderMetadata(
            code="WITS_TRAINS",
            name="WITS / UNCTAD TRAINS",
            category="TARIFF",
            capabilities=("mfn_tariff", "preferential_tariff"),
            reliability="A",
            enabled=enabled,
            health="AVAILABLE" if enabled else "DISABLED",
        )

    async def get_tariff(self, hs_code: str, reporter: str, partner: str, year: int) -> list[TariffRecord]:
        if not self.metadata.enabled:
            return []
        url = (
            f"{self.base_url}/datasource/TRN/reporter/{reporter}/partner/{partner}"
            f"/product/{hs_code}/year/{year}/datatype/reported"
        )
        response = await self.client.get(url, params={"format": "JSON"})
        response.raise_for_status()
        payload = response.json()
        series = payload.get("dataSets", [{}])[0].get("series", {})
        records: list[TariffRecord] = []
        for value in series.values():
            observations = value.get("observations", {})
            tariff = next(iter(observations.values()), [None])[0] if observations else None
            records.append(
                TariffRecord(
                    hs_code=hs_code,
                    reporter_iso3=reporter.upper(),
                    partner_code=partner.upper(),
                    year=year,
                    mfn_tariff=float(tariff) if tariff is not None else None,
                    preferential_tariff=None,
                    tariff_type=value.get("TARIFFTYPE"),
                    nomenclature=value.get("NOMENCODE"),
                    source_identifier=url,
                )
            )
        return records

    async def get_ntm(self, hs_code: str, reporter: str, year: int) -> list[dict]:
        return []


class WtoTariffProvider(NullTariffProvider):
    def __init__(self, api_key: str = "", *, enabled: bool = False) -> None:
        self.api_key = api_key
        active = enabled and bool(api_key)
        self.metadata = ProviderMetadata(
            code="WTO",
            name="WTO Timeseries API",
            category="TARIFF",
            capabilities=("bound_tariff", "applied_tariff", "preferential_tariff", "ntm"),
            reliability="A",
            enabled=active,
            health="AVAILABLE" if active else "AUTH_REQUIRED",
            rate_limit="Subscription plan limits apply",
        )


class FixtureTariffProvider(NullTariffProvider):
    metadata = ProviderMetadata(
        code="TARIFF_FIXTURE",
        name="Tariff fixture",
        category="TARIFF",
        capabilities=("mfn_tariff",),
        reliability="A",
        enabled=True,
        health="TEST_DATA",
    )

    async def get_tariff(self, hs_code: str, reporter: str, partner: str, year: int) -> list[TariffRecord]:
        if hs_code != "902620" or reporter.upper() != "TUR":
            return []
        return [TariffRecord(hs_code, "TUR", partner.upper(), year, 4.2, None, "MFN", "H6", "fixture:tariff")]
