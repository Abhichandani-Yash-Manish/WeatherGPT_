# Data-folder and architecture review — 12 September 2026

**Decision: keep the architecture and existing evidence; repair the remaining contracts, then build a small end-to-end answer service.** More undirected data collection is not the next milestone. The foundation can support a clearly labelled prototype, but it cannot yet support all promised current, local, specialist or warning answers.

This assessment uses the captured SIH26068 requirements, the source registry, current implementation, three hardening batches, stored databases and reproducible offline checks. National and specialist scope remains the goal; farmer workflows and Ahmedabad/Gujarat remain the documented initial demonstration. No fresh weather-provider access, scientific forecast benchmark or exhaustive PDF transcription review was performed. Production code and existing data were not changed; this review adds evidence and recommendations only.

## What was independently checked

| Check | Current result | What that establishes |
|---|---|---|
| Full existing test suite | 100/100 pass in isolated Python 3.12 with declared dependencies | Existing regression behavior; additional probes below still expose gaps |
| Registry validation | 60 entries, 219 tracked evidence assets; PASS | IDs, references, hashes, imports and generated views are consistent |
| All stored SQLite files under `data/` | 12/12 integrity checks pass; no declared foreign-key violations | Physical/declared relational integrity, not scientific truth |
| Geography audit | 1,516 entities, 1,496 assessments, no orphaned coverage references | Stored lineage and counts reconcile; assessments remain reference-only |
| Frozen foundation audit | Output evidence passes; implementation drift is identified | Earlier evidence survives the documented later hardening work |
| Saved-response ingestion rehearsal | 10 jobs, 10 duplicate enqueues, 2,383 scalar records, backup/restore PASS | The normal queue and recovery path works with known valid inputs; zero provider calls |
| Extra review probes | Three gaps reproduced | Rainfall coverage semantics, refresh-health reporting, incomplete backup validation |

The default system Python initially ran 95 tests successfully and failed five because `shapely` was absent. After installing `requirements-foundation.txt` into a temporary environment, all 100 passed. This is an environment setup issue, not five application regressions. The exact test environment is recorded in [environment.txt](environment.txt).

## What the data actually contains

The `data/` tree has **702 files and 342,353,556 logical bytes, approximately 326.5 MiB**, excluding `.DS_Store`. Processed data accounts for approximately 284.4 MiB; runtime evidence 29.0 MiB; imported raw material 12.6 MiB. These figures exclude `research/` and do not measure the filesystem's physical allocation or compression.

| Collection | Verified extent | Consequence for the output |
|---|---|---|
| National rainfall and temperature | 4,216 records; 1901–2024; no missing normalized values | Can answer bounded national historical questions; cannot answer local weather or daily dry spells |
| District rainfall | 32 imported files; 60,568 district-year rows; 640 historical series; overall 1901–2010 | Useful historical source series, with varying year coverage and unresolved compatibility with modern boundaries |
| District missingness | 15,817 missing monthly cells; 555 series contain missing months; 329 have internal missing years | Baseline/trend selection must check both absent rows and blank cells, per series and requested interval |
| National rainfall reconciliation | Six published aggregates exceed the pipeline's rounding-bound comparison | Preserve the published values and discrepancy flags; silently replacing totals would damage provenance |
| Official warning snapshot | 764 raw features; 742 accepted; 22 quarantined | Missing or rejected geography cannot become an all-clear |
| CAP snapshot | Nine messages; no time-eligible info blocks in the historical checkpoint | Saved messages demonstrate parsing, not present-day warning coverage |
| Farmer directory | 36 source-listed regions and 698 district entries | A directory entry does not prove a current, applicable crop bulletin |
| Numeric/specialist evidence | Representative land forecasts, airports, sea points, modeled river flow and historical samples | Supports named sample capabilities; does not establish complete national observation or specialist coverage |

The counts 640, 698, 764 and 1,516 describe different inventories. They must never share an administrative-coverage denominator. Historical rainfall has monthly, seasonal and annual measures that overlap; summing all measures would double-count rainfall. Missing-month percentages calculated only over existing rows also conceal missing years.

Ahmedabad's 1,870 historical values have source reconciliation evidence; the other district series do not have equivalent reconciliation. District history ends in 2010, so it cannot supply a complete 1991–2020 baseline. These limitations are already captured in the project and remain relevant.

## Three additional changes needed

### DF01 — Preserve failed-refresh visibility when future work is planned

**Evidence:** [ingestion.py](../../../weathergpt_data/ingestion.py), `IngestionDB.latest`, lines 245–258; [findings.json](findings.json).

The serving read selects the job with the greatest collection timestamp, including future jobs. The probe publishes a valid forecast, fails its next refresh, then schedules a later job. Status changes from `refresh_failed_or_missed` to `prototype_snapshot`, although no replacement data was fetched. The returned latest job becomes `pending`, hiding the failed due refresh from this response.

**Change:** report the latest due collection separately from the next planned collection. Calculate current refresh health from due jobs, including overdue pending/running work and expired leases, without requiring a worker mutation to make those conditions visible. Keep the published version and its age separate from job health.

**Acceptance:** enqueueing future work never clears an existing refresh failure; a successful due refresh does. Test failed → future pending, overdue pending, running with expired lease, and later success.

### DF02 — Validate backup completeness before reporting successful restoration

**Evidence:** [ingestion.py](../../../weathergpt_data/ingestion.py), `restore`, lines 369–390; [findings.json](findings.json).

The probe supplies a manifest containing `{"files": {}}`. Restore copies nothing, opens a missing `ingestion.sqlite` with a writable connection, creates an empty database, passes SQLite integrity, and reports success. This is an incomplete-manifest scenario; the genuine saved backups passed their checks.

**Change:** require a versioned manifest with the expected database member; open the copied database without creating it; validate required schema, foreign keys, heads and published result hashes; verify that every committed version's referenced raw object is present and hash-matched. Reject incomplete restoration before publishing the destination directory.

**Acceptance:** reject missing database entries, empty/unrelated databases, missing required tables, broken version pointers and omitted referenced raw payloads. A valid empty queue is acceptable only with the full expected schema.

### DF03 — Make coverage specific to each variable's actual time support

**Evidence:** [adapters.py](../../../weathergpt_data/adapters.py), `hourly`, and [ingestion.py](../../../weathergpt_data/ingestion.py), lines 184–198; [findings.json](findings.json).

The adapter correctly records precipitation as a preceding-hour accumulation. However, the combined coverage receipt uses one calendar window for every variable. In the probe, that receipt is **12 September 00:00 through 15 September 00:00 UTC**, while rainfall intervals actually cover **11 September 23:00 through 14 September 23:00 UTC**. Sample timestamps are complete; rainfall accumulation over the receipt's full calendar window is not.

This is a coverage-contract gap, not evidence of an already delivered wrong rain total. The existing receipt explicitly calls its timestamps samples, but it is insufficient to authorize a future whole-window rain calculation.

**Change:** distinguish point sample coverage from interval accumulation coverage, per variable. Require exact coverage of the requested accumulation interval before computing totals. Fetch an additional endpoint/window where the provider contract and budgets support it, or return partial coverage. Preserve original interval bounds.

**Acceptance:** test UTC-midnight boundaries, end-of-horizon requests and user-local dates. Because IST boundaries fall between UTC hourly boundaries, an exact local-day total may require finer-resolution input or an explicitly disclosed approximation; do not silently split an hourly total in half.

## Existing work that should be retained

The raw → validated → published separation, source hashes, explicit nulls, frozen builds, separate geography identities and bounded local numeric queue are useful foundations. The previous numeric schema, date-range and cache-promotion fixes are present and pass. They should not be reported again as unfixed original bugs.

Keep numerical calculation deterministic and separate from document retrieval. The LLM should interpret a question and phrase evidence returned by tools. Forecasts, observations, official warnings, historical aggregates and bulletins need different evidence rules even when their final answers share a common presentation format.

The proposed long-term database stack remains an architectural option. Current code uses files and SQLite. A database migration alone will not resolve location applicability, time coverage or document context. First establish one shared publication/serving contract; use measured multi-cycle workload and concurrency needs to decide the migration scope. Bulk embedding of numeric tables adds no value to exact numerical queries.

## Remaining blockers between stored data and intended answers

| Gap still present | Concrete next change |
|---|---|
| Coverage catalogue and ingestion receipts are separate | Add a serving resolver that joins the selected product/version to the selected entity and requested interval, with explicit applicability and publication gates |
| Administrative crosswalk incomplete | Acquire a dated authoritative inventory and review source mappings; handle district changes and ambiguity rather than resolving by name alone |
| Warnings remain reference-only | Remove silent CAP truncation at 20 items; expose feed counts/completeness; reconcile updates/cancellations and exact validity; review geographic applicability |
| CAP, geocoding and documents have narrower cache validation | Validate each product before publication so malformed refreshes cannot displace the last acceptable version |
| Farmer/marine PDFs are extracted pages | Preserve parent document, region, issue/revision/expiry and crop/stage context; evaluate extraction before marking passages eligible or embedding them |
| Official observations/nowcasts remain blocked in saved evidence | Obtain supported payload access and document coverage; model output must continue to be labelled as modeled |
| Source-question map has semantic errors | Map S57 primarily to Q04; add dedicated aviation/marine cases; replace translation-only mappings for S56/S58/S59 with meaningful product questions |
| Historical-use and scientific gates remain open | Retain the recorded source restrictions, reconcile relevant series, and validate appropriate baselines and observation comparisons before dependent claims |
| Mobile, language and voice integration absent | Build these around the same grounded answer payload, with tests for place, numbers, units, time and negation |

No new legal conclusion or live access claim is made here; restrictions and access states above describe the existing project evidence.

## The next implementation milestone

**Deliver a grounded forecast-and-advisory prototype, preceded by a small contract-repair batch.** Keep explicit blocked/partial outcomes for capabilities whose required evidence remains unavailable. Maintain national and specialist acceptance cases while starting implementation with the documented Gujarat example.

1. **Repair DF01–DF03 and extend semantic publication checks.** Add regression tests for the reproduced failures. Preserve the existing 100-test gate and saved-response rehearsal.
2. **Implement an evidence-selection service.** Inputs: intent, explicitly resolved place or coordinates, user timezone, requested interval, language and any relevant crop/activity context. It selects stored evidence and computes numerical results deterministically. Its read path should not bypass provider budgets.
3. **Return one stable answer payload.** Include answer status; source/provider and product; observation/model distinction; requested location and actual spatial support; requested and supported intervals; values and units; issue time when available; retrieval time; freshness and coverage; citations; unresolved inputs and limitations. Use evidence-quality states rather than an invented confidence percentage.
4. **Validate a small set of complete user journeys.** Forecast for a selected location/time; applicable official crop-bulletin explanation; national historical lookup; unavailable-source response; and official-warning response that remains explicitly unverifiable until lifecycle/geography gates pass. Add explicit aviation/marine boundaries to the acceptance set.
5. **Run the existing plan's initial seven-day ingestion rehearsal over a declared, budgeted footprint.** Measure completed/missed cycles, publication age, schema rejects, location coverage, latency, requests and storage growth. This provides operational evidence; forecast accuracy needs compatible observations and a separate evaluation.
6. **Connect mobile text, then evaluated multilingual/voice interaction to that payload.** Expand regions and specialist products through the same contracts as their individual acceptance gates close.

The milestone passes when an answer can be traced from question → selected location/time → eligible stored evidence → deterministic values or cited passage → final wording, and missing, expired, wrong-place or cancelled evidence cannot silently enter the answer. A nationwide scheduler and full document embedding should follow their own readiness gates.

## Folder maintenance

Keep the current raw/processed/runtime/registry separation. Add a versioned active-build index so consumers select published builds explicitly instead of choosing the newest directory name. Distinguish current implementation status from historical discovery status in maintained documentation; several historical next-step sentences are now stale.

The content audit found approximately **69.9 MiB of repeated logical bytes**, including identical 48.4 MiB district databases and repeated warning blobs. Frozen checkpoints, backups and replay evidence explain some duplication. Do not delete them by filename or hash alone. For future builds, use explicit retention classes and shared immutable raw objects where provenance permits; measure growth across repeated cycles before undertaking storage redesign.

## Evidence and reproduction

- [Additional findings and district profile](findings.json); [offline reproduction](reproduce.py).
- [Test results](tests.txt); [exact environment](environment.txt).
- [Registry audit](registry-check.json); [geography audit](geography-check.json); [checkpoint audit](checkpoint-check.json); [tracker check](tracker-check.txt).
- [Saved-response rehearsal](rehearsal.txt); [all-database integrity and duplicate-content audit](storage-check.json).

Run the existing test suite with the declared foundation dependencies. Run `python research/reviews/data-folder-20260912/reproduce.py` from the project environment for the additional probes; they mutate temporary directories only and make no network calls. Historical checkpoint test counts remain historical, rather than being relabelled as current validation.
