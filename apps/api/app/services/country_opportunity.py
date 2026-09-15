from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Country, HsProduct, SourceSnapshot, TradeObservation
from app.scoring.engine import (
    cagr,
    coefficient_of_variation,
    growth_score,
    momentum_score,
    stability_score,
    yoy,
)


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _percentiles(values: dict[str, float]) -> dict[str, float]:
    """Return inclusive percentile ranks in O(n log n), averaging ties."""
    if not values:
        return {}
    if len(values) == 1:
        return {next(iter(values)): 100.0}
    grouped: dict[float, list[str]] = defaultdict(list)
    for key, value in values.items():
        grouped[value].append(key)
    result: dict[str, float] = {}
    position = 0
    denominator = len(values) - 1
    for value in sorted(grouped):
        keys = grouped[value]
        average_rank = position + (len(keys) - 1) / 2
        score = round(100 * average_rank / denominator, 2)
        result.update(dict.fromkeys(keys, score))
        position += len(keys)
    return result


def _weighted(parts: dict[str, tuple[float | None, float]]) -> tuple[float, float]:
    available = [
        (value, weight)
        for value, weight in parts.values()
        if value is not None and math.isfinite(value)
    ]
    if not available:
        return 0.0, 0.0
    weight = sum(item[1] for item in available)
    return round(sum(value * item_weight for value, item_weight in available) / weight, 2), weight


def _trend(latest: float | None, previous: float | None, annual_growth: float | None) -> str:
    if latest is None:
        return "UNKNOWN"
    momentum = yoy(latest, previous)
    if latest > 0 and (previous is None or previous == 0):
        return "NEW"
    if momentum is not None and annual_growth is not None:
        if momentum >= 0.2 and annual_growth >= 0.15:
            return "FAST_GROWTH"
        if momentum > 0 and momentum >= annual_growth + 0.05:
            return "ACCELERATING"
    if (annual_growth is not None and annual_growth >= 0.05) or (
        momentum is not None and momentum >= 0.1
    ):
        return "GROWING"
    if momentum is not None and momentum <= -0.1:
        return "DECLINING"
    return "STABLE"


def _bulk_source_filter():
    return or_(
        SourceSnapshot.source_identifier.like("local:%"),
        SourceSnapshot.source_type == "FIXTURE",
    )


def country_opportunity_catalog(
    db: Session, *, year: int, origin_iso3: str = "CHN"
) -> dict[str, Any]:
    origin_iso3 = origin_iso3.upper()
    history_rows = db.execute(
        select(
            TradeObservation.reporter_iso3,
            TradeObservation.period_year,
            TradeObservation.partner_iso3,
            func.sum(TradeObservation.trade_value_usd),
            func.count(TradeObservation.id),
        )
        .join(SourceSnapshot, SourceSnapshot.id == TradeObservation.source_snapshot_id)
        .where(
            _bulk_source_filter(),
            TradeObservation.partner_iso3.in_([origin_iso3, "WLD"]),
            TradeObservation.flow == "IMPORT",
            TradeObservation.period_type == "YEAR",
            TradeObservation.period_year.between(year - 3, year),
        )
        .group_by(
            TradeObservation.reporter_iso3,
            TradeObservation.period_year,
            TradeObservation.partner_iso3,
        )
    ).all()
    histories: dict[str, dict[str, dict[int, float]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    hs_counts: dict[str, dict[str, dict[int, int]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for iso3, period_year, partner, value, hs_count in history_rows:
        histories[iso3][partner][period_year] = float(value)
        hs_counts[iso3][partner][period_year] = int(hs_count)
    reporter_codes = [iso3 for iso3, values in histories.items() if values.get("WLD")]
    countries = {
        item.iso3: item
        for item in db.scalars(
            select(Country).where(Country.iso3.in_(reporter_codes))
        ).all()
    }

    items = []
    year_counts: dict[int, int] = defaultdict(int)
    for iso3 in reporter_codes:
        country = countries.get(iso3)
        if country is None:
            continue
        latest_year = max(histories[iso3]["WLD"])
        year_counts[latest_year] += 1
        china_history = histories[iso3][origin_iso3]
        latest = china_history.get(latest_year)
        total_value = histories[iso3]["WLD"][latest_year]
        previous = china_history.get(latest_year - 1)
        old = china_history.get(latest_year - 3)
        annual_growth = cagr(latest, old)
        items.append(
            {
                "iso3": iso3,
                "name": country.name_en,
                "name_zh": country.name_zh,
                "region": country.region,
                "year": latest_year,
                "china_import_value_usd": latest,
                "total_import_value_usd": total_value,
                "china_share": _safe_ratio(latest, total_value),
                "yoy_growth": yoy(latest, previous),
                "cagr_3y": annual_growth,
                "hs_count": hs_counts[iso3]["WLD"][latest_year],
                "imported_hs_count": hs_counts[iso3][origin_iso3].get(latest_year, 0),
                "trend": _trend(latest, previous, annual_growth),
            }
        )
    items.sort(
        key=lambda item: (
            item["china_import_value_usd"] is None,
            -(item["china_import_value_usd"] or 0),
            item["iso3"],
        )
    )
    for rank, item in enumerate(items, 1):
        item["rank"] = rank
    return {
        "year": year,
        "origin_iso3": origin_iso3,
        "countries": len(items),
        "latest_year_counts": dict(sorted(year_counts.items(), reverse=True)),
        "total_china_import_value_usd": sum(
            item["china_import_value_usd"] or 0 for item in items
        ),
        "items": items,
    }


def country_opportunity_detail(
    db: Session,
    *,
    country_iso3: str,
    year: int | None,
    max_year: int,
    min_year: int,
    origin_iso3: str = "CHN",
    sort: str = "opportunity",
    q: str | None = None,
    opportunity_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any] | None:
    country_iso3 = country_iso3.upper()
    origin_iso3 = origin_iso3.upper()
    country = db.scalar(select(Country).where(Country.iso3 == country_iso3))
    if country is None:
        return None

    available_years = db.scalars(
        select(TradeObservation.period_year)
        .join(SourceSnapshot, SourceSnapshot.id == TradeObservation.source_snapshot_id)
        .where(
            _bulk_source_filter(),
            TradeObservation.reporter_iso3 == country_iso3,
            TradeObservation.partner_iso3 == "WLD",
            TradeObservation.flow == "IMPORT",
            TradeObservation.period_type == "YEAR",
            TradeObservation.period_year <= max_year,
        )
        .distinct()
        .order_by(TradeObservation.period_year.desc())
    ).all()
    if not available_years:
        return None
    target_year = year if year is not None else available_years[0]
    if target_year not in available_years:
        return None

    history_rows = db.execute(
        select(
            TradeObservation.hs_code,
            TradeObservation.period_year,
            TradeObservation.partner_iso3,
            func.sum(TradeObservation.trade_value_usd),
        )
        .join(SourceSnapshot, SourceSnapshot.id == TradeObservation.source_snapshot_id)
        .where(
            _bulk_source_filter(),
            TradeObservation.reporter_iso3 == country_iso3,
            TradeObservation.partner_iso3.in_([origin_iso3, "WLD"]),
            TradeObservation.flow == "IMPORT",
            TradeObservation.period_type == "YEAR",
            TradeObservation.period_year.between(
                max(min_year, target_year - 3), target_year
            ),
        )
        .group_by(
            TradeObservation.hs_code,
            TradeObservation.period_year,
            TradeObservation.partner_iso3,
        )
    ).all()
    histories: dict[str, dict[str, dict[int, float]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    annual: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for hs_code, period_year, partner, value in history_rows:
        numeric = float(value)
        histories[hs_code][partner][period_year] = numeric
        annual[partner][period_year] += numeric

    current_codes = [
        hs_code
        for hs_code, partner_history in histories.items()
        if target_year in partner_history["WLD"]
    ]
    products = {
        product.hs_code: product
        for product in db.scalars(
            select(HsProduct).where(
                HsProduct.level == 6,
                HsProduct.hs_code.in_(current_codes),
            )
        ).all()
    }

    raw_products = []
    for hs_code in current_codes:
        product = products.get(hs_code)
        if product is None:
            continue
        china_history = histories[hs_code][origin_iso3]
        latest = china_history.get(target_year)
        previous = china_history.get(target_year - 1)
        old = china_history.get(target_year - 3)
        annual_growth = cagr(latest, old) if target_year - 3 >= min_year else None
        market_value = histories[hs_code]["WLD"][target_year]
        raw_products.append(
            {
                "hs_code": hs_code,
                "name_en": product.name_en,
                "name_zh": product.name_zh,
                "china_import_value_usd": latest,
                "total_import_value_usd": market_value,
                "unserved_value_usd": max(0.0, market_value - latest)
                if latest is not None
                else None,
                "china_share": _safe_ratio(latest, market_value),
                "yoy_growth": yoy(latest, previous),
                "cagr_3y": annual_growth,
                "volatility": coefficient_of_variation(
                    [china_history[item_year] for item_year in sorted(china_history)]
                ),
                "trend": _trend(latest, previous, annual_growth),
                "history": [
                    {"year": item_year, "value_usd": china_history[item_year]}
                    for item_year in sorted(china_history)
                ],
            }
        )

    scale = _percentiles(
        {
            item["hs_code"]: math.log1p(item["china_import_value_usd"])
            for item in raw_products
            if item["china_import_value_usd"] is not None
        }
    )
    headroom = _percentiles(
        {
            item["hs_code"]: math.log1p(item["unserved_value_usd"])
            for item in raw_products
            if item["unserved_value_usd"] is not None
        }
    )
    for item in raw_products:
        hs_code = item["hs_code"]
        score, coverage = _weighted(
            {
                "scale": (scale.get(hs_code), 30),
                "growth": (growth_score(item["cagr_3y"]), 25),
                "momentum": (momentum_score(item["yoy_growth"]), 15),
                "headroom": (headroom.get(hs_code), 20),
                "stability": (stability_score(item["volatility"]), 10),
            }
        )
        item["opportunity_score"] = score
        item["score_coverage"] = coverage
        share = item["china_share"]
        if item["trend"] == "FAST_GROWTH":
            item["opportunity_type"] = "FAST_GROWTH"
        elif headroom.get(hs_code, 0) >= 80 and share is not None and share < 0.1:
            item["opportunity_type"] = "WHITE_SPACE"
        elif scale.get(hs_code, 0) >= 80:
            item["opportunity_type"] = "SCALE_LEADER"
        elif item["trend"] in {"NEW", "ACCELERATING", "GROWING"}:
            item["opportunity_type"] = "EMERGING"
        else:
            item["opportunity_type"] = "WATCH"

    imported = sorted(
        (
            item
            for item in raw_products
            if item["china_import_value_usd"] is not None
            and item["china_import_value_usd"] > 0
        ),
        key=lambda item: (-item["china_import_value_usd"], item["hs_code"]),
    )
    for rank, item in enumerate(imported, 1):
        item["china_import_rank"] = rank
    imported_ranks = {item["hs_code"]: item["china_import_rank"] for item in imported}
    for item in raw_products:
        item["china_import_rank"] = imported_ranks.get(item["hs_code"])
    raw_products.sort(key=lambda item: (-item["opportunity_score"], item["hs_code"]))
    for rank, item in enumerate(raw_products, 1):
        item["opportunity_rank"] = rank

    filtered_products = raw_products
    if q and q.strip():
        term = q.strip().casefold()
        filtered_products = [
            item
            for item in filtered_products
            if term in item["hs_code"].casefold()
            or term in item["name_en"].casefold()
            or term in (item["name_zh"] or "").casefold()
        ]
    if opportunity_type:
        filtered_products = [
            item
            for item in filtered_products
            if item["opportunity_type"] == opportunity_type
        ]
    sort_key = {
        "china_import": lambda item: item["china_import_value_usd"]
        if item["china_import_value_usd"] is not None
        else -math.inf,
        "growth": lambda item: item["cagr_3y"] if item["cagr_3y"] is not None else -math.inf,
        "headroom": lambda item: item["unserved_value_usd"]
        if item["unserved_value_usd"] is not None
        else -math.inf,
        "opportunity": lambda item: item["opportunity_score"],
    }[sort]
    filtered_products.sort(key=lambda item: (-sort_key(item), item["hs_code"]))
    product_total = len(filtered_products)
    start = (page - 1) * page_size
    paginated_products = filtered_products[start : start + page_size]

    annual_history = []
    for item_year in range(max(min_year, target_year - 3), target_year + 1):
        china_value = annual[origin_iso3].get(item_year)
        total_value = annual["WLD"].get(item_year)
        if china_value is None and total_value is None:
            continue
        annual_history.append(
            {
                "year": item_year,
                "china_import_value_usd": china_value,
                "total_import_value_usd": total_value,
                "china_share": _safe_ratio(china_value, total_value),
            }
        )
    latest_china = annual[origin_iso3].get(target_year)
    latest_total = annual["WLD"].get(target_year)
    return {
        "country": {
            "iso3": country.iso3,
            "name": country.name_en,
            "name_zh": country.name_zh,
            "region": country.region,
            "subregion": country.subregion,
        },
        "origin_iso3": origin_iso3,
        "year": target_year,
        "summary": {
            "china_import_value_usd": latest_china,
            "total_import_value_usd": latest_total,
            "china_share": _safe_ratio(latest_china, latest_total),
            "yoy_growth": yoy(latest_china, annual[origin_iso3].get(target_year - 1)),
            "cagr_3y": cagr(latest_china, annual[origin_iso3].get(target_year - 3))
            if target_year - 3 >= min_year
            else None,
            "analyzed_hs_count": len(raw_products),
            "imported_hs_count": len(imported),
        },
        "history": annual_history,
        "products": paginated_products,
        "product_pagination": {
            "page": page,
            "page_size": page_size,
            "total": product_total,
            "sort": sort,
            "q": q,
            "opportunity_type": opportunity_type,
        },
        "methodology": {
            "score_version": "country_opportunity",
            "weights": {
                "china_import_scale": 30,
                "cagr_3y": 25,
                "yoy_momentum": 15,
                "market_headroom": 20,
                "stability": 10,
            },
        },
    }
