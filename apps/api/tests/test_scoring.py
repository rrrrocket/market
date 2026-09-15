import pytest

from app.integrations.supplier import SupplySummary
from app.scoring.engine import (
    cagr,
    coefficient_of_variation,
    confidence_score,
    distribution_opportunity_score,
    growth_score,
    momentum_score,
    percentile_scores,
    stability_score,
    weighted_score,
    yoy,
)
from app.services.opportunity import calculate_economics, calculate_supply_fit


def test_percentile_rank_and_ties():
    scores = percentile_scores({"a": 1, "b": 2, "c": 2, "d": 4})
    assert scores == {"a": 0.0, "b": 50.0, "c": 50.0, "d": 100.0}


def test_growth_momentum_and_stability_bounds():
    assert growth_score(-0.25) == 0
    assert growth_score(0.50) == 100
    assert momentum_score(-0.50) == 0
    assert momentum_score(1.0) == 100
    assert stability_score(0) == 100
    assert stability_score(1.5) == 0


def test_metrics():
    assert cagr(133.1, 100) == pytest.approx(0.1)
    assert yoy(120, 100) == pytest.approx(0.2)
    assert coefficient_of_variation([100, 100, 100, 100]) == 0
    assert coefficient_of_variation([100, 100, 100]) is None


def test_missing_component_reweights_but_reduces_coverage():
    score = weighted_score(100, 50, 0, None)
    assert score.coverage == 90
    assert score.total == pytest.approx((4500 + 1500) / 90, abs=0.01)


def test_confidence_is_independent_from_business_score():
    result = confidence_score(80, ["A", "B_PLUS"], ["FRESH", "AGING"], 75)
    assert 0 < result.score < 100
    assert result.label in {"HIGH", "MEDIUM", "LOW"}


def test_distribution_score_requires_supply_and_economics():
    assert (
        distribution_opportunity_score(
            demand=90,
            supply_fit=None,
            economics=None,
            competition=60,
            market_access=80,
            risk=70,
        )
        is None
    )
    assert (
        distribution_opportunity_score(
            demand=90,
            supply_fit=80,
            economics=70,
            competition=None,
            market_access=80,
            risk=70,
        )
        is not None
    )


def test_verified_supply_and_economics_can_unlock_distribution_inputs():
    supply = calculate_supply_fit(
        SupplySummary(
            hs_code="902620",
            supplier_count=12,
            active_offer_count=8,
            quality_score=82,
            historical_delivery_score=90,
            available=True,
        )
    )
    economics = calculate_economics(
        exw_cost=20,
        freight_cost=4,
        insurance_cost=1,
        tariff_rate=5,
        platform_commission_rate=12,
        fulfillment_cost=3,
        payment_cost=1,
        return_allowance=2,
        target_sale_price=50,
    )
    assert supply is not None
    assert economics["contribution_margin"] > 0
    assert economics["economics_score"] > 50
