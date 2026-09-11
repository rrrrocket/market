from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

SCORE_VERSION = "market_attractiveness_v1"
WEIGHTS = {"size": 45.0, "growth": 30.0, "momentum": 15.0, "stability": 10.0}
RELIABILITY_SCORES = {
    "A_PLUS": 100.0,
    "A": 92.0,
    "A_MINUS": 85.0,
    "B_PLUS": 78.0,
    "B": 70.0,
    "C": 50.0,
    "D": 25.0,
}
FRESHNESS_SCORES = {"FRESH": 100.0, "AGING": 65.0, "STALE": 25.0, "UNKNOWN": 0.0}


def percentile_scores(values: dict[str, float]) -> dict[str, float]:
    """Inclusive percentile ranks; ties receive the same averaged rank."""
    if not values:
        return {}
    if len(values) == 1:
        return {next(iter(values)): 100.0}
    sorted_values = sorted(values.values())
    result: dict[str, float] = {}
    for key, value in values.items():
        indices = [i for i, candidate in enumerate(sorted_values) if candidate == value]
        average_rank = sum(indices) / len(indices)
        result[key] = round(100 * average_rank / (len(sorted_values) - 1), 2)
    return result


def linear_score(value: float, lower: float, upper: float) -> float:
    return round(100 * (min(max(value, lower), upper) - lower) / (upper - lower), 2)


def growth_score(cagr: float | None) -> float | None:
    return None if cagr is None else linear_score(cagr, -0.25, 0.50)


def momentum_score(yoy: float | None) -> float | None:
    return None if yoy is None else linear_score(yoy, -0.50, 1.00)


def stability_score(cv: float | None) -> float | None:
    return None if cv is None else round(100 - linear_score(cv, 0, 1.5), 2)


def cagr(latest: float | None, old: float | None, years: int = 3) -> float | None:
    if latest is None or old is None or latest < 0 or old <= 0:
        return None
    return (latest / old) ** (1 / years) - 1


def yoy(latest: float | None, previous: float | None) -> float | None:
    if latest is None or previous is None or previous <= 0:
        return None
    return latest / previous - 1


def coefficient_of_variation(values: list[float]) -> float | None:
    if len(values) < 4 or statistics.mean(values) <= 0:
        return None
    return statistics.pstdev(values) / statistics.mean(values)


@dataclass(frozen=True)
class ScoreResult:
    total: float
    coverage: float
    size: float | None
    growth: float | None
    momentum: float | None
    stability: float | None


def weighted_score(size: float | None, growth: float | None, momentum: float | None, stability: float | None) -> ScoreResult:
    parts = {"size": size, "growth": growth, "momentum": momentum, "stability": stability}
    available_weight = sum(WEIGHTS[key] for key, value in parts.items() if value is not None and math.isfinite(value))
    total = sum(WEIGHTS[key] * value for key, value in parts.items() if value is not None and math.isfinite(value)) / available_weight if available_weight else 0
    return ScoreResult(round(total, 2), available_weight, size, growth, momentum, stability)


@dataclass(frozen=True)
class ConfidenceResult:
    score: float
    label: str


def confidence_score(
    coverage: float,
    reliabilities: list[str],
    freshness: list[str],
    consistency: float | None,
) -> ConfidenceResult:
    reliability = (
        sum(RELIABILITY_SCORES.get(value, 0) for value in reliabilities) / len(reliabilities)
        if reliabilities else 0
    )
    freshness_score = (
        sum(FRESHNESS_SCORES.get(value, 0) for value in freshness) / len(freshness)
        if freshness else 0
    )
    parts = {
        "coverage": (coverage, 35.0),
        "reliability": (reliability, 30.0),
        "freshness": (freshness_score, 20.0),
        "consistency": (consistency, 15.0),
    }
    available = [(value, weight) for value, weight in parts.values() if value is not None]
    score = sum(value * weight for value, weight in available) / sum(weight for _, weight in available)
    rounded = round(score, 2)
    label = "HIGH" if rounded >= 80 else "MEDIUM" if rounded >= 55 else "LOW"
    return ConfidenceResult(rounded, label)


def distribution_opportunity_score(
    *,
    demand: float | None,
    supply_fit: float | None,
    economics: float | None,
    competition: float | None,
    market_access: float | None,
    risk: float | None,
) -> float | None:
    if demand is None or supply_fit is None or economics is None:
        return None
    weighted = {
        "demand": (demand, 30.0),
        "supply_fit": (supply_fit, 25.0),
        "economics": (economics, 20.0),
        "competition": (competition, 10.0),
        "market_access": (market_access, 10.0),
        "risk": (risk, 5.0),
    }
    available = [(value, weight) for value, weight in weighted.values() if value is not None]
    return round(sum(value * weight for value, weight in available) / sum(weight for _, weight in available), 2)
