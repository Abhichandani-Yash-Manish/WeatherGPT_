# Ensemble spread: the member distribution of one model, measured and not scored — 15 September 2026

PS3's definition of done lists **ensemble spread** as missing. This batch adds a governed
ensemble product for a point and window: the mean, the population spread, the member range and
nearest-rank p10/p50/p90 of one model's perturbed members, with the control run reported
separately. It is the last open half of the NWP row, after model-vs-model comparison
([docs/57](57-model-comparison.md)).

## What landed

| Landed | Where | Evidence |
|---|---|---|
| A catalogue of three governed ensemble models and three variables, each with its unit | `weathergpt_data/adapters.py` | `tests/test_ensemble.py` |
| One response normalised into control and member-statistic records: mean, population spread, min, max, nearest-rank p10/p50/p90, with the member count on every record | `weathergpt_data/adapters.py` | `test_mean_spread_range_and_nearest_rank_percentiles` |
| A member exceedance count for a precipitation threshold, reported as “k of n members” | `weathergpt_data/adapters.py` | `test_precipitation_exceedance_is_a_member_frequency` |
| A fetch path with model, variable and window selection through the governed store | `weathergpt_data/foundation.py` | `FoundationEnsembleTests` |
| A command-line artefact writing the packet and a Markdown summary | `scripts/ensemble.py` | `research/implementation/ensemble-spread-20260915/gfs025-2026-09-15T084*.md` |
| A product view `/api/ensemble` | `weathergpt_data/product_api.py` | `ProductViewTests` |

## The source is measured, not read from a table

The ensemble endpoint **requires** a model id and rejects an unknown one, so the ids and member
counts are what the service returned. `scripts/probe_ensemble_catalogue.py` records them and
confirms the rejection with an invalid-id control
(`research/implementation/ensemble-spread-20260915/ensemble-probe.json`):

- **gfs025** 30 members, **ecmwf_ifs025** 50, **icon_seamless** 39, each returning
  `temperature_2m` (°C), `precipitation` (mm) and `wind_speed_10m` (km/h) at a 0.25° cell.
- The endpoint also serves a stored mean/spread route with longer history; the probe records it
  and this batch does not use it.

## The statistics are deterministic and disclosed

Every number is computed from the returned members; none is inferred:

- **mean** is the arithmetic mean of the returned perturbed members;
- **spread** is the population standard deviation across them;
- **p10/p50/p90** are nearest-rank order statistics, so no value is interpolated;
- **exceedance** is a count of members at or above a stated threshold.

The method travels with the packet in `coverage.statistics`, and the answer notes that spread is
a property of the ensemble, **not a probability, a confidence, a risk or a skill score**, and
that a member exceedance is a frequency over members that are not independent draws. Fewer than
two non-null members at an hour leaves the spread and percentiles unknown rather than zero.

## Measured on this machine, 15 September 2026

A live `gfs025` run for Ahmedabad over two days returned status `ok` with 30 members per
variable. At 00:00 UTC the temperature mean was 24.860 °C with a 0.172 °C spread; the wind mean
was 9.773 km/h with a 2.510 km/h spread; the largest precipitation spread over the window was
0.786 mm. Artefact: `research/implementation/ensemble-spread-20260915/gfs025-2026-09-15T084*.{json,md}`.

**853 Python tests** are collected; the thirteen added here pass.

## What this does not establish

- No forecast skill, calibration or reliability. A spread is not an error, and a narrow spread
  is not an accurate forecast.
- No probability of an event: a member exceedance is a raw frequency, and members are not
  independent samples.
- No official warning, all-clear, field decision or operational clearance.
- The model run lineage is unspecified, so spread cannot be attributed to a particular run.
- No chat exposure yet, and no daily-aggregation or mean-route path. The stored mean/spread
  route is recorded but unused.

## Registry

The connector names **S68** (*Open-Meteo ensemble member forecast delivery*). Registering it in
`data/registry/sources.json` and rebuilding `data/registry/source-review.json` with
`python3 scripts/audit_sources.py --apply` is left to the repository owner, to keep the generated
ledger and its counts in one hand; the probe evidence above is what that registration should
cite.

## Files

- `weathergpt_data/adapters.py`, `weathergpt_data/foundation.py`, `weathergpt_data/product_api.py`
- `scripts/ensemble.py`, `scripts/probe_ensemble_catalogue.py`
- `tests/test_ensemble.py`
- `research/implementation/ensemble-spread-20260915/ensemble-probe.json`, `gfs025-2026-09-15T084*.{json,md}`
