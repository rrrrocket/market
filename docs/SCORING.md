# Market Attractiveness v1

```text
45% Market Size + 30% Structural Growth + 15% Momentum + 10% Stability
```

- Size: percentile rank of `log(import_value_usd + 1)` within the analyzed product cohort.
- Growth: 3-year CAGR, clipped to −25%…+50%, linearly mapped to 0…100.
- Momentum: latest complete-year YoY, clipped to −50%…+100%, linearly mapped.
- Stability: four-year population coefficient of variation. CV 0 → 100; CV ≥1.5 → 0.

Coverage equals the sum of weights whose inputs are present. Missing inputs are excluded and remaining weights are normalized; they are never silently scored as zero. This separates market attractiveness from data confidence.

The version string is `market_attractiveness_v1`. Formula changes require `v2`; historical definitions must not change in place.

The rule-based explanation reports observed percentile, CAGR, YoY, and volatility conditions. It does not call a generative model or invent market facts.

## Independent layer scores

Structural, digital, marketplace, explicit, market-access, country-capacity, supply-fit, economics, competition, and risk scores are nullable and versioned independently. A layer has no score until its minimum evidence requirements are satisfied.

## Distribution Opportunity

The reference weighting is Demand 30%, Supply Fit 25%, Economics 20%, Competition 10%, Market Access 10%, and Risk 5%. Demand, Supply Fit, and Economics are mandatory. If Supply Fit or Economics is absent, the result is `null` and the UI says `Not enough data`; Market Attractiveness is never relabeled as Distribution Opportunity.

## Confidence

Confidence uses Coverage 35%, Source Reliability 30%, Freshness 20%, and Cross-source Consistency 15%. Missing confidence components are reweighted and never treated as zero. Confidence maps to HIGH, MEDIUM, or LOW and remains separate from commercial scoring.
