from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
import os
import time
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx
import pycountry
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.integrations.country_codes import (
    comma_separated_comtrade_reporters,
    comtrade_area_to_iso3,
)
from app.models import (
    AnalysisRun,
    Country,
    DataSource,
    HsProduct,
    MarketOpportunity,
    SourceSnapshot,
    TradeObservation,
)
from app.scoring.engine import SCORE_VERSION
from app.services.analysis import execute_analysis, upsert_observation


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utcnow().isoformat()


class ComtradeLocalPipeline:
    """Download, persist, import, and analyze the HS2022 market universe."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = Path(settings.comtrade_data_dir)
        self.raw_dir = self.root / "raw"
        self.manifest_path = self.root / "manifest.json"

    def ensure_storage(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @property
    def years(self) -> list[int]:
        return list(
            range(self.settings.trade_data_start_year, self.settings.trade_data_end_year + 1)
        )

    def hs_codes(self, db: Session) -> list[str]:
        return list(
            db.scalars(
                select(HsProduct.hs_code)
                .where(HsProduct.level == 6, HsProduct.is_active.is_(True))
                .order_by(HsProduct.hs_code)
            ).all()
        )

    def batches(self, db: Session) -> list[list[str]]:
        codes = self.hs_codes(db)
        size = max(1, self.settings.comtrade_batch_size)
        return [codes[index : index + size] for index in range(0, len(codes), size)]

    def load_manifest(self) -> dict[str, Any]:
        if not self.manifest_path.exists():
            return {}
        return json.loads(self.manifest_path.read_text())

    def write_manifest(self, manifest: dict[str, Any]) -> None:
        manifest["updated_at"] = iso_now()
        temporary = self.manifest_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        os.replace(temporary, self.manifest_path)

    def initial_manifest(self, db: Session) -> dict[str, Any]:
        batches = self.batches(db)
        existing = self.load_manifest()
        signature = {
            "classification": "HS2022",
            "years": self.years,
            "origin_iso3": self.settings.default_origin_iso3,
            "batch_size": self.settings.comtrade_batch_size,
            "total_hs": sum(len(batch) for batch in batches),
            "total_batches": len(batches),
        }
        if existing and all(existing.get(key) == value for key, value in signature.items()):
            return existing
        return {
            **signature,
            "status": "PENDING",
            "current_batch": 0,
            "downloaded_batches": {},
            "imported_batches": [],
            "analyzed_hs": 0,
            "no_data_hs": 0,
            "failed_hs": 0,
            "records_downloaded": 0,
            "bytes_downloaded": 0,
            "created_at": iso_now(),
            "updated_at": iso_now(),
            "error": None,
        }

    async def download(self, db: Session) -> dict[str, Any]:
        if not self.settings.comtrade_api_key:
            raise ValueError("COMTRADE_API_KEY is required")
        self.ensure_storage()
        manifest = self.initial_manifest(db)
        batches = self.batches(db)
        reporters = comma_separated_comtrade_reporters(
            ",".join(
                country.alpha_3
                for country in pycountry.countries
                if country.alpha_3 != self.settings.default_origin_iso3
            )
        )
        downloaded = manifest.setdefault("downloaded_batches", {})
        manifest.update({"status": "DOWNLOADING", "error": None, "started_at": iso_now()})
        self.write_manifest(manifest)
        url = f"{self.settings.comtrade_final_api_base_url.rstrip('/')}/C/A/HS"
        timeout = httpx.Timeout(180, connect=30)
        last_request_started = 0.0
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                for index, codes in enumerate(batches, 1):
                    key = str(index)
                    existing = downloaded.get(key)
                    if existing and (self.raw_dir / existing["file"]).exists():
                        continue
                    elapsed = time.monotonic() - last_request_started
                    if elapsed < 1.05:
                        await asyncio.sleep(1.05 - elapsed)
                    params = {
                        "period": ",".join(map(str, self.years)),
                        "cmdCode": ",".join(codes),
                        "flowCode": "M",
                        "reporterCode": reporters,
                        "partnerCode": f"0,{self._origin_m49()}",
                        "partner2Code": "0",
                        "customsCode": "C00",
                        "motCode": "0",
                        "maxRecords": 100_000,
                    }
                    headers = {
                        "Ocp-Apim-Subscription-Key": self.settings.comtrade_api_key
                    }
                    response = None
                    for attempt in range(self.settings.provider_retry_attempts):
                        last_request_started = time.monotonic()
                        try:
                            response = await client.get(url, params=params, headers=headers)
                            if response.status_code < 500 and response.status_code != 429:
                                break
                        except httpx.RequestError:
                            if attempt + 1 >= self.settings.provider_retry_attempts:
                                raise
                        await asyncio.sleep(
                            self.settings.provider_retry_delay_seconds * (2**attempt)
                        )
                    if response is None:
                        raise RuntimeError(f"Batch {index} returned no response")
                    response.raise_for_status()
                    payload = response.json()
                    if payload.get("error"):
                        raise RuntimeError(f"Batch {index}: {payload['error']}")
                    rows = payload.get("data", [])
                    if len(rows) >= 100_000:
                        raise RuntimeError(
                            f"Batch {index} reached the Free API record limit; reduce batch size"
                        )
                    envelope = {
                        "metadata": {
                            "batch": index,
                            "classification": "HS as reported",
                            "classification_code": "HS",
                            "hs_codes": codes,
                            "years": self.years,
                            "origin_iso3": self.settings.default_origin_iso3,
                            "retrieved_at": iso_now(),
                            "api_count": payload.get("count", len(rows)),
                            "partial_years": [self.settings.trade_data_end_year],
                        },
                        "data": rows,
                    }
                    filename = f"hs2022-{self.years[0]}-{self.years[-1]}-{index:04d}.json.gz"
                    target = self.raw_dir / filename
                    temporary = target.with_suffix(".json.gz.tmp")
                    with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=6) as handle:
                        json.dump(envelope, handle, ensure_ascii=False, separators=(",", ":"))
                    os.replace(temporary, target)
                    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
                    downloaded[key] = {
                        "file": filename,
                        "hs_codes": codes,
                        "records": len(rows),
                        "bytes": target.stat().st_size,
                        "checksum": checksum,
                        "completed_at": iso_now(),
                    }
                    manifest["current_batch"] = index
                    manifest["records_downloaded"] = sum(
                        item["records"] for item in downloaded.values()
                    )
                    manifest["bytes_downloaded"] = sum(
                        item["bytes"] for item in downloaded.values()
                    )
                    self.write_manifest(manifest)
            manifest["status"] = "DOWNLOADED"
            manifest["download_finished_at"] = iso_now()
            self.write_manifest(manifest)
            return manifest
        except Exception as exc:
            message = self._safe_error(exc)
            manifest["status"] = "FAILED"
            manifest["error"] = message
            self.write_manifest(manifest)
            raise RuntimeError(message) from None

    def _origin_m49(self) -> str:
        country = pycountry.countries.get(alpha_3=self.settings.default_origin_iso3)
        if country is None:
            raise ValueError(f"Unknown origin: {self.settings.default_origin_iso3}")
        return str(int(country.numeric))

    def _safe_error(self, exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            return f"UN Comtrade returned HTTP {exc.response.status_code}"
        if isinstance(exc, httpx.RequestError):
            return f"UN Comtrade network error: {type(exc).__name__}"
        message = str(exc).strip() or type(exc).__name__
        if self.settings.comtrade_api_key:
            message = message.replace(self.settings.comtrade_api_key, "[REDACTED]")
        return message

    def import_downloads(self, db: Session) -> dict[str, Any]:
        manifest = self.load_manifest()
        if not manifest.get("downloaded_batches"):
            raise ValueError("No downloaded Comtrade batches are available")
        manifest.update({"status": "IMPORTING", "error": None})
        self.write_manifest(manifest)
        imported = set(manifest.setdefault("imported_batches", []))
        source = db.scalar(select(DataSource).where(DataSource.code == "UN_COMTRADE"))
        known_countries = set(db.scalars(select(Country.iso3)).all())
        try:
            for key, batch in sorted(
                manifest["downloaded_batches"].items(), key=lambda item: int(item[0])
            ):
                if int(key) in imported:
                    continue
                path = self.raw_dir / batch["file"]
                with gzip.open(path, "rt", encoding="utf-8") as handle:
                    envelope = json.load(handle)
                grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for row in envelope.get("data", []):
                    normalized = self._normalize_row(row, known_countries)
                    if normalized:
                        grouped[normalized["hs_code"]].append(normalized)
                for hs_code in batch["hs_codes"]:
                    rows = grouped.get(hs_code, [])
                    snapshot = SourceSnapshot(
                        source_id=source.id if source else None,
                        source_type="UN_COMTRADE",
                        source_identifier=f"local:{batch['file']}#{hs_code}",
                        request_payload={
                            "hs_code": hs_code,
                            "years": self.years,
                            "origin_iso3": self.settings.default_origin_iso3,
                            "reporter_scope": "ALL_ACTIVE",
                        },
                        response_payload={
                            "local_file": batch["file"],
                            "batch_checksum": batch["checksum"],
                            "record_count": len(rows),
                        },
                        checksum=hashlib.sha256(
                            f"{batch['checksum']}:{hs_code}".encode()
                        ).hexdigest(),
                        status="SUCCESS",
                    )
                    db.add(snapshot)
                    db.flush()
                    values = [
                        {
                            **row,
                            "source_snapshot_id": snapshot.id,
                        }
                        for row in rows
                    ]
                    self._upsert_trade_rows(db, values)
                if source:
                    source.enabled = True
                    source.status = "READY"
                    source.last_success_at = utcnow()
                db.commit()
                imported.add(int(key))
                manifest["imported_batches"] = sorted(imported)
                manifest["current_batch"] = int(key)
                self.write_manifest(manifest)
            manifest["status"] = "IMPORTED"
            manifest["import_finished_at"] = iso_now()
            self.write_manifest(manifest)
            # The public country dashboard reads this compact aggregate instead
            # of grouping every raw observation on every page visit.
            if db.bind and db.bind.dialect.name == "postgresql":
                db.execute(text("REFRESH MATERIALIZED VIEW country_trade_yearly"))
                db.commit()
            return manifest
        except Exception as exc:
            db.rollback()
            manifest["status"] = "FAILED"
            manifest["error"] = str(exc).strip() or type(exc).__name__
            self.write_manifest(manifest)
            raise

    def _normalize_row(
        self, row: dict[str, Any], known_countries: set[str]
    ) -> dict[str, Any] | None:
        code = str(row.get("cmdCode") or "").zfill(6)
        period = str(row.get("period") or row.get("refYear") or "")[:4]
        if len(code) != 6 or not period.isdigit():
            return None
        reporter = (row.get("reporterISO") or "").strip().upper()
        if reporter not in known_countries:
            try:
                reporter = comtrade_area_to_iso3(row.get("reporterCode"))
            except (TypeError, ValueError):
                return None
        partner_code = row.get("partnerCode")
        if str(partner_code).strip() in {"0", "000"}:
            partner = "WLD"
        else:
            partner = (row.get("partnerISO") or "").strip().upper()
            if partner not in known_countries:
                try:
                    partner = comtrade_area_to_iso3(partner_code)
                except (TypeError, ValueError):
                    return None
        year = int(period)
        return {
            "classification": row.get("classificationCode") or "HS",
            "hs_code": code,
            "period_year": year,
            "period_type": "YEAR",
            "period_start": date(year, 1, 1),
            "period_end": date(year, 12, 31),
            "reporter_iso3": reporter,
            "partner_iso3": partner,
            "flow": "IMPORT",
            "trade_value_usd": float(row.get("primaryValue") or 0),
            "net_weight_kg": float(row["netWgt"])
            if row.get("netWgt") is not None
            else None,
            "quantity": float(row["qty"]) if row.get("qty") is not None else None,
            "quantity_unit": row.get("qtyUnitAbbr"),
        }

    def _upsert_trade_rows(self, db: Session, values: list[dict[str, Any]]) -> None:
        if not values:
            return
        if db.bind and db.bind.dialect.name == "postgresql":
            for offset in range(0, len(values), 2_000):
                chunk = values[offset : offset + 2_000]
                statement = pg_insert(TradeObservation).values(chunk)
                excluded = statement.excluded
                db.execute(
                    statement.on_conflict_do_update(
                        constraint="uq_trade_observation_period",
                        set_={
                            "period_year": excluded.period_year,
                            "period_end": excluded.period_end,
                            "trade_value_usd": excluded.trade_value_usd,
                            "net_weight_kg": excluded.net_weight_kg,
                            "quantity": excluded.quantity,
                            "quantity_unit": excluded.quantity_unit,
                            "source_snapshot_id": excluded.source_snapshot_id,
                        },
                    )
                )
            return
        for item in values:
            upsert_observation(db, item)

    async def analyze(self, db: Session) -> dict[str, Any]:
        manifest = self.load_manifest()
        imported_count = len(manifest.get("imported_batches", []))
        if not manifest.get("total_batches") or imported_count < manifest["total_batches"]:
            raise ValueError("Local Comtrade files must be imported before analysis")
        manifest.update({"status": "ANALYZING", "error": None})
        self.write_manifest(manifest)
        codes = self.hs_codes(db)
        analyzed = 0
        no_data = 0
        failed = 0
        try:
            for index, hs_code in enumerate(codes, 1):
                ready = db.scalar(
                    select(func.count())
                    .select_from(MarketOpportunity)
                    .where(
                        MarketOpportunity.hs_code == hs_code,
                        MarketOpportunity.origin_iso3 == self.settings.default_origin_iso3,
                        MarketOpportunity.period_year == self.settings.latest_complete_year,
                        MarketOpportunity.score_version == SCORE_VERSION,
                    )
                )
                if ready:
                    analyzed += 1
                    continue
                completed_without_data = db.scalar(
                    select(AnalysisRun.id)
                    .where(
                        AnalysisRun.hs_code == hs_code,
                        AnalysisRun.origin_iso3 == self.settings.default_origin_iso3,
                        AnalysisRun.requested_year == self.settings.latest_complete_year,
                        AnalysisRun.status == "COMPLETED",
                        AnalysisRun.countries_succeeded == 0,
                    )
                    .limit(1)
                )
                if completed_without_data:
                    no_data += 1
                    continue
                run = AnalysisRun(
                    hs_code=hs_code,
                    origin_iso3=self.settings.default_origin_iso3,
                    requested_year=self.settings.latest_complete_year,
                )
                db.add(run)
                db.commit()
                await execute_analysis(db, run.id, self.settings)
                db.refresh(run)
                if run.status == "COMPLETED" and run.countries_succeeded:
                    analyzed += 1
                elif run.status == "COMPLETED":
                    no_data += 1
                else:
                    failed += 1
                if index % 10 == 0 or index == len(codes):
                    manifest.update(
                        {
                            "current_hs": hs_code,
                            "analyzed_hs": analyzed,
                            "no_data_hs": no_data,
                            "failed_hs": failed,
                        }
                    )
                    self.write_manifest(manifest)
            manifest["status"] = "COMPLETED"
            manifest["analysis_finished_at"] = iso_now()
            self.write_manifest(manifest)
            return manifest
        except Exception as exc:
            manifest["status"] = "FAILED"
            manifest["error"] = str(exc).strip() or type(exc).__name__
            self.write_manifest(manifest)
            raise


def pipeline_status(settings: Settings, db: Session) -> dict[str, Any]:
    pipeline = ComtradeLocalPipeline(settings)
    manifest = pipeline.load_manifest()
    downloaded = manifest.get("downloaded_batches", {})
    total_batches = manifest.get("total_batches", 0)
    downloaded_batches = len(downloaded)
    imported_batches = len(manifest.get("imported_batches", []))
    total_hs = manifest.get(
        "total_hs",
        db.scalar(
            select(func.count())
            .select_from(HsProduct)
            .where(HsProduct.level == 6, HsProduct.is_active.is_(True))
        )
        or 0,
    )
    analyzed_hs = (
        db.scalar(
            select(func.count(func.distinct(MarketOpportunity.hs_code))).where(
                MarketOpportunity.period_year == settings.latest_complete_year,
                MarketOpportunity.score_version == SCORE_VERSION,
            )
        )
        or 0
    )
    no_data_hs = manifest.get("no_data_hs", 0)
    failed_hs = manifest.get("failed_hs", 0)
    processed_hs = min(total_hs, analyzed_hs + no_data_hs + failed_hs)
    return {
        "status": manifest.get("status", "NOT_STARTED"),
        "years": manifest.get(
            "years",
            list(range(settings.trade_data_start_year, settings.trade_data_end_year + 1)),
        ),
        "complete_through": settings.latest_complete_year,
        "partial_years": [settings.trade_data_end_year],
        "total_hs": total_hs,
        "batch_size": manifest.get("batch_size", settings.comtrade_batch_size),
        "total_batches": total_batches,
        "downloaded_batches": downloaded_batches,
        "imported_batches": imported_batches,
        "download_percent": round(downloaded_batches / total_batches * 100, 2)
        if total_batches
        else 0,
        "import_percent": round(imported_batches / total_batches * 100, 2)
        if total_batches
        else 0,
        "analyzed_hs": analyzed_hs,
        "analysis_percent": round(processed_hs / total_hs * 100, 2) if total_hs else 0,
        "records_downloaded": manifest.get("records_downloaded", 0),
        "bytes_downloaded": manifest.get("bytes_downloaded", 0),
        "current_batch": manifest.get("current_batch", 0),
        "current_hs": manifest.get("current_hs"),
        "no_data_hs": no_data_hs,
        "failed_hs": failed_hs,
        "updated_at": manifest.get("updated_at"),
        "error": manifest.get("error"),
    }
