# Stakeholder audit repairs (SA01–SA06)

Repair date: 15 September 2026. Source audit: `research/reviews/stakeholder-audit-20260915/`
(REPORT.md, findings.json, journeys.json). This document records the repairs made against the
six findings the audit asked to address first. It is a repair record, not a promotion of any
readiness or acceptance status. All historical evidence in docs 14, 17–23 and 26–63 remains
unchanged.

## Integration note (15 September 2026)

The record below describes the earlier audit workspace, not the final merged branch.
The latest integrated product status remains [docs/72](72-integrated-status-and-ps-review.md).
During integration with `main`, historical registry batches and the unified warning and
station rendering were preserved. The warning card uses today’s published day row; missing
coverage stays explicit. The API also exposes the derived headline and summary.
The source-fixture helper uses the upstream tracked-only, SHA-256-verified lookup, with
compatibility names for the audit tests. Historical measure order follows the question;
the existing coverage test checks both measures without imposing a different order.
The notification-verb filter and the existing Indic product-word filter both remain active.
The failed audit runs below remain historical evidence.

Final integrated verification: 25 steps, 0 failed, including 1035 Python tests,
eight JavaScript component suites, the status-drift guard and the frontend audit.
See [integration verification](../research/reviews/stakeholder-audit-20260915/integration-verification.txt).
This does not establish live model, language, domain or operational acceptance.

## Verdict

All six findings have a scoped, verified repair. The engine and warning-display defects are
fixed at their cause rather than at the reported phrasing. Reproducibility is fixed for this
working tree: the Python suite runs green from the tracked fixtures and a declared test runner.
Warning delivery, nationwide corpus coverage, language/voice acceptance and mobile remain
outstanding and are not addressed here.

Acceptance run: the project's own `python3 scripts/verify_all.py` — 24 steps, 0 failed,
including 878 Python tests, the seven Node component suites, the status-drift guard and the
frontend workspace audit. The full suite previously recorded 824 passed, 5 failed and 31
errors; the failed and errored cases were missing fixtures and an undeclared test dependency,
not separate logic defects.

## SA01 — Warning-card false quiet headline

**Cause.** `web/home.js` read `data.severity`, which `/api/warnings/place` did not supply, and
treated the absent value as "No warning in this product". The same card showed a yellow
Thunderstorm/lightning/squall Today row for Ahmedabad.

**Repair.**
- `weathergpt_data/product_api.py::warnings_place` now derives the headline from the same day
  rows the strip shows, using the existing `district_warnings.severity` and `summary`. It
  supplies `has_hazard`, `severity` (null when no hazard), `headline` and `summary`, and states
  in the limitations that the severity is derived, not a new IMD field.
- `web/home.js::hero` prefers the backend headline/summary and, for a thinner payload, derives
  from the day rows. An absent summary is now **unknown** ("Warning state not established"),
  never quiet.

**Evidence.** Live Ahmedabad point: `has_hazard=true`, `severity=yellow`, headline
"A yellow warning is published for this district", summary naming Day 1 as today's yellow day.
Regression: `tests/test_stakeholder_repairs.py::WarningHeadlineTests`.

## SA02 — Missing part of a question marked complete

**Cause.** `rule_planner.single_request` chose a single historical parameter
(`'temperature' if 'temperature' else 'rainfall'`), so "India annual rainfall and mean
temperature for 2024" dropped rainfall; the counter then counted the shortened plan.

**Repair.** The history branch collects every named measure, in the order asked, and passes the
list to the task. `historical_tasks.execute_history` already iterated parameters, so no
execution change was needed.

**Evidence.** Both orderings now return two values and a complete count:
`rainfall 1206.6 mm` and `temperature 25.7431 °C` for 2024, in either order. Regression:
`MultiMeasureHistoryTests`.

## SA03 — Water-level question answered as weather

**Cause.** The rules never produced a river task for "observed water level"; the broad
observed/now route produced an observation task, and ordinary station weather was returned as
the answer.

**Repair.** `rule_planner.distinct_quantity` detects a requested river quantity — observed
water level, gauge level, danger level, flood extent or impact — before the observation and
forecast routes and plans a `river` task with that parameter. `execute_specialist` now states an
unsupported quantity *before* demanding a window, and labels it in the reader's terms. The
existing clause checks in `specialist_tasks.DISTINCT` are unchanged and still refuse a planner
rename. Groundwater is excluded and remains a research gap; "warning level" keeps the warning
route, while a river "danger level" routes to the river tool.

**Evidence.** Live: status `unavailable`, empty facts, answer naming the unsupported observed
water level and the no-substitution rule. Regressions: `WaterLevelTests`.

## SA04 — Broken readiness check and missing default model

**Cause.** `preflight.providers()` called `OllamaClient.available()`, which did not exist, so
the reachable Ollama service was reported unreachable.

**Repair.** `OllamaClient` now has `catalogue()` (reads `/api/tags`) and `available()`
returning `(available, reason)` like OpenRouter. `preflight.providers()` separates service
reachability from installed-model availability and reports the missing configured model by name
with the install action. `ModelRouter.describe`/`complete` now get a truthful Ollama
availability too.

**Evidence.** Live preflight: "the service is reachable but the configured model
qwen3.6:latest is not installed (installed: kimi-k2.6:cloud); set WEATHERGPT_MODEL or run
`ollama pull qwen3.6:latest`". Regression: `ProviderReadinessTests`. The missing model still
means live LLM follow-ups fail over to the rules floor; no claim is made that a live LLM was
exercised.

## SA05 — Non-reproducible setup

**Cause.** The default environment had no test runner; the saved bulletin fixtures lived only in
the Git-ignored `data/runtime` cache; four tests reached an undeclared embedding dependency.

**Repair.**
- `requirements-dev.txt` declares `pytest` and the runtime requirements; `scripts/doctor.py`
  reports a missing test runner with the correct install action; `scripts/verify_all.py`
  checks the file is present.
- `tests/source_fixtures.py` resolves saved sources from the tracked curated evidence
  (`research/implementation/*/verified-evidence`, `.../source-pdfs`) before the runtime cache,
  and names a missing fixture rather than skipping silently. The bulletin layout and parent
  context tests use it; a changed current bulletin is never substituted.
- `document_ingest.ingest` accepts an optional `encoder`, and the intake tests inject a
  deterministic encoder, so they no longer require the heavy embedding stack. Real corpus
  building still uses the versioned model.
- README documents the setup and the corpus rebuild (`scripts/ingest_documents.py`).

**Evidence.** `verify_all.py` green with 878 tests, including the previously failing 5 and
erroring 31. `SavedFixtureTests` resolves all six layout/held sources.

## SA06 — Notification word read as a place

**Cause.** "Notify me ..." reached place extraction through the Hinglish locative `me`, so the
watch verb "Notify" was read as a place, the turn asked the reader to choose a Noti village,
and no watch was registered.

**Repair.** `rule_planner.places_of` rejects a watch verb (`notify`, `alert`, `inform`, `tell`,
`warn`, `remind`) as a place name. The place after "for/in" resolves normally, so the warning
lookup completes and the watch registers.

**Evidence.** Live: places `['Ahmedabad']`, status `answered`, and a local watch registered for
Ahmedabad. Regression: `WatchIntentPlaceTests`.

## What this does not change

Warning origin authentication, CAP applicability and any form of delivery remain absent. The
indexed corpus on this machine is still empty and no nationwide edition coverage is claimed.
Live LLM understanding is untested here because the configured model is not installed. Language
output, speech and mobile remain at their previously recorded states. The audit's
`research/reviews/stakeholder-audit-20260915/` evidence is preserved unmodified.
