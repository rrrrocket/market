from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.integrations.trade import (
    ComtradeTradeDataProvider,
    FixtureTradeDataProvider,
    TradeDataProvider,
    TradeRecord,
    payload_checksum,
)
from app.models import (
    AnalysisRun,
    DataSource,
    DemandSignal,
    Evidence,
    MarketMetric,
    MarketOpportunity,
    SourceSnapshot,
    TradeObservation,
)
from app.scoring.engine import (
    SCORE_VERSION,
    cagr,
    coefficient_of_variation,
    confidence_score,
    growth_score,
    momentum_score,
    percentile_scores,
    stability_score,
    weighted_score,
    yoy,
)


def fixture_path() -> Path:
    relative = Path("data/fixtures/comtrade/hs_902620_test.json")
    for root in Path(__file__).resolve().parents:
        candidate = root / relative
        if candidate.exists():
            return candidate
    return Path("/") / relative


def provider_for(settings: Settings) -> TradeDataProvider:
    if settings.trade_data_provider.lower() in {"comtrade", "un_comtrade"}:
        return ComtradeTradeDataProvider(settings.comtrade_api_key)
    # Fixture is deliberately the safe default. Live data activation is explicit.
    return FixtureTradeDataProvider(fixture_path())


def upsert_observation(db: Session, values: dict) -> None:
    existing = db.scalar(select(TradeObservation).where(
        TradeObservation.classification == values["classification"], TradeObservation.hs_code == values["hs_code"],
        TradeObservation.period_type == values["period_type"], TradeObservation.period_start == values["period_start"], TradeObservation.reporter_iso3 == values["reporter_iso3"],
        TradeObservation.partner_iso3 == values["partner_iso3"], TradeObservation.flow == values["flow"],
    ))
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
    else:
        db.add(TradeObservation(**values))


async def execute_analysis(db: Session, run_id: str, settings: Settings) -> None:
    run = db.get(AnalysisRun, run_id)
    if not run:
        return
    run.status, run.started_at = "RUNNING", datetime.now(UTC)
    db.commit()
    try:
        provider = provider_for(settings)
        source_code = "COMTRADE_FIXTURE" if provider.source_type == "FIXTURE" else "UN_COMTRADE"
        data_source = db.scalar(select(DataSource).where(DataSource.code == source_code))
        years = list(range(run.requested_year - 4, run.requested_year + 1))
        cutoff = datetime.now(UTC) - timedelta(days=settings.comtrade_cache_ttl_days)
        cached = db.scalars(
            select(TradeObservation)
            .join(SourceSnapshot)
            .where(
                TradeObservation.hs_code == run.hs_code,
                TradeObservation.period_year.in_(years),
                SourceSnapshot.source_type == provider.source_type,
                SourceSnapshot.retrieved_at >= cutoff,
            )
        ).all()
        snapshot = None
        if cached and set(years).issubset({row.period_year for row in cached}):
            all_records = [
                TradeRecord(
                    row.classification,
                    row.hs_code,
                    row.period_year,
                    row.reporter_iso3,
                    row.partner_iso3,
                    row.flow,
                    row.trade_value_usd,
                    row.net_weight_kg,
                    row.quantity,
                    row.quantity_unit,
                    row.period_type,
                    row.period_start,
                    row.period_end,
                )
                for row in cached
            ]
            snapshot = db.scalar(
                select(SourceSnapshot)
                .where(SourceSnapshot.id == cached[0].source_snapshot_id)
            )
        else:
            all_records = []
            try:
                for year in years:
                    all_records.extend(await provider.get_imports(run.hs_code, year))
            except Exception:
                stale = db.scalars(
                    select(TradeObservation).where(
                        TradeObservation.hs_code == run.hs_code,
                        TradeObservation.period_year.in_(years),
                    )
                ).all()
                if not stale:
                    raise
                all_records = [
                    TradeRecord(
                        row.classification,
                        row.hs_code,
                        row.period_year,
                        row.reporter_iso3,
                        row.partner_iso3,
                        row.flow,
                        row.trade_value_usd,
                        row.net_weight_kg,
                        row.quantity,
                        row.quantity_unit,
                        row.period_type,
                        row.period_start,
                        row.period_end,
                    )
                    for row in stale
                ]
                snapshot = db.get(SourceSnapshot, stale[0].source_snapshot_id)
                snapshot.status = "STALE"
            if snapshot is None:
                payload = provider.snapshot_payload(all_records)
                snapshot = SourceSnapshot(
                    source_id=data_source.id if data_source else None,
                    source_type=provider.source_type,
                    source_identifier=provider.source_identifier,
                    request_payload={"hs_code": run.hs_code, "years": years},
                    response_payload=payload,
                    checksum=payload_checksum(payload),
                    status="SUCCESS",
                )
                db.add(snapshot)
                db.flush()
                for record in all_records:
                    period_start = record.period_start or date(record.year, 1, 1)
                    period_end = record.period_end or date(record.year, 12, 31)
                    upsert_observation(db, {"classification": record.classification, "hs_code": record.hs_code, "period_year": record.year, "period_type": record.period_type, "period_start": period_start, "period_end": period_end, "reporter_iso3": record.reporter_iso3, "partner_iso3": record.partner_iso3, "flow": record.flow, "trade_value_usd": record.trade_value_usd, "net_weight_kg": record.net_weight_kg, "quantity": record.quantity, "quantity_unit": record.quantity_unit, "source_snapshot_id": snapshot.id})
        db.flush()
        totals = {(r.reporter_iso3, r.year): r for r in all_records if r.partner_iso3 == "WLD"}
        bilateral = {(r.reporter_iso3, r.year): r for r in all_records if r.partner_iso3 == run.origin_iso3}
        countries = sorted({country for country, year in totals if year == run.requested_year})
        db.execute(delete(Evidence).where(Evidence.entity_type == "MARKET_OPPORTUNITY", Evidence.entity_id.in_(select(MarketOpportunity.id).where(MarketOpportunity.hs_code == run.hs_code))))
        db.execute(delete(MarketOpportunity).where(MarketOpportunity.hs_code == run.hs_code, MarketOpportunity.origin_iso3 == run.origin_iso3, MarketOpportunity.period_year == run.requested_year, MarketOpportunity.score_version == SCORE_VERSION))
        db.execute(delete(MarketMetric).where(MarketMetric.hs_code == run.hs_code, MarketMetric.origin_iso3 == run.origin_iso3, MarketMetric.period_year == run.requested_year))
        db.execute(delete(DemandSignal).where(DemandSignal.hs_code == run.hs_code, DemandSignal.signal_layer == "STRUCTURAL", DemandSignal.period_start == date(run.requested_year, 1, 1)))
        size_inputs = {country: totals[(country, run.requested_year)].trade_value_usd for country in countries}
        sizes = percentile_scores({country: __import__("math").log(value + 1) for country, value in size_inputs.items()})
        staged = []
        for country in countries:
            latest = size_inputs[country]
            previous = totals.get((country, run.requested_year - 1))
            old = totals.get((country, run.requested_year - 3))
            history = [totals[(country, year)].trade_value_usd for year in range(run.requested_year - 3, run.requested_year + 1) if (country, year) in totals]
            y = yoy(latest, previous.trade_value_usd if previous else None)
            g = cagr(latest, old.trade_value_usd if old else None)
            cv = coefficient_of_variation(history)
            china_value = bilateral.get((country, run.requested_year))
            metric = MarketMetric(hs_code=run.hs_code, country_iso3=country, origin_iso3=run.origin_iso3, period_year=run.requested_year, import_value_usd=latest, import_value_prev_year=previous.trade_value_usd if previous else None, import_value_3y_ago=old.trade_value_usd if old else None, yoy_growth=y, cagr_3y=g, china_import_value_usd=china_value.trade_value_usd if china_value else None, china_import_share=china_value.trade_value_usd / latest if china_value and latest else None, unit_value_usd=latest / totals[(country, run.requested_year)].net_weight_kg if totals[(country, run.requested_year)].net_weight_kg else None, market_volatility=cv)
            db.add(metric)
            score = weighted_score(sizes[country], growth_score(g), momentum_score(y), stability_score(cv))
            confidence = confidence_score(score.coverage, [data_source.reliability if data_source else "A"], ["FRESH"], None)
            opportunity = MarketOpportunity(product_scope_type="HS", product_scope_id=run.hs_code, hs_code=run.hs_code, origin_iso3=run.origin_iso3, destination_iso3=country, period_year=run.requested_year, period_start=date(run.requested_year, 1, 1), period_end=date(run.requested_year, 12, 31), market_attractiveness_score=score.total, structural_demand_score=score.total, data_coverage_score=score.coverage, confidence_score=confidence.score, size_score=score.size, growth_score=score.growth, momentum_score=score.momentum, stability_score=score.stability, score_version=SCORE_VERSION)
            db.add(opportunity)
            staged.append((opportunity, metric))
        db.flush()
        staged.sort(key=lambda item: (-item[0].market_attractiveness_score, item[0].destination_iso3))
        for rank, (opportunity, metric) in enumerate(staged, 1):
            opportunity.rank_global = rank
            evidence_values = [("IMPORT_VALUE", metric.import_value_usd, f"${metric.import_value_usd:,.0f}"), ("CAGR_3Y", metric.cagr_3y, f"{metric.cagr_3y:.1%}" if metric.cagr_3y is not None else "Missing"), ("YOY_GROWTH", metric.yoy_growth, f"{metric.yoy_growth:.1%}" if metric.yoy_growth is not None else "Missing"), ("CHINA_SHARE", metric.china_import_share, f"{metric.china_import_share:.1%}" if metric.china_import_share is not None else "Missing")]
            for key, raw, display in evidence_values:
                evidence = Evidence(entity_type="MARKET_OPPORTUNITY", entity_id=opportunity.id, metric_key=key, value_numeric=raw if isinstance(raw, (int, float)) else None, source_id=data_source.id if data_source else None, source_type=snapshot.source_type, source_identifier=snapshot.source_identifier, source_url=data_source.base_url if data_source else None, source_reliability=data_source.reliability if data_source else "A", observed_type="REPORTED", period=str(run.requested_year), period_start=date(run.requested_year, 1, 1), period_end=date(run.requested_year, 12, 31), raw_value=raw, display_value=display, retrieved_at=snapshot.retrieved_at, raw_snapshot_id=snapshot.id, confidence=confidence.score, notes="TEST DATA" if snapshot.source_type == "FIXTURE" else None)
                db.add(evidence)
                db.flush()
                db.add(DemandSignal(signal_layer="STRUCTURAL", hs_code=run.hs_code, country_iso3=opportunity.destination_iso3, metric_key=key, value_numeric=raw if isinstance(raw, (int, float)) else None, period_start=date(run.requested_year, 1, 1), period_end=date(run.requested_year, 12, 31), source_id=data_source.id if data_source else 1, evidence_id=evidence.id, observed_type="REPORTED", source_reliability=data_source.reliability if data_source else "A", freshness_status="FRESH", confidence=confidence.score))
        run.status, run.finished_at = "COMPLETED", datetime.now(UTC)
        run.countries_analyzed = run.countries_succeeded = len(countries)
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(AnalysisRun, run_id)
        if run:
            run.status, run.error_message, run.finished_at = "FAILED", str(exc), datetime.now(UTC)
            db.commit()
        raise
