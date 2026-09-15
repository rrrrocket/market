from __future__ import annotations

import asyncio
import calendar
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

import httpx

from app.integrations.base import ProviderMetadata
from app.integrations.country_codes import (
    comma_separated_comtrade_reporters,
    comma_separated_m49,
    comtrade_area_to_iso3,
)


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
        self,
        hs_code: str,
        year: int,
        month: int,
        reporter: str | None = None,
        partner: str | None = None,
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

    async def get_imports(
        self, hs_code: str, year: int, reporter: str | None = None, partner: str | None = None
    ) -> list[TradeRecord]:
        return self._select("IMPORT", hs_code, year, reporter, partner)

    async def get_exports(
        self, hs_code: str, year: int, reporter: str | None = None, partner: str | None = None
    ) -> list[TradeRecord]:
        return self._select("EXPORT", hs_code, year, reporter, partner)

    async def get_monthly_imports(
        self,
        hs_code: str,
        year: int,
        month: int,
        reporter: str | None = None,
        partner: str | None = None,
    ) -> list[TradeRecord]:
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

    def _select(
        self, flow: str, hs_code: str, year: int, reporter: str | None, partner: str | None
    ) -> list[TradeRecord]:
        records = [TradeRecord(**record) for record in self.payload.get("records", [])]
        for market in self.payload.get("markets", []):
            value = market["imports"].get(str(year))
            if value is None:
                continue
            records.append(
                TradeRecord(
                    "HS2022",
                    self.payload["hs_code"],
                    year,
                    market["iso3"],
                    "WLD",
                    "IMPORT",
                    value,
                    value / market.get("unit_value", 100),
                )
            )
            records.append(
                TradeRecord(
                    "HS2022",
                    self.payload["hs_code"],
                    year,
                    market["iso3"],
                    "CHN",
                    "IMPORT",
                    value * market["china_share"].get(str(year), 0),
                )
            )
            if year == max(map(int, market["imports"])):
                for supplier, share in market.get("supplier_shares", {}).items():
                    if supplier != "CHN":
                        records.append(
                            TradeRecord(
                                "HS2022",
                                self.payload["hs_code"],
                                year,
                                market["iso3"],
                                supplier,
                                "IMPORT",
                                value * share,
                            )
                        )
        return [
            r
            for r in records
            if r.flow == flow
            and r.hs_code == hs_code
            and r.year == year
            and (reporter is None or r.reporter_iso3 == reporter)
            and (partner is None or r.partner_iso3 == partner)
        ]

    @property
    def source_identifier(self) -> str:
        return f"fixture:{self.fixture_path.name}"

    def snapshot_payload(self, records: list[TradeRecord]) -> list[dict]:
        return [asdict(record) for record in records]


class ComtradeTradeDataProvider:
    source_type = "UN_COMTRADE"
    base_url = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"

    def __init__(
        self,
        api_key: str = "",
        client: httpx.AsyncClient | None = None,
        *,
        base_url: str = "https://comtradeapi.un.org/public/v1/preview",
        final_base_url: str = "https://comtradeapi.un.org/data/v1/get",
        max_concurrency: int = 4,
        retry_attempts: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.final_base_url = final_base_url.rstrip("/")
        self.client = client or httpx.AsyncClient(timeout=45)
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self.retry_attempts = max(1, retry_attempts)
        self.retry_delay_seconds = max(0, retry_delay_seconds)
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
        return self.final_base_url if self.api_key else self.base_url

    def snapshot_payload(self, records: list[TradeRecord]) -> list[dict]:
        payload = []
        for record in records:
            item = asdict(record)
            item["period_start"] = (
                record.period_start.isoformat() if record.period_start else None
            )
            item["period_end"] = record.period_end.isoformat() if record.period_end else None
            payload.append(item)
        return payload

    async def get_imports(
        self, hs_code: str, year: int, reporter: str | None = None, partner: str | None = None
    ) -> list[TradeRecord]:
        return await self._fetch("M", hs_code, year, reporter, partner)

    async def get_exports(
        self, hs_code: str, year: int, reporter: str | None = None, partner: str | None = None
    ) -> list[TradeRecord]:
        return await self._fetch("X", hs_code, year, reporter, partner)

    async def get_monthly_imports(
        self,
        hs_code: str,
        year: int,
        month: int,
        reporter: str | None = None,
        partner: str | None = None,
    ) -> list[TradeRecord]:
        if not 1 <= month <= 12:
            raise ValueError("month must be between 1 and 12")
        return await self._fetch("M", hs_code, year, reporter, partner, month=month)

    async def _fetch(
        self,
        flow_code: str,
        hs_code: str,
        year: int,
        reporter: str | None,
        partner: str | None,
        month: int | None = None,
    ) -> list[TradeRecord]:
        period = f"{year}{month:02d}" if month else str(year)
        frequency = "M" if month else "A"
        api_base = self.final_base_url if self.api_key else self.base_url
        url = f"{api_base}/C/{frequency}/HS"
        params = {
            "period": period,
            "cmdCode": hs_code,
            "flowCode": flow_code,
            "reporterCode": comma_separated_comtrade_reporters(reporter),
            "partnerCode": comma_separated_m49(partner),
            "partner2Code": "0",
            "customsCode": "C00",
            "motCode": "0",
            "maxRecords": 250_000 if self.api_key else 500,
        }
        if self.api_key:
            headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        else:
            headers = {}
        response = None
        last_request_error: httpx.RequestError | None = None
        async with self._semaphore:
            for attempt in range(self.retry_attempts):
                try:
                    response = await self.client.get(url, params=params, headers=headers)
                except httpx.RequestError as exc:
                    last_request_error = exc
                    if attempt + 1 >= self.retry_attempts:
                        raise
                    await asyncio.sleep(self.retry_delay_seconds * (2**attempt))
                    continue
                if response.status_code < 500 and response.status_code != 429:
                    break
                if attempt + 1 < self.retry_attempts:
                    await asyncio.sleep(self.retry_delay_seconds * (2**attempt))
        if response is None:
            if last_request_error:
                raise last_request_error
            raise RuntimeError("UN Comtrade request returned no response")
        response.raise_for_status()
        data = response.json().get("data", [])
        start = date(year, month, 1) if month else date(year, 1, 1)
        end = (
            date(year, month, calendar.monthrange(year, month)[1]) if month else date(year, 12, 31)
        )
        records = []
        for row in data:
            reporter_iso3 = row.get("reporterISO") or comtrade_area_to_iso3(
                row.get("reporterCode")
            )
            partner_iso3 = row.get("partnerISO") or comtrade_area_to_iso3(
                row.get("partnerCode")
            )
            records.append(
                TradeRecord(
                    classification=row.get("classificationCode") or "HS",
                    hs_code=str(row.get("cmdCode", hs_code)),
                    year=year,
                    reporter_iso3=reporter_iso3,
                    partner_iso3=partner_iso3,
                    flow="IMPORT" if flow_code == "M" else "EXPORT",
                    trade_value_usd=float(row.get("primaryValue") or 0),
                    net_weight_kg=float(row["netWgt"]) if row.get("netWgt") is not None else None,
                    quantity=float(row["qty"]) if row.get("qty") is not None else None,
                    quantity_unit=row.get("qtyUnitAbbr"),
                    period_type="MONTH" if frequency == "M" else "YEAR",
                    period_start=start,
                    period_end=end,
                )
            )
        return records


def payload_checksum(payload: dict | list) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
