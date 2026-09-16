# Forecast verification: archived runs measured against reanalysis, never a skill claim — 16 September 2026

[The gap register](31-full-solution-gap-register.md) records **G16**: no scientific forecast
verification has been performed, and the required inputs are archived forecast vintages with run
identity plus matched observations. This batch connects the archived runs and builds the measurement
machinery, records what the measurement shows, and keeps the skill half open rather than approximating
it.

## What landed

| Landed | Where | Evidence |
|---|---|---|
| Two measured endpoints: archived runs at fixed lead-time offsets, and ERA5 hourly reanalysis | `weathergpt_data/adapters.py` | `tests/test_verification.py` |
| A catalogue of the two carried variables and the five lead-time offsets, with units kept per variable | `weathergpt_data/adapters.py` | `test_leads_are_kept_apart_and_units_stay_with_their_variable` |
| A normaliser that turns each archived `_previous_dayN` column into one record per variable, valid hour and lead | `weathergpt_data/adapters.py` | `test_previous_runs_normalises_each_lead_into_its_own_record` |
| Closed-form error statistics over matched pairs, with a declared sample floor | `weathergpt_data/verification.py` | `ErrorStatisticTests`, `test_short_sample_is_unmeasured_not_a_number` |
| A fetch path through the governed store, with the completed-window and five-day-delay refusals | `weathergpt_data/foundation.py` | `FoundationVerificationTests` |
| A product view `/api/verification` | `weathergpt_data/product_api.py` | `ProductViewTests` |
| A command-line artefact | `scripts/verify_forecast.py` | `research/implementation/forecast-verification-20260916/verification-gfs_seamless-2026-09-16T131714Z.{json,md}` |
| A verification surface and a guided tool that opens it | `web/shell.js`, `web/index.html`, `web/panels.js`, `web/home.js` | `tests/test_suite_ui.js` |
| A deterministic chat shape, planned by the rules with no model call | `weathergpt_data/verification_tasks.py`, `weathergpt_data/rule_planner.py`, `weathergpt_data/task_dispatch.py`, `weathergpt_data/language.py`, `weathergpt_data/capabilities.py` | `tests/test_verification.py`; `research/implementation/forecast-verification-20260916/live-chat.json` |

## The two sources are measured, not read from a table

`scripts/probe_verification_sources.py` records, from what the services returned, the hourly
catalogue, the returned grid and the lead-time columns
(`research/implementation/forecast-verification-20260916/verification-source-probe.json`), and pins
four negative controls:

- The archived-runs service answers hourly for the lead-time offsets the catalogue carries
  (**1 to 7 days**; the probe sampled 1, 2, 3, 5 and 7) for `gfs_seamless`, `ecmwf_ifs025` and
  `best_match`; a `start_date`/`end_date` window is honoured.
- A **daily** aggregation is rejected with HTTP 400, which is why this product stays hourly.
- A lead **beyond day 7** is *accepted* and returns nulls, not an error — so the adapter caps its
  leads itself rather than trusting the service to refuse.
- The **ERA5 hourly** reference answers for the same valid hours and carries a **five-day
  publication delay**; a window inside that delay is refused with a named reason.

## The limits are the point

- The reference is **ERA5 reanalysis, a modelled analysis, not a station observation**. Every figure
  is agreement with that analysis over the matched hours, not agreement with a gauge or a
  thermometer.
- The upstream **model cycle is not exposed**: the `_previous_dayN` columns give a lead offset, not
  the exact run identity, and retrieval time is not issue time.
- The statistics describe **one model, one variable and one window**. They are **not forecast
  skill, calibration, accuracy, a confidence or a risk**, and **no model is ranked against another**.
- A lead with **fewer than 24 matched hours** is reported `unmeasured` with its count, not given a
  number, and a series with no variation reports its correlation as undefined rather than zero.

## Measured on this machine, 16 September 2026

- `python3 scripts/probe_verification_sources.py` measured the two endpoints and the four negative
  controls above at Ahmedabad (23.0258, 72.5873), the archived runs returning a 23.0199, 72.5391
  grid and ERA5 the same point.
- `python3 scripts/verify_forecast.py --model gfs_seamless --start 2026-08-28 --end 2026-09-10`
  wrote a fourteen-day artefact for five leads, **336 matched hours per lead**:
  - `temperature_2m` bias **0.918–1.596 °C**, MAE **1.197–1.707 °C**, RMSE **1.454–2.100 °C**,
    correlation **0.810–0.923**;
  - `precipitation` bias **−0.011–0.008 mm**, MAE **0.013–0.031 mm**, RMSE **0.039–0.138 mm**,
    correlation **−0.052–0.042**.
- The precipitation correlation is shown as measured and is **not** read as a result: at this point
  and season the reference series is near-constant, so a correlation over it is uninformative. The
  packet says so in its own limit lines.
- `python3 scripts/rehearse_verification_chat.py` answered four deterministic-rules turns with no
  model call (`research/implementation/forecast-verification-20260916/live-chat.json`): a
  temperature-accuracy question and a precipitation-accuracy question each returned **28 computed
  facts** (seven leads × bias, MAE, RMSE and correlation) over the most recent completed window,
  naming that window and disclosing that no past window was named; a question naming a single
  recent day was **refused** with the five-day reanalysis delay rather than answered for another
  window; and an ordinary "will it rain tomorrow" turn stayed a forecast. The temperature MAE ran
  **1.132–1.707 °C** across the seven leads, 336 matched hours each.

**1160 Python tests** are collected; the checks added here pass.

## What this does not establish

- No **forecast skill, calibration or representativeness**, because the reference is an analysis
  and not an observation, and no station series is connected at scale.
- No **run identity**: the exact upstream model cycle behind each archived value is not exposed.
- No **ranking, single score, probability, confidence or risk** of any kind.
- No **operational clearance** and no distribution of the numbers. The chat shape is a
  deterministic reading of a completed window; it answers with a measurement, never a forecast,
  and it refuses a window it cannot measure instead of substituting another.

## Registry

The archived-runs connector names **S70** (*Open-Meteo previous-runs delivery*); the reference is the
already-registered **S22** (*ERA5 reanalysis*). S70 is registered in `data/registry/sources.json`,
classified in `scripts/audit_sources.py`, and its ledger row is rebuilt by
`python3 scripts/audit_sources.py --only S70 --apply`. Registration is not selection: the entry
stays at `approved_local_prototype`, redistribution is not approved, and no production approval is
granted.

## Files

- `weathergpt_data/adapters.py`, `weathergpt_data/verification.py`, `weathergpt_data/foundation.py`,
  `weathergpt_data/product_api.py`, `weathergpt_data/verification_tasks.py`
- `weathergpt_data/rule_planner.py`, `weathergpt_data/task_dispatch.py`, `weathergpt_data/language.py`,
  `weathergpt_data/tasks.py`, `weathergpt_data/capabilities.py`
- `scripts/verify_forecast.py`, `scripts/probe_verification_sources.py`, `scripts/rehearse_verification_chat.py`
- `web/shell.js`, `web/index.html`, `web/panels.js`, `web/home.js`
- `tests/test_verification.py`, `tests/test_suite_ui.js`, `tests/test_workspace_ui.js`
- `research/implementation/forecast-verification-20260916/verification-source-probe.json`,
  `verification-gfs_seamless-2026-09-16T131714Z.{json,md}`, `live-chat.json`
