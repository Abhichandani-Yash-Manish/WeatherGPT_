# WeatherGPT: the weather suite overhaul

Recorded 14 September 2026; a historical record of the eleven-surface state. The current surface is [docs/46](46-frontend-instrument-desk.md), which adds the twelfth surface and the Instrument Desk design. Plan: the approved suite-overhaul plan. Assessment that led here: [docs/26](26-ps-gap-analysis-and-official-source-assessment.md). Evidence: [research/reviews/suite-overhaul-20260914](../research/reviews/suite-overhaul-20260914).

## What changed, and why

The workspace was a single conversation surface over a careful evidence engine. A person could not see a national warning picture, look at a station, read a published rainfall record or inspect a map without asking the assistant to narrate it. That is the gap this batch closes: the product is now an eleven-surface suite with a self-hosted map, and the assistant is one surface among them that any other surface can hand context to.

Underlying infrastructure that existed but had no product surface is now reachable in the interface: the national district warning collection (764 source features), the CAP relay state, the GeoNames place index, 2,071 AWS and 145 METAR stations, 39 radar stations, 220 river sub-basins, 17 named coastal zones, 756 vendored district polygons, 635 published district rainfall series with per-year provenance, 36 advisory states, airport reports, marine and river series, the coverage and capability registries, and the ingestion health projection.

## The eleven surfaces

| Surface | What it shows | Sources |
|---|---|---|
| Overview | National district warning tally, radar network summary, and a per-place warning strip | S63, S15 |
| Warnings | Your place resolved to its district, the CAP relay reported separately, and the searchable national table of 756 districts with day 1 to day 5 | S63, S06 |
| Map | Choropleth of the official district warning geometry with land, state, basin, coastal-zone and city layers, pan and zoom, and click-to-inspect | S63 |
| Observations | Nearest official METAR and AWS stations with distance, observation instant, per-row staleness and verbatim reported values | S63 |
| Forecast | Point forecast series for any returned parameter with the answering grid, model string and quality flags | S21, S62 |
| Climate | Published district rainfall 1901 to 2010 as a chart with per-year source page, source row and table label | S27 |
| Advisories | State to district directory, with a hand-off that asks the assistant for that district's passages | S57 |
| Aviation | METAR and TAF by ICAO code with the raw report, age and freshness | S18, S19, S20 |
| Marine | Modeled wave and discharge series naming the answering cell and its distance | S56, S37 |
| Assistant | The existing conversation, now reachable from every surface with that surface's place and intent carried in | all |
| Settings | Capability matrix, sources with integration status and unresolved terms, vendored basemap provenance, collection health | registry, S63 |

## New backend

**Read-model API** in `weathergpt_data/product_api.py`, one payload contract for every surface:

    {schema_version, generated_at_utc, view, status, data, sources[], coverage{}, limitations[], not_established[]}

Routes, all loopback and token guarded: `/api/overview`, `/api/warnings/national`, `/api/warnings/place`, `/api/warnings/cap`, `/api/observations/near`, `/api/observations/network`, `/api/radar`, `/api/basins`, `/api/forecast`, `/api/marine`, `/api/river`, `/api/aviation`, `/api/places/search`, `/api/map/layers`, `/api/map/static/<layer>`, `/api/climate/index`, `/api/climate/series`, `/api/advisories/states`, `/api/advisories/districts`, `/api/settings/capabilities`. An unknown path stays a 404, so the existing contract is preserved.

**New adapters.** `weathergpt_data/observations.py` reads the AWS and METAR station layers; `weathergpt_data/national.py` reads radar network status and river sub-basins. Both go through the governed `Foundation`/`Store` path, so every response is hashed, cached and event-logged like the rest of the evidence.

**Vendored basemap.** `scripts/build_map_basemap.py` builds `data/processed/map-basemap/basemap-v1-<digest>/` once from five official layers: land, 37 states, 756 districts, 220 sub-basins, 17 coastal zones, plus 184 administrative place labels from the local GeoNames extract. Total 2.3 MB against an 8 MB budget. District geometry comes from the warning layer itself, so the map and the warning table share one key space and cannot disagree. State names are attributed geometrically from a second official layer: 755 of 756 districts attributed, 619 by exact name and the rest by overlap. No basemap imagery, no third-party cartography and no external tile origin is used, so the strict Content-Security-Policy is intact.

**Client.** `web/shell.js` (transport, routing, shared components, working place, evidence drawer), `web/panels.js` (the eleven surfaces), `web/map.js` (SVG renderer) and the existing `views.js`/`charts.js`/`app.js`, all registered in the asset allowlist. No build step, no framework, no inline style or script.

## Source problems found and handled

**A placeholder polygon was being drawn as a district.** The source supplies LAKSHADWEEP as a perfect bounding box (area-to-bbox ratio 1.000, 15.9 square degrees) rather than a coastline. It is now detected during the build, flagged `p=1`, drawn as an outlined box instead of a filled district, described in words in the interface, and listed in the build audit. Four other districts needed a fifth decimal place to stay topologically valid after rounding; that is recorded too.

**The AWS layer carries a 1970 placeholder time.** Every AWS row has a `time` field fixed at 1970-01-01, which is not the observation instant. The adapter takes the instant from the `dat` date and the `update_time` string, reports the rejected placeholder verbatim, and never displays it as the observation time. Five METAR rows are years old, so staleness is decided per row and shown per row.

**Size, correctness and duplication.** A naive implementation would re-download a 19 MB geometry layer per point; place resolution now uses the vendored 1.5 MB geometry and answers in 0.04 s. The warning layer is read as attributes only (948 KB) for the national table, and only 8 of 764 source features are unkeyable, each listed with its object id.

## Verification

- **432 Python tests pass**, including 13 new basemap checks, 22 new observation checks, and route tests for auth, unknown paths and parameter validation.
- **47 JavaScript component checks pass** across eight suites, 12 of them new for the suite: every surface has a renderer, each paints an ok payload, caveats from the payload reach the DOM, the map draws one path per district, flags placeholder geometry, never paints an unmapped district as quiet, and every request carries the workspace token.
- **A real browser walk of all eleven surfaces** at 1440x1200 with a recorded journey file, plus mobile captures at 390x844 for the overview, map and warnings surfaces. The map draws 756 district paths with 1 flagged placeholder at both widths.
- **Eight product views returned ok** in the browser with their sources and limitations attached: overview, national warnings, radar, basins, map layers, CAP, settings and climate index.

## What this batch does not establish

- **Watch and notifications are not built.** The Watch control exists and states plainly that no delivery mechanism is connected. Early-warning dissemination with duplicate, update and cancel handling remains the largest open PS requirement.
- **Voice is not built.** It needs a hosted key from the user; credentials belong in local backend configuration and never in browser code.
- **Mobile is still a responsive desktop surface**, not a mobile platform, and no mobile acceptance journey has been run beyond layout captures.
- **Source terms are unresolved.** Every source remains `user_review: pending`; S63 carries the S15 terms. Nothing here is approved for sharing or redistribution.
- **Advisories shows a directory, not retrieval.** Passages still come from the assistant, and whole-document recall across editions remains partial.
- **No forecast skill, calibration, coverage or operational readiness** is claimed from any of this.

## Registry and document changes

Only after the evidence above: a `suite_overhaul_batch` section in `data/registry/hardening-progress.json`, the S5 stage advanced in scope in `data/registry/product-progress.json` with its remaining deliverables still open, and `S63` registered as a source with honest integration status and unresolved terms.
