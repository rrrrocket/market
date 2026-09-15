from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from xml.etree import ElementTree

import httpx

from app.integrations.base import ProviderMetadata
from app.integrations.country_codes import iso3_to_m49


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

    async def get_ntm(self, hs_code: str, reporter: str, year: int) -> list[dict]: ...


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

    async def get_tariff(
        self, hs_code: str, reporter: str, partner: str, year: int
    ) -> list[TariffRecord]:
        return []

    async def get_ntm(self, hs_code: str, reporter: str, year: int) -> list[dict]:
        return []


class WitsTariffProvider:
    base_url = "https://wits.worldbank.org/API/V1/SDMX/V21"

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        enabled: bool = False,
        base_url: str = "https://wits.worldbank.org/API/V1/SDMX/V21",
    ) -> None:
        self.client = client or httpx.AsyncClient(timeout=45)
        self.base_url = base_url.rstrip("/")
        self.metadata = ProviderMetadata(
            code="WITS_TRAINS",
            name="WITS / UNCTAD TRAINS",
            category="TARIFF",
            capabilities=("mfn_tariff", "preferential_tariff"),
            reliability="A",
            enabled=enabled,
            health="AVAILABLE" if enabled else "DISABLED",
        )

    async def get_tariff(
        self, hs_code: str, reporter: str, partner: str, year: int
    ) -> list[TariffRecord]:
        if not self.metadata.enabled:
            return []
        mfn = await self._fetch_series(hs_code, reporter, "000", year)
        preferential = await self._fetch_series(
            hs_code, reporter, iso3_to_m49(partner).zfill(3), year
        )
        if not mfn and not preferential:
            return []
        mfn_value = next(
            (row["value"] for row in mfn if row.get("tariff_type") == "MFN"),
            mfn[0]["value"] if mfn else None,
        )
        preferential_value = next(
            (row["value"] for row in preferential if row.get("tariff_type") == "PREF"),
            preferential[0]["value"] if preferential else None,
        )
        row = next(iter(preferential or mfn))
        return [
            TariffRecord(
                hs_code=hs_code,
                reporter_iso3=reporter.upper(),
                partner_code=partner.upper(),
                year=year,
                mfn_tariff=mfn_value,
                preferential_tariff=preferential_value,
                tariff_type="PREF" if preferential_value is not None else "MFN",
                nomenclature=row.get("nomenclature"),
                source_identifier=row["source_identifier"],
            )
        ]

    async def _fetch_series(
        self, hs_code: str, reporter: str, partner_m49: str, year: int
    ) -> list[dict]:
        reporter_m49 = iso3_to_m49(reporter).zfill(3)
        key = f"A.{reporter_m49}.{partner_m49}.{hs_code}.reported"
        url = f"{self.base_url}/rest/data/DF_WITS_Tariff_TRAINS/{key}"
        response = await self.client.get(
            url,
            params={"startPeriod": year, "endPeriod": year, "detail": "Full"},
            headers={"Accept": "application/vnd.sdmx.genericdata+xml;version=2.1"},
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        rows: list[dict] = []
        for series in root.findall(".//{*}Series"):
            attributes = {
                value.attrib.get("id"): value.attrib.get("value")
                for value in series.findall(".//{*}Value")
            }
            for observation in series.findall("./{*}Obs"):
                value_node = observation.find("./{*}ObsValue")
                period_node = observation.find("./{*}ObsDimension")
                if value_node is None or value_node.attrib.get("value") is None:
                    continue
                rows.append(
                    {
                        "value": float(value_node.attrib["value"]),
                        "year": int(period_node.attrib.get("value", year))
                        if period_node is not None
                        else year,
                        "tariff_type": attributes.get("TARIFFTYPE"),
                        "nomenclature": attributes.get("NOMENCODE"),
                        "source_identifier": url,
                    }
                )
        return rows

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

    async def get_tariff(
        self, hs_code: str, reporter: str, partner: str, year: int
    ) -> list[TariffRecord]:
        if hs_code != "902620" or reporter.upper() != "TUR":
            return []
        return [
            TariffRecord(
                hs_code, "TUR", partner.upper(), year, 4.2, None, "MFN", "H6", "fixture:tariff"
            )
        ]
