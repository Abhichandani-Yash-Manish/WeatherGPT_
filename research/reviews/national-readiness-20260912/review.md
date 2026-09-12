# WeatherGPT: review before state and national ingestion

Review date: 12 September 2026 IST. Scope: inspect the existing registry, runtime adapters, historical pipelines and saved samples; reproduce likely ingestion failures in isolation; review current official access/scale documentation; propose the next implementation gates. No bulk collection, deployment or runtime fixes were performed in this review. Existing weather access results retain their original timestamps.

## Decision

Proceed with designing and hardening the ingestion foundation. Do not yet run continuous state/national collection or bulk embedding. The project is a development prototype with useful source discovery and working sample adapters, not a complete operational data service. The earlier phrase “prototype integration ready” needs this qualification: new isolated checks found correctness gaps that must be closed before scheduled ingestion and user-facing claims.

A guarantee that we have every dataset needed for future, unspecified features would be false. We can establish completeness for a declared capability, location set, variable set, time horizon and quality standard, and expose exceptions. National and specialist coverage remain in scope. Gujarat is a proposed first operational rehearsal, not a reduction of the final scope.

## Evidence reviewed

- Registry version 6 contains 60 entries: 42 classified data products, 11 catalogue leads, four capability gaps, one identity-evidence entry, one enabling service and one reference. These classifications do not imply 42 working data connectors.
- Registry verification passed: 219 referenced evidence assets, input/output hashes, references and generated views.
- All 30 existing tests passed again. Four additional synthetic review demonstrations exposed missing acceptance checks; see `reproduce.py`, `reproductions.json` and `review.ipynb`.
- The earlier 17-check smoke run used six Indian forecast locations, six airports and three sea points plus national warning/CAP and other examples. It is historical evidence of representative retrieval, not a fresh nationwide uptime study.
- Earlier warning snapshot: 764 source features, 742 accepted, 22 quarantined. The advisory directory had 698 entries; the historical collection had 640 district series. These are different source inventories, not interchangeable district denominators.
- Official LGD, provider pricing/API documentation, NCEP product documentation, PostGIS and Parquet documentation were checked during this review. No new claim of working authenticated IMD access is made.

## Highest-priority cracks

| ID / priority | Evidence and implication | Required action before dependent work |
|---|---|---|
| R01 / critical for scaling | No authoritative versioned crosswalk connects user locations, current administrative entities, warning districts, stations and model grids. A city point or district centroid cannot establish conditions everywhere in an area. | Build a geography catalogue with separate entity types, source namespaces, dated mappings and boundary provenance. Fail on unresolved location rather than infer identity from names. |
| R02 / critical for alerting | WFS day validity remains unresolved; 22 features were quarantined. CAP handling caps processing at 20 feed items without a completeness count and does not resolve update/cancel chains. | Establish exact product timing, expected coverage, truncation detection, lifecycle reconciliation and area matching. Keep actionable warning answers disabled until these pass. |
| R03 / high, reproduced | `transport.py:47–51` promotes a response after JSON validation. `Foundation.get` performs only generic JSON validation before product parsing. A valid JSON `{}` replaces the current good cache, then the forecast adapter rejects it. | Separate downloaded, validated and published versions. Promote the current pointer only after full product/coverage checks. Preserve the previous validated version; reject bad versions without losing it. |
| R04 / high, reproduced | A three-day forecast request accepts a two-hour payload as `ok`; missing returned latitude/longitude is also accepted. `adapters.hourly` validates alignment but not the requested window or mandatory spatial identity. | Validate requested versus actual interval coverage, required location metadata and justified grid matching. Expose partial coverage explicitly; no invented interpolation or coordinates. |
| R05 / high, reproduced | A seven-day river request accepts a one-day payload dated 2000 as `ok`. `Foundation.river/daily` lacks forecast-window/current-validity enforcement. | Give every product a temporal contract. Historical queries may return old dates intentionally; current forecast queries must satisfy their requested interval and freshness rules. |
| R06 / high, static inspection | No provider-wide request budgets, Retry-After/backoff handling, job deduplication, concurrency ownership, retry queue or current-version ordering. Atomic JSON replacement alone does not prevent competing workers from publishing an older result last. | Build bounded scheduled jobs, source budgets, per-product locks/idempotency keys and transactional version promotion. Test duplicate jobs, delayed completions, 429/5xx and process restarts. |
| R07 / high, demonstrated by capacity arithmetic | Expanding point-by-point collection can exceed free limits before adding other products. Long-format repeated forecast snapshots grow quickly. | Select source units and variables first; estimate calls, bytes and retention. Evaluate native bulk/grid delivery rather than fetch the same grid separately for every settlement. |
| R08 / high | Core observations/nowcasts remain access-blocked in saved checks. S60 offers station search but weather requests were 403 and its HTML contained unrelated Android external-window code. Several apparent alternatives share the same provider or upstream model. | Establish supported access and real payloads; maintain a source-dependency map. Never substitute a model forecast as an observation or assume alternate URLs provide independent resilience. Keep S60 on hold. |
| R09 / high | A downloaded farmer/marine PDF is not a structured applicable advisory. Crop/stage, issue/validity, table headers and continued rows are not consistently extracted. Gujarati document availability is not language-quality validation. | Create document-family parsers with physical-page provenance, parent context, revision/validity metadata and an extraction-review state. Assess scanned/rotated/local-language documents separately. |
| R10 / high | Historical district data has reuse restrictions and only Ahmedabad's 1,870 values are reconciled against the original. Modern boundaries and homogeneous long-term series are unresolved. | Record permitted uses per source; keep restricted research data out of public exports or external processing pending permission. Reconcile relevant series and baseline coverage before district climate claims. |
| R11 / high | No sustained scientific benchmark or full ingestion-to-answer evaluation exists. Current tests check selected parser/integrity behavior; they did not detect R03–R05. | Add tests for explicit data contracts, missing coverage, stale source publications, revision handling, recovery and answer grounding. Maintain forecasts as issued before outcomes for skill evaluation. |
| R12 / medium, static inspection | `processing-plan.md` still describes implemented tasks as future work. `finalize_foundation_checkpoint.py:54–63` hardcodes registry version 5, replaces readiness and rewrites a checkpoint manifest. Source-question mappings are weak: S57 is assigned Q07 rather than its primary crop-advisory Q04, and marine products mainly reference translation Q14. | Treat the finalizer as a one-time legacy script, not a scheduler. Replace it with append-only version-aware builds. Correct semantic source/question coverage and keep current planning separate from frozen evidence. Do not interpret syntactically valid question IDs as adequate capability coverage. |

The reproduced failures use synthetic inputs and temporary caches. They demonstrate adapter acceptance gaps, not that providers actually returned those payloads. No external alert was sent. The existing runtime deliberately marks warning products reference-only, which prevents these unresolved lifecycle issues from being presented as current actionable warnings today.

## What data is still needed for specific promises?

| Intended answer | Existing contribution | Missing evidence or contract |
|---|---|---|
| Current conditions for a user location | Airport observations and station-identity examples | Supported non-airport observations, coverage/cadence, station representativeness and dated mapping. Current gridded model values must be labelled as modeled. |
| Local forecast | GFS delivery with four variables | Explicit variable/horizon catalogue, valid coverage, grid/elevation context, upstream run identity where available, update/revision policy. Rain probability, gusts and other features are not provided by the current four-variable contract. |
| Village/district warning | WFS and CAP samples | Boundaries, current crosswalk, timing, lifecycle, completeness and hazard-specific products. “No record” must remain distinct from an explicit applicable no-warning state. |
| Farmer bulletin explanation | English/local PDF retrieval | Crop/stage vocabulary, actual conditions and temporal applicability. Independent field recommendations need crop/soil/irrigation/operation context and validated rules beyond the bulletin. |
| Daily dry spells and recent district climatology | National aggregates, historical district totals, sampled ERA5 | Appropriate daily data, baseline years, threshold/missingness rules, geographic comparability and reuse permission. S27 ends in 2010 and cannot supply a 1991–2020 baseline. |
| Forecast changes and forecast accuracy | Latest forecast retrieval and saved snapshots | Archive explicit run/revision identity and as-of availability; collect compatible observations. A new retrieval of unchanged data is not a new model run. |
| Aviation briefing | METAR, TAF, station information | Define briefing boundaries; relevant SIGMET/AIRMET, upper-air/en-route and other required inputs remain incomplete. No operational flight decision claim. |
| Marine briefing | Wave values, sea/coastal PDFs | Region matching, structured validity, wind/gust/current/tide products where required, port/cyclone/fishermen warnings and applicable interpretation. No navigation clearance claim. |
| Flood impacts | Rain forecasts and modeled discharge | Named river/gauge mapping, observed levels/discharge, reservoirs where relevant, basin context, terrain/drainage, exposure and validated impact model. Rainfall alone is insufficient. |
| Multilingual/voice answers | Gujarati source example; service leads | Translation/speech model selection and access, region-specific place names, code-switching, weather terminology and critical negation/time tests. |

For every capability, create a coverage ledger keyed by **product + entity/grid + variable + requested interval + source/version**. Store expected, fetched, validated, missing and quarantined coverage. Keep “not applicable” distinct from “unavailable”: marine coverage is not expected for an inland village. The source registry answers “where might we get it?”; this ledger answers “can we answer this request now?”

## Geography must be a separate foundation

Use current LGD codes as a candidate administrative identity backbone, with downloaded edition/date and change history. LGD provides standard codes and mappings, but a directory download does not by itself supply validated polygons or reconcile IMD product IDs. [Official LGD](https://lgdirectory.gov.in/).

Keep parallel entities: state, district, subdistrict/taluka, village, urban local body/city, ward/locality where actually available, station/airport, forecast grid, river basin/gauge and marine region. These are not one simple parent-child tree. Store names/aliases per language and documented relationships with effective dates. Do not use postal codes as weather boundaries. Historical names and boundaries need their own namespace/version.

A point forecast can serve a village query if its spatial support is disclosed; it does not become a village-scale measurement. An area-average forecast needs a defined aggregation method and spatial coverage. Avoid fetching an identical grid once for every place inside it, but deduplicate only when product/model/grid/elevation or downscaling settings make the outputs equivalent.

## Capacity: why prefetching needs a budget

Illustrative scenarios below are not counts of Indian or Gujarat administrative units. Assumptions: one product, four variables, 72 hourly values, one separate HTTP request per point per refresh, and every snapshot stored in long format.

| Hypothetical workload | Requests/day | Scalar rows/day | Scalar rows/30 days |
|---|---:|---:|---:|
| 300 points, four refreshes/day | 1,200 | 345,600 | 10,368,000 |
| 5,000 points, four refreshes/day | 20,000 | 5,760,000 | 172,800,000 |
| 5,000 points, hourly refresh | 120,000 | 34,560,000 | 1,036,800,000 |

At an illustrative 100 bytes per stored scalar row, the middle case is 17.28 GB over 30 days before indexes, duplicated metadata, raw responses, backups and replicas. This is arithmetic, not a measured disk requirement; compression, wide layouts and deduplication change it substantially. Actual storage must be measured using a representative batch.

Open-Meteo currently documents a free non-commercial limit of 10,000 calls/day, with additional rate limits and no uptime guarantee. Provider-accounted calls can depend on query size; batching is not a promise of free capacity. [Official pricing and call accounting](https://open-meteo.com/en/pricing).

Start free with a bounded footprint and source-aware schedules. Compare point delivery with native regional/grid ingestion once measured volume justifies it. NOAA documents GFS GRIB2 products at several grid resolutions, but our direct-file ingestion and cost have not been validated. Bulk data still needs download, decoding, subsetting, storage and operating capacity; it is not automatically cheaper. [NCEP GFS products](https://www.nco.ncep.noaa.gov/pmb/products/gfs/).

## Proposed fetching, processing and storage design

1. **Source contracts:** supported endpoints, authentication, quotas, formats, variables, issue/valid times, spatial support, expected coverage, permitted uses, source health and fallback semantics. Track owner/next action for blocked dependencies.
2. **Jobs:** request work by product/region/run/window, not by every user question. Separate observations, numerical forecasts, warnings, bulletins and static history schedules. Observe publication cadence; do not treat a cache TTL as the publisher's update interval. Backoff, jitter, budget reserves and deduplication are necessary before concurrency.
3. **Raw evidence:** store original bytes and fetch metadata with immutable identity. Repeated identical bytes may share an object; each retrieval event remains independently recorded. Preserve raw and transformed provenance; do not execute publisher scripts as part of ingestion.
4. **Staging and validation:** parse; check schema, finite values, units, mandatory location identity, requested time span, source freshness, counts, geography, duplicates, revision ordering and permissions. Quarantine failures with reasons. Some plausible extremes need flagging rather than simplistic rejection.
5. **Publication:** atomically expose a validated product/version together with its coverage result. Never silently merge incompatible runs. A newest malformed response must not displace the last valid version. Represent completeness, freshness, validity and applicability as separate fields rather than overloading one `status` string.
6. **Storage:** use PostgreSQL for source/job/version metadata and serving records; evaluate PostGIS for geometries, crosswalks and spatial queries. Keep large raw objects outside row tables. Use a measured columnar/archive strategy for long history; native scientific arrays need suitable multidimensional storage, not millions of duplicated JSON fragments. [PostGIS](https://postgis.net/docs/using_postgis_dbmanagement.html), [Parquet](https://parquet.apache.org/docs/overview/).
7. **Document preparation:** preserve sections, table headings, conditions and parent-document/page links. Build text and semantic indexes only for permitted, reviewed text; retain original-language passages. Changed chunks get a new revision; expiry/cancellation must remove them from current-answer eligibility even if embeddings remain archived. Numerical records remain queryable data.
8. **Serving:** resolve location and interval; consult coverage/validity; select compatible observations, forecasts, warnings or passages. Compute values deterministically. Return citations and explicit gaps. On-demand fetching is a bounded fallback, not a means to evade collection budgets.
9. **Operations:** monitor coverage loss, publisher age versus retrieval age, schema rejects, missed cycles, quota use, queue backlog, indexing lag and storage growth. Test restart/replay and backup restore. Define retention separately for current serving data, raw evidence, historical research and forecast evaluation.

## Implementation order and acceptance gates

| Gate | Deliverable | Acceptance before proceeding |
|---|---|---|
| A: contracts and evidence matrix | Named products/variables, entity types, horizons and restricted capabilities | Every proposed answer has required evidence and an explicit supported/partial/blocked state. Add dedicated aviation/marine acceptance cases to the current question map. |
| B: correctness repairs | R03–R05 fixes, lifecycle/completeness design, source-aware publishing | Synthetic failure cases become regression tests that reject/label bad data; last validated data survives failed refreshes. |
| C: Gujarat geography rehearsal | Dated administrative inventory and verified source mappings | Every entity at each declared supported level is either mapped or explicitly unresolved; sample boundary edges, coastal/inland, rural/urban and duplicate names. Do not claim village-level resolution if only district support exists. |
| D: bounded ingestion and storage | Scheduler/jobs, quotas, raw/staging/published versions and schema | Repeat jobs without duplicate published records; test out-of-order completion, stale publications, 429/5xx, truncated responses, missing stations and restart recovery. Measure one representative collection batch. |
| E: longitudinal reliability | Proposed initial seven-day observation window plus synthetic failure replay | Publish actual coverage, missing cycles, latency and storage measurements. Seven days is an initial check, not proof of seasonal/extreme-event reliability; extend where evidence requires. |
| F: document retrieval preparation | Contextual chunks, metadata filtering, multilingual evaluation set | Wrong district/date/crop/stage, expired revisions and source instructions cannot become eligible current evidence. Validate extraction before embedding the full corpus. |
| G: national expansion | Same contracts, additional regions and specialist footprints | Validate mountains, northeast, islands and different source/language layouts; budget capacity from measured workloads. Gujarat success alone is insufficient. |

This review does not defer specialist coverage away: it separates operational acceptance from merely having a specialist source in the registry. No purchase, account creation, scheduled job or provider communication has been initiated.

## What is ready to do next

The immediate next work is contracts + geography + ingestion correctness, followed by bounded state-wide fetching and storage. Bulk chunking and embedding should follow the document/metadata gate. Keep national source discovery running only to close named dependencies, rather than accumulating more links without a use case.
