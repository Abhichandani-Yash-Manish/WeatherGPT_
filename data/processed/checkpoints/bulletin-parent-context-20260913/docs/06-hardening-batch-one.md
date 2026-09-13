# First hardening batch — verified 12 September 2026

The first implementation batch is complete. It closes the four reproduced numeric acceptance/cache gaps and replaces the destructive checkpoint finalizer. This is development hardening for SIH26068's accurate, contextual, real-time weather answers; it does not establish complete national or operational readiness.

## Changes and their user-facing effect

| Before | Now | Product effect |
|---|---|---|
| Three-day forecast could accept two hours | Weather and marine requests require the full requested UTC calendar-day axis; daily river requests require their complete date range | Incomplete data cannot silently answer a longer time request |
| Missing grid coordinates accepted | Returned coordinates must be present, finite and within coordinate bounds | Unknown spatial identity is rejected; actual geographic applicability remains to be validated |
| Current river forecast could accept an old one-day payload | Date range checked against the current requested UTC days | Historical/obsolete data cannot masquerade as a current forecast; intentional historical queries still work |
| Valid JSON with an invalid weather schema replaced the cache | Product validation occurs before current cache publication; rejected bytes are saved separately | A bad refresh preserves the previous validated version |
| Cache reuse depended mainly on TTL | Revalidate cached data against current product/time requirements, including during fallback | Cached data crossing midnight or becoming unsuitable during a failed request is refused |
| Single status hid missing values and source-age uncertainty | Additive numeric `quality` fields identify interval coverage, missing values, grid identity, delivery freshness and unknown source issue freshness | Later answer generation can distinguish “recently fetched” from “issued recently” |
| Parallel identical requests could write independently | Per-request POSIX file locks and atomic immutable blob publication | Concurrent identical local requests share the cache without partial blob writes |
| Finalizer rewrote readiness and hardcoded registry v5 | New versioned snapshot command copies current code/registry/readiness and refuses an existing name | S60's hold and newer registry decisions cannot be silently downgraded; old snapshots remain unchanged |

Product-schema publication gates apply to weather/marine forecasts, river discharge, historical daily data, aviation and warning WFS. A WFS parse can still return quarantined features and reference-only status: schema validation does not resolve warning semantics. Other document/CAP/geocoding routes retain their narrower validation and are explicitly unfinished.

The stricter day-window checks follow the requested UTC time basis: forecast_days represents calendar days starting at 00:00, not an arbitrary number of hours after the request. See the [GFS API](https://open-meteo.com/en/docs/gfs-api), [marine API](https://open-meteo.com/en/docs/marine-weather-api) and [flood API](https://open-meteo.com/en/docs/flood-api). Precipitation still preserves the preceding-hour interval, including its boundary at the first timestamp.

## Verification

- Before implementation, the new 12-test file reported seven failures and four errors, reproducing missing behavior in the old implementation.
- After implementation, **49 tests pass**: the original 30 plus 19 hardening cases. Coverage includes wrong units, missing fields, null values, invalid grids, obsolete/incomplete dates, safe fallback, midnight rollover during a request, concurrent identical requests, historical dates and immutable checkpoint creation.
- **15 saved payloads replayed successfully** at their original recorded check times: six forecasts, three marine samples, three aviation products, historical daily data, river discharge and national warning WFS. This is offline compatibility evidence, not current weather verification.
- **Three new live numeric requests passed**: Ahmedabad forecast (288 scalar records), Ahmedabad-area discharge (7 daily records), and an Arabian Sea point (216 scalar records). These are bounded examples, not an uptime/accuracy study.
- The 60-entry registry and 219 evidence assets passed their existing integrity/reference checks. The old foundation payload hashes remain unchanged; the historical audit now reports current implementation drift separately rather than confusing legitimate code changes with damaged frozen data.

Evidence is under `data/processed/hardening/20260912T051521Z/`. The `before/` directory and its hash manifest preserve pre-change code and registry/readiness inputs. Tests, replay results, live responses and post-change metadata provide the before/after trail.

## Snapshot command

```sh
python3 scripts/finalize_foundation_checkpoint.py --name my-new-checkpoint
```

Creates `data/processed/checkpoints/my-new-checkpoint/` with copied code, tests, registry, readiness and a hash manifest. It refuses reuse of an existing name and does not change source registration, readiness or prior foundation pointers. Snapshot creation itself is not a test run or approval of operational use. Omit the name for a unique UTC timestamp.

## Remaining work

- H2 geography and coverage ledger; coordinate presence alone cannot prove the correct station/grid/area association.
- H3 provider-wide quotas, retries/backoff, scheduled jobs, distributed concurrency, retention, database serving and restart/restore validation. Current locking supports macOS/Linux local request stores, not a distributed scheduler.
- H4 warning temporal/spatial applicability and lifecycle; document extraction semantics and CAP/cache publication gates.
- Source publication freshness when issue/run metadata is absent; download time cannot supply it.
- Source-access/rights dependencies, broader PS evidence coverage, numerical benchmarks and multilingual/voice evaluation.

No bulk national collection, scheduled automation, database migration, embeddings or deployment was initiated. The next planned batch establishes geography and a per-product coverage ledger while retaining the national and specialist acceptance scope.
