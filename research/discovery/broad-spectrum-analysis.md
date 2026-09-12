# WeatherGPT: broad data discovery and product simulation

Evidence checked 11 September 2026. National scope; Ahmedabad district is the shared example. Free-access candidates take priority. Full-access scenarios below are design proposals, not implemented capabilities.

## The finding that changes the picture

We retrieved real JSON data from **two IMD public-site services**: a district-warning WFS service and Mausamgram's gridded forecast service. A third Mausamgram response exposed temperature variants and forecast lead hours. These requests required no account or key during this check.

This does **not** establish access to IMD's managed `/api/v1` platform. Its current-weather and city-forecast routes still returned 401. A read-only city-selection request to the city website returned 403 and was not pursued. Public-site services and supported partner APIs must remain separate entries in our source register: successful access does not establish a stability commitment, redistribution terms or national completeness.

The earlier result was therefore too narrow to settle IMD access as a whole. It correctly identified the managed API restriction, but public IMD products offer additional machine-readable paths. [Managed reference](https://api.imd.gov.in/public/api_reference.html), [public warning map](https://mausam.imd.gov.in/responsive/districtWiseWarningGIS.php), [Mausamgram](https://mausamgram.imd.gov.in/).

## What actually responded

Every successful result below has a saved response, request URL, retrieval time and SHA-256 hash in the linked manifest. Counts describe these bounded samples only.

| Product and request | Result | Evidence and remaining limitation |
|---|---|---|
| IMD district-warning WFS, filtered for Ahmedabad | HTTP 200; one GeoJSON feature, district spelling `AHMADABAD`, `Obj_id=273`, issue date 2026-09-11, five day-code fields and polygon geometry | [Manifest](evidence/imd-live-20260911T160337Z/manifest.json). Mapping is established for this WFS record; managed-API compatibility and administrative boundary version remain unverified. |
| IMD Mausamgram, 3-hour product, cycle `2026091100`, grid 23.000°N, 72.500°E | HTTP 200; 15 arrays, each with 41 entries, including an initial string `NaN` | [Manifest](evidence/imd-grid-20260911T160416Z/manifest.json). Rainfall, temperature, humidity, cloud and wind fields are present. Exact accumulation semantics and full model lineage need confirmation. |
| IMD Mausamgram temperature service for the same grid/date | HTTP 200; lead hours 0–120 every 3 hours, raw and bias-corrected temperature variants | [Manifest](evidence/imd-context-20260911T160450Z/manifest.json). Do not silently interchange variants or treat the accompanying analysis values as station observations. |
| NOAA Aviation Weather Center station lookup | HTTP 200; VAAH, WMO 42647, coordinates 23.077°N, 72.635°E | [Manifest](evidence/broad-20260911T160113Z/manifest.json). This establishes an airport/station relationship, not district-wide representativeness. |
| AWC VAAH METAR, previous three hours | HTTP 200; five observation reports with observation and receipt times, raw reports and decoded fields | Same manifest. Latest observation in the snapshot: 2026-09-11 15:30 UTC. Retain native units and quality fields. |
| AWC VAAH TAF | HTTP 200; one forecast with issue/validity times and three forecast segments | Same manifest. Terminal forecast; not a complete operational aviation briefing. |
| Open-Meteo GFS endpoint, Ahmedabad example point | HTTP 200; 72 hourly timestamps and four weather variables | [Manifest](evidence/numeric-20260911T160221Z/manifest.json). Provider-served GFS output; this response lacks a complete forecast-run identity. |
| Open-Meteo historical endpoint, explicitly selecting ERA5 | HTTP 200; seven daily records for 1–7 July 2025 | Same manifest. Reanalysis, not a station rainfall measurement or a climate-trend result. |
| NASA POWER daily point API | HTTP 200; seven dates for temperature and corrected precipitation; response identifies MERRA2 and missing-value code -999 | Same manifest. Requested UTC days; do not directly compare with the ERA5 sample's local days. |
| Open-Meteo geocoding | HTTP 200; Indian Ahmedabad plus two Pakistani alternatives | [Manifest](evidence/broad-20260911T160113Z/manifest.json). Country/state disambiguation is necessary. These IDs are not LGD or IMD codes. |

The two `/api/v1` 401 responses are saved in the numeric manifest. The city-site 403 is recorded as an HTTP error in the IMD-live manifest; its response body was not preserved. A 200 response containing `{"error":"No data found"}` from the initial unsnapped Mausamgram request is also preserved, demonstrating why HTTP status alone cannot indicate usable data.

## What to obtain from where

This is a proposed division of responsibilities. An organization appearing here does not mean every product or API has been sampled.

| Product need | What to obtain | Primary candidates and access evidence | What fuller access would add |
|---|---|---|---|
| Current conditions | Station observations, coordinates, observation/receipt times, quality flags | IMD Current Weather/AWS via [managed reference](https://api.imd.gov.in/public/api_reference.html), authentication unresolved; [AWC METAR](https://aviationweather.gov/data/api/) sampled now | More representative station coverage and confirmed ingestion cadence |
| Forecast for an activity window | Subdaily temperature, rainfall, wind, humidity; run and valid times | IMD Mausamgram sampled; [Open-Meteo GFS](https://open-meteo.com/en/docs/gfs-api) sampled | Supported IMD forecast delivery and richer model metadata |
| Official warnings | Hazard codes/text, area, issue/validity, updates and cancellations | IMD WFS sampled; district nowcast/managed warnings and CAP feed require lifecycle checks | Supported alert delivery, complete updates, regional-language versions |
| Weather-related crop guidance | Dated crop/stage/condition-specific advisories | IMD/AMFU Gujarat bulletin inspected in checkpoint 1; [ICAR-CRIDA contingency plans](https://www.icar-crida.res.in/Crop_Contingency_Plan.html) catalogued | Current local guidance, structured distribution and expert validation |
| Historical rain and climate | Long time series, missingness, grid/station metadata and baseline definition | [IMD gridded rainfall](https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html): earlier catalogue only, this pass's web fetch timed out; ERA5 and POWER samples retrieved | IMD numerical archives and reliable district aggregation |
| Explicit NWP integration | GRIB2/NetCDF fields, cycle, lead time, level and grid | [NOAA NOMADS](https://nomads.ncep.noaa.gov/) and [ECMWF open data](https://www.ecmwf.int/en/forecasts/datasets/open-data) documented; GFS served through Open-Meteo sampled | Direct upstream subsets and IMD regional output where available |
| Forecast uncertainty and skill | Ensemble members and archived pre-event forecasts matched with observations | ECMWF open products documented; [Open-Meteo single runs](https://open-meteo.com/en/docs/single-runs-api) documented, not sampled | Local calibration and defensible evaluation by lead time/season |
| Radar and satellite context | Named product, scan/acquisition time, projection, quality and processing level | IMD radar catalogue; [MOSDAC download API](https://mosdac.gov.in/downloadapi-manual); [NASA GPM IMERG](https://gpm.nasa.gov/data/imerg), documented only | Authenticated satellite downloads and suitable radar numerical products |
| River flood support | Gauge levels, thresholds, inflow/outflow, basin forecasts | [CWC flood portal](https://ffs.india-water.gov.in/) located; [Open-Meteo flood API](https://open-meteo.com/en/docs/flood-api) documented, not sampled | Basin-specific validation plus reservoirs, terrain and exposure data |
| Marine support | Waves, swell, currents and official sea/port warnings | [INCOIS services](https://incois.gov.in/) and IMD marine products documented only | Marine location samples and supported feeds; Ahmedabad is unsuitable for this test |
| Aviation information | METAR, TAF and appropriate additional aviation products | AWC METAR/TAF sampled; Indian authoritative briefing requirements not assessed | A separate specialist workflow and its required verified sources |
| Place resolution | Names/aliases, official codes, versioned geometry, station/grid links | Open-Meteo geocoding sampled; [LGD catalogue](https://data.gov.in/catalog/local-government-directory-lgd) documented; IMD warning geometry sampled | Validated village/district crosswalks and boundary change history |
| Gujarati and voice | Local place names, weather terminology, test utterances, translation/speech capabilities | [BHASHINI service catalogue](https://dibd-bhashini.gitbook.io/bhashini-apis/available-models-for-usage), not called | Language-specific access and evaluations; a speech service is not a weather source |
| Personal decision context | User's chosen location, crop/stage, activity/time, irrigation and relevant conditions | Collected explicitly in WeatherGPT; simulated profiles must be labelled | Real user feedback and, where available, user-authorized field measurements |

WRF is a modelling system, not a universal data endpoint. A meaningful integration needs a named producer, domain, configuration, cycle and available output. Fuller access would let us evaluate a specific regional WRF product; simply adding WRF to the architecture does not supply one.

MOSDAC documents unauthenticated catalogue searching and account-based downloads. ECMWF describes an open forecast subset, not unrestricted access to every product. Open-Meteo's hosted free tier is intended for non-commercial use and prototyping; commercial hosting terms differ from the underlying data licence. [MOSDAC](https://mosdac.gov.in/downloadapi-manual), [ECMWF](https://www.ecmwf.int/en/forecasts/datasets/open-data), [Open-Meteo pricing](https://open-meteo.com/en/pricing).

## Three product scenarios under fuller access

### 1. Farmer: explain weather implications for a planned activity

Hypothetical question: “I grow cotton in this village and plan a field operation tomorrow afternoon. What should I consider?”

1. Resolve the village and exact time window; collect crop stage and the specific activity.
2. Match the location to official warning coverage and an appropriate forecast grid/station. Display the geographic support honestly.
3. Retrieve the current district/AMFU advisory with crop, stage and conditions intact.
4. Present the applicable warning, time-window forecast and sourced advice as separately attributable evidence.
5. Explain unresolved conditions. A suitability recommendation requires defensible activity-specific criteria, not a threshold invented by the LLM.
6. With user opt-in, store the plan and evidence versions, then re-evaluate when those products change.

This could become an activity card with a time window, evidence, missing context and a “what changed” view. It is a proposed product, not a farm recommendation derived in this research pass.

### 2. Citizen or disaster operator: understand a warning and its changes

Hypothetical question: “Which of our saved locations are covered, and what changed since the previous bulletin?”

Match each location to the warning geometry/codes, interpret the correct dated warning fields, and compare with a preserved earlier version. Display issuing authority, hazard, affected area and source time. A map can show published coverage; it cannot establish flood depth, building exposure or evacuation routing without additional evidence and validated methods.

The WFS sample gives us a real starting record. It does not yet demonstrate cancellation events, a full alert archive or complete national coverage.

### 3. Researcher: reproduce a rainfall analysis

Hypothetical question: “Compare Ahmedabad district's monsoon rainfall with 1991–2020 and export the calculation.”

Select a suitable long record, obtain a versioned district boundary, define the season and baseline, compute spatial weights and missing-data rules, and publish a chart with provenance and exportable inputs. Our seven-day samples prove numeric retrieval, not the availability or completeness of that entire comparison.

For forecast skill, preserve predictions as issued before each event. The Open-Meteo historical-forecast documentation describes a stitched time series; the single-run interface is the appropriate candidate when complete forecast horizons matter. Reanalysis cannot substitute for an archived pre-event forecast. [Historical forecast documentation](https://open-meteo.com/en/docs/historical-forecast-api).

## New engineering lessons from real samples

**Location is a relation between identifiers, not a single string.** The geocoder's city point is 23.02579, 72.58727; AWC's airport is 23.077, 72.635; the tested Mausamgram grid is 23.000, 72.500; the warning record uses Obj_id 273. Preserve all four roles. The WFS includes dubious auxiliary latitude/longitude properties despite plausible polygon bounds, so do not use those auxiliary fields as a centroid. Geometry validity and point containment still need checking.

**The successful grid request follows source behavior.** The public page floors coordinates to 0.125° increments and formats them to three decimals. Reproducing that step changed a no-data response into 15 populated arrays. This is the website's lookup rule, not a generally correct nearest-grid method for other sources. Its 12 × 12 km area disclaimer also limits farm-specific claims.

**Time and missing values are part of the data contract.** Mausamgram's initial `NaN` is a string; convert it to null, retaining its reason. Its chart code anchors samples to the cycle in UTC and uses the chosen interval; the temperature response independently lists lead hours. Preserve the raw cycle and derivation. Confirm rainfall accumulation intervals before sums. NASA POWER's UTC days and the ERA5 request's IST days require alignment before comparison.

**Temperature variants have lineage.** The website fetches an additional temperature service, exposing raw, previous-five-day bias-corrected and realtime bias-corrected series. The initial forecast endpoint alone is not sufficient to reproduce every displayed temperature. Their relative accuracy has not been evaluated.

**A live response has levels of meaning.** Distinguish reachable service, valid payload, applicable place/time, interpretable fields and validated performance. We reached the first several levels for selected products. We did not prove operational reliability or forecast accuracy.

## Proposed product foundation

Keep immutable raw snapshots. Build a place registry and separate records for observations, forecast runs, warnings, advisories and historical series. Each interpreted record should point back to its source version. Run numerical calculations and geographic matching in deterministic code; let the LLM understand questions, request missing context and explain the resulting evidence.

The shared mobile experience can then expose three workflows: local weather/alerts, activity guidance, and historical exploration. A source/time/coverage view and a clear unavailable state belong in each. Background ingestion and opt-in alert delivery need a separate execution path from chat.

Recommended next build: one Ahmedabad evidence viewer showing the sampled IMD warning, IMD forecast grid, airport observation and advisory section, each with its own provenance. Alongside it, create a small historical chart from a clearly labelled reanalysis sample. Keep the source choices replaceable while access and quality checks continue.

Before using these paths as production dependencies, resolve supported access/terms, validity and revision behavior, boundary mapping, rainfall interval definitions and local validation. Repeat checks across representative districts and dates; do not infer national usability from this example. Beneficiary feedback remains unavailable, so usefulness and impact are hypotheses.

## Your independent checks

1. Open Mausamgram at the Ahmedabad example point and compare its cycle, grid selection and displayed temperature variant with the saved responses.
2. Inspect the warning GeoJSON's `District`, `Obj_id`, issue date and day-code fields against the public map and source legend. Record differences rather than assuming every product uses identical timing.
3. Trace one proposed user question through the source matrix. Identify the evidence we have, the context we would ask the user for, and the missing validation that would prevent a stronger answer.

Use the [sample audit](broad-sample-audit.json) for a compact machine-readable summary. Nothing in this report claims that an operational WeatherGPT backend or alert system has already been built.
