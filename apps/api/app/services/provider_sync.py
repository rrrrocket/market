from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.integrations.demand import TedExplicitDemandProvider
from app.integrations.macro import WorldBankProvider
from app.integrations.marketplace import EbayMarketplaceProvider, HttpMarketplaceProvider
from app.integrations.supplier import HttpSupplierNetworkClient
from app.integrations.tariff import WitsTariffProvider
from app.integrations.trade import ComtradeTradeDataProvider, payload_checksum
from app.models import (
    Country,
    DataJob,
    DataSource,
    ExplicitDemand,
    MarketplaceSignal,
    SourceSnapshot,
)
from app.schemas.api import (
    CountrySyncRequest,
    DatasetImportRequest,
    ExplicitDemandSyncRequest,
    MarketplaceSyncRequest,
    TariffSyncRequest,
    TradeSyncRequest,
)
from app.services.dataset_import import import_records
from app.services.opportunity import sync_supply_fit


def _countries(db: Session, requested: list[str], *, exclude: str | None = None) -> list[str]:
    values = [item.upper() for item in requested]
    if not values:
        values = list(
            db.scalars(
                select(Country.iso3).where(
                    Country.is_active.is_(True), Country.numeric_code.is_not(None)
                )
            ).all()
        )
    if exclude:
        values = [value for value in values if value != exclude.upper()]
    known = set(db.scalars(select(Country.iso3).where(Country.iso3.in_(values))).all())
    unknown = sorted(set(values) - known)
    if unknown:
        raise ValueError(f"Unknown countries: {', '.join(unknown)}")
    return sorted(set(values))


def _mark_source_enabled(db: Session, code: str) -> None:
    source = db.scalar(select(DataSource).where(DataSource.code == code))
    if source:
        source.enabled = True
        db.flush()


async def sync_comtrade(db: Session, settings: Settings, request: TradeSyncRequest) -> dict:
    origin = request.origin_iso3.upper()
    countries = _countries(db, request.countries, exclude=origin)
    years = sorted(
        set(
            request.years
            or range(settings.trade_data_start_year, settings.trade_data_end_year + 1)
        )
    )
    provider = ComtradeTradeDataProvider(
        settings.comtrade_api_key,
        base_url=settings.comtrade_api_base_url,
        final_base_url=settings.comtrade_final_api_base_url,
        max_concurrency=settings.comtrade_max_concurrency,
        retry_attempts=settings.provider_retry_attempts,
        retry_delay_seconds=settings.provider_retry_delay_seconds,
    )
    reporter_scope = ",".join(countries)
    annual_batches = await asyncio.gather(
        *(
            provider.get_imports(
                hs_code=request.hs_code,
                year=year,
                reporter=reporter_scope,
                partner=f"WLD,{origin}",
            )
            for year in years
        )
    )
    records = [record for batch in annual_batches for record in batch]
    monthly_count = 0
    if request.monthly_months:
        monthly_year = request.monthly_year or max(years)
        invalid = [month for month in request.monthly_months if not 1 <= month <= 12]
        if invalid:
            raise ValueError(f"Invalid months: {invalid}")
        monthly_batches = await asyncio.gather(
            *(
                provider.get_monthly_imports(
                    request.hs_code,
                    monthly_year,
                    month,
                    reporter_scope,
                    f"WLD,{origin}",
                )
                for month in sorted(set(request.monthly_months))
            )
        )
        monthly = [record for batch in monthly_batches for record in batch]
        monthly_count = len(monthly)
        records.extend(monthly)
    if not records:
        raise ValueError("UN Comtrade returned no observations for the requested scope")
    _mark_source_enabled(db, "UN_COMTRADE")
    result = import_records(
        db,
        DatasetImportRequest(
            dataset_type="TRADE",
            provider_code="UN_COMTRADE",
            format="JSON",
            records=[
                {
                    "classification": record.classification,
                    "hs_code": record.hs_code,
                    "period_year": record.year,
                    "period_type": record.period_type,
                    "period_start": record.period_start.isoformat()
                    if record.period_start
                    else None,
                    "period_end": record.period_end.isoformat() if record.period_end else None,
                    "reporter_iso3": record.reporter_iso3,
                    "partner_iso3": record.partner_iso3,
                    "flow": record.flow,
                    "trade_value_usd": record.trade_value_usd,
                    "net_weight_kg": record.net_weight_kg,
                    "quantity": record.quantity,
                    "quantity_unit": record.quantity_unit,
                }
                for record in records
            ],
        ),
    )
    result.update(
        {"annual_observations": len(records) - monthly_count, "monthly_observations": monthly_count}
    )
    return result


async def sync_world_bank(db: Session, settings: Settings, request: CountrySyncRequest) -> dict:
    countries = _countries(db, request.countries)
    provider = WorldBankProvider(
        enabled=True,
        base_url=settings.world_bank_api_base_url,
    )
    batches = await asyncio.gather(
        *(provider.get_country_metrics(country, request.year) for country in countries)
    )
    records = [record for batch in batches for record in batch]
    if not records:
        raise ValueError("World Bank returned no metrics for the requested scope")
    _mark_source_enabled(db, "WORLD_BANK")
    result = import_records(
        db,
        DatasetImportRequest(
            dataset_type="MACRO",
            provider_code="WORLD_BANK",
            format="JSON",
            records=[
                {
                    "country_iso3": record.country_iso3,
                    "metric_key": record.metric_key,
                    "value_numeric": record.value,
                    "unit": record.unit,
                    "period_year": record.period_year,
                    "observed_type": "REPORTED",
                }
                for record in records
            ],
        ),
    )
    result["countries"] = len(countries)
    return result


async def sync_wits(db: Session, settings: Settings, request: TariffSyncRequest) -> dict:
    origin = request.origin_iso3.upper()
    countries = _countries(db, request.countries, exclude=origin)
    year = request.year or settings.latest_complete_year
    provider = WitsTariffProvider(enabled=True, base_url=settings.wits_api_base_url)
    semaphore = asyncio.Semaphore(4)

    async def fetch(country: str):
        async with semaphore:
            return await provider.get_tariff(request.hs_code, country, origin, year)

    batches = await asyncio.gather(*(fetch(country) for country in countries))
    records = [record for batch in batches for record in batch]
    if not records:
        raise ValueError("WITS returned no tariff observations for the requested scope")
    _mark_source_enabled(db, "WITS_TRAINS")
    result = import_records(
        db,
        DatasetImportRequest(
            dataset_type="TARIFF",
            provider_code="WITS_TRAINS",
            format="JSON",
            records=[
                {
                    "hs_code": record.hs_code,
                    "country_iso3": record.reporter_iso3,
                    "origin_iso3": origin,
                    "period_year": record.year,
                    "mfn_tariff": record.mfn_tariff,
                    "preferential_tariff": record.preferential_tariff,
                    "china_applicable_tariff": record.preferential_tariff
                    if record.preferential_tariff is not None
                    else record.mfn_tariff,
                    "duty_free_flag": (
                        record.preferential_tariff
                        if record.preferential_tariff is not None
                        else record.mfn_tariff
                    )
                    == 0,
                    "market_access_score": max(
                        0,
                        min(
                            100,
                            100
                            - 2
                            * (
                                record.preferential_tariff
                                if record.preferential_tariff is not None
                                else record.mfn_tariff
                            ),
                        ),
                    )
                    if (record.preferential_tariff is not None or record.mfn_tariff is not None)
                    else None,
                    "observed_type": "REPORTED",
                }
                for record in records
            ],
        ),
    )
    result["countries_with_data"] = len({record.reporter_iso3 for record in records})
    return result


async def sync_supplier(db: Session, settings: Settings, hs_code: str) -> dict:
    if not (settings.supplier_api_base_url and settings.supplier_api_key):
        raise ValueError("Supplier API configuration is incomplete")
    provider = HttpSupplierNetworkClient(
        settings.supplier_api_base_url,
        settings.supplier_api_key,
        timeout_seconds=settings.supplier_api_timeout_seconds,
    )
    summary = await provider.get_supply_summary(hs_code)
    row = sync_supply_fit(db, hs_code, summary)
    return {
        "status": "COMPLETED",
        "supply_fit_id": row.id,
        "supply_fit_score": row.supply_fit_score,
    }


async def sync_marketplace(
    db: Session, settings: Settings, request: MarketplaceSyncRequest
) -> dict:
    if settings.ebay_client_id and settings.ebay_client_secret:
        provider = EbayMarketplaceProvider(
            settings.ebay_client_id,
            settings.ebay_client_secret,
            base_url=settings.ebay_api_base_url,
            oauth_url=settings.ebay_oauth_url,
            timeout_seconds=settings.marketplace_api_timeout_seconds,
        )
    elif (
        settings.marketplace_provider_code
        and settings.marketplace_api_base_url
        and settings.marketplace_api_key
    ):
        provider = HttpMarketplaceProvider(
            settings.marketplace_provider_code,
            settings.marketplace_api_base_url,
            settings.marketplace_api_key,
            timeout_seconds=settings.marketplace_api_timeout_seconds,
        )
    else:
        raise ValueError("Configure eBay credentials or the marketplace gateway")
    records = await provider.get_keyword_metrics(
        request.marketplace, request.country_iso3.upper(), request.keyword
    )
    source = db.scalar(select(DataSource).where(DataSource.code == "MARKETPLACES"))
    if source is None:
        raise ValueError("MARKETPLACES data source is not registered")
    snapshot = SourceSnapshot(
        source_id=source.id,
        source_type="MARKETPLACE",
        source_identifier=provider.metadata.code,
        request_payload=request.model_dump(),
        response_payload=records,
        checksum=payload_checksum(records),
        status="SUCCESS",
    )
    db.add(snapshot)
    db.flush()
    imported = 0
    for record in records:
        observed_at = (
            datetime.fromisoformat(record["observed_at"])
            if isinstance(record.get("observed_at"), str)
            else record.get("observed_at") or datetime.now(UTC)
        )
        product_ref = record.get("product_ref") or f"keyword:{request.keyword}"
        row = db.scalar(
            select(MarketplaceSignal).where(
                MarketplaceSignal.marketplace == request.marketplace,
                MarketplaceSignal.country_iso3 == request.country_iso3.upper(),
                MarketplaceSignal.product_ref == product_ref,
                MarketplaceSignal.observed_at == observed_at,
            )
        )
        if row is None:
            row = MarketplaceSignal(
                marketplace=request.marketplace,
                country_iso3=request.country_iso3.upper(),
                product_ref=product_ref,
                observed_at=observed_at,
                source_id=source.id,
            )
            db.add(row)
        row.keyword = request.keyword
        row.price = record.get("price")
        row.currency = record.get("currency")
        row.rating = record.get("rating")
        row.review_count = record.get("review_count")
        row.review_growth = record.get("review_growth")
        row.rank = record.get("rank")
        row.rank_change = record.get("rank_change")
        row.seller_count = record.get("seller_count")
        row.promotion_flag = record.get("promotion_flag")
        row.stock_status = record.get("stock_status")
        row.estimated_sales = record.get("estimated_sales")
        row.observed_type = record.get("observed_type", "OBSERVED")
        row.source_reliability = "A_MINUS"
        row.confidence = record.get("confidence")
        row.source_id = source.id
        imported += 1
    source.enabled = True
    source.status = "READY"
    source.last_success_at = datetime.now(UTC)
    db.add(
        DataJob(
            job_type="INGEST",
            provider_code=source.code,
            status="COMPLETED",
            attempt=1,
            payload=request.model_dump(),
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
    )
    db.commit()
    return {"status": "COMPLETED", "rows_imported": imported, "snapshot_id": snapshot.id}


async def sync_explicit_demand(
    db: Session, settings: Settings, request: ExplicitDemandSyncRequest
) -> dict:
    if not settings.enable_ted:
        raise ValueError("TED provider is disabled")
    provider = TedExplicitDemandProvider(enabled=True, base_url=settings.ted_api_base_url)
    records = await provider.search_demands(
        hs_code=request.hs_code,
        country_iso3=request.country_iso3,
        keyword=request.keyword,
    )
    source = db.scalar(select(DataSource).where(DataSource.code == "EXPLICIT_DEMAND"))
    if source is None:
        raise ValueError("EXPLICIT_DEMAND data source is not registered")
    snapshot = SourceSnapshot(
        source_id=source.id,
        source_type="TENDER",
        source_identifier="TED_EU",
        request_payload=request.model_dump(),
        response_payload=records,
        checksum=payload_checksum(records),
        status="SUCCESS",
    )
    db.add(snapshot)
    db.flush()
    for record in records:
        row = db.scalar(
            select(ExplicitDemand).where(
                ExplicitDemand.source_type == record["source_type"],
                ExplicitDemand.source_identifier == record["source_identifier"],
            )
        )
        if row is None:
            row = ExplicitDemand(
                source_type=record["source_type"],
                source_identifier=record["source_identifier"],
                source_id=source.id,
            )
            db.add(row)
        for field in (
            "buyer_name",
            "buyer_country_iso3",
            "title",
            "description",
            "hs_code",
            "quantity",
            "quantity_unit",
            "budget_min",
            "budget_max",
            "currency",
            "deadline",
            "published_at",
            "requirements",
            "source_url",
            "status",
            "observed_type",
            "source_reliability",
        ):
            value = record.get(field)
            if field in {"deadline", "published_at"} and isinstance(value, str):
                value = datetime.fromisoformat(value)
            setattr(row, field, value)
        row.source_id = source.id
        row.retrieved_at = datetime.now(UTC)
    now = datetime.now(UTC)
    source.enabled = True
    source.status = "READY"
    source.last_success_at = now
    db.add(
        DataJob(
            job_type="INGEST",
            provider_code=source.code,
            status="COMPLETED",
            attempt=1,
            payload=request.model_dump(),
            started_at=now,
            finished_at=now,
        )
    )
    db.commit()
    return {"status": "COMPLETED", "rows_imported": len(records), "snapshot_id": snapshot.id}
