# Data foundation handoff — 12 September 2026

Update: the [first hardening batch](06-hardening-batch-one.md) closes the four reproduced numeric validation/cache gaps. Broader ingestion and operational gates remain open.

For expanded numeric collection, use the [governed ingestion worker](09-bounded-ingestion.md). It adds shared local budgets, fixed-date jobs, retry/recovery and database-first reads. The direct adapter commands below remain ad-hoc research tools and do not use the worker's shared budgets. Operational national acceptance is still incomplete.

This checkpoint supplies a working Python library and command-line interface for nationwide discovery and representative national and specialist retrieval. It is ready for prototype integration. It is **not an operational warning service or an exhaustive validation of every Indian location**. The acceptance scope includes national and specialist coverage; the remaining gates below are part of that scope, not deferred out of it.

## Start here

Run from the WeatherGPT project root on macOS or Linux using Python 3.9 or newer (the request cache uses POSIX file locks):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-foundation.txt
.venv/bin/python -m weathergpt_data readiness
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m weathergpt_data forecast --lat 23.02579 --lon 72.58727 --output /tmp/ahmedabad-forecast.json
```

No account or key is needed for the implemented public routes. Provider availability and terms still apply. Do not publish the entire working directory: it contains source material with unresolved or restrictive redistribution terms.

## What to get from where

| Need | Implemented route | Verified scope and limits |
|---|---|---|
| Point weather forecast | S21, Open-Meteo GFS delivery | Six Indian city points; temperature, humidity, hourly rain and wind. Model forecast, not live station observation. |
| Official district warnings | S15, IMD national WFS | 764 supplied features, 742 accepted, 22 quarantined. Day labels retained; current-warning applicability disabled until time semantics are established. |
| Official alert messages | S06, IMD CAP mirror | Nine sampled messages, all expired. Lifecycle references retained; completeness, cancellations and spatial applicability unresolved. |
| Farmer bulletins | S57, IMD/GKMS district selectors and PDFs | 36 source-listed regions, 698 district entries. English PDFs sampled for Ahmedabad, Kamrup and Coimbatore; Gujarati Ahmedabad PDF also retrieved. Entries do not prove a current bulletin. |
| Airport conditions and forecast | S18–S20, Aviation Weather Center | METAR, TAF and station metadata for VAAH, VIDP, VABB, VOMM, VECC, VEGT. Native reports and TAF change groups retained. Not a complete aviation briefing. |
| Marine waves | S56, Open-Meteo marine | Arabian Sea, Bay of Bengal and Andaman Sea sample points; wave height, direction and period. Inspect selected sea grid. |
| Official marine bulletins | S58–S59, RSMC current pages | Sea-area and coastal PDF discovery/extraction. Each document's printed geography and validity require verification. |
| Historical daily climate | S22, ERA5 via Open-Meteo | Ahmedabad seven-day example, arbitrary bounded point/date requests supported. Reanalysis, not station observations. |
| River discharge | S37, GloFAS via Open-Meteo | Seven daily Ahmedabad-area values. River cell has not been reconciled to a named river/gauge; not an inundation or flood-warning model. |
| National historical tables | S25–S26, supplied tables | 4,216 normalized records, 1901–2024; exact decimal and source-row provenance. National aggregates never answer district questions. |
| District historical rainfall | S27, supplied CSVs and original IMD publication | 60,568 rows, 640 historical series. Ahmedabad's 1,870 cells match original pages 611–613; remaining series are not source-reconciled. |
| Place search | S24, geocoding | Indian candidates; caller must resolve ambiguity. No automatic equivalence between place, station, source district and LGD IDs. |

## Commands and SDK

```sh
python3 -m weathergpt_data places Ahmedabad
python3 -m weathergpt_data warnings --output /tmp/national-warnings.json
python3 -m weathergpt_data warnings --lat 23.02579 --lon 72.58727 --output /tmp/ahmedabad-warning-reference.json
python3 -m weathergpt_data cap --output /tmp/cap-reference.json
python3 -m weathergpt_data advisory-catalog --state Gujarat
python3 -m weathergpt_data advisory --state Gujarat --district Ahmedabad --output /tmp/ahmedabad-advisory.json
python3 -m weathergpt_data advisory --state Gujarat --district Ahmedabad --language local --output /tmp/gujarati-advisory.json
python3 -m weathergpt_data aviation --ids VAAH,VIDP,VABB,VOMM,VECC,VEGT --kind metar --output /tmp/metar.json
python3 -m weathergpt_data aviation --ids VAAH,VIDP --kind taf --output /tmp/taf.json
python3 -m weathergpt_data marine --lat 20 --lon 69 --output /tmp/waves.json
python3 -m weathergpt_data marine-bulletin --kind sea
python3 -m weathergpt_data marine-bulletin --kind sea --document-index 0 --output /tmp/sea-bulletin.json
python3 -m weathergpt_data marine-bulletin --kind coastal
python3 -m weathergpt_data river --lat 23.02579 --lon 72.58727 --output /tmp/river-model.json
python3 -m weathergpt_data history --lat 23.02579 --lon 72.58727 --start 2025-07-01 --end 2025-07-07 --output /tmp/history.json
python3 -m weathergpt_data build-climate
python3 -m weathergpt_data build-districts
```

Build commands print the immutable output directory. Pass its SQLite file to the lookup command; do not assume a future rebuild has the same directory name.

```sh
python3 -m weathergpt_data lookup-climate --database data/processed/climate/national-climate-v1-a203fc0eb4a31c58/climate.sqlite --source S25 --year 2024 --period ANNUAL
python3 -m weathergpt_data district-history --database data/processed/districts/district-v1-c8b978172b77182e/districts.sqlite --state Gujarat --district Ahmedabad --year 2010 --period annual
```

```python
from weathergpt_data.foundation import Foundation
from weathergpt_data.advisories import document
f = Foundation()
forecast = f.forecast(23.02579, 72.58727)
bulletin = document(f.store, 'Gujarat', 'Ahmedabad', language='local')
```

CLI errors return JSON on stderr with exit code 2. Library callers should catch `SourceError` (a `ValueError`) and handle unexpected provider/schema failures. Successful extraction can still return `reference_only`, `partial`, `no_data` or another limited status: exit code zero does not establish fitness for a decision.

## Data contract and answering rules

Every live product has `schema_version`, `source_id`, `family`, `status`, `records`, `count`, `provenance`, `coverage` and `limitations`. Provenance contains retrieval/check time, request URL, response SHA-256 and blob location. Records retain their source JSON location or physical PDF page. Historical queries preserve source file, row, column, hash and exact decimal string.

- `ok`: the implemented adapter checks passed; does not establish scientific accuracy, full coverage or operational suitability.
- `reference_only`: preserve and cite the source, but do not present it as a verified current applicable advisory/warning.
- `needs_selection`: resolve a place before proceeding.
- `partial`, `unknown_coverage`, `no_data`, `unavailable`: inspect coverage and limitations; absence is not zero rain or an all-clear.
- `stale`, `outside_validity`, `degraded` or provenance `delivery=stale_cache`: show age and failure explicitly; never relabel the result as fresh.
- `active_by_time_and_status` on an individual CAP info block checks only that block. It does not resolve later cancellation, update chains, location or feed completeness. `actionable_current_alerts` remains false.

Forecast rain is the sum for the **preceding hour**. Forecast wind is km/h; AWC report wind remains knots. ERA5 daily periods are UTC, not IMD's observation-day rainfall convention. Missing values stay null/blank. Model run identity remains unspecified where the provider did not supply it. Returned grid coordinates may differ from requested coordinates.

An LLM should select a deterministic data tool and explain its result. It must not calculate a district climate value from the national series, transform model discharge into a flood declaration, turn a PDF directory into a current advisory, or invent an observed IMD station reading. Translate original warning instructions with source/validity preserved; language and voice quality remain to be evaluated.

## Persistence and refresh

`data/runtime/blobs/` is content-addressed raw evidence; `events/` records network successes/errors; `cache/` is a replaceable request index. Hash checks detect changed cache contents. Network calls have a 25-second timeout and bounded response size. On retrieval or validation failure, an older cached body may be returned with `stale_cache` only if it satisfies the configured current validators; otherwise the request fails explicitly. No hidden synthetic fallback is used.

Prototype TTLs: forecasts/warning snapshots/CAP feed 15 minutes; METAR 5 minutes; TAF/station information/marine/river/bulletin PDFs 1 hour; place search/history/advisory directories 24 hours. These are local request budgets, **not measured publisher SLAs or meteorological validity periods**. PDF text extraction does not guarantee correct reading order; scanned pages require OCR. Forecast, marine, river, historical daily, aviation and WFS adapters now validate their product schema before cache publication. Forecast/marine/river calls also validate the requested UTC calendar-day window, including cache reuse across midnight. Invalid candidates retain raw evidence and a rejection event; a prior cached response is returned only if it passes the current request checks. CAP, geocoding and document/selector routes retain their narrower transport/payload validation and need further hardening. Spatial identity being present does not establish local applicability or source issue freshness.

`python3 scripts/smoke_foundation.py` performs 17 bounded representative checks and records individual errors as data. Read the report, not just the process exit code. It may use cache; each result records network/cache delivery. `--refresh` on individual supported commands forces a new retrieval. Do not rapidly loop calls or treat repeated requests in one session as an uptime study.

## Acceptance gates still open

1. **Official current weather/nowcasts and operational warnings:** canonical IMD API routes sampled earlier returned 401. Obtain supported access and field documentation. Resolve WFS day validity, missing/invalid polygons, district code versions and CAP lifecycle/coverage before alert dissemination. Public WFS access does not mean the authenticated APIs work.
2. **Nationwide location correctness:** validate current administrative boundaries, source-district/LGD/station crosswalks and revised districts; test mountains, islands, coastlines and missing stations. Six city tests and 640 historical districts are not exhaustive present-day coverage.
3. **Specialist completeness:** aviation still needs the relevant SIGMET/AIRMET, upper-air, en-route and other briefing inputs; marine still needs structured official region/validity interpretation and relevant operational products. River queries need CWC/gauge context and exposure data for flood impacts. These gaps do not prevent a clearly labelled data-exploration prototype.
4. **Farmer and multilingual usability:** extract bulletin issuance/validity, crop and stage in context; assess local-language PDF extraction, translations and speech with suitable test cases. Do not prescribe a crop action from rainfall alone. No field-user feedback has been collected.
5. **Reuse rights:** the original IMD district rainfall publication's page 3 restricts copying/storage/transmission/redistribution without permission. Keep the research index local while permissions and intended deployment are resolved. Hosted Open-Meteo free access is for non-commercial use under its terms, separate from attribution requirements. No licence is inferred from an HTTP 200.
6. **Scientific and service validation:** establish forecast versus observation benchmarks, source update/revision behavior, outage recovery, provider quotas and load/latency targets. A source-access test cannot establish forecast skill or production reliability.

See `data/registry/readiness.json` for machine-readable gates and the checkpoint manifest for frozen outputs. These are the exact remaining validation obligations before claiming the full requested operational scope is ready.

## Source documentation

- [IMD district warning map](https://mausam.imd.gov.in/responsive/districtWiseWarningGIS.php)
- [IMD district farmer bulletins](https://mausam.imd.gov.in/responsive/agromet_adv_ser_district_current_en.php)
- [RSMC sea-area bulletins](https://rsmcnewdelhi.imd.gov.in/sea-area-bulletin.php)
- [RSMC coastal bulletins](https://rsmcnewdelhi.imd.gov.in/coastal-weather-bulletin.php)
- [AWC API](https://aviationweather.gov/data/api/)
- [GFS delivery](https://open-meteo.com/en/docs/gfs-api), [marine](https://open-meteo.com/en/docs/marine-weather-api), [flood](https://open-meteo.com/en/docs/flood-api), [hosted-use terms](https://open-meteo.com/en/pricing)

Numerical results now include additive `quality` metadata for schema, interval/value coverage, grid identity and freshness. `source_issue_freshness=unknown` remains explicit when no issuance time is available. Each identical request is serialized by a local POSIX lock; this is not a provider-wide quota manager or distributed job scheduler.
