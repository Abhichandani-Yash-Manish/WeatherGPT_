# Repair batch four and the first grounded answer workflow

This batch implements the three additional data-folder findings and one complete question-to-answer path: **a selected place point and time interval → stored GFS forecast → deterministic calculation → cited prototype answer**. It also supports temperature, humidity and wind sample ranges through the same path. National and specialist scope remains unchanged; the first named-place demonstration uses Ahmedabad, Gujarat.

Implementation: [answers.py](../weathergpt_data/answers.py), [ingestion.py](../weathergpt_data/ingestion.py), [adapters.py](../weathergpt_data/adapters.py). Source permissions for this serving path are explicit in [answer-policy.json](../data/registry/answer-policy.json); named capabilities and remaining acceptance gates are in [answer-acceptance.json](../data/registry/answer-acceptance.json).

## Repairs completed

| Finding | Change | Regression evidence |
|---|---|---|
| DF01: a future job hides a failed refresh | Reads separate the latest due collection from the next planned collection. Overdue pending work and expired leases are visible without mutating the queue. A failed refresh survives future planning; later success clears it. | `test_repairs_four.py`, including future planning, failure, success, overdue work and lost leases |
| DF02: incomplete backup can restore as an empty database | New manifests are versioned. Restoration requires the database, expected schema, coherent successful jobs/versions/heads and every referenced raw object. Database validation uses a non-creating read-only connection. Structurally valid legacy bundles remain supported. | Empty manifest/database, missing table/head/raw object, valid empty queue and legacy-manifest tests |
| DF03: sample window is insufficient for rain totals | Receipts add actual temporal support per variable. Rain intervals retain their preceding-hour start/end. Answer calculations require complete, unsplit coverage, reject nulls and use decimal arithmetic. | Midnight/horizon boundaries, IST half-hour boundaries, missing values and exact decimal sums |

Earlier frozen outputs are preserved. Old receipt schemas remain readable; the answer service derives variable support from their records and checks new receipts when present. These repairs do not validate unknown publisher model-run identity or geographic representativeness.

## Use it

Use Python with the dependencies in `requirements-foundation.txt`. From the project root, first ask:

```sh
python -m weathergpt_data answer \
  'How much rain is forecast for Ahmedabad tomorrow from 09:30 to 12:30?'
```

The saved catalogue contains Ahmedabad city and district source records, so this returns `needs_selection`. Choose the intended city point, then repeat:

```sh
python -m weathergpt_data answer \
  'How much rain is forecast for Ahmedabad tomorrow from 09:30 to 12:30?' \
  --entity-id 561ffd73856dcd649bc696839ab9068f5b5d3a067b1bdf698e2470c9e761afb2
```

That ID belongs to this frozen source catalogue. For another place or catalogue edition, use the returned candidates rather than reusing the example ID. The query reads the shared default ingestion database; it does not fetch, enqueue, update the catalogue or change job state. If no usable collection exists, it returns an explicit unavailable/stale result.

The implemented English forms are:

- `How much rain is forecast for PLACE tomorrow from 09:30 to 12:30?`
- `What is the weather forecast for PLACE today between 14:30 and 17:30?`
- `What is the temperature forecast for PLACE on 2026-09-13 from 09:30 to 12:30?`
- Substitute `wind speed` or `humidity` for `temperature`.

Use 24-hour times. `today` and `tomorrow` resolve in `--timezone`, which defaults to `Asia/Kolkata`. An end clock earlier than the start means the following local day. Nonexistent/ambiguous daylight-saving times require clarification. This current-forecast path requires an interval starting at or after the answer time; historical data has separate tools.

Explicit coordinates work across the supported model footprint:

```sh
python -m weathergpt_data answer \
  'How much rain is forecast for selected point tomorrow from 09:30 to 12:30?' \
  --lat 23.02579 --lon 72.58727
```

Coordinates must be paired with the phrase `selected point`, so they cannot silently override a different named place. A matching governed collection must exist. No nearest-city substitution or district-average inference occurs.

`--database`, `--raw-root` and `--geography-database` select another stored environment. `--output PATH` saves the complete JSON response. The Python `AnswerService.answer(...)` interface returns the same payload for a future backend/mobile client. This is a constrained deterministic English parser, not a general conversational LLM or a deployed web/mobile service.

## Collect and verify

The explicit live check uses the same default ingestion database, provider budgets and one bounded worker iteration:

```sh
python scripts/check_answer_live.py --output data/processed/hardening/NEW_UNIQUE_LIVE_CHECK
```

It enqueues Ahmedabad using the current UTC hour as the collection cycle. Repeating in the same hour shares the job identity. Each invocation processes at most one due job and exits. It neither installs nor starts recurring ingestion. When other jobs are queued, that one iteration may process earlier due work; inspect the report's target job and worker result.

For general collection use the [bounded ingestion commands](09-bounded-ingestion.md). Reads enforce a **one-hour prototype retrieval-age ceiling**, plus the existing UTC collection-date expiry; this is a local serving policy, not a publisher update SLA or proof of fresh model issuance. The returned grid must be within a **50 km prototype rejection threshold** of the requested point. Passing that guard does not establish village/district representativeness; actual coordinates and distance are disclosed.

## Answer contract and limitations

Every response includes status, original question, resolved request, selected location, values, citations, freshness, coverage, missing information and explicit eligibility. Successful numeric responses also have a stable answer identity for that request, evidence and as-of time.

| Field | Meaning |
|---|---|
| `status` | `prototype_answer`, `partial`, `degraded`, `stale`, `unavailable`, `needs_selection`, `needs_clarification` or `outside_validity` |
| `request` | Parsed intent, variables, timezone and explicit local/UTC interval |
| `location` | Selected entity/version or explicit point, original location evidence, returned grid and distance |
| `values` | Decimal rain total or range of hourly samples, units, method, source locators and missing coverage |
| `citations` | Provider/product, URL, original response hash, raw reference and published job identity |
| `freshness` | Retrieval age, due-collection health and next planned collection; source issue time remains unknown |
| `coverage` | Request-specific assessment joining the selected entity, source version and published job; per-variable temporal support |
| `eligibility` | Prototype numeric evidence can be permitted; operational eligibility remains false |

Serving selects a published version for the exact requested point inside one database read transaction. It verifies the published payload hash and referenced raw evidence, checks source policy, separates retrieval age from model issue freshness, and computes from one version. For multiple horizons in the same collection cycle, it chooses a sufficient horizon using actual variable coverage. It does not silently borrow an older long forecast when a newer short version cannot cover the request.

The new per-answer coverage assessment joins catalogue identity to ingestion evidence at read time. It does **not** promote the historical reference-only geography ledger or claim an authoritative crosswalk. A persistent reconciled operational ledger remains future work.

Rainfall uses the source's preceding-hour accumulation intervals. For example, 09:30–12:30 IST aligns with whole UTC source intervals; 09:00–12:00 IST splits them. The latter returns an unavailable exact total rather than inventing half-hour rainfall. Temperature/wind/humidity ranges describe hourly samples, not continuous extrema. No probability, operational threshold or confidence percentage is invented.

Warnings, crop decisions, aviation, marine, observed current conditions and flood impacts are recognized as requiring separate evidence and return explicit unavailable outcomes in this workflow. Their specialist adapters remain available through existing research tools. General multilingual understanding, speech, document extraction and warning lifecycle work are not claimed complete.

## Verification and observed output

**130 automated tests pass**, including 30 new repair/answer tests. They cover exact totals and citations, wrong/missing/ambiguous locations, district-versus-city selection, multiple horizons, stale/future evidence, source holds, corrupt data, invalid dates, timezone boundaries, nulls, half-hour rain boundaries, refresh failures, malformed backups and explicit specialist gates.

The [saved-response rehearsal](../data/processed/hardening/answers-batch-four-20260912/replay-final/report.json) republishes ten hash-verified saved numeric responses, checks normal backup/restore, and exercises **16 answer scenarios**, including all six existing land sample points. It makes zero live provider calls. Ahmedabad's rain total independently matches a calculation from the original raw response. The demonstration is prominently labelled historical replay; simulated retrieval times are not current weather access.

The [live check](../data/processed/hardening/answers-batch-four-20260912/live/report.json) at **07:38 UTC on 12 September 2026** made **one governed request**. It published 288 scalar forecast values and answered the next-day Ahmedabad rain question with no additional provider call. The observed result was **1.7 mm for 13 September 2026, 09:30–12:30 IST**, at the returned grid approximately 5.0 km from the selected point. This is a timestamped model example, not a continuing weather claim.

- [Live answer](../data/processed/hardening/answers-batch-four-20260912/live/answer.md) and [complete payload](../data/processed/hardening/answers-batch-four-20260912/live/answer.json).
- [Historical replay answer](../data/processed/hardening/answers-batch-four-20260912/replay-final/example-answer.md) and [all replay payloads](../data/processed/hardening/answers-batch-four-20260912/replay-final/answers.json).
- [Test output](../data/processed/hardening/answers-batch-four-20260912/tests.txt).

Reproduce the offline pipeline with a new output directory:

```sh
python scripts/rehearse_answers.py --output data/processed/hardening/NEW_UNIQUE_ANSWER_REPLAY
python -m unittest discover -s tests -v
python data/registry/scripts/manage_registry.py --check
python scripts/render_hardening_progress.py --check
```

The first replay attempt correctly exposed multiple Vadodara source candidates where the initial rehearsal expectation assumed an unavailable place. The final rehearsal now tests that selection behavior separately from an explicitly unlisted locality; no application behavior was weakened to force the rehearsal to pass.

## Next dependent work

1. Extend semantic publication checks to geocoding, CAP and document routes; current answers do not call these routes.
2. Complete warning lifecycle/validity and reviewed crop-bulletin extraction before enabling those answers. Acquire the dated administrative crosswalk needed by area-based claims.
3. Establish an initial seven-day, budgeted collection evaluation with explicit footprint/cadence and metrics. No seven-day study has been run or scheduled by this batch.
4. Connect a mobile/text client, then evaluated multilingual/voice interaction, to this answer contract; expand supported language understanding deliberately.

The source registry's older semantic question-map corrections remain tracked under R12. The new acceptance matrix adds explicit specialist questions without rewriting frozen source-discovery evidence.
