from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.integrations.supplier import SupplySummary
from app.models import (
    DataSource,
    DistributionEconomics,
    MarketAccessMetric,
    MarketOpportunity,
    SupplyFit,
)
from app.scoring.engine import distribution_opportunity_score


def _weighted_available(parts: list[tuple[float | None, float]]) -> float | None:
    available = [(value, weight) for value, weight in parts if value is not None]
    if not available:
        return None
    return round(
        sum(value * weight for value, weight in available) / sum(weight for _, weight in available),
        2,
    )


def calculate_supply_fit(summary: SupplySummary) -> float | None:
    if not summary.available or summary.supplier_count <= 0:
        return None
    return _weighted_available(
        [
            (min(summary.supplier_count / 20, 1) * 100, 35),
            (min(summary.active_offer_count / 20, 1) * 100, 20),
            (summary.quality_score, 25),
            (summary.historical_delivery_score, 20),
        ]
    )


def sync_supply_fit(db: Session, hs_code: str, summary: SupplySummary) -> SupplyFit:
    source = db.scalar(select(DataSource).where(DataSource.code == "SUPPLIER_NETWORK"))
    row = db.scalar(
        select(SupplyFit).where(
            SupplyFit.hs_code == hs_code,
            SupplyFit.country_iso3.is_(None),
            SupplyFit.channel.is_(None),
        )
    )
    values = {
        "supplier_count": summary.supplier_count,
        "product_count": summary.product_count,
        "active_offer_count": summary.active_offer_count,
        "min_price": summary.min_price,
        "median_price": summary.median_price,
        "currency": summary.currency,
        "moq_min": summary.moq_min,
        "moq_median": summary.moq_median,
        "stock_total": summary.stock_total,
        "lead_time_min": summary.lead_time_min,
        "lead_time_median": summary.lead_time_median,
        "certified_supplier_count": summary.certified_supplier_count,
        "dropship_supplier_count": summary.dropship_supplier_count,
        "quality_score": summary.quality_score,
        "supply_fit_score": calculate_supply_fit(summary),
        "source_id": source.id if source else None,
        "calculated_at": datetime.now(UTC),
    }
    if row is None:
        row = SupplyFit(hs_code=hs_code, **values)
        db.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)
    if source:
        source.enabled = True
        source.status = "READY"
        source.last_success_at = datetime.now(UTC)
    db.flush()
    for opportunity in db.scalars(
        select(MarketOpportunity).where(MarketOpportunity.hs_code == hs_code)
    ):
        recompute_distribution_opportunity(db, opportunity)
    db.commit()
    db.refresh(row)
    return row


def calculate_economics(
    *,
    exw_cost: float,
    freight_cost: float,
    insurance_cost: float,
    tariff_rate: float,
    platform_commission_rate: float,
    fulfillment_cost: float,
    payment_cost: float,
    return_allowance: float,
    target_sale_price: float,
) -> dict:
    customs_base = exw_cost + freight_cost + insurance_cost
    landed_cost = customs_base * (1 + tariff_rate / 100)
    channel_cost = (
        target_sale_price * platform_commission_rate / 100
        + fulfillment_cost
        + payment_cost
        + return_allowance
    )
    total_variable_cost = landed_cost + channel_cost
    gross_profit = target_sale_price - landed_cost
    contribution_profit = target_sale_price - total_variable_cost
    gross_margin = gross_profit / target_sale_price
    contribution_margin = contribution_profit / target_sale_price
    break_even_price = (landed_cost + fulfillment_cost + payment_cost + return_allowance) / (
        1 - platform_commission_rate / 100
    )
    economics_score = max(0, min(100, round(50 + contribution_margin * 200, 2)))
    return {
        "landed_cost": round(landed_cost, 4),
        "channel_cost": round(channel_cost, 4),
        "total_variable_cost": round(total_variable_cost, 4),
        "gross_profit": round(gross_profit, 4),
        "contribution_profit": round(contribution_profit, 4),
        "gross_margin": round(gross_margin, 6),
        "contribution_margin": round(contribution_margin, 6),
        "break_even_price": round(break_even_price, 4),
        "economics_score": economics_score,
    }


def recompute_distribution_opportunity(db: Session, opportunity: MarketOpportunity) -> None:
    supply = db.scalar(
        select(SupplyFit)
        .where(
            SupplyFit.hs_code == opportunity.hs_code,
            or_(
                SupplyFit.country_iso3 == opportunity.destination_iso3,
                SupplyFit.country_iso3.is_(None),
            ),
        )
        .order_by(desc(SupplyFit.country_iso3), SupplyFit.calculated_at.desc())
    )
    economics = db.scalar(
        select(DistributionEconomics)
        .where(DistributionEconomics.opportunity_id == opportunity.id)
        .order_by(DistributionEconomics.calculated_at.desc())
    )
    access = db.scalar(
        select(MarketAccessMetric)
        .where(
            MarketAccessMetric.hs_code == opportunity.hs_code,
            MarketAccessMetric.country_iso3 == opportunity.destination_iso3,
            MarketAccessMetric.origin_iso3 == opportunity.origin_iso3,
        )
        .order_by(MarketAccessMetric.period_year.desc())
    )
    economics_score = economics.inputs.get("economics_score") if economics else None
    opportunity.supply_fit_score = supply.supply_fit_score if supply else None
    opportunity.economics_score = economics_score
    opportunity.market_access_score = access.market_access_score if access else None
    opportunity.distribution_opportunity_score = distribution_opportunity_score(
        demand=opportunity.structural_demand_score,
        supply_fit=opportunity.supply_fit_score,
        economics=opportunity.economics_score,
        competition=opportunity.competition_score,
        market_access=opportunity.market_access_score,
        risk=opportunity.risk_score,
    )
