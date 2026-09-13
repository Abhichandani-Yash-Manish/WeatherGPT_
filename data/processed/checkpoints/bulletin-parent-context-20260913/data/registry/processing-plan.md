# From registered sources to usable WeatherGPT evidence

> Historical processing proposal: implementation status below is superseded by the [foundation guide](../../docs/04-data-foundation.md) and [national ingestion review](../../research/reviews/national-readiness-20260912/review.md). Follow the review gates for new ingestion work.

Status updated 12 September 2026 IST: the S25/S26 local pipeline and deterministic lookup are **implemented and tested**; the remaining pipelines below are proposed. See the [first pipeline guide](../../docs/03-climate-pipeline.md). Begin with saved samples so parsing and interpretation can be checked independently of network access. Keep all audiences in scope; the farmer brief is the first integrated demonstration proposal.

## First processing sequence

| Order | Sources and work | Why now | Done when |
|---|---|---|---|
| 1 — completed | S25–S26: national rainfall/temperature to typed long-format records | Small, source-compared tables provide a reproducible first pipeline | Every published value, year, unit and period round-trips to the CSV; totals and missingness remain explicit; one cited national climate answer reproduces exactly. |
| 2 | S27: source-check and normalise Ahmedabad history | Moves the same contract to our shared location | Candidate publication pages 611–613 are reconciled with the 110-row series; historical geography is stated; a declared baseline uses only covered, valid years. |
| 3 | S20/S24/S10 plus S14/S35: identity and geography | Every local forecast/warning depends on place resolution | India/Gujarat Ahmedabad is explicitly selected; city point, VAAH/WMO station, source district ID and forecast grid remain distinct. Village applicability stays unavailable until boundary/crosswalk validation passes. |
| 4 | S18 and S21/S16: observation and forecast adapters | Establishes numeric answers with provenance | Native units, timestamp, requested/returned location, model/run where available and missing/error states are preserved. IMD rainfall interpretation waits for interval/unit confirmation. |
| 5 | S15/S06/S08: official warning parsing and applicability | Enables the disaster-management part without inventing severity | Official codes and day validity are verified; geometry and location checks pass; expired/update/cancel/missing-feed cases remain distinct. An unavailable source never becomes an all-clear. |
| 6 | S07: Ahmedabad advisory extraction | Connects forecasts and warnings to the farmer use case | A crop row retains district/AMFU, stage, conditions, issue/validity and physical-page citation, including content inherited across pages. |
| 7 | Combine records into a cited Ahmedabad brief | Tests actual utilisation across the data layers | Each sentence is traceable to applicable evidence; missing inputs and old evidence are visible. User can inspect the numeric record or original passage behind it. |

Steps 1–2 create the research path while steps 3–6 establish the local citizen/farmer/warning path. Observation and forecast parsers can be developed independently once their record contracts are fixed. These are task dependencies, not a requirement to finish every national dataset before a local demonstration.

## Record families to keep separate

Use shared provenance fields across families, while preserving the semantics unique to each. A single generic `weather_value` record would hide distinctions that matter.

| Family | Essential fields beyond shared provenance | Example / interpretation |
|---|---|---|
| `observation` | station ID, observed time, parameter, value, unit, native quality and amendment fields | VAAH METAR describes an airport observation; it does not establish conditions throughout a district. |
| `forecast` | provider, upstream model, run time if known, lead time, valid interval, grid/level, parameter, variant, value/unit | Preserve unknown run identity as null with a reason. Do not invent it from retrieval time. |
| `warning` | issuer, original alert/feature ID, raw/decoded hazards, severity, issued/updated/valid times, area, lifecycle references | A district map feature and CAP message are separate records unless an explicit correspondence is established. |
| `advisory` | issuer/AMFU, district, crop, stage, applicability conditions, issue/validity, exact passage and page | Conditions and table headings belong to the extracted advice. Unknown validity must remain unknown. |
| `climate_aggregate` | source series, historical geography/version, parameter, year, period type/code, published value/unit and flags | Monthly, seasonal and annual records overlap; queries select a period class before aggregating. |
| `reanalysis` / `historical_grid` | dataset/version, time interval/calendar, grid, parameter, processing/aggregation method, value/unit | Model analysis and gridded historical estimates remain distinct from direct station observations. |
| `geography` | source namespace/ID, entity type, name/aliases, coordinates or geometry, CRS, version, relationship evidence | A crosswalk is a sourced relationship, not a name-based assumption. |
| `reference` | publication/edition, section/page, topic, time convention and applicability | Ephemeris sections remain optional reference material, outside core weather ingestion. |

All processed records should carry `record_id`, `source_id`, `asset_sha256`, a project-relative raw asset path, original locator (row/page/JSON path), `retrieved_at_utc` when recorded, transformation version, native values/units, normalised values/units where justified, and quality flags. Local import time and source issue/observation time are different fields. If the actual fetch timestamp is absent, record that absence.

Use deterministic identities from source keys, run/valid time and relevant series/parameter/variant; retain revisions. Do not overwrite one forecast run with another or collapse updated warnings. Raw response bytes and request metadata belong in immutable snapshot storage; a relational or columnar processing format can be chosen after the first parsers work.

## Source-specific rules that protect the answer

1. **Published historical aggregates stay published.** National rainfall totals can differ from the sum of months. Keep the source total, a separately named computed sum and the discrepancy flag. Temperatures are not additive. Never combine monthly and seasonal rows in the same rainfall sum.
2. **Missing rainfall is not zero.** S27 has 15,817 missing monthly cells. S16/S17 contain string `NaN`; S23 uses `-999`. Parse each source's own missing convention, retain the original token, and reject malformed payloads. An HTTP 200 error object is not a data sample.
3. **Historical geography stays historical.** Ahmedabad's S27 series spans 1901–2010 without missing months; that does not prove consistent modern district geometry or unchanged observational coverage. A provisional result must name the source series and unresolved geography. Reconcile the original publication before presenting a validated baseline.
4. **Time intervals must be comparable.** S22 sampled local-day aggregates; S23 sampled UTC-day aggregates. Resolve interval boundaries before comparison. For precipitation forecasts, identify whether each value is a rate, interval total or cumulative total before summing or differencing it.
5. **Forecast variants and upstream models stay identifiable.** S17 variants have no established relative accuracy. S21 is served GFS, not an independent alternative to S12. Reanalysis cannot serve as an archived prediction in a forecast-skill test.
6. **Place precision limits answer precision.** A grid cell, airport, historical district and current village have different spatial support. Preserve requested and returned coordinates. Verify geometry/CRS and boundary version before applying alerts to a village.
7. **Warnings retain issuer meaning.** Decode with official source definitions; do not infer hazard/severity from arbitrary colour numbers. Feed absence means unavailable/unknown coverage unless a supported product explicitly establishes otherwise. Keep updates, cancellations and expiry distinct.
8. **Numerical results come from code; prose comes from evidence.** Store structured weather values for deterministic queries. Retrieve advisory/reference passages with citations. Avoid embedding CSV rows as the sole method for calculations. Translation must preserve place, time, severity, conditions and negation.

## First integrated demonstration

Use a user-provided Ahmedabad location, crop/stage and intended activity/time. Assemble a brief with four inspectable sections: an applicable official warning, the forecast for the requested interval, a crop/stage-matched bulletin passage, and an explicit description of missing or incompatible evidence. Historical rainfall can supply separate labelled context; it cannot determine tomorrow's operation.

Initially replay the **September 2026 saved snapshot**, labelled with its actual issue/validity dates. It must not be described as current weather. Only enable a live brief after retrieval, timestamp/validity checks and refresh behaviour work end to end.

For a genuinely current run, archive each response and verify its source time, expected interval coverage, selected location and schema. Set freshness rules per product after its publication schedule is established; there is no universal weather-data expiry duration.

Do not add a crop-water-stress percentage, irrigation deadline, commute-risk probability, hyperlocal rain arrival time or flood-impact score merely because earlier concept notes mention them. Those require separately defined methods, suitable inputs and validation. Where expert/user validation remains unavailable, communicate usefulness as a hypothesis rather than measured impact.

## Acceptance examples for the first slice

| Input or failure | Required behaviour |
|---|---|
| “What was India's annual rainfall in 2024?” | Query S25's published annual value and cite its source row; do not silently replace it with a monthly sum. |
| “Show Ahmedabad's 1991–2020 rainfall baseline” using only S27 | Explain the missing 2011–2020 coverage. Offer a separately labelled covered period, never fill unavailable years. |
| A daily maximum-temperature forecast is supplied for “tomorrow afternoon” | State the temporal limitation or use an actually subdaily product. |
| “Ahmedabad” returns multiple countries | Resolve country/state before fetching local weather. |
| Forecast arrays contain `NaN`, or endpoint returns an error object with HTTP 200 | Preserve missingness or reject the payload; do not fabricate zero weather. |
| CAP feed is empty/unavailable | State the alert-source status; do not conclude there is no warning. |
| A bulletin crop row continues on the next page | Preserve inherited district, crop, stage and conditions with all needed page citations. |
| Forecast and guidance disagree or cover different dates | Display the difference and applicability limits; do not invent a confidence score or silently blend them. |

The S25/S26 normalisation and cited lookup are complete. The next gate is **S27 Ahmedabad source reconciliation**, alongside one forecast adapter. The national pipeline supplies a tested provenance pattern for the next datasets.
