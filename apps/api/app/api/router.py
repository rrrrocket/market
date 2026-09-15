from __future__ import annotations

import base64
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import case, desc, exists, func, or_, select
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
    CountrySyncRequest,
    DatasetFileImportRequest,
    DatasetImportRequest,
    DataSourceUpdate,
    DistributionPlanCreate,
    EconomicsInput,
    ExplicitDemandSyncRequest,
    HistoryItem,
    MarketplaceSyncRequest,
    OpportunityListItem,
    ProductOut,
    SupplierItem,
    SupplierSyncRequest,
    TariffSyncRequest,
    TradeSyncRequest,
    WatchlistCreate,
)
from app.services.analysis import execute_analysis
from app.services.bulk_pipeline import pipeline_status
from app.services.country_opportunity import (
    country_opportunity_catalog,
    country_opportunity_detail,
)
from app.services.dataset_import import import_records, parse_dataset_file
from app.services.opportunity import calculate_economics, recompute_distribution_opportunity
from app.services.provider_sync import (
    sync_comtrade,
    sync_explicit_demand,
    sync_marketplace,
    sync_supplier,
    sync_wits,
    sync_world_bank,
)

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
    return db.scalars(
        select(Country).where(Country.is_active.is_(True)).order_by(Country.name_en)
    ).all()


@router.get("/country-opportunities")
def country_opportunities(
    year: int | None = None,
    origin_iso3: str = "CHN",
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return country_opportunity_catalog(
        db,
        year=year or settings.latest_complete_year,
        origin_iso3=origin_iso3,
    )


@router.get("/country-opportunities/{country_iso3}")
def country_opportunity(
    country_iso3: str,
    year: int | None = None,
    origin_iso3: str = "CHN",
    sort: str = Query(
        default="opportunity", pattern=r"^(opportunity|china_import|growth|headroom)$"
    ),
    q: str | None = Query(default=None, max_length=100),
    opportunity_type: str | None = Query(
        default=None,
        pattern=r"^(FAST_GROWTH|WHITE_SPACE|SCALE_LEADER|EMERGING|WATCH)$",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    result = country_opportunity_detail(
        db,
        country_iso3=country_iso3,
        year=year,
        max_year=settings.latest_complete_year,
        min_year=settings.trade_data_start_year,
        origin_iso3=origin_iso3,
        sort=sort,
        q=q,
        opportunity_type=opportunity_type,
        page=page,
        page_size=page_size,
    )
    if result is None:
        raise HTTPException(404, "Country opportunity analysis not found")
    return result


@router.get("/catalog/hs")
def hs_analysis_catalog(
    q: str | None = Query(default=None, max_length=100),
    status: str = Query(default="ALL", pattern=r"^(ALL|READY|NOT_ANALYZED)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    verified_opportunity_codes = (
        select(MarketOpportunity.hs_code)
        .where(
            exists(
                select(Evidence.id).where(
                    Evidence.entity_type == "MARKET_OPPORTUNITY",
                    Evidence.entity_id == MarketOpportunity.id,
                    Evidence.source_type != "FIXTURE",
                )
            )
        )
        .distinct()
    )
    opportunity_exists = HsProduct.hs_code.in_(verified_opportunity_codes)
    filters = [HsProduct.level == 6, HsProduct.is_active.is_(True)]
    if q and q.strip():
        term = f"%{q.strip()}%"
        filters.append(
            or_(
                HsProduct.hs_code.like(term),
                HsProduct.name_en.ilike(term),
                HsProduct.name_zh.ilike(term),
            )
        )
    if status == "READY":
        filters.append(opportunity_exists)
    elif status == "NOT_ANALYZED":
        filters.append(~opportunity_exists)

    total = db.scalar(select(func.count()).select_from(HsProduct).where(*filters)) or 0
    products = db.scalars(
        select(HsProduct)
        .where(*filters)
        .order_by(HsProduct.hs_code)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    codes = [product.hs_code for product in products]
    latest_runs: dict[str, AnalysisRun] = {}
    top_markets: dict[str, tuple[MarketOpportunity, Country]] = {}
    market_counts: dict[str, int] = {}
    if codes:
        for run in db.scalars(
            select(AnalysisRun)
            .where(AnalysisRun.hs_code.in_(codes))
            .order_by(AnalysisRun.hs_code, AnalysisRun.started_at.desc())
        ):
            latest_runs.setdefault(run.hs_code, run)
        opportunity_rows = db.execute(
            select(MarketOpportunity, Country)
            .join(Country, Country.iso3 == MarketOpportunity.destination_iso3)
            .where(
                MarketOpportunity.hs_code.in_(codes),
                exists(
                    select(Evidence.id).where(
                        Evidence.entity_type == "MARKET_OPPORTUNITY",
                        Evidence.entity_id == MarketOpportunity.id,
                        Evidence.source_type != "FIXTURE",
                    )
                ),
            )
            .order_by(
                MarketOpportunity.hs_code,
                MarketOpportunity.period_year.desc(),
                MarketOpportunity.rank_global,
            )
        ).all()
        latest_years: dict[str, int] = {}
        for opportunity, country in opportunity_rows:
            latest_year = latest_years.setdefault(opportunity.hs_code, opportunity.period_year)
            if opportunity.period_year != latest_year:
                continue
            market_counts[opportunity.hs_code] = market_counts.get(opportunity.hs_code, 0) + 1
            top_markets.setdefault(opportunity.hs_code, (opportunity, country))

    analyzed_total = (
        db.scalar(select(func.count()).select_from(verified_opportunity_codes.subquery())) or 0
    )
    hs_total = (
        db.scalar(
            select(func.count())
            .select_from(HsProduct)
            .where(HsProduct.level == 6, HsProduct.is_active.is_(True))
        )
        or 0
    )
    items = []
    for product in products:
        top = top_markets.get(product.hs_code)
        run = latest_runs.get(product.hs_code)
        items.append(
            {
                "hs_code": product.hs_code,
                "name_en": product.name_en,
                "name_zh": product.name_zh,
                "status": "READY"
                if top
                else (
                    run.status
                    if run and run.status in {"PENDING", "RUNNING", "FAILED"}
                    else "NOT_ANALYZED"
                ),
                "analysis_year": top[0].period_year if top else None,
                "markets_count": market_counts.get(product.hs_code, 0),
                "top_market_iso3": top[1].iso3 if top else None,
                "top_market_name": top[1].name_en if top else None,
                "top_score": top[0].market_attractiveness_score if top else None,
                "coverage": top[0].data_coverage_score if top else None,
                "last_analyzed_at": top[0].calculated_at if top else None,
                "error": run.error_message if run and run.status == "FAILED" else None,
            }
        )
    return {
        "summary": {
            "total_hs": hs_total,
            "analyzed_hs": analyzed_total,
            "remaining_hs": max(0, hs_total - analyzed_total),
            "coverage_percent": round(analyzed_total / hs_total * 100, 2) if hs_total else 0,
        },
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": items,
    }


@router.post("/analyses", response_model=AnalysisOut, status_code=202)
def create_analysis(
    payload: AnalysisCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    product = db.scalar(select(HsProduct).where(HsProduct.hs_code == payload.hs_code))
    if not product:
        raise HTTPException(404, "HS product not found")
    run = AnalysisRun(
        hs_code=payload.hs_code,
        origin_iso3=payload.origin_iso3.upper(),
        requested_year=settings.latest_complete_year,
    )
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
    latest_year = (
        select(func.max(MarketOpportunity.period_year))
        .where(
            MarketOpportunity.hs_code == hs_code,
            MarketOpportunity.origin_iso3 == origin_iso3,
        )
        .scalar_subquery()
    )
    return (
        select(MarketOpportunity, MarketMetric, Country)
        .join(
            MarketMetric,
            (MarketMetric.hs_code == MarketOpportunity.hs_code)
            & (MarketMetric.country_iso3 == MarketOpportunity.destination_iso3)
            & (MarketMetric.origin_iso3 == MarketOpportunity.origin_iso3)
            & (MarketMetric.period_year == MarketOpportunity.period_year),
        )
        .join(Country, Country.iso3 == MarketOpportunity.destination_iso3)
        .where(
            MarketOpportunity.hs_code == hs_code,
            MarketOpportunity.origin_iso3 == origin_iso3,
            MarketOpportunity.period_year == latest_year,
        )
    )


def serialize_opportunity(row) -> OpportunityListItem:
    opp, metric, country = row
    return OpportunityListItem(
        id=opp.id,
        rank=opp.rank_global,
        hs_code=opp.hs_code,
        destination_iso3=opp.destination_iso3,
        country_name=country.name_en,
        region=country.region,
        period_year=opp.period_year,
        score=opp.market_attractiveness_score,
        coverage=opp.data_coverage_score,
        import_value_usd=metric.import_value_usd,
        cagr_3y=metric.cagr_3y,
        yoy_growth=metric.yoy_growth,
        china_share=metric.china_import_share,
        size_score=opp.size_score,
        growth_score=opp.growth_score,
        momentum_score=opp.momentum_score,
        stability_score=opp.stability_score,
    )


def confidence_label(score: float | None) -> str:
    if score is None:
        return "UNKNOWN"
    return "HIGH" if score >= 80 else "MEDIUM" if score >= 55 else "LOW"


@router.get("/opportunities", response_model=list[OpportunityListItem])
def opportunities(
    hs_code: str,
    origin_iso3: str = "CHN",
    sort: str = "score",
    limit: int = Query(50, ge=1, le=250),
    region: str | None = None,
    min_score: float = 0,
    min_coverage: float = 0,
    db: Session = Depends(get_db),
):
    query = opportunity_query(hs_code, origin_iso3).where(
        MarketOpportunity.market_attractiveness_score >= min_score,
        MarketOpportunity.data_coverage_score >= min_coverage,
    )
    if region:
        query = query.where(Country.region == region)
    order = {
        "score": MarketOpportunity.market_attractiveness_score,
        "growth": MarketMetric.cagr_3y,
        "size": MarketMetric.import_value_usd,
    }.get(sort, MarketOpportunity.market_attractiveness_score)
    return [
        serialize_opportunity(row)
        for row in db.execute(query.order_by(desc(order)).limit(limit)).all()
    ]


@router.get("/opportunities/{opportunity_id}")
def opportunity_detail(opportunity_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        select(MarketOpportunity, MarketMetric, Country)
        .join(
            MarketMetric,
            (MarketMetric.hs_code == MarketOpportunity.hs_code)
            & (MarketMetric.country_iso3 == MarketOpportunity.destination_iso3)
            & (MarketMetric.period_year == MarketOpportunity.period_year),
        )
        .join(Country, Country.iso3 == MarketOpportunity.destination_iso3)
        .where(MarketOpportunity.id == opportunity_id)
    ).first()
    if not row:
        raise HTTPException(404, "Opportunity not found")
    item = serialize_opportunity(row)
    opp = row[0]
    evidence = db.scalars(
        select(Evidence).where(
            Evidence.entity_type == "MARKET_OPPORTUNITY", Evidence.entity_id == opportunity_id
        )
    ).all()
    signals = db.scalars(
        select(DemandSignal)
        .where(
            DemandSignal.hs_code == opp.hs_code, DemandSignal.country_iso3 == opp.destination_iso3
        )
        .order_by(DemandSignal.signal_layer, DemandSignal.metric_key)
    ).all()
    supply = db.scalar(
        select(SupplyFit)
        .where(
            SupplyFit.hs_code == opp.hs_code,
            or_(SupplyFit.country_iso3 == opp.destination_iso3, SupplyFit.country_iso3.is_(None)),
        )
        .order_by(SupplyFit.calculated_at.desc())
    )
    economics = db.scalar(
        select(DistributionEconomics)
        .where(DistributionEconomics.opportunity_id == opportunity_id)
        .order_by(DistributionEconomics.calculated_at.desc())
    )
    risks = db.scalars(
        select(OpportunityRisk).where(OpportunityRisk.opportunity_id == opportunity_id)
    ).all()
    recommendations = db.scalars(
        select(DecisionRecommendation)
        .where(DecisionRecommendation.opportunity_id == opportunity_id)
        .order_by(DecisionRecommendation.created_at.desc())
    ).all()
    access = db.scalar(
        select(MarketAccessMetric)
        .where(
            MarketAccessMetric.hs_code == opp.hs_code,
            MarketAccessMetric.country_iso3 == opp.destination_iso3,
            MarketAccessMetric.origin_iso3 == opp.origin_iso3,
        )
        .order_by(MarketAccessMetric.period_year.desc())
    )
    macro: dict[str, dict] = {}
    for metric in db.scalars(
        select(CountryMetric)
        .where(CountryMetric.country_iso3 == opp.destination_iso3)
        .order_by(CountryMetric.period_year.desc(), CountryMetric.metric_key)
    ):
        macro.setdefault(
            metric.metric_key,
            {
                "value": metric.value_numeric,
                "value_text": metric.value_text,
                "unit": metric.unit,
                "year": metric.period_year,
                "observed_type": metric.observed_type,
            },
        )
    tenders = db.scalars(
        select(ExplicitDemand)
        .where(
            ExplicitDemand.hs_code == opp.hs_code,
            ExplicitDemand.buyer_country_iso3 == opp.destination_iso3,
        )
        .order_by(ExplicitDemand.published_at.desc())
        .limit(20)
    ).all()
    history = trade_history(opp.hs_code, opp.destination_iso3, opp.origin_iso3, db)
    reasons = []
    if opp.size_score >= 90:
        reasons.append(
            {"sentiment": "positive", "text": "Market size ranks in the global top 10%."}
        )
    if item.cagr_3y is not None:
        reasons.append(
            {
                "sentiment": "positive" if item.cagr_3y >= 0 else "negative",
                "text": f"Three-year structural growth is {item.cagr_3y:.1%}.",
            }
        )
    if item.yoy_growth is not None:
        reasons.append(
            {
                "sentiment": "positive" if item.yoy_growth >= 0 else "negative",
                "text": f"Latest complete-year momentum is {item.yoy_growth:.1%}.",
            }
        )
    if opp.stability_score is not None and opp.stability_score < 50:
        reasons.append(
            {
                "sentiment": "negative",
                "text": "Recent import values are more volatile than a stable market.",
            }
        )
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
    signal_layers = {
        layer: []
        for layer in ("STRUCTURAL", "DIGITAL", "MARKETPLACE", "EXPLICIT", "MACRO", "ACCESS")
    }
    for signal in signals:
        signal_layers.setdefault(signal.signal_layer, []).append(
            {
                "metric_key": signal.metric_key,
                "value_numeric": signal.value_numeric,
                "value_text": signal.value_text,
                "normalized_value": signal.normalized_value,
                "observed_type": signal.observed_type,
                "reliability": signal.source_reliability,
                "freshness": signal.freshness_status,
                "confidence": signal.confidence,
            }
        )
    return {
        **item.model_dump(),
        "market": {
            "hs_code": opp.hs_code,
            "origin_iso3": opp.origin_iso3,
            "destination_iso3": opp.destination_iso3,
            "country_name": item.country_name,
            "channel": opp.channel,
            "period_start": opp.period_start,
            "period_end": opp.period_end,
            "status": opp.status,
        },
        "scores": scores,
        "confidence_label": confidence_label(opp.confidence_score),
        "score_version": opp.score_version,
        "history": [h.model_dump() for h in history],
        "signals": signal_layers,
        "macro": macro,
        "market_access": {
            column.name: getattr(access, column.name)
            for column in MarketAccessMetric.__table__.columns
            if column.name not in {"id", "source_id"}
        }
        if access
        else None,
        "explicit_demands": [
            {
                "id": tender.id,
                "buyer_name": tender.buyer_name,
                "title": tender.title,
                "budget_max": tender.budget_max,
                "currency": tender.currency,
                "deadline": tender.deadline,
                "published_at": tender.published_at,
                "source_url": tender.source_url,
                "status": tender.status,
                "observed_type": tender.observed_type,
            }
            for tender in tenders
        ],
        "supply": {
            "status": "CONNECTED",
            **{
                column.name: getattr(supply, column.name)
                for column in SupplyFit.__table__.columns
                if column.name not in {"id", "source_id"}
            },
        }
        if supply
        else {"status": "NOT_CONNECTED"},
        "economics": {
            "status": "AVAILABLE",
            **{
                column.name: getattr(economics, column.name)
                for column in DistributionEconomics.__table__.columns
                if column.name not in {"id", "opportunity_id"}
            },
        }
        if economics
        else {"status": "NOT_ENOUGH_DATA"},
        "risk": [
            {
                "risk_type": risk.risk_type,
                "score": risk.score,
                "reason": risk.reason,
                "status": risk.status,
                "evidence_ids": risk.evidence_ids,
            }
            for risk in risks
        ],
        "evidence": [
            {
                "id": e.id,
                "metric_key": e.metric_key,
                "source_type": e.source_type,
                "source_identifier": e.source_identifier,
                "source_url": e.source_url,
                "source_reliability": e.source_reliability,
                "observed_type": e.observed_type,
                "freshness": "FRESH",
                "period": e.period,
                "raw_value": e.raw_value,
                "display_value": e.display_value,
                "retrieved_at": e.retrieved_at,
                "confidence": e.confidence,
                "notes": e.notes,
            }
            for e in evidence
        ],
        "recommendations": [
            {
                "recommendation": row.recommendation,
                "reason": row.reason,
                "evidence_ids": row.evidence_ids,
                "confidence": row.confidence,
                "human_status": row.human_status,
            }
            for row in recommendations
        ],
        "reasons": reasons,
    }


@router.get("/trade/history", response_model=list[HistoryItem])
def trade_history(
    hs_code: str, country_iso3: str, origin_iso3: str = "CHN", db: Session = Depends(get_db)
):
    totals = db.scalars(
        select(TradeObservation)
        .where(
            TradeObservation.hs_code == hs_code,
            TradeObservation.reporter_iso3 == country_iso3,
            TradeObservation.partner_iso3 == "WLD",
            TradeObservation.flow == "IMPORT",
        )
        .order_by(TradeObservation.period_year)
    ).all()
    bilateral = {
        r.period_year: r.trade_value_usd
        for r in db.scalars(
            select(TradeObservation).where(
                TradeObservation.hs_code == hs_code,
                TradeObservation.reporter_iso3 == country_iso3,
                TradeObservation.partner_iso3 == origin_iso3,
                TradeObservation.flow == "IMPORT",
            )
        ).all()
    }
    return [
        HistoryItem(
            year=r.period_year,
            import_value_usd=r.trade_value_usd,
            china_value_usd=bilateral.get(r.period_year),
            china_share=bilateral.get(r.period_year) / r.trade_value_usd
            if bilateral.get(r.period_year) and r.trade_value_usd
            else None,
        )
        for r in totals
    ]


@router.get("/trade/suppliers", response_model=list[SupplierItem])
def suppliers(hs_code: str, country_iso3: str, year: int, db: Session = Depends(get_db)):
    total = (
        db.scalar(
            select(TradeObservation.trade_value_usd).where(
                TradeObservation.hs_code == hs_code,
                TradeObservation.reporter_iso3 == country_iso3,
                TradeObservation.partner_iso3 == "WLD",
                TradeObservation.period_year == year,
            )
        )
        or 0
    )
    rows = db.execute(
        select(TradeObservation, Country)
        .outerjoin(Country, Country.iso3 == TradeObservation.partner_iso3)
        .where(
            TradeObservation.hs_code == hs_code,
            TradeObservation.reporter_iso3 == country_iso3,
            TradeObservation.partner_iso3 != "WLD",
            TradeObservation.period_year == year,
        )
        .order_by(TradeObservation.trade_value_usd.desc())
    ).all()
    return [
        SupplierItem(
            supplier_iso3=record.partner_iso3,
            supplier_name=country.name_en if country else record.partner_iso3,
            trade_value_usd=record.trade_value_usd,
            share=record.trade_value_usd / total if total else 0,
            rank=index,
        )
        for index, (record, country) in enumerate(rows, 1)
    ]


@router.get("/admin/data")
def admin_data(db: Session = Depends(get_db)):
    latest = db.scalar(
        select(SourceSnapshot.retrieved_at).order_by(SourceSnapshot.retrieved_at.desc()).limit(1)
    )
    runs = db.scalars(select(AnalysisRun).order_by(AnalysisRun.started_at.desc()).limit(20)).all()
    return {
        "source_status": "READY" if latest else "NO_DATA",
        "last_sync": latest,
        "analysis_runs": [
            {
                "id": r.id,
                "hs_code": r.hs_code,
                "status": r.status,
                "started_at": r.started_at,
                "error": r.error_message,
            }
            for r in runs
        ],
        "cached_products": db.scalar(select(func.count()).select_from(HsProduct)),
        "trade_records": db.scalar(select(func.count()).select_from(TradeObservation)),
    }


@router.get("/admin/comtrade-pipeline")
def comtrade_pipeline_status(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    return pipeline_status(settings, db)


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
def tariffs(
    hs_code: str, country_iso3: str, origin_iso3: str = "CHN", db: Session = Depends(get_db)
):
    rows = db.scalars(
        select(MarketAccessMetric)
        .where(
            MarketAccessMetric.hs_code == hs_code,
            MarketAccessMetric.country_iso3 == country_iso3.upper(),
            MarketAccessMetric.origin_iso3 == origin_iso3.upper(),
        )
        .order_by(MarketAccessMetric.period_year.desc())
    ).all()
    return [
        {column.name: getattr(row, column.name) for column in MarketAccessMetric.__table__.columns}
        for row in rows
    ]


@router.get("/macro")
def macro(country_iso3: str, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(CountryMetric)
        .where(CountryMetric.country_iso3 == country_iso3.upper())
        .order_by(CountryMetric.period_year.desc(), CountryMetric.metric_key)
    ).all()
    return [
        {column.name: getattr(row, column.name) for column in CountryMetric.__table__.columns}
        for row in rows
    ]


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
        "records": [
            {
                column.name: getattr(row, column.name)
                for column in MarketplaceSignal.__table__.columns
            }
            for row in rows
        ],
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
        "records": [
            {column.name: getattr(row, column.name) for column in ExplicitDemand.__table__.columns}
            for row in rows
        ],
    }


@router.get("/supply")
def supply(hs_code: str, country_iso3: str | None = None, db: Session = Depends(get_db)):
    query = select(SupplyFit).where(SupplyFit.hs_code == hs_code)
    if country_iso3:
        query = query.where(
            or_(SupplyFit.country_iso3 == country_iso3.upper(), SupplyFit.country_iso3.is_(None))
        )
    rows = db.scalars(query.order_by(SupplyFit.calculated_at.desc())).all()
    return [
        {column.name: getattr(row, column.name) for column in SupplyFit.__table__.columns}
        for row in rows
    ]


@router.get("/economics")
def economics(opportunity_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(DistributionEconomics)
        .where(DistributionEconomics.opportunity_id == opportunity_id)
        .order_by(DistributionEconomics.calculated_at.desc())
    ).all()
    return [
        {
            column.name: getattr(row, column.name)
            for column in DistributionEconomics.__table__.columns
        }
        for row in rows
    ]


@router.post("/economics", status_code=201)
def create_economics(payload: EconomicsInput, db: Session = Depends(get_db)):
    if not payload.verified:
        raise HTTPException(400, "Economics inputs must be verified before scoring")
    opportunity = db.get(MarketOpportunity, payload.opportunity_id)
    if opportunity is None:
        raise HTTPException(404, "Opportunity not found")
    calculated = calculate_economics(
        exw_cost=payload.exw_cost,
        freight_cost=payload.freight_cost,
        insurance_cost=payload.insurance_cost,
        tariff_rate=payload.tariff_rate,
        platform_commission_rate=payload.platform_commission_rate,
        fulfillment_cost=payload.fulfillment_cost,
        payment_cost=payload.payment_cost,
        return_allowance=payload.return_allowance,
        target_sale_price=payload.target_sale_price,
    )
    inputs = payload.model_dump(exclude={"input_source", "verified", "opportunity_id"})
    inputs["economics_score"] = calculated["economics_score"]
    row = DistributionEconomics(
        opportunity_id=opportunity.id,
        inputs=inputs,
        landed_cost=calculated["landed_cost"],
        channel_cost=calculated["channel_cost"],
        total_variable_cost=calculated["total_variable_cost"],
        target_sale_price=payload.target_sale_price,
        gross_profit=calculated["gross_profit"],
        contribution_profit=calculated["contribution_profit"],
        gross_margin=calculated["gross_margin"],
        contribution_margin=calculated["contribution_margin"],
        break_even_price=calculated["break_even_price"],
        input_source=payload.input_source,
        calculation_version="distribution_economics_v1",
    )
    db.add(row)
    db.flush()
    recompute_distribution_opportunity(db, opportunity)
    db.commit()
    db.refresh(row)
    return {
        column.name: getattr(row, column.name) for column in DistributionEconomics.__table__.columns
    }


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
    return db.scalars(
        select(OpportunityEvent).order_by(OpportunityEvent.detected_at.desc()).limit(limit)
    ).all()


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
def evidence_registry(
    entity_type: str | None = None, entity_id: int | None = None, db: Session = Depends(get_db)
):
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


def _sync_error(db: Session, provider_code: str, exc: Exception) -> None:
    db.rollback()
    now = datetime.now(UTC)
    source = db.scalar(select(DataSource).where(DataSource.code == provider_code))
    if source:
        source.last_failure_at = now
        source.status = "FAILED"
    db.add(
        DataJob(
            job_type="INGEST",
            provider_code=provider_code,
            status="FAILED",
            attempt=1,
            payload={},
            error=str(exc),
            started_at=now,
            finished_at=now,
        )
    )
    db.commit()


@router.post("/admin/sync/comtrade", status_code=202)
async def sync_comtrade_data(
    payload: TradeSyncRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        return await sync_comtrade(db, settings, payload)
    except Exception as exc:
        _sync_error(db, "UN_COMTRADE", exc)
        raise HTTPException(502, f"UN Comtrade sync failed: {exc}") from exc


@router.post("/admin/sync/world-bank", status_code=202)
async def sync_world_bank_data(
    payload: CountrySyncRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        return await sync_world_bank(db, settings, payload)
    except Exception as exc:
        _sync_error(db, "WORLD_BANK", exc)
        raise HTTPException(502, f"World Bank sync failed: {exc}") from exc


@router.post("/admin/sync/wits", status_code=202)
async def sync_wits_data(
    payload: TariffSyncRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        result = await sync_wits(db, settings, payload)
        opportunities = db.scalars(
            select(MarketOpportunity).where(MarketOpportunity.hs_code == payload.hs_code)
        ).all()
        for opportunity in opportunities:
            recompute_distribution_opportunity(db, opportunity)
        db.commit()
        return result
    except Exception as exc:
        _sync_error(db, "WITS_TRAINS", exc)
        raise HTTPException(502, f"WITS sync failed: {exc}") from exc


@router.post("/admin/sync/supplier", status_code=202)
async def sync_supplier_data(
    payload: SupplierSyncRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        return await sync_supplier(db, settings, payload.hs_code)
    except Exception as exc:
        _sync_error(db, "SUPPLIER_NETWORK", exc)
        raise HTTPException(502, f"Supplier sync failed: {exc}") from exc


@router.post("/admin/sync/marketplace", status_code=202)
async def sync_marketplace_data(
    payload: MarketplaceSyncRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        return await sync_marketplace(db, settings, payload)
    except Exception as exc:
        _sync_error(db, "MARKETPLACES", exc)
        raise HTTPException(502, f"Marketplace sync failed: {exc}") from exc


@router.post("/admin/sync/explicit-demand", status_code=202)
async def sync_explicit_demand_data(
    payload: ExplicitDemandSyncRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        return await sync_explicit_demand(db, settings, payload)
    except Exception as exc:
        _sync_error(db, "EXPLICIT_DEMAND", exc)
        raise HTTPException(502, f"TED explicit-demand sync failed: {exc}") from exc


@router.get("/admin/data-quality")
def data_quality(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    source_query = select(DataSource)
    if settings.trade_data_provider.lower() not in {"fixture", "test"}:
        source_query = source_query.where(DataSource.code != "COMTRADE_FIXTURE")
    sources = db.scalars(source_query.order_by(DataSource.category, DataSource.name)).all()
    providers = {item["code"]: item for item in build_provider_registry(settings).describe()}
    failed_runs = (
        db.scalar(
            select(func.count()).select_from(AnalysisRun).where(AnalysisRun.status == "FAILED")
        )
        or 0
    )
    failed_jobs = (
        db.scalar(select(func.count()).select_from(DataJob).where(DataJob.status == "FAILED")) or 0
    )
    missing_mappings = (
        db.scalar(
            select(func.count())
            .select_from(ProductHsMapping)
            .where(ProductHsMapping.status != "CONFIRMED")
        )
        or 0
    )
    low_confidence = (
        db.scalar(
            select(func.count())
            .select_from(MarketOpportunity)
            .where(
                or_(
                    MarketOpportunity.confidence_score < 55,
                    MarketOpportunity.confidence_score.is_(None),
                )
            )
        )
        or 0
    )
    reliability_query = select(DataSource.reliability, func.count())
    if settings.trade_data_provider.lower() not in {"fixture", "test"}:
        reliability_query = reliability_query.where(DataSource.code != "COMTRADE_FIXTURE")
    reliability = db.execute(reliability_query.group_by(DataSource.reliability)).all()
    source_ids = {source.id: source.code for source in sources}
    record_counts = {source.code: 0 for source in sources}

    def add_counts(model) -> None:
        for source_id, count in db.execute(
            select(model.source_id, func.count()).group_by(model.source_id)
        ):
            code = source_ids.get(source_id)
            if code:
                record_counts[code] = record_counts.get(code, 0) + int(count)

    for model in (CountryMetric, MarketAccessMetric, ExplicitDemand, MarketplaceSignal, SupplyFit):
        add_counts(model)
    for source_id, count in db.execute(
        select(SourceSnapshot.source_id, func.count(TradeObservation.id))
        .join(TradeObservation, TradeObservation.source_snapshot_id == SourceSnapshot.id)
        .group_by(SourceSnapshot.source_id)
    ):
        code = source_ids.get(source_id)
        if code:
            record_counts[code] = record_counts.get(code, 0) + int(count)

    def provider_state(source: DataSource) -> tuple[str, str]:
        connector_status = providers.get(source.code, {}).get("health", source.status)
        count = record_counts.get(source.code, 0)
        if count > 0:
            return connector_status, "DATA_READY"
        if source.last_success_at:
            return connector_status, "SYNCED_EMPTY"
        if connector_status == "AVAILABLE":
            return connector_status, "CONNECTOR_AVAILABLE"
        return connector_status, connector_status

    return {
        "generated_at": datetime.now(UTC),
        "provider_health": [
            {
                "code": source.code,
                "name": providers.get(source.code, {}).get("name", source.name),
                "category": source.category,
                "enabled": providers.get(source.code, {}).get("enabled", source.enabled),
                "connector_status": provider_state(source)[0],
                "status": provider_state(source)[1],
                "record_count": record_counts.get(source.code, 0),
                "reliability": source.reliability,
                "last_success_at": source.last_success_at,
                "last_failure_at": source.last_failure_at,
                "freshness_ttl_hours": source.freshness_ttl_hours,
            }
            for source in sources
        ],
        "coverage": {
            "trade_observations": db.scalar(select(func.count()).select_from(TradeObservation))
            or 0,
            "demand_signals": db.scalar(select(func.count()).select_from(DemandSignal)) or 0,
            "tariff_records": db.scalar(select(func.count()).select_from(MarketAccessMetric)) or 0,
            "macro_records": db.scalar(select(func.count()).select_from(CountryMetric)) or 0,
            "tender_records": db.scalar(select(func.count()).select_from(ExplicitDemand)) or 0,
            "opportunities": db.scalar(select(func.count()).select_from(MarketOpportunity)) or 0,
        },
        "stale_sources": [source.code for source in sources if source.status == "STALE"],
        "failed_syncs": failed_runs + failed_jobs,
        "missing_hs_mappings": missing_mappings,
        "low_confidence_opportunities": low_confidence,
        "source_reliability": {key: count for key, count in reliability},
        "recent_revisions": db.scalar(
            select(func.count())
            .select_from(SourceSnapshot)
            .where(SourceSnapshot.source_revision.is_not(None))
        )
        or 0,
    }
