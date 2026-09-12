# Bounded ingestion: third hardening batch

This batch addresses R06 and contributes measured evidence to R07/R11. It implements an explicitly invoked local worker for the existing **land forecast, marine forecast and modeled river-discharge** adapters. The [original review](../research/reviews/national-readiness-20260912/review.md) and [living checklist](08-hardening-progress.md) remain the acceptance references. National and specialist scope is unchanged; this worker does not establish complete coverage.

## What works

| Behavior | Implementation | Effect on WeatherGPT |
|---|---|---|
| Job identity | Product, coordinates, horizon, contract and explicit UTC collection cycle determine an idempotency key. Repeating the same enqueue returns the same job. | Repeated requests can share planned collection work. A new user question need not cause another provider fetch. |
| Fixed request date | Jobs keep their UTC request day and expire at its next midnight. The relative-date API cannot silently move an old job to a new date. | Prevents serving the wrong forecast window after a delayed retry. |
| Shared provider budget | All three endpoints share persisted rolling budgets and cooldowns in one database. Exact query parameters are checked before reserving a request. | Limits survive worker restarts and account for retries across product endpoints. |
| Bounded concurrency | SQLite transactions allocate jobs; a process file lock holds the provider network slot across response reading. | Competing local workers cannot claim the same job or overlap governed provider requests. |
| Retry handling | 408/429/5xx and transient connection failures reschedule with exponential backoff and jitter. Retry-After supports seconds and HTTP dates. | A provider outage does not create a tight retry loop. No worker sleeps waiting for a retry. |
| Lease recovery | Jobs have expiring ownership tokens. A new claimant invalidates the old token. Attempts are bounded; quota deferrals do not consume failure attempts. | Restart recovery cannot let an abandoned worker publish later. |
| Validated publication | Fresh, matching, complete numeric results and their coverage receipts are committed in one transaction. Attempt caches are isolated. | Malformed or partial refreshes do not replace the prior complete version. Bad raw payloads remain available for inspection. |
| Collection ordering | Current pointers advance only to a later collection cycle. Older successful jobs can be archived without becoming current. | A delayed completion cannot roll the current collection backwards. This is **not** a claim about upstream model-run ordering. |
| Database-first reads | A stream lookup returns the stored result, provenance, age, latest collection-job state and coverage receipt. | Reads need no weather API call; failed/missed refreshes and expired request dates remain visible. |
| Portable recovery | SQLite backup plus hash-checked raw payloads for committed versions can be restored to a new location. | Queue state and published evidence can survive loss of the working directory. |

Every published result remains prototype numeric evidence. Source publication freshness, authoritative geographic mapping and scientific accuracy are not established by successful ingestion. Coverage receipts retain `operational_eligible: false`. These receipts are stored transactionally with job versions; reconciliation into the separate geography/coverage catalogue remains open.

## Provider scope and limits

The reviewed worker accepts one location, one of three fixed product contracts, and 1–7 days per request. Land has four variables, marine three, river one. Larger queries, arbitrary endpoints, redirects and extra parameters are rejected. One attempted HTTP request reserves one local budget unit, including failed attempts.

Local prototype ceilings are **20 attempts per rolling minute, 100 per rolling hour, 200 per rolling day and 1,000 per rolling 31 days**, shared across the supported Open-Meteo endpoints. These are deliberately small project settings, not claimed provider entitlements. Open-Meteo documents a non-commercial free tier, rate limits and query-dependent call accounting; current simple requests fit its described ordinary single-call category. Future variable/model/location expansion requires a new accounting contract. [Official pricing and call accounting](https://open-meteo.com/en/pricing).

For illustration, ten requests at two collection cycles per day would reserve 20 units/day and 620 over 31 days before retries. That fits these local ceilings, but does not establish an appropriate meteorological update cadence or national coverage. Source publication cadence still needs acceptance. Retry-After is handled according to the two HTTP forms, without shortening a valid long publisher wait. [HTTP semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-retry-after).

All participating workers must share the **same local SQLite database and filesystem**. Separate databases, direct adapter CLI calls, other applications and other machines are outside this budget. Existing ad-hoc `forecast`, `marine` and `river` commands remain direct research tools; expanded collection should use this worker. This is a macOS/Linux local implementation, not a distributed service or a national scheduler.

## Commands

Run from the project root. The cycle timestamp below is an example: choose the actual planned UTC collection cycle, and reuse it when repeating the same enqueue. An old date expires without being fetched.

```sh
python3 scripts/ingest.py enqueue --product forecast --lat 23.02579 --lon 72.58727 --days 3 --cycle-at 2026-09-12T06:00:00Z
python3 scripts/ingest.py run --max-jobs 3
python3 scripts/ingest.py status
```

The enqueue response contains `stream`. Use it for a local read:

```sh
python3 scripts/ingest.py latest --stream STREAM_ID_FROM_ENQUEUE
```

Each invocation runs at most the specified number of due jobs, then exits. It does not install an automation or continuously refill the queue. A maximum of 100 jobs per invocation and 1,000 unfinished jobs are enforced. Future collection cycles must be explicitly planned; generating a new timestamp for every question defeats deduplication.

Backup and restore use new destinations:

```sh
python3 scripts/ingest.py backup --output data/backups/UNIQUE_BACKUP_NAME
python3 scripts/ingest.py restore --bundle data/backups/UNIQUE_BACKUP_NAME --output data/restored/UNIQUE_RESTORE_NAME
python3 scripts/ingest.py --database data/restored/UNIQUE_RESTORE_NAME/ingestion.sqlite --raw-root data/restored/UNIQUE_RESTORE_NAME/raw status
```

Backups include queue state, versions, coverage receipts and raw bytes for committed versions. Failed-attempt raw evidence and transport caches are excluded; retain the complete raw tree separately when that forensic history is required. Restoration verifies file hashes and database integrity, and refuses existing destinations. Storage location and access controls remain the operator's responsibility; no external backup destination was configured.

## Verification

**100 tests pass**, including 28 new ingestion tests. They exercise duplicate enqueue, competing database connections, fixed-date expiry, restart recovery, exhausted attempts, stale ownership tokens, out-of-order completion, schema rejection, null coverage, timeouts, 429/503/401 handling, both Retry-After forms, cross-product cooldowns, rolling budgets, process locks, rejected endpoints/query expansion, bounded execution, corrupted reads and backup restoration.

The [offline rehearsal](../data/processed/hardening/ingestion-batch-three-20260912/rehearsal-final/report.json) sent ten saved, hash-verified responses through the real queue and adapters at a fixed historical clock: six land points, three marine points and one river point. Ten duplicate enqueues caused no extra fetches; running the completed queue again made no calls. Restored job state and published results matched the original.

| Measured item | Result |
|---|---:|
| Real provider calls in offline rehearsal | 0 |
| Simulated requests / published versions | 10 / 10 |
| Published scalar records | 2,383 |
| SQLite file | 1,081,344 bytes |
| Raw response payloads | 21,663 bytes |
| Raw tree including cache/event metadata | 33,737 bytes |
| Backup SQLite plus committed raw payloads | 1,103,007 bytes |

These are measurements of this small JSON/SQLite prototype, not per-row production storage estimates. SQLite overhead, duplicated record metadata, retention, repeated cycles, archive compression and shared raw-object storage can change growth substantially. No forecast latency or accuracy claim follows from an offline replay.

The [live check](../data/processed/hardening/ingestion-batch-three-20260912/live/report.json), completed at 05:57 UTC on 12 September 2026, made three governed requests. Land forecast, marine forecast and river discharge all succeeded, publishing **288, 216 and 7 values**, respectively. Total observed batch time was about 5.14 seconds. This is one small access/contract check, not sustained uptime or nationwide performance evidence. The final query guard was additionally checked against all ten saved requests offline.

Reproduce the offline rehearsal in a new directory:

```sh
python3 scripts/rehearse_ingestion.py --output data/processed/hardening/UNIQUE_REHEARSAL_NAME
python3 -m unittest discover -s tests -v
python3 scripts/render_hardening_progress.py --check
```

## Gates still open

- **R01/R02:** authoritative geographic exports/crosswalks, warning feed completeness and update/cancel chains, exact warning validity and region matching.
- **R03/R09:** semantic publication and context extraction for CAP, geocoding and document families. Numeric worker acceptance does not fix those routes.
- **R06/R07:** other providers and source families, distributed ownership, publication-cadence planning, retention/compaction, bulk-grid comparison, a reconciled geographic coverage ledger and sustained expanded-footprint measurements.
- **R08/R10/R11:** supported official observation access, source-run identity, historical permissions/reconciliation, scientific forecast benchmarks and end-to-end answer evaluation.
- **R12:** semantic question-map corrections and dedicated specialist acceptance questions. The tracker remains partial until those are completed.

S60 remains on hold, warnings remain reference-only, and mobile/voice/retrieval interfaces remain later integration work. No recurring ingestion, public service or alert dissemination was enabled.
