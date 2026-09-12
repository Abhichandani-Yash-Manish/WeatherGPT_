# Coverage audit and first processing checkpoint

Reviewed **12 September 2026 IST** against the eight supplied SIH26068 features and named use cases. This is a finite requirements audit, not proof that every possible useful dataset has been found.

**Verdict: enough data to start a grounded prototype; not all required data is collected or validated.** The original 38-entry registry combined saved datasets, single-response samples, catalogues, identity evidence, a geography gap and a language service. The distinction remains essential even as the inventory grows.

## Requirement coverage

| SIH feature | Available evidence | Still required for the full capability |
|---|---|---|
| Real-time weather | S18 airport METAR samples; S01 and S39 documented official observation routes | Broader station coverage, supported access, unit/time interpretation, repeated freshness checks. Airport conditions are not district-wide conditions. |
| Natural-language forecasts | S16 gridded forecast arrays, S21 served GFS, S08 daily bulletin | Forecast contracts, precipitation interval definitions, date/location resolution, grounded query engine. Saved samples alone are not a live service. |
| NWP integration | S21 served GFS sample; S12/S29 direct-model leads | Explicit run/lead/grid/level identity and retained predictions. Direct GFS is not yet sampled; no WRF output acquired. The problem says models “such as GFS/WRF”, so both are not mandatory merely because they are named. |
| Extreme alerts and dissemination | S15 warning feature, S06 RSS, S08 bulletin; cyclone products now individually registered | Official product-specific decoding, valid intervals, geography, updates/cancellations, and application-side subscriptions/delivery records. No alert has been sent. |
| Location-based forecast/advice | Place/station metadata and Ahmedabad crop bulletin | Versioned administrative crosswalks; user crop/stage/activity context; applicable guidance and a validated method for any derived recommendation. |
| Indian-language support | S38 service catalogue and original-language guidance candidates | Access to chosen language services, terminology, language variants and evaluation cases. A catalogue does not demonstrate Gujarati accuracy. |
| Historical/climate analysis | National CSVs now processed; district CSVs audited; small reanalysis samples | Original district-publication reconciliation, historical geography, suitable daily records, declared baselines and scientifically appropriate trend methods. |
| Rural voice interaction | Speech-service lead | Representative utterances, local-name disambiguation, transcription checks, voice interface and accessibility testing. No beneficiary recordings collected. |

Named-use-case boundaries: METAR/TAF are only part of an aviation briefing; INCOIS/IMD marine leads need coastal samples; rainfall and river-flow products do not establish flood inundation or exposure. Smart-city applications may need additional local sensor coverage. Numerical forecast uncertainty requires appropriate ensemble/skill evidence, not an invented percentage.

## Corrections and additions

The registry now contains **55 entries**. The 17 additions make omissions explicit rather than claiming new data acquisition:

- **S39–S42:** AWS/ARG observations, their station mapping, district rainfall monitoring and basin precipitation forecasts.
- **S43–S45:** separate cyclone track, wind-polygon and uncertainty-cone products.
- **S46–S48:** radar/lightning index leads and a saved reference for product-specific codes.
- **S49–S51:** explicit gaps for user field/activity context, impact-model inputs and language/voice evaluation data.
- **S52–S55:** specific IMD marine products and the fishermen-warning index lead.

The [current IMD API reference](https://api.imd.gov.in/public/api_reference.html) supplies the documented routes and index leads. Index-only products are labelled accordingly: this inspection did not establish callable radar, lightning or fishermen-warning routes. Other variants in the index remain documented through S48 rather than being treated as mandatory independent integrations.

**One material interpretation correction:** district-warning colours encode red as `1` and green as `4`; the documented nowcast mapping uses green as `1` and red as `4`. The [saved namespaced reference](../reference/imd-code-namespaces.json) keeps these separate. This resolves the documented distinction; it does not certify every public-site payload or alert's validity.

No original datasets were deleted. S28 ephemeris stays optional, and S17 temperature-variant comparison is now optional until one forecast path is working. Upstream and delivery products remain separate for access tracking, but must not be counted as independent forecast models. User-specific field context is collected through the product where needed; it cannot be downloaded from a weather API.

## Fresh access checks

[Request manifest](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json) and [payload inspection](../../research/discovery/evidence/recheck-20260911T185811Z/payload-checks.json) preserve the results of **14 unauthenticated GET requests** made on 11 September UTC / 12 September IST.

| Check | Result | Meaning |
|---|---|---|
| IMD current, city forecast, AWS Gujarat, district rainfall, cyclone track and basin QPF | Six HTTP 401 responses | These unauthenticated requests obtained no weather payload. Other untested managed routes are not assumed accessible or blocked. |
| CAP RSS | HTTP 200, nine entries | Feed parsed; local applicability and full lifecycle remain unvalidated. |
| IMD warning WFS | HTTP 200, one Ahmedabad feature | Geographic feature and warning attributes obtained; validity and boundary version still need work. |
| AWC METAR / station metadata | HTTP 200, six reports / one station | Airport reports and station metadata parsed; latest sampled report time 11 September 18:30 UTC. |
| Open-Meteo GFS delivery | HTTP 200, 72 hourly timestamps | Returned local interval runs 11–13 September, including elapsed hours at retrieval; do not label every returned hour as future. |
| IMD API reference / Mausamgram run pointer | HTTP 200 | Documentation and run metadata accessible; run-pointer success is not a fresh forecast-payload test. |
| IMD daily rainfall catalogue | TLS handshake timeout | This attempt did not retrieve the page. It does not establish permanent unavailability. |

These checks do not measure uptime, quotas, national completeness, permission to redistribute or meteorological accuracy. The remaining registry entries keep their earlier evidence status. No credentials, paid products or new accounts were used.

## Processing actually completed

S25 and S26 now have a versioned, standard-library Python pipeline: verified raw CSV → exact decimal records → CSV/JSONL/SQLite → deterministic lookup with row/column citation. See the [pipeline guide](../../docs/03-climate-pipeline.md).

- **4,216 records:** 2,108 per source, preserving 17 monthly/seasonal/annual measures for each year from 1901 to 2024.
- All 4,216 values round-trip to their original cells. Record identities are unique, and the current tables contain no missing numeric values.
- Rainfall reconciliation checks 620 seasonal/annual totals. **Six** exceed the rounding bound used for one-decimal published values; the source totals are retained and flagged. This is a consistency finding, not a determination of the meteorological cause.
- Eleven tests cover source preservation, missingness, unsupported geography/year/period, invalid numbers, metadata/schema drift, duplicate years, period boundaries, idempotence and file-integrity failures.

The most visible example is 2024 national rainfall: published annual total **1,206.6 mm**, monthly sum **1,204.1 mm**, difference **2.5 mm**. The answer uses the published annual value and discloses the discrepancy. The two national tables had already matched the saved official HTML; this processing pass checks transformation fidelity rather than re-fetching those tables.

The [executed audit notebook](../../research/discovery/processing-checkpoint.ipynb) records the checks. The [first answer](../processed/climate/national-climate-v1-a203fc0eb4a31c58/example-answer.md) demonstrates an actual query result. This is a local historical-data component; no mobile chat, live ingestion service, district baseline or warning-delivery system has been implemented in this step.

| Quality finding | Severity for intended use | Evidence confidence and cause | Remediation |
|---|---|---|---|
| Six published rainfall aggregates exceed the stated rounding bound | Medium for historical lookup; material for derived aggregations | High confidence in exact decimal reconciliation; upstream cause unresolved | Preserve published values, surface flags and resolve methodology before analyses that depend on reconciliation. |
| Different product colour-number mappings | High for warning interpretation | High confidence in the inspected reference; arises from separate product conventions | Use namespaced dictionaries and reject unknown codes; verify each payload's product before decoding. |
| Historical district geometry/source reconciliation incomplete | High for modern district claims | Unresolved compatibility, not an observed claim that boundaries are wrong | Reconcile publication and geographic version; keep provisional results labelled. |
| Only a few live locations/times sampled | High for a nationwide operational claim | Scope limitation directly established by saved requests; reliability and national coverage unmeasured | Expand representative samples and measure freshness before claiming that coverage. |

## Next gate

Proceed with **S27 Ahmedabad source reconciliation** and **one forecast adapter**, using the established provenance pattern. Source-check the rainfall publication before calling a district baseline validated. For a farmer demonstration, close the location, forecast interval, official-warning and crop-context gaps before introducing derived advice. Discovery continues only where one of these concrete requirements lacks suitable evidence.
