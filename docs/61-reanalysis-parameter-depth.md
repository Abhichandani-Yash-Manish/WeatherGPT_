# Reanalysis parameter depth: a measured daily catalogue and three models — 15 September 2026

The daily history tool knew one reanalysis model and four variables. This batch grows it to
twenty measured daily variables across ERA5, ERA5-Land and ERA5-seamless, makes the model the
user names part of the collection identity, and refuses a variable a model does not carry
instead of showing it as an empty series. It closes no gap-register item on its own and
promotes no finding; it is the locally resolvable half of PS7, whose station-level half stays
blocked.

## What landed

| Landed | Where | Evidence |
|---|---|---|
| A daily catalogue of twenty variables, each recording its unit, domain and the models that actually return it | `weathergpt_data/adapters.py` | `tests/test_reanalysis_depth.py`, `tests/test_point_tasks.py` |
| Three governed reanalysis models — `era5`, `era5_land`, `era5_seamless` — selectable from the user's own words, never inferred | `weathergpt_data/adapters.py`, `weathergpt_data/point_tasks.py` | `test_model_word_is_read_deterministically`, `test_named_model_reaches_the_collection_identity` |
| The model is part of the request identity, so a different model is a different collection and never a cache hit on another model's payload | `weathergpt_data/ingestion.py` | `test_default_model_is_era5_and_is_recorded`; the stored spec carries `models` |
| A variable a model does not carry is refused by name, with the models that do carry it, instead of being requested and shown empty | `weathergpt_data/point_tasks.py` | `test_era5_land_refuses_a_variable_it_does_not_carry` |
| The daily validator now applies each variable's upper bound, so humidity or cloud outside 0–100 is rejected before publication | `weathergpt_data/foundation.py` | `test_daily_validator_applies_the_upper_bound` |
| Provenance, citation and the answer note name the model that answered, not a fixed ERA5 string | `weathergpt_data/foundation.py`, `weathergpt_data/point_tasks.py` | the citation product reads `ERA5-Land via Open-Meteo` |
| A past day-level date becomes a daily-history task in the rules, so the deterministic path answers it with no model | `weathergpt_data/rule_planner.py` | `test_a_past_day_level_date_becomes_a_daily_history_task`; the live turns below ran with `provider: deterministic_rules` |
| Only the selected model's variables are requested, because a request for a variable a model does not carry returns nulls that make the payload unpublishable | `weathergpt_data/foundation.py`, `weathergpt_data/ingestion.py` | `test_era5_land_publishes_when_the_columns_it_does_not_carry_are_null` |

## The catalogue is measured, not read from a table

The archive API answers a variable a model does not carry with `null` rather than an error, so
a returned field is not proof the model supports it. `scripts/probe_reanalysis_catalogue.py`
asks every candidate of every model over one completed window and records which columns are
absent, entirely null or real. First run
(`research/implementation/reanalysis-depth-20260915/catalogue-probe.json`):

- **ERA5** and **ERA5-seamless**: all twenty candidates returned.
- **ERA5-Land**: ten returned, ten entirely null — precipitation, rain, wind speed and gusts,
  wind direction, cloud cover, surface pressure, shortwave radiation, reference
  evapotranspiration and apparent temperature. Its long record starts in 1950; ERA5 in 1940.

The per-model support set is built from that result, so the refusal clause has a measured
basis and not the provider's documentation.

## The rules path now answers a past day-level date

A question with a real day — “relative humidity in Ahmedabad on 2024-07-01”, “daily mean
temperature from 1 through 3 July 2025” — was planned by the rules as an annual/monthly table
lookup or a forecast, neither of which can answer it, and the new parameters were unreachable
through the default rules-first path for the same reason. A past day-level date is now planned
as a daily-history task directly, with the measure read from the same wording the forecast
uses, so the deterministic engine answers it and no model is required. A month with only a
year (“July 1990”) stays an annual table lookup; a future date, or a range it cannot resolve to
two days, is left to a model rather than shortened. The model prompt also lists the supported
daily parameters and asks that a model the user names be kept in the quoted clause, because the
tool reads the model from the user's own words.

## Measured on this machine, 15 September 2026

- `python3 scripts/probe_reanalysis_catalogue.py` recorded the capability table above.
- `python3 scripts/rehearse_reanalysis_depth.py` ran the real adapter through the governed
  store: ERA5 returned all twenty variables at a 0.25° cell; ERA5-Land returned its ten at a
  0.1° cell, which is the resolution difference the model choice buys. Evidence:
  `research/implementation/reanalysis-depth-20260915/live-rehearsal.json`.
- `python3 scripts/rehearse_reanalysis_conversations.py` ran four turns end to end on the
  local server with no model call (`provider: deterministic_rules`): ERA5 humidity, ERA5-Land
  temperature at the 0.1° cell, the ERA5-Land rainfall refusal, and ERA5-seamless soil
  moisture. Evidence: `research/implementation/reanalysis-depth-20260915/live-conversations.json`.
- **840 Python tests** are collected; the checks added here pass. The eight component suites
  are unchanged.

## What this does not establish

- No forecast skill, reanalysis accuracy or station agreement. A reanalysis value remains a
  modelled history at a provider-selected cell, not an observation or a district average.
- No station-level history. The connected observation series is absent, so that half of PS7
  stays blocked rather than approximated.
- No window beyond the existing one-to-seven whole days; longer archives remain a separate
  change with their own workload ceilings.
- No fluent-language coverage of the new parameters, and no agronomic or hydrological meaning
  is attached to soil moisture, evapotranspiration or radiation.
- The live turns were planned by the rules on this machine; a model-planned daily turn on a
  weaker local model was not reliable, which is why the deterministic rule was added. Model
  plan quality on the daily shape remains unmeasured.

## Files

- `scripts/probe_reanalysis_catalogue.py`, `scripts/rehearse_reanalysis_depth.py`,
  `scripts/rehearse_reanalysis_conversations.py`
- `research/implementation/reanalysis-depth-20260915/catalogue-probe.json`, `live-rehearsal.json`,
  `live-conversations.json`
- `tests/test_reanalysis_depth.py`, and updated `tests/test_point_tasks.py`, `tests/test_providers.py`
