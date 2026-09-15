from __future__ import annotations

import csv
import json
from datetime import UTC, date, datetime
from io import BytesIO, StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.trade import payload_checksum
from app.models import (
    CountryMetric,
    DataJob,
    DataSource,
    MarketAccessMetric,
    SourceSnapshot,
    TradeObservation,
)
from app.schemas.api import DatasetImportRequest


def parse_dataset_file(format_name: str, content: bytes) -> list[dict]:
    normalized = format_name.upper()
    if normalized == "CSV":
        return list(csv.DictReader(StringIO(content.decode("utf-8-sig"))))
    if normalized == "JSON":
        payload = json.loads(content)
        records = payload.get("records", []) if isinstance(payload, dict) else payload
        if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
            raise ValueError("JSON dataset must be an array of objects or contain a records array")
        return records
    if normalized == "PARQUET":
        import pyarrow.parquet as parquet

        return parquet.read_table(BytesIO(content)).to_pylist()
    raise ValueError(f"Unsupported dataset format: {format_name}")


def _date(value: str | date | None, fallback: date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value) if value else fallback


def _upsert(db: Session, model, filters: tuple, values: dict) -> None:
    existing = db.scalar(select(model).where(*filters))
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
    else:
        db.add(model(**values))


def import_records(db: Session, payload: DatasetImportRequest) -> dict:
    source = db.scalar(select(DataSource).where(DataSource.code == payload.provider_code))
    if source is None:
        raise ValueError(f"Unknown provider_code: {payload.provider_code}")

    job = DataJob(
        job_type="INGEST",
        provider_code=payload.provider_code,
        status="RUNNING",
        attempt=1,
        payload={"dataset_type": payload.dataset_type, "format": payload.format},
        started_at=datetime.now(UTC),
    )
    db.add(job)
    snapshot = SourceSnapshot(
        source_id=source.id,
        source_type=source.category,
        source_identifier=f"manual:{payload.provider_code}:{payload.format}",
        request_payload={"dataset_type": payload.dataset_type, "format": payload.format},
        response_payload=payload.records,
        checksum=payload_checksum(payload.records),
        source_revision=payload.source_revision,
        status="SUCCESS",
    )
    db.add(snapshot)
    db.flush()

    imported = 0
    dataset_type = payload.dataset_type.upper()
    for record in payload.records:
        if dataset_type in {"TRADE", "TRADE_ANNUAL", "TRADE_MONTHLY"}:
            year = int(record["period_year"])
            period_type = record.get("period_type", "YEAR")
            start = _date(record.get("period_start"), date(year, 1, 1))
            end = _date(record.get("period_end"), date(year, 12, 31))
            values = {
                "classification": record.get("classification", "HS2022"),
                "hs_code": str(record["hs_code"]),
                "period_year": year,
                "period_type": period_type,
                "period_start": start,
                "period_end": end,
                "reporter_iso3": record["reporter_iso3"].upper(),
                "partner_iso3": record.get("partner_iso3", "WLD").upper(),
                "flow": record.get("flow", "IMPORT"),
                "trade_value_usd": float(record["trade_value_usd"]),
                "net_weight_kg": record.get("net_weight_kg"),
                "quantity": record.get("quantity"),
                "quantity_unit": record.get("quantity_unit"),
                "source_snapshot_id": snapshot.id,
            }
            filters = (
                TradeObservation.classification == values["classification"],
                TradeObservation.hs_code == values["hs_code"],
                TradeObservation.period_type == period_type,
                TradeObservation.period_start == start,
                TradeObservation.reporter_iso3 == values["reporter_iso3"],
                TradeObservation.partner_iso3 == values["partner_iso3"],
                TradeObservation.flow == values["flow"],
            )
            _upsert(db, TradeObservation, filters, values)
        elif dataset_type == "MACRO":
            values = {
                "country_iso3": record["country_iso3"].upper(),
                "metric_key": record["metric_key"],
                "value_numeric": record.get("value_numeric"),
                "value_text": record.get("value_text"),
                "unit": record.get("unit"),
                "period_year": int(record["period_year"]),
                "source_id": source.id,
                "observed_type": record.get("observed_type", "REPORTED"),
            }
            filters = (
                CountryMetric.country_iso3 == values["country_iso3"],
                CountryMetric.metric_key == values["metric_key"],
                CountryMetric.period_year == values["period_year"],
                CountryMetric.source_id == source.id,
            )
            _upsert(db, CountryMetric, filters, values)
        elif dataset_type == "TARIFF":
            values = {
                "hs_code": str(record["hs_code"]),
                "country_iso3": record["country_iso3"].upper(),
                "origin_iso3": record.get("origin_iso3", "CHN").upper(),
                "period_year": int(record["period_year"]),
                "mfn_tariff": record.get("mfn_tariff"),
                "preferential_tariff": record.get("preferential_tariff"),
                "china_applicable_tariff": record.get("china_applicable_tariff"),
                "bound_tariff": record.get("bound_tariff"),
                "duty_free_flag": record.get("duty_free_flag"),
                "ntm_count": record.get("ntm_count"),
                "ntm_categories": record.get("ntm_categories"),
                "market_access_score": record.get("market_access_score"),
                "source_id": source.id,
                "observed_type": record.get("observed_type", "REPORTED"),
            }
            filters = (
                MarketAccessMetric.hs_code == values["hs_code"],
                MarketAccessMetric.country_iso3 == values["country_iso3"],
                MarketAccessMetric.origin_iso3 == values["origin_iso3"],
                MarketAccessMetric.period_year == values["period_year"],
                MarketAccessMetric.source_id == source.id,
            )
            _upsert(db, MarketAccessMetric, filters, values)
        else:
            job.status = "PARTIAL"
            job.error = (
                "Raw snapshot stored; no canonical normalizer is registered for this dataset type."
            )
            continue
        imported += 1

    if job.status == "RUNNING":
        job.status = "COMPLETED"
    job.finished_at = datetime.now(UTC)
    source.last_success_at = job.finished_at
    source.status = "READY"
    db.commit()
    return {
        "job_id": job.id,
        "status": job.status,
        "rows_received": len(payload.records),
        "rows_imported": imported,
        "snapshot_id": snapshot.id,
        "checksum": snapshot.checksum,
    }
