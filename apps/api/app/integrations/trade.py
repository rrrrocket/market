from __future__ import annotations

import calendar
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

import httpx

from app.integrations.base import ProviderMetadata


@dataclass(frozen=True)
class TradeRecord:
    classification: str
    hs_code: str
    year: int
    reporter_iso3: str
    partner_iso3: str
    flow: str
    trade_value_usd: float
    net_weight_kg: float | None = None
    quantity: float | None = None
    quantity_unit: str | None = None
    period_type: str = "YEAR"
    period_start: date | None = None
    period_end: date | None = None


class TradeDataProvider(Protocol):
    source_type: str
    source_identifier: str

    async def get_imports(
        self, hs_code: str, year: int, reporter: str | None = None, partner: str | None = None
    ) -> list[TradeRecord]: ...

    async def get_exports(
        self, hs_code: str, year: int, reporter: str | None = None, partner: str | None = None
    ) -> list[TradeRecord]: ...

    async def get_monthly_imports(
        self, hs_code: str, year: int, month: int,
        reporter: str | None = None, partner: str | None = None,
    ) -> list[TradeRecord]: ...

    def snapshot_payload(self, records: list[TradeRecord]) -> list[dict]: ...


class FixtureTradeDataProvider:
    source_type = "FIXTURE"

    def __init__(self, fixture_path: Path) -> None:
        self.fixture_path = fixture_path
        self.payload = json.loads(fixture_path.read_text())
        self.metadata = ProviderMetadata(
            code="COMTRADE_FIXTURE",
            name="UN Comtrade fixture",
            category="TRADE",
            capabilities=("annual_imports", "monthly_imports", "annual_exports"),
            reliability="A",
            enabled=True,
            health="TEST_DATA",
        )

    async def get_imports(self, hs_code: str, year: int, reporter: str | None = None, partner: str | None = None) -> list[TradeRecord]:
        return self._select("IMPORT", hs_code, year, reporter, partner)

    async def get_exports(self, hs_code: str, year: int, reporter: str | None = None, partner: str | None = None) -> list[TradeRecord]:
        return self._select("EXPORT", hs_code, year, reporter, partner)

    async def get_monthly_imports(self, hs_code: str, year: int, month: int, reporter: str | None = None, partner: str | None = None) -> list[TradeRecord]:
        if not 1 <= month <= 12:
            raise ValueError("month must be between 1 and 12")
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        return [
            TradeRecord(
                classification=record.classification,
                hs_code=record.hs_code,
                year=record.year,
                reporter_iso3=record.reporter_iso3,
                partner_iso3=record.partner_iso3,
                flow=record.flow,
                trade_value_usd=record.trade_value_usd / 12,
                net_weight_kg=record.net_weight_kg / 12 if record.net_weight_kg else None,
                period_type="MONTH",
                period_start=start,
                period_end=end,
            )
            for record in self._select("IMPORT", hs_code, year, reporter, partner)
        ]

    def _select(self, flow: str, hs_code: str, year: int, reporter: str | None, partner: str | None) -> list[TradeRecord]:
        records = [TradeRecord(**record) for record in self.payload.get("records", [])]
        for market in self.payload.get("markets", []):
            value = market["imports"].get(str(year))
            if value is None:
                continue
            records.append(TradeRecord("HS2022", self.payload["hs_code"], year, market["iso3"], "WLD", "IMPORT", value, value / market.get("unit_value", 100)))
            records.append(TradeRecord("HS2022", self.payload["hs_code"], year, market["iso3"], "CHN", "IMPORT", value * market["china_share"].get(str(year), 0)))
            if year == max(map(int, market["imports"])):
                for supplier, share in market.get("supplier_shares", {}).items():
                    if supplier != "CHN":
                        records.append(TradeRecord("HS2022", self.payload["hs_code"], year, market["iso3"], supplier, "IMPORT", value * share))
        return [r for r in records if r.flow == flow and r.hs_code == hs_code and r.year == year and (reporter is None or r.reporter_iso3 == reporter) and (partner is None or r.partner_iso3 == partner)]

    @property
    def source_identifier(self) -> str:
        return f"fixture:{self.fixture_path.name}"

    def snapshot_payload(self, records: list[TradeRecord]) -> list[dict]:
        return [asdict(record) for record in records]


class ComtradeTradeDataProvider:
    source_type = "UN_COMTRADE"
    base_url = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"

    def __init__(self, api_key: str = "", client: httpx.AsyncClient | None = None) -> None:
        self.api_key = api_key
        self.client = client or httpx.AsyncClient(timeout=45)
        self.metadata = ProviderMetadata(
            code="UN_COMTRADE",
            name="UN Comtrade",
            category="TRADE",
            capabilities=("annual_imports", "monthly_imports", "annual_exports"),
            reliability="A",
            enabled=True,
            health="AVAILABLE",
            rate_limit="Official public/preview API limits apply",
        )

    @property
    def source_identifier(self) -> str:
        return "https://comtradeapi.un.org/public/v1/preview/C/A/HS"

    def snapshot_payload(self, records: list[TradeRecord]) -> list[dict]:
        return [asdict(record) for record in records]

    async def get_imports(self, hs_code: str, year: int, reporter: str | None = None, partner: str | None = None) -> list[TradeRecord]:
        return await self._fetch("M", hs_code, year, reporter, partner)

    async def get_exports(self, hs_code: str, year: int, reporter: str | None = None, partner: str | None = None) -> list[TradeRecord]:
        return await self._fetch("X", hs_code, year, reporter, partner)

    async def get_monthly_imports(self, hs_code: str, year: int, month: int, reporter: str | None = None, partner: str | None = None) -> list[TradeRecord]:
        if not 1 <= month <= 12:
            raise ValueError("month must be between 1 and 12")
        return await self._fetch("M", hs_code, year, reporter, partner, month=month)

    async def _fetch(self, flow_code: str, hs_code: str, year: int, reporter: str | None, partner: str | None, month: int | None = None) -> list[TradeRecord]:
        # UN Comtrade expects numeric area codes in production. ISO input is retained
        # at the adapter boundary so a future country-code resolver remains isolated.
        period = f"{year}{month:02d}" if month else str(year)
        frequency = "M" if month else "A"
        url = f"https://comtradeapi.un.org/public/v1/preview/C/{frequency}/HS"
        params = {"period": period, "cmdCode": hs_code, "flowCode": flow_code, "reporterCode": reporter or "0", "partnerCode": partner or "0", "partner2Code": "0", "customsCode": "C00", "motCode": "0", "maxRecords": 500}
        headers = {"Ocp-Apim-Subscription-Key": self.api_key} if self.api_key else {}
        response = await self.client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json().get("data", [])
        start = date(year, month, 1) if month else date(year, 1, 1)
        end = date(year, month, calendar.monthrange(year, month)[1]) if month else date(year, 12, 31)
        return [TradeRecord(classification="HS2022", hs_code=str(row.get("cmdCode", hs_code)), year=year, reporter_iso3=row.get("reporterISO") or reporter or "WLD", partner_iso3=row.get("partnerISO") or partner or "WLD", flow="IMPORT" if flow_code == "M" else "EXPORT", trade_value_usd=float(row.get("primaryValue") or 0), net_weight_kg=float(row["netWgt"]) if row.get("netWgt") is not None else None, quantity=float(row["qty"]) if row.get("qty") is not None else None, quantity_unit=row.get("qtyUnitAbbr"), period_type=frequency == "M" and "MONTH" or "YEAR", period_start=start, period_end=end) for row in data]


def payload_checksum(payload: dict | list) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
