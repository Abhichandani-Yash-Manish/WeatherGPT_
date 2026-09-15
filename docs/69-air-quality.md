# Air quality: modelled pollutants and the source's own index, never a health call — 15 September 2026

This batch adds a governed air-quality product for a point: hourly concentrations of six
pollutants and the source's own US and European air-quality indices, plus the provider's
current hour. It closes **no named gap** in the problem-statement coverage matrix — the
real PS1 gaps are radar/satellite imagery and a live station observation for an arbitrary
place — and it says so rather than claiming a feature it does not close.

## What landed

| Landed | Where | Evidence |
|---|---|---|
| A catalogue of six pollutants and two air-quality indices, each with its own unit, kept apart | `weathergpt_data/adapters.py` | `tests/test_air_quality.py` |
| One response normalised into hourly records and the provider's current-instant block | `weathergpt_data/adapters.py` | `test_pollutants_and_indices_keep_their_own_units`, `test_a_missing_current_variable_is_unknown_not_zero` |
| A fetch path through the governed store | `weathergpt_data/foundation.py` | `FoundationAirQualityTests` |
| A command-line artefact | `scripts/air_quality.py` | `research/implementation/air-quality-20260915/air-quality-2026-09-15T121236Z.{json,md}` |
| A product view `/api/air-quality` | `weathergpt_data/product_api.py` | `ProductViewTests` |
| An air-quality question answered in chat, with the current hour kept apart from the window | `weathergpt_data/air_quality_tasks.py`, `weathergpt_data/task_dispatch.py` | `AirQualityChatTests`; `research/implementation/air-quality-20260915/live-chat.json` |
| A deterministic rules shape, prompt entry and tool catalogue entry | `weathergpt_data/rule_planner.py`, `weathergpt_data/language.py`, `weathergpt_data/capabilities.py` | `test_an_air_quality_question_is_an_air_quality_task` |

## The source is measured, not read from a table

`scripts/probe_air_quality_catalogue.py` records the hourly catalogue, the units, the
returned grid and the current block from what the service returned, and pins three
negative controls (`research/implementation/air-quality-20260915/air-quality-probe.json`):

- The six pollutants return in **µg/m³** and the two indices in **USAQI** and **EAQI**;
  the current block answers.
- A **daily** aggregation is rejected, which is why this product stays hourly; a forecast
  beyond **seven days** is rejected; an **unknown variable** is rejected.
- India is served by the **CAMS global** domain (0.4° ≈ 45 km), returned at a coarse cell;
  the European 11 km domain does not apply.

## The limits are the point

- It is **CAMS modelled output**, not a monitor measurement, and **no ground monitor is
  connected**; the answering grid cell is named with its distance from the requested point.
- An **air-quality index is the source's own index** (US EPA or European EEA). The product
  reports its number and its unit; it **never computes its own risk score, band or combined
  index**, and never renames a concentration to an index.
- **No health advice** is produced: no safe-to-go-outside, masks, avoid-exercise or
  school-closure wording, and no official air-quality warning — CPCB and IMD are not
  connected.
- Missing stays missing: a current hour the provider omits is unknown with a quality flag,
  not zero.

## Measured on this machine, 15 September 2026

- `python3 scripts/air_quality.py --lat 28.6139 --lon 77.2090 --days 2` wrote a Delhi
  artefact: current PM2.5 40.2 µg/m³ and US AQI 185 in the provider's own index, an hourly
  window of 37.6–118.3 µg/m³ and 105–214 USAQI, at the returned cell 28.60, 77.20.
- `python3 scripts/rehearse_air_quality_chat.py` answered four turns, every one planned by
  the deterministic rules (`provider: deterministic_rules`): a general air-quality question
  (100 facts), PM2.5 for New Delhi (25), ozone for Ahmedabad (25), and a plain forecast
  that stayed a forecast.

**995 Python tests** are collected; the checks added here pass.

## What this does not establish

- No health, exposure or risk assessment, and no medical or protective-action advice.
- No monitor agreement: modelled cells are not nearby-station readings, and the cell can be
  tens of kilometres from the requested point.
- No official air-quality warning or CPCB/IMD applicability.
- No pollen, ammonia, CO₂, UV or aerosol optical depth, and no European 11 km domain.
- Model run lineage is not exposed, and this product uses the Foundation store rather than
  the ingestion job queue, so member-level budgets and leases for it remain a follow-up.

## Registry

The connector names **S69** (*Open-Meteo air-quality delivery*). It is registered in
`data/registry/sources.json`, classified in `scripts/audit_sources.py`, and its ledger row
is rebuilt by `python3 scripts/audit_sources.py --only S69 --apply`.

## Files

- `weathergpt_data/adapters.py`, `weathergpt_data/foundation.py`, `weathergpt_data/product_api.py`,
  `weathergpt_data/air_quality_tasks.py`, `weathergpt_data/rule_planner.py`, `weathergpt_data/task_dispatch.py`
- `scripts/air_quality.py`, `scripts/probe_air_quality_catalogue.py`, `scripts/rehearse_air_quality_chat.py`
- `tests/test_air_quality.py`, `tests/test_providers.py`
- `research/implementation/air-quality-20260915/air-quality-probe.json`, `air-quality-2026-09-15T121236Z.{json,md}`, `live-chat.json`
