from __future__ import annotations

import base64
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal, get_db
from app.integrations.macro import WorldBankProvider
from app.integrations.registry import build_provider_registry
from app.models import (
    AnalysisRun,
    Country,
    CountryMetric,
    DataJob,
    DataSource,
    DecisionRecommendation,
    DemandSignal,
    DistributionEconomics,
    DistributionPlan,
    Evidence,
    ExplicitDemand,
    HsProduct,
    MarketAccessMetric,
    MarketMetric,
    MarketOpportunity,
    MarketplaceSignal,
    OpportunityEvent,
    OpportunityRisk,
    ProductHsMapping,
    SourceSnapshot,
    SupplyFit,
    TradeObservation,
    Watchlist,
)
from app.schemas.api import (
    AnalysisCreate,
    AnalysisOut,
    CountryOut,
    DatasetFileImportRequest,
    DatasetImportRequest,
    DataSourceUpdate,
    DistributionPlanCreate,
    HistoryItem,
    OpportunityListItem,
    ProductOut,
    SupplierItem,
    WatchlistCreate,
)
from app.services.analysis import execute_analysis
from app.services.dataset_import import import_records, parse_dataset_file

router = APIRouter(prefix="/api/v1")
PRODUCT_ALIASES = {
    "pressure sensor": "902620",
    "pressure sensors": "902620",
    "pressure gauge": "902620",
    "motorcycle helmet": "650610",
    "motorcycle helmets": "650610",
}


def analysis_task(run_id: str, settings: Settings) -> None:
    import asyncio
    with SessionLocal() as db:
        asyncio.run(execute_analysis(db, run_id, settings))


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/products/search", response_model=list[ProductOut])
def search_products(q: str = Query(min_length=1, max_length=100), db: Session = Depends(get_db)):
    cleaned = q.strip()
    alias_code = PRODUCT_ALIASES.get(cleaned.casefold())
    term = f"%{cleaned}%"
    prefix = f"{cleaned}%"
    relevance = case(
        (HsProduct.hs_code == alias_code, -1),
        (HsProduct.hs_code == cleaned, 0),
        (HsProduct.hs_code.like(prefix), 1),
        (HsProduct.name_en.ilike(prefix), 2),
        else_=3,
    )
    return db.scalars(
        select(HsProduct)
        .where(
            or_(
                HsProduct.hs_code == alias_code,
                HsProduct.hs_code.like(term),
                HsProduct.name_en.ilike(term),
                HsProduct.name_zh.ilike(term),
            )
        )
        .order_by(relevance, HsProduct.level.desc(), HsProduct.hs_code)
        .limit(20)
    ).all()


@router.get("/countries", response_model=list[CountryOut])
def countries(db: Session = Depends(get_db)):
    return db.scalars(select(Country).where(Country.is_active.is_(True)).order_by(Country.name_en)).all()


@router.post("/analyses", response_model=AnalysisOut, status_code=202)
def create_analysis(payload: AnalysisCreate, background: BackgroundTasks, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    product = db.scalar(select(HsProduct).where(HsProduct.hs_code == payload.hs_code))
    if not product:
        raise HTTPException(404, "HS product not found")
    run = AnalysisRun(hs_code=payload.hs_code, origin_iso3=payload.origin_iso3.upper(), requested_year=settings.latest_complete_year)
    db.add(run)
    db.commit()
    db.refresh(run)
    background.add_task(analysis_task, run.id, settings)
    return run


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut)
def analysis_status(analysis_id: str, db: Session = Depends(get_db)):
    run = db.get(AnalysisRun, analysis_id)
    if not run:
        raise HTTPException(404, "Analysis not found")
    return run


def opportunity_query(hs_code: str, origin_iso3: str):
    return select(MarketOpportunity, MarketMetric, Country).join(MarketMetric, (MarketMetric.hs_code == MarketOpportunity.hs_code) & (MarketMetric.country_iso3 == MarketOpportunity.destination_iso3) & (MarketMetric.origin_iso3 == MarketOpportunity.origin_iso3) & (MarketMetric.period_year == MarketOpportunity.period_year)).join(Country, Country.iso3 == MarketOpportunity.destination_iso3).where(MarketOpportunity.hs_code == hs_code, MarketOpportunity.origin_iso3 == origin_iso3)


def serialize_opportunity(row) -> OpportunityListItem:
    opp, metric, country = row
    return OpportunityListItem(id=opp.id, rank=opp.rank_global, hs_code=opp.hs_code, destination_iso3=opp.destination_iso3, country_name=country.name_en, region=country.region, period_year=opp.period_year, score=opp.market_attractiveness_score, coverage=opp.data_coverage_score, import_value_usd=metric.import_value_usd, cagr_3y=metric.cagr_3y, yoy_growth=metric.yoy_growth, china_share=metric.china_import_share, size_score=opp.size_score, growth_score=opp.growth_score, momentum_score=opp.momentum_score, stability_score=opp.stability_score)


def confidence_label(score: float | None) -> str:
    if score is None:
        return "UNKNOWN"
    return "HIGH" if score >= 80 else "MEDIUM" if score >= 55 else "LOW"


@router.get("/opportunities", response_model=list[OpportunityListItem])
def opportunities(hs_code: str, origin_iso3: str = "CHN", sort: str = "score", limit: int = Query(50, ge=1, le=250), region: str | None = None, min_score: float = 0, min_coverage: float = 0, db: Session = Depends(get_db)):
    query = opportunity_query(hs_code, origin_iso3).where(MarketOpportunity.market_attractiveness_score >= min_score, MarketOpportunity.data_coverage_score >= min_coverage)
    if region:
        query = query.where(Country.region == region)
    order = {"score": MarketOpportunity.market_attractiveness_score, "growth": MarketMetric.cagr_3y, "size": MarketMetric.import_value_usd}.get(sort, MarketOpportunity.market_attractiveness_score)
    return [serialize_opportunity(row) for row in db.execute(query.order_by(desc(order)).limit(limit)).all()]


@router.get("/opportunities/{opportunity_id}")
def opportunity_detail(opportunity_id: int, db: Session = Depends(get_db)):
    row = db.execute(select(MarketOpportunity, MarketMetric, Country).join(MarketMetric, (MarketMetric.hs_code == MarketOpportunity.hs_code) & (MarketMetric.country_iso3 == MarketOpportunity.destination_iso3) & (MarketMetric.period_year == MarketOpportunity.period_year)).join(Country, Country.iso3 == MarketOpportunity.destination_iso3).where(MarketOpportunity.id == opportunity_id)).first()
    if not row:
        raise HTTPException(404, "Opportunity not found")
    item = serialize_opportunity(row)
    opp = row[0]
    evidence = db.scalars(select(Evidence).where(Evidence.entity_type == "MARKET_OPPORTUNITY", Evidence.entity_id == opportunity_id)).all()
    signals = db.scalars(select(DemandSignal).where(DemandSignal.hs_code == opp.hs_code, DemandSignal.country_iso3 == opp.destination_iso3).order_by(DemandSignal.signal_layer, DemandSignal.metric_key)).all()
    supply = db.scalar(select(SupplyFit).where(SupplyFit.hs_code == opp.hs_code, or_(SupplyFit.country_iso3 == opp.destination_iso3, SupplyFit.country_iso3.is_(None))).order_by(SupplyFit.calculated_at.desc()))
    economics = db.scalar(select(DistributionEconomics).where(DistributionEconomics.opportunity_id == opportunity_id).order_by(DistributionEconomics.calculated_at.desc()))
    risks = db.scalars(select(OpportunityRisk).where(OpportunityRisk.opportunity_id == opportunity_id)).all()
    recommendations = db.scalars(select(DecisionRecommendation).where(DecisionRecommendation.opportunity_id == opportunity_id).order_by(DecisionRecommendation.created_at.desc())).all()
    history = trade_history(opp.hs_code, opp.destination_iso3, opp.origin_iso3, db)
    reasons = []
    if opp.size_score >= 90:
        reasons.append({"sentiment": "positive", "text": "Market size ranks in the global top 10%."})
    if item.cagr_3y is not None:
        reasons.append({"sentiment": "positive" if item.cagr_3y >= 0 else "negative", "text": f"Three-year structural growth is {item.cagr_3y:.1%}."})
    if item.yoy_growth is not None:
        reasons.append({"sentiment": "positive" if item.yoy_growth >= 0 else "negative", "text": f"Latest complete-year momentum is {item.yoy_growth:.1%}."})
    if opp.stability_score is not None and opp.stability_score < 50:
        reasons.append({"sentiment": "negative", "text": "Recent import values are more volatile than a stable market."})
    scores = {
        "market_attractiveness": opp.market_attractiveness_score,
        "structural_demand": opp.structural_demand_score,
        "digital_demand": opp.digital_demand_score,
        "marketplace_demand": opp.marketplace_demand_score,
        "explicit_demand": opp.explicit_demand_score,
        "market_access": opp.market_access_score,
        "country_capacity": opp.country_capacity_score,
        "supply_fit": opp.supply_fit_score,
        "economics": opp.economics_score,
        "risk": opp.risk_score,
        "distribution_opportunity": opp.distribution_opportunity_score,
        "confidence": opp.confidence_score,
    }
    signal_layers = {layer: [] for layer in ("STRUCTURAL", "DIGITAL", "MARKETPLACE", "EXPLICIT", "MACRO", "ACCESS")}
    for signal in signals:
        signal_layers.setdefault(signal.signal_layer, []).append({
            "metric_key": signal.metric_key,
            "value_numeric": signal.value_numeric,
            "value_text": signal.value_text,
            "normalized_value": signal.normalized_value,
            "observed_type": signal.observed_type,
            "reliability": signal.source_reliability,
            "freshness": signal.freshness_status,
            "confidence": signal.confidence,
        })
    return {
        **item.model_dump(),
        "market": {"hs_code": opp.hs_code, "origin_iso3": opp.origin_iso3, "destination_iso3": opp.destination_iso3, "country_name": item.country_name, "channel": opp.channel, "period_start": opp.period_start, "period_end": opp.period_end, "status": opp.status},
        "scores": scores,
        "confidence_label": confidence_label(opp.confidence_score),
        "score_version": opp.score_version,
        "history": [h.model_dump() for h in history],
        "signals": signal_layers,
        "supply": {"status": "CONNECTED", **{column.name: getattr(supply, column.name) for column in SupplyFit.__table__.columns if column.name not in {"id", "source_id"}}} if supply else {"status": "NOT_CONNECTED"},
        "economics": {"status": "AVAILABLE", **{column.name: getattr(economics, column.name) for column in DistributionEconomics.__table__.columns if column.name not in {"id", "opportunity_id"}}} if economics else {"status": "NOT_ENOUGH_DATA"},
        "risk": [{"risk_type": risk.risk_type, "score": risk.score, "reason": risk.reason, "status": risk.status, "evidence_ids": risk.evidence_ids} for risk in risks],
        "evidence": [{"id": e.id, "metric_key": e.metric_key, "source_type": e.source_type, "source_identifier": e.source_identifier, "source_url": e.source_url, "source_reliability": e.source_reliability, "observed_type": e.observed_type, "freshness": "FRESH", "period": e.period, "raw_value": e.raw_value, "display_value": e.display_value, "retrieved_at": e.retrieved_at, "confidence": e.confidence, "notes": e.notes} for e in evidence],
        "recommendations": [{"recommendation": row.recommendation, "reason": row.reason, "evidence_ids": row.evidence_ids, "confidence": row.confidence, "human_status": row.human_status} for row in recommendations],
        "reasons": reasons,
    }


@router.get("/trade/history", response_model=list[HistoryItem])
def trade_history(hs_code: str, country_iso3: str, origin_iso3: str = "CHN", db: Session = Depends(get_db)):
    totals = db.scalars(select(TradeObservation).where(TradeObservation.hs_code == hs_code, TradeObservation.reporter_iso3 == country_iso3, TradeObservation.partner_iso3 == "WLD", TradeObservation.flow == "IMPORT").order_by(TradeObservation.period_year)).all()
    bilateral = {r.period_year: r.trade_value_usd for r in db.scalars(select(TradeObservation).where(TradeObservation.hs_code == hs_code, TradeObservation.reporter_iso3 == country_iso3, TradeObservation.partner_iso3 == origin_iso3, TradeObservation.flow == "IMPORT")).all()}
    return [HistoryItem(year=r.period_year, import_value_usd=r.trade_value_usd, china_value_usd=bilateral.get(r.period_year), china_share=bilateral.get(r.period_year) / r.trade_value_usd if bilateral.get(r.period_year) and r.trade_value_usd else None) for r in totals]


@router.get("/trade/suppliers", response_model=list[SupplierItem])
def suppliers(hs_code: str, country_iso3: str, year: int, db: Session = Depends(get_db)):
    total = db.scalar(select(TradeObservation.trade_value_usd).where(TradeObservation.hs_code == hs_code, TradeObservation.reporter_iso3 == country_iso3, TradeObservation.partner_iso3 == "WLD", TradeObservation.period_year == year)) or 0
    rows = db.execute(select(TradeObservation, Country).outerjoin(Country, Country.iso3 == TradeObservation.partner_iso3).where(TradeObservation.hs_code == hs_code, TradeObservation.reporter_iso3 == country_iso3, TradeObservation.partner_iso3 != "WLD", TradeObservation.period_year == year).order_by(TradeObservation.trade_value_usd.desc())).all()
    return [SupplierItem(supplier_iso3=record.partner_iso3, supplier_name=country.name_en if country else record.partner_iso3, trade_value_usd=record.trade_value_usd, share=record.trade_value_usd / total if total else 0, rank=index) for index, (record, country) in enumerate(rows, 1)]


@router.get("/admin/data")
def admin_data(db: Session = Depends(get_db)):
    latest = db.scalar(select(SourceSnapshot.retrieved_at).order_by(SourceSnapshot.retrieved_at.desc()).limit(1))
    runs = db.scalars(select(AnalysisRun).order_by(AnalysisRun.started_at.desc()).limit(20)).all()
    return {"source_status": "READY" if latest else "NO_DATA", "last_sync": latest, "analysis_runs": [{"id": r.id, "hs_code": r.hs_code, "status": r.status, "started_at": r.started_at, "error": r.error_message} for r in runs], "cached_products": db.scalar(select(func.count()).select_from(HsProduct)), "trade_records": db.scalar(select(func.count()).select_from(TradeObservation))}


@router.get("/integrations/providers")
def integration_providers(settings: Settings = Depends(get_settings)):
    return build_provider_registry(settings).describe()


@router.patch("/admin/data-sources/{source_code}")
def update_data_source(source_code: str, payload: DataSourceUpdate, db: Session = Depends(get_db)):
    source = db.scalar(select(DataSource).where(DataSource.code == source_code.upper()))
    if source is None:
        raise HTTPException(404, "Data source not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, key, value)
    db.commit()
    db.refresh(source)
    return source


@router.get("/signals")
def demand_signals(
    hs_code: str | None = None,
    country_iso3: str | None = None,
    layer: str | None = None,
    db: Session = Depends(get_db),
):
    query = select(DemandSignal)
    if hs_code:
        query = query.where(DemandSignal.hs_code == hs_code)
    if country_iso3:
        query = query.where(DemandSignal.country_iso3 == country_iso3.upper())
    if layer:
        query = query.where(DemandSignal.signal_layer == layer.upper())
    rows = db.scalars(query.order_by(DemandSignal.period_end.desc()).limit(500)).all()
    return [
        {
            "id": row.id,
            "signal_layer": row.signal_layer,
            "hs_code": row.hs_code,
            "country_iso3": row.country_iso3,
            "channel": row.channel,
            "metric_key": row.metric_key,
            "value_numeric": row.value_numeric,
            "value_text": row.value_text,
            "normalized_value": row.normalized_value,
            "period_start": row.period_start,
            "period_end": row.period_end,
            "observed_type": row.observed_type,
            "source_reliability": row.source_reliability,
            "freshness_status": row.freshness_status,
            "confidence": row.confidence,
        }
        for row in rows
    ]


@router.get("/trade/monthly")
def monthly_trade(
    hs_code: str,
    country_iso3: str,
    origin_iso3: str = "CHN",
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(TradeObservation)
        .where(
            TradeObservation.hs_code == hs_code,
            TradeObservation.reporter_iso3 == country_iso3.upper(),
            TradeObservation.partner_iso3.in_(["WLD", origin_iso3.upper()]),
            TradeObservation.period_type == "MONTH",
        )
        .order_by(TradeObservation.period_start)
    ).all()
    return [
        {
            "period_start": row.period_start,
            "period_end": row.period_end,
            "partner_iso3": row.partner_iso3,
            "trade_value_usd": row.trade_value_usd,
            "quantity": row.quantity,
            "quantity_unit": row.quantity_unit,
        }
        for row in rows
    ]


@router.get("/tariffs")
def tariffs(hs_code: str, country_iso3: str, origin_iso3: str = "CHN", db: Session = Depends(get_db)):
    rows = db.scalars(
        select(MarketAccessMetric)
        .where(
            MarketAccessMetric.hs_code == hs_code,
            MarketAccessMetric.country_iso3 == country_iso3.upper(),
            MarketAccessMetric.origin_iso3 == origin_iso3.upper(),
        )
        .order_by(MarketAccessMetric.period_year.desc())
    ).all()
    return [{column.name: getattr(row, column.name) for column in MarketAccessMetric.__table__.columns} for row in rows]


@router.get("/macro")
def macro(country_iso3: str, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(CountryMetric)
        .where(CountryMetric.country_iso3 == country_iso3.upper())
        .order_by(CountryMetric.period_year.desc(), CountryMetric.metric_key)
    ).all()
    return [{column.name: getattr(row, column.name) for column in CountryMetric.__table__.columns} for row in rows]


@router.get("/marketplaces")
def marketplace_signals(
    country_iso3: str | None = None,
    marketplace: str | None = None,
    db: Session = Depends(get_db),
):
    query = select(MarketplaceSignal)
    if country_iso3:
        query = query.where(MarketplaceSignal.country_iso3 == country_iso3.upper())
    if marketplace:
        query = query.where(MarketplaceSignal.marketplace == marketplace)
    rows = db.scalars(query.order_by(MarketplaceSignal.observed_at.desc()).limit(250)).all()
    return {
        "status": "CONNECTED" if rows else "NOT_CONNECTED",
        "records": [{column.name: getattr(row, column.name) for column in MarketplaceSignal.__table__.columns} for row in rows],
    }


@router.get("/demands")
def explicit_demands(
    hs_code: str | None = None,
    country_iso3: str | None = None,
    db: Session = Depends(get_db),
):
    query = select(ExplicitDemand)
    if hs_code:
        query = query.where(ExplicitDemand.hs_code == hs_code)
    if country_iso3:
        query = query.where(ExplicitDemand.buyer_country_iso3 == country_iso3.upper())
    rows = db.scalars(query.order_by(ExplicitDemand.published_at.desc()).limit(250)).all()
    return {
        "status": "CONNECTED" if rows else "NOT_CONNECTED",
        "records": [{column.name: getattr(row, column.name) for column in ExplicitDemand.__table__.columns} for row in rows],
    }


@router.get("/supply")
def supply(hs_code: str, country_iso3: str | None = None, db: Session = Depends(get_db)):
    query = select(SupplyFit).where(SupplyFit.hs_code == hs_code)
    if country_iso3:
        query = query.where(or_(SupplyFit.country_iso3 == country_iso3.upper(), SupplyFit.country_iso3.is_(None)))
    rows = db.scalars(query.order_by(SupplyFit.calculated_at.desc())).all()
    return [{column.name: getattr(row, column.name) for column in SupplyFit.__table__.columns} for row in rows]


@router.get("/economics")
def economics(opportunity_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(select(DistributionEconomics).where(DistributionEconomics.opportunity_id == opportunity_id).order_by(DistributionEconomics.calculated_at.desc())).all()
    return [{column.name: getattr(row, column.name) for column in DistributionEconomics.__table__.columns} for row in rows]


@router.get("/watchlists")
def watchlists(db: Session = Depends(get_db)):
    return db.scalars(select(Watchlist).order_by(Watchlist.created_at.desc())).all()


@router.post("/watchlists", status_code=201)
def create_watchlist(payload: WatchlistCreate, db: Session = Depends(get_db)):
    if not any((payload.product_id, payload.hs_code, payload.country_iso3, payload.channel)):
        raise HTTPException(400, "At least one watch target is required")
    row = Watchlist(
        name=payload.name,
        product_id=payload.product_id,
        hs_code=payload.hs_code,
        country_iso3=payload.country_iso3.upper() if payload.country_iso3 else None,
        channel=payload.channel,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/watchlists/{watchlist_id}", status_code=204)
def delete_watchlist(watchlist_id: int, db: Session = Depends(get_db)):
    row = db.get(Watchlist, watchlist_id)
    if row is None:
        raise HTTPException(404, "Watchlist item not found")
    db.delete(row)
    db.commit()


@router.get("/events")
def events(limit: int = Query(50, ge=1, le=250), db: Session = Depends(get_db)):
    return db.scalars(select(OpportunityEvent).order_by(OpportunityEvent.detected_at.desc()).limit(limit)).all()


@router.post("/integrations/erp/distribution-plans", status_code=201)
def create_distribution_plan(payload: DistributionPlanCreate, db: Session = Depends(get_db)):
    opportunity = db.get(MarketOpportunity, payload.opportunity_id)
    if opportunity is None:
        raise HTTPException(404, "Opportunity not found")
    if opportunity.distribution_opportunity_score is None:
        raise HTTPException(409, "Distribution plan requires verified supply fit and economics")
    plan = DistributionPlan(
        opportunity_id=opportunity.id,
        product_id=payload.product_id or opportunity.product_id,
        destination_iso3=opportunity.destination_iso3,
        channel=payload.channel or opportunity.channel,
        supplier_offer_ref=payload.supplier_offer_ref,
        target_price=payload.target_price,
        expected_cost=payload.expected_cost,
        currency=payload.currency,
        evidence_ids=payload.evidence_ids,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/evidence")
def evidence_registry(entity_type: str | None = None, entity_id: int | None = None, db: Session = Depends(get_db)):
    query = select(Evidence)
    if entity_type:
        query = query.where(Evidence.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(Evidence.entity_id == entity_id)
    return db.scalars(query.order_by(Evidence.retrieved_at.desc()).limit(500)).all()


@router.post("/admin/datasets/import", status_code=202)
def dataset_import(payload: DatasetImportRequest, db: Session = Depends(get_db)):
    try:
        return import_records(db, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/admin/datasets/import-file", status_code=202)
def dataset_file_import(payload: DatasetFileImportRequest, db: Session = Depends(get_db)):
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
        records = parse_dataset_file(payload.format, content)
        normalized = DatasetImportRequest(
            dataset_type=payload.dataset_type,
            provider_code=payload.provider_code,
            format=payload.format,
            records=records,
            source_revision=payload.source_revision,
        )
        return import_records(db, normalized)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/admin/sync/macro", status_code=202)
async def sync_macro(
    country_iso3: str,
    year: int | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    provider = WorldBankProvider(enabled=settings.enable_world_bank)
    if not provider.metadata.enabled:
        raise HTTPException(409, "World Bank provider is disabled")
    try:
        records = await provider.get_country_metrics(country_iso3.upper(), year)
    except Exception as exc:
        source = db.scalar(select(DataSource).where(DataSource.code == "WORLD_BANK"))
        if source:
            source.last_failure_at = datetime.now(UTC)
            source.status = "FAILED"
            db.commit()
        raise HTTPException(502, f"World Bank sync failed: {exc}") from exc
    payload = DatasetImportRequest(
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
    )
    return import_records(db, payload)


@router.get("/admin/data-quality")
def data_quality(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    sources = db.scalars(select(DataSource).order_by(DataSource.category, DataSource.name)).all()
    providers = {item["code"]: item for item in build_provider_registry(settings).describe()}
    failed_runs = db.scalar(select(func.count()).select_from(AnalysisRun).where(AnalysisRun.status == "FAILED")) or 0
    failed_jobs = db.scalar(select(func.count()).select_from(DataJob).where(DataJob.status == "FAILED")) or 0
    missing_mappings = db.scalar(select(func.count()).select_from(ProductHsMapping).where(ProductHsMapping.status != "CONFIRMED")) or 0
    low_confidence = db.scalar(select(func.count()).select_from(MarketOpportunity).where(or_(MarketOpportunity.confidence_score < 55, MarketOpportunity.confidence_score.is_(None)))) or 0
    reliability = db.execute(select(DataSource.reliability, func.count()).group_by(DataSource.reliability)).all()
    return {
        "generated_at": datetime.now(UTC),
        "provider_health": [
            {
                "code": source.code,
                "name": source.name,
                "category": source.category,
                "enabled": source.enabled,
                "status": providers.get(source.code, {}).get("health", source.status),
                "reliability": source.reliability,
                "last_success_at": source.last_success_at,
                "last_failure_at": source.last_failure_at,
                "freshness_ttl_hours": source.freshness_ttl_hours,
            }
            for source in sources
        ],
        "coverage": {
            "trade_observations": db.scalar(select(func.count()).select_from(TradeObservation)) or 0,
            "demand_signals": db.scalar(select(func.count()).select_from(DemandSignal)) or 0,
            "tariff_records": db.scalar(select(func.count()).select_from(MarketAccessMetric)) or 0,
            "macro_records": db.scalar(select(func.count()).select_from(CountryMetric)) or 0,
            "opportunities": db.scalar(select(func.count()).select_from(MarketOpportunity)) or 0,
        },
        "stale_sources": [source.code for source in sources if source.status == "STALE"],
        "failed_syncs": failed_runs + failed_jobs,
        "missing_hs_mappings": missing_mappings,
        "low_confidence_opportunities": low_confidence,
        "source_reliability": {key: count for key, count in reliability},
        "recent_revisions": db.scalar(select(func.count()).select_from(SourceSnapshot).where(SourceSnapshot.source_revision.is_not(None))) or 0,
    }
