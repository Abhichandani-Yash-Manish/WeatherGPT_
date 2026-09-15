# Forecast vintages: what can be measured, and what still cannot — 15 September 2026

[The gap register](31-full-solution-gap-register.md) records **G16**: no scientific forecast verification has been performed, and the required inputs are archived forecast vintages with run identity plus matched observations. This batch checks what the local store actually holds, measures the part that is honestly measurable, and records the skill half as blocked rather than approximating it.

## What the store holds

The ingestion store keeps 64 committed versions, 37 of them forecast retrievals for the same point (Ahmedabad), spanning 12 to 14 September 2026, plus marine, river and one historical window. Each version carries the full result payload with per-hour records and coverage, and the committed instant. Upstream model run identity is **not** exposed; the records say so themselves ("Run identity not exposed; retrieval time is not model issue time").

## What was measured: vintage variance, not skill

scripts/measure_vintage_variance.py compares, for every requested point, parameter and valid hour covered by more than one stored retrieval, the earliest and latest value. Live report: research/implementation/vintage-variance-20260915/report.json.

| Parameter | Valid hours compared | Mean absolute change | Largest absolute change |
|---|---:|---:|---:|
| temperature_2m | 744 | 0.70 °C | 4.8 °C |
| relative_humidity_2m | 744 | 3.98 % | 36 % |
| precipitation | 744 | 0.94 mm | 30.3 mm |
| wind_speed_10m | 744 | recorded in the report | recorded in the report |

One example makes the interpretation limit concrete: a 4.8 °C difference for the same valid hour came from two retrievals committed **one second apart**, so the change cannot be attributed to a model rerun. The report states what it does not establish: forecast skill, calibration or accuracy; attribution to a model run; spatial representativeness.

**635 automated tests pass**, including two checks over a synthetic store: overlapping hours are compared while single-vintage hours are ignored, and a single-vintage store reports no change while stating the skill limitation.

## The skill half stays blocked

Forecast verification needs three things the workspace does not have:

1. **Archived vintages with upstream run identity.** Retrieval time is not issue time, and the store records no run identity.
2. **Matched observations or a verified analysis** for the same valid hours and place. The daily reanalysis adapter is modelled history with a recent-day gap, and no station series is connected at scale.
3. **A predeclared verification design** (horizon, variable, place, season, sample size).

Until those exist, no skill, calibration or accuracy number is produced anywhere, and vintage variance is reported only as what it is.
