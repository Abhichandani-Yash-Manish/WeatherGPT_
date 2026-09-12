# WeatherGPT source cards

Generated from `sources.json`; edit the JSON and regenerate. Original discovery: 11 September 2026. Selected routes rechecked on 12 September IST; see individual access checks. Other access statuses remain historical.

## S01 — IMD Current Weather

**Evidence:** access_blocked · **Processing:** sample_missing · **Priority:** later

**Where:** https://api.imd.gov.in/api/v1/current_wx

**Geography:** Station; Ahmedabad station coverage not sampled

**Time:** Observation timestamps documented as UTC; actual cadence unmeasured

**Fields/units:** Unverified unless specified in documented/observed metadata.

**First task:** Resolve authorised access, then save and inspect a representative payload. Keep public website services as separate sources.

**Unresolved:** Ahmedabad station mapping and coverage Missing-value conventions Actual update latency

**Terms:** Not established for production redistribution

**Questions:** Q01, Q12, Q16

**Evidence files:**

- [manifest.json](../../research/discovery/evidence/20260911T153818096820Z/manifest.json)
- [imd-current.response](../../research/discovery/evidence/20260911T153818096820Z/imd-current.response)
- [api-reference.html](../../research/discovery/evidence/api-reference.html)
- [S01.response](../../research/discovery/evidence/recheck-20260911T185811Z/S01.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S02 — IMD City Forecast

**Evidence:** access_blocked · **Processing:** sample_missing · **Priority:** later

**Where:** https://api.imd.gov.in/api/v1/cityforecast

**Geography:** City/station

**Time:** Documented 7-day daily forecast; no payload

**Fields/units:** Unverified unless specified in documented/observed metadata.

**First task:** Resolve authorised access, then save and inspect a representative payload. Keep public website services as separate sources.

**Unresolved:** Subdaily product needed for afternoon questions Run identity and revision archive Separation of observed and forecast fields

**Terms:** Not established for production redistribution

**Questions:** Q02, Q07, Q17

**Evidence files:**

- [manifest.json](../../research/discovery/evidence/20260911T153818096820Z/manifest.json)
- [imd-city-forecast.response](../../research/discovery/evidence/20260911T153818096820Z/imd-city-forecast.response)
- [api-reference.html](../../research/discovery/evidence/api-reference.html)
- [S02.response](../../research/discovery/evidence/recheck-20260911T185811Z/S02.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S03 — IMD District Nowcast

**Evidence:** access_blocked · **Processing:** sample_missing · **Priority:** later

**Where:** https://api.imd.gov.in/api/v1/districtnowcast

**Geography:** District

**Time:** Nowcast issue and validity fields documented; time conventions not validated

**Fields/units:** Unverified unless specified in documented/observed metadata.

**First task:** Resolve authorised access, then save and inspect a representative payload. Keep public website services as separate sources.

**Unresolved:** District identifier mapping Timezone and rollover semantics Update/cancellation behavior

**Terms:** Not established for production redistribution

**Questions:** Q03, Q08, Q09

**Evidence files:**

- [manifest.json](../../research/discovery/evidence/20260911T153818096820Z/manifest.json)
- [imd-nowcast.response](../../research/discovery/evidence/20260911T153818096820Z/imd-nowcast.response)
- [api-reference.html](../../research/discovery/evidence/api-reference.html)
- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [imd-code-namespaces.json](../../data/reference/imd-code-namespaces.json)

**Review:** pending · **Production:** not_validated

## S04 — IMD District Warning

**Evidence:** access_blocked · **Processing:** sample_missing · **Priority:** later

**Where:** https://api.imd.gov.in/api/v1/districtwarning

**Geography:** District

**Time:** Five day-labelled fields documented; exact day boundaries unresolved

**Fields/units:** Unverified unless specified in documented/observed metadata.

**First task:** Resolve authorised access, then save and inspect a representative payload. Keep public website services as separate sources.

**Unresolved:** Ahmedabad district object ID Exact day-boundary convention Supersession and all-clear semantics

**Terms:** Not established for production redistribution

**Questions:** Q03, Q08, Q09

**Evidence files:**

- [manifest.json](../../research/discovery/evidence/20260911T153818096820Z/manifest.json)
- [imd-warning.response](../../research/discovery/evidence/20260911T153818096820Z/imd-warning.response)
- [api-reference.html](../../research/discovery/evidence/api-reference.html)
- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [imd-code-namespaces.json](../../data/reference/imd-code-namespaces.json)

**Review:** pending · **Production:** not_validated

## S05 — IMD City Forecast Mapping

**Evidence:** access_blocked · **Processing:** sample_missing · **Priority:** later

**Where:** https://api.imd.gov.in/api/v1/cityforecast_mapping

**Geography:** City/station identifiers; schema not sampled

**Time:** See documented/observed metadata; retrieval date is not weather validity.

**Fields/units:** Unverified unless specified in documented/observed metadata.

**First task:** Resolve authorised access, then save and inspect a representative payload. Keep public website services as separate sources.

**Unresolved:** Mapping fields and identifier semantics Whether city IDs align across products City point versus district coverage

**Terms:** Not established for production redistribution

**Questions:** Q01, Q02, Q03

**Evidence files:**

- [manifest.json](../../research/discovery/evidence/20260911T153818096820Z/manifest.json)
- [imd-city-mapping.response](../../research/discovery/evidence/20260911T153818096820Z/imd-city-mapping.response)
- [api-reference.html](../../research/discovery/evidence/api-reference.html)

**Review:** pending · **Production:** not_validated

## S06 — IMD-linked CAP RSS

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** next

**Where:** https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml

**Geography:** National feed; Ahmedabad applicability unestablished

**Time:** See documented/observed metadata; retrieval date is not weather validity.

**Fields/units:** RSS entries; parse linked CAP messages separately if obtainable

**First task:** Preserve identifiers and references; collect active, updated, cancelled and expired examples before enabling alert lifecycle logic.

**Unresolved:** Nine feed items is not evidence of complete national alert coverage. Feed absence cannot mean no warning or cancellation. Feed completeness and cadence Active Ahmedabad coverage Update and cancellation examples Language pairing

**Terms:** Not established for production redistribution

**Questions:** Q03, Q08, Q09

**Evidence files:**

- [manifest.json](../../research/discovery/evidence/20260911T153818096820Z/manifest.json)
- [imd-cap-rss.response](../../research/discovery/evidence/20260911T153818096820Z/imd-cap-rss.response)
- [S06.response](../../research/discovery/evidence/recheck-20260911T185811Z/S06.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)
- [payload-checks.json](../../research/discovery/evidence/recheck-20260911T185811Z/payload-checks.json)
- [cap-messages.json](../../data/processed/foundation/20260911T194849Z/cap-messages.json)
- [acb3456e7acb7f0e21de80da03c6d6ee9b1d7dde0384206cccc89cd297eed391.bin](../../data/runtime/blobs/acb3456e7acb7f0e21de80da03c6d6ee9b1d7dde0384206cccc89cd297eed391.bin)
- [5c04db0de6de0b8f562b7ba37d2cc8ffe46d894858c1f1d2354709c8c862c7c8.bin](../../data/runtime/blobs/5c04db0de6de0b8f562b7ba37d2cc8ffe46d894858c1f1d2354709c8c862c7c8.bin)
- [ff28ff1011b0344488db70a193ff0ab6d86fe16c09c6c2f47dc793b1fc2d4958.bin](../../data/runtime/blobs/ff28ff1011b0344488db70a193ff0ab6d86fe16c09c6c2f47dc793b1fc2d4958.bin)
- [c5066d5c2fb6ee002c17212bd22ce02b43bd31baa9118d08365f5b48dd5396cd.bin](../../data/runtime/blobs/c5066d5c2fb6ee002c17212bd22ce02b43bd31baa9118d08365f5b48dd5396cd.bin)
- [24e302167e261f53854e7e31c8ff66bfa178507f4e8b055ff7067f9e740f24e3.bin](../../data/runtime/blobs/24e302167e261f53854e7e31c8ff66bfa178507f4e8b055ff7067f9e740f24e3.bin)
- [449ad0b821a6c2dcbaf256962ea775c553c1d0284f226efeb64b9d3de51dbb34.bin](../../data/runtime/blobs/449ad0b821a6c2dcbaf256962ea775c553c1d0284f226efeb64b9d3de51dbb34.bin)
- [8b165e577dc7f0f0f77906412e271c62a11910e8020f2b2f1782165b8ed933b9.bin](../../data/runtime/blobs/8b165e577dc7f0f0f77906412e271c62a11910e8020f2b2f1782165b8ed933b9.bin)
- [479f58bf07dd627a1c6cc68c422daaf0c682823aa3c6122627b577b375dc242d.bin](../../data/runtime/blobs/479f58bf07dd627a1c6cc68c422daaf0c682823aa3c6122627b577b375dc242d.bin)
- [2ced79b3396100d4bdf55401fca92193c2a8a99913ad62a01b986c7c2dfb103b.bin](../../data/runtime/blobs/2ced79b3396100d4bdf55401fca92193c2a8a99913ad62a01b986c7c2dfb103b.bin)
- [2ebb682f2306815b36d6a1276b20bee0e2367046f8042ea5b2a71a8ab30226fb.bin](../../data/runtime/blobs/2ebb682f2306815b36d6a1276b20bee0e2367046f8042ea5b2a71a8ab30226fb.bin)
- [18-bulletin-retrieval-and-warning-lifecycle.md](../../docs/18-bulletin-retrieval-and-warning-lifecycle.md)
- [acceptance.json](../../research/implementation/evidence-retrieval-20260913/acceptance.json)

**Review:** pending · **Production:** not_validated

## S07 — Gujarat composite agromet bulletin, issue 70/2026

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://mausam.imd.gov.in/ahmedabad/mcdata/agromet.pdf

**Geography:** Gujarat bulletin; AMFU Arnej/Ahmedabad section starts physical page 62

**Time:** Issue 70/2026 dated 2026-09-09; section validity must be extracted

**Fields/units:** Crop, stage, conditions, guidance and weather tables; preserve original units

**First task:** Extract Ahmedabad pages with inherited headings, crop/stage and page citations; manually reconcile the passage and validity.

**Unresolved:** PDF metadata title says Maharashtra while printed content is Gujarat. Use body and issuer, not title alone. Source link can be overwritten; archive each retrieval hash. Explicit validity of each advisory section Current Gujarati counterpart Archive/revision route Crop-stage and district inheritance during extraction

**Terms:** Not established for production redistribution

**Questions:** Q04, Q05, Q06, Q14

**Evidence files:**

- [bulletin-manifest.json](../../research/discovery/evidence/20260911T153818096820Z/bulletin-manifest.json)
- [gujarat-agromet.pdf](../../research/discovery/evidence/20260911T153818096820Z/gujarat-agromet.pdf)

**Review:** pending · **Production:** not_validated

## S08 — Gujarat district forecast and warnings bulletin

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://mausam.imd.gov.in/ahmedabad/mcdata/district.pdf

**Geography:** Gujarat district rows; Ahmedabad physical page 2

**Time:** Issued 2026-09-11 12:00 IST; dates 11–17 September

**Fields/units:** Daily district forecast and warning table, with date header on physical page 1

**First task:** Join page 1 date header to page 2 Ahmedabad row and reconcile every extracted cell with the rendered PDF.

**Unresolved:** Daily wording does not resolve an hourly forecast question. Machine-readable equivalent Historical revision retention Meaning of probability terms No hourly detail demonstrated

**Terms:** Not established for production redistribution

**Questions:** Q02, Q03, Q08, Q17

**Evidence files:**

- [bulletin-manifest.json](../../research/discovery/evidence/20260911T153818096820Z/bulletin-manifest.json)
- [gujarat-district-forecast.pdf](../../research/discovery/evidence/20260911T153818096820Z/gujarat-district-forecast.pdf)

**Review:** pending · **Production:** not_validated

## S09 — IMD crop-specific advisory web interface

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://imdagrimet.gov.in/cropAdvisory_3.php

**Geography:** District/crop selector; selected Ahmedabad payload not inspected

**Time:** Default page displayed 2026-07-31; not proof that every district product is stale

**Fields/units:** Unverified unless specified in documented/observed metadata.

**First task:** Inspect the selected Ahmedabad/crop result and its issue/validity date.

**Unresolved:** Whether selecting a district gives newer content Exact district product link Usable documented API route

**Terms:** Not established for production redistribution

**Questions:** Q04, Q05, Q14

**Evidence files:**

- [imd-agromet-crop.response](../../research/discovery/evidence/20260911T153818096820Z/imd-agromet-crop.response)
- [manifest.json](../../research/discovery/evidence/20260911T153818096820Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S10 — Ahmedabad city forecast link on IMD regional homepage

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://mausam.imd.gov.in/ahmedabad/

**Geography:** Ahmedabad regional homepage links city ID 42647

**Time:** See documented/observed metadata; retrieval date is not weather validity.

**Fields/units:** Unverified unless specified in documented/observed metadata.

**First task:** Cross-reference S20 without treating this city ID as a district or LGD ID.

**Unresolved:** Confirm cross-product identifier compatibility District/village code crosswalk Coordinates and station representation

**Terms:** Not established for production redistribution

**Questions:** Q01, Q02, Q03

**Evidence files:**

- [imd-ahmedabad.response](../../research/discovery/evidence/20260911T153818096820Z/imd-ahmedabad.response)
- [manifest.json](../../research/discovery/evidence/20260911T153818096820Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S11 — IMD 0.25 degree daily gridded rainfall catalogue

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html

**Geography:** India 0.25-degree grid catalogue; actual grid file not inspected

**Time:** See documented/observed metadata; retrieval date is not weather validity.

**Fields/units:** Daily rainfall; units, calendar, missingness and grid metadata await file inspection

**First task:** Download a small permitted representative NetCDF subset/file and inspect metadata before analysis.

**Unresolved:** Earlier catalogue description/year selector differed; establish coverage from the actual file. Download representative NetCDF Read actual time coverage and missing values Resolve catalogue description/year-selector discrepancy

**Terms:** Not established for production redistribution

**Questions:** Q10, Q11, Q13

**Evidence files:**

- [imd_gridded_rainfall_catalog.html](../../research/evidence/imd_gridded_rainfall_catalog.html)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S12 — NOAA GFS numerical forecast output

**Evidence:** lead · **Processing:** sample_missing · **Priority:** later

**Where:** https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast

**Geography:** Global NWP; exact distribution/grid/level not selected

**Time:** See documented/observed metadata; retrieval date is not weather validity.

**Fields/units:** Unverified unless specified in documented/observed metadata.

**First task:** Select a NOMADS GRIB2 subset with cycle, lead time, parameter, level, grid and accumulation interval.

**Unresolved:** Choose exact distribution/product and small subset Record run, valid time, level and accumulation interval Identify forecast archive access

**Terms:** Not established for production redistribution

**Questions:** Q02, Q07, Q12, Q18

**Evidence files:**

- No local sample.

**Review:** pending · **Production:** not_validated

## S13 — ERA5 hourly single-level reanalysis

**Evidence:** lead · **Processing:** sample_missing · **Priority:** later

**Where:** https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview

**Geography:** ERA5 single-level gridded data; direct file not sampled

**Time:** See documented/observed metadata; retrieval date is not weather validity.

**Fields/units:** Unverified unless specified in documented/observed metadata.

**First task:** Obtain a permitted CDS subset, preserving request, dataset version, calendar and accumulation semantics.

**Unresolved:** Obtain representative subset Document revised/preliminary state Inspect variable-specific units and accumulation semantics

**Terms:** Not established for production redistribution

**Questions:** Q10, Q11, Q13

**Evidence files:**

- No local sample.

**Review:** pending · **Production:** not_validated

## S14 — Ahmedabad district/village boundaries and gazetteer

**Evidence:** lead · **Processing:** source_missing · **Priority:** first

**Where:** Source not selected

**Geography:** Unresolved; do not assume national operational coverage.

**Time:** See documented/observed metadata; retrieval date is not weather validity.

**Fields/units:** Unverified unless specified in documented/observed metadata.

**First task:** Select versioned authoritative geometry and create an explicit crosswalk between village/district, warning polygon, station and grid.

**Unresolved:** Select authoritative compatible boundary/gazetteer sources Record version and identifiers Establish local-script place aliases and ambiguous-name behavior

**Terms:** Not established for production redistribution

**Questions:** Q01, Q03, Q08, Q10, Q15

**Evidence files:**

- No local sample.

**Review:** pending · **Production:** not_validated

## S15 — IMD public warning-map WFS

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://reactjs.imd.gov.in/geoserver/wfs?service=WFS&version=1.1.0&request=GetFeature&typename=imd%3Adistrict_warnings_india&srsname=EPSG%3A4326&outputFormat=application%2Fjson&maxFeatures=1&CQL_FILTER=District+ILIKE+%27%25AHM%25%27

**Geography:** Sample AHMADABAD polygon, Obj_id 273; boundary version unknown

**Time:** 11 September 2026 sample with issue/update and five day-labelled warning fields

**Fields/units:** Coded hazards/colours, district attributes and MultiPolygon geometry

**First task:** Verify official code meanings, valid day intervals and polygon validity; test location containment and revisions.

**Unresolved:** HTTP 200 is not a supported API commitment. Auxiliary coordinate fields are unsuitable as a district centroid. Obj_id 273 is a source ID, not an established LGD crosswalk. Confirm update and revision behavior Confirm suitability for intended location and question Supported interface contract and access policy for public-site service

**Terms:** Production integration and redistribution terms not established in this sample test

**Questions:** Q03, Q08, Q09

**Evidence files:**

- [imd-ahmedabad-warning.response](../../research/discovery/evidence/imd-live-20260911T160337Z/imd-ahmedabad-warning.response)
- [broad-sample-audit.json](../../research/discovery/broad-sample-audit.json)
- [imd-warning-map.response](../../research/discovery/evidence/broad-20260911T160113Z/imd-warning-map.response)
- [manifest.json](../../research/discovery/evidence/imd-live-20260911T160337Z/manifest.json)
- [manifest.json](../../research/discovery/evidence/broad-20260911T160113Z/manifest.json)
- [S15.response](../../research/discovery/evidence/recheck-20260911T185811Z/S15.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)
- [payload-checks.json](../../research/discovery/evidence/recheck-20260911T185811Z/payload-checks.json)
- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [imd-code-namespaces.json](../../data/reference/imd-code-namespaces.json)
- [national-warning-snapshot.json](../../data/processed/foundation/20260911T194849Z/national-warning-snapshot.json)
- [d7501bfb4ae0586e280f15788aceb93ba2b8c42ed57ee4181f4943001b6930a5.bin](../../data/runtime/blobs/d7501bfb4ae0586e280f15788aceb93ba2b8c42ed57ee4181f4943001b6930a5.bin)

**Review:** pending · **Production:** not_validated

## S16 — IMD Mausamgram public forecast data

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://mausamgram.imd.gov.in/test4_mme.php?lat_gfs=23.000&lon_gfs=72.500&date=2026091100_3hr_0p125

**Geography:** Sample grid 23.000 N, 72.500 E; website applies floor-to-0.125-degree transformation

**Time:** Sample cycle 2026-09-11 00 UTC; 41 positions at 3-hour leads 0–120

**Fields/units:** 15 arrays: rh, ghi, apcp, gust, tcdc, temp, wdir, wspd, temp_bc and wind at 80/100/120 m; units need verified field dictionary

**First task:** Parse aligned arrays and string NaN; verify valid-time construction, units, rainfall interval and model lineage against page code/documentation.

**Unresolved:** Unsnapped-coordinate request returned HTTP 200 with no-data error. Model lineage, rainfall accumulation and interface support remain unresolved. Confirm update and revision behavior Confirm suitability for intended location and question Supported interface contract and access policy for public-site service

**Terms:** Production integration and redistribution terms not established in this sample test

**Questions:** Q02, Q05, Q07, Q18

**Evidence files:**

- [imd-mausamgram-grid.response](../../research/discovery/evidence/imd-grid-20260911T160416Z/imd-mausamgram-grid.response)
- [broad-sample-audit.json](../../research/discovery/broad-sample-audit.json)
- [homepage.response](../../research/discovery/evidence/mausamgram-20260911T160131Z/homepage.response)
- [imd-mausamgram-run.response](../../research/discovery/evidence/numeric-20260911T160221Z/imd-mausamgram-run.response)
- [imd-chart-code.response](../../research/discovery/evidence/imd-context-20260911T160450Z/imd-chart-code.response)
- [imd-mausamgram-3hr.response](../../research/discovery/evidence/imd-live-20260911T160337Z/imd-mausamgram-3hr.response)
- [manifest.json](../../research/discovery/evidence/imd-grid-20260911T160416Z/manifest.json)
- [manifest.json](../../research/discovery/evidence/mausamgram-20260911T160131Z/manifest.json)
- [manifest.json](../../research/discovery/evidence/numeric-20260911T160221Z/manifest.json)
- [manifest.json](../../research/discovery/evidence/imd-context-20260911T160450Z/manifest.json)
- [manifest.json](../../research/discovery/evidence/imd-live-20260911T160337Z/manifest.json)
- [imd-run.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-run.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S17 — IMD Mausamgram public temperature variants

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** optional

**Where:** https://mausamgram.imd.gov.in/rtbc_proxy.php?lat=23.000&lon=72.500&date=20260911&fcst_ic_utc=00

**Geography:** Sample grid 23.000 N, 72.500 E

**Time:** Cycle 2026-09-11 00 UTC; lead 0–120 hours every 3 hours

**Fields/units:** temp_bc_realtime, fcsttemp, fcsttemp_bc_p5days plus rtma fields; variants stay distinct

**First task:** Preserve forecast variant names, time axes and missingness; distinguish RTMA analysis from station observation.

**Unresolved:** No evidence that one temperature variant is more accurate. RTMA-like analysis values are not station observations. Confirm update and revision behavior Confirm suitability for intended location and question Supported interface contract and access policy for public-site service

**Terms:** Production integration and redistribution terms not established in this sample test

**Questions:** Q02, Q07, Q17

**Evidence files:**

- [imd-temperature-bc.response](../../research/discovery/evidence/imd-context-20260911T160450Z/imd-temperature-bc.response)
- [broad-sample-audit.json](../../research/discovery/broad-sample-audit.json)
- [imd-chart-code.response](../../research/discovery/evidence/imd-context-20260911T160450Z/imd-chart-code.response)
- [manifest.json](../../research/discovery/evidence/imd-context-20260911T160450Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S18 — NOAA AWC VAAH METAR dissemination

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://aviationweather.gov/api/data/metar?ids=VAAH&format=json&hours=3

**Geography:** VAAH airport station, not the entire Ahmedabad district

**Time:** Five reports obtained in a requested three-hour window on 11 September

**Fields/units:** METAR raw and decoded fields; inspect each native unit before conversion

**First task:** Normalise observation time and native units; retain raw report, amendments and missing values.

**Unresolved:** AWC disseminates the report; provider and original issuing station must be distinct. Confirm update and revision behavior Confirm suitability for intended location and question

**Terms:** Production integration and redistribution terms not established in this sample test

**Questions:** Q01, Q12, Q21

**Evidence files:**

- [awc-metar.response](../../research/discovery/evidence/broad-20260911T160113Z/awc-metar.response)
- [broad-sample-audit.json](../../research/discovery/broad-sample-audit.json)
- [manifest.json](../../research/discovery/evidence/broad-20260911T160113Z/manifest.json)
- [S18.response](../../research/discovery/evidence/recheck-20260911T185811Z/S18.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)
- [payload-checks.json](../../research/discovery/evidence/recheck-20260911T185811Z/payload-checks.json)
- [aviation-metar.json](../../data/processed/foundation/20260911T194849Z/aviation-metar.json)
- [c22bc6b3d7afb2866bd7793684f7a5086ec4677b10c9285a263e64b687bc7a73.bin](../../data/runtime/blobs/c22bc6b3d7afb2866bd7793684f7a5086ec4677b10c9285a263e64b687bc7a73.bin)
- [3706c5d848587746c55ea186ee66adfe53fdccf0f91acb06b86f36a00cdfd774.bin](../../research/implementation/conversation-engine-20260912/verified-evidence/3706c5d848587746c55ea186ee66adfe53fdccf0f91acb06b86f36a00cdfd774.bin)

**Review:** pending · **Production:** not_validated

## S19 — NOAA AWC VAAH TAF dissemination

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** next

**Where:** https://aviationweather.gov/api/data/taf?ids=VAAH&format=json

**Geography:** VAAH terminal forecast

**Time:** One TAF with three forecast segments sampled

**Fields/units:** TAF raw/decoded forecast segments and change groups

**First task:** Preserve issue time, validity, segment intervals and change-group semantics.

**Unresolved:** Not a complete aviation briefing or district-wide forecast. Confirm update and revision behavior Confirm suitability for intended location and question

**Terms:** Production integration and redistribution terms not established in this sample test

**Questions:** Q02, Q07, Q21

**Evidence files:**

- [awc-taf.response](../../research/discovery/evidence/broad-20260911T160113Z/awc-taf.response)
- [broad-sample-audit.json](../../research/discovery/broad-sample-audit.json)
- [manifest.json](../../research/discovery/evidence/broad-20260911T160113Z/manifest.json)
- [aviation-taf.json](../../data/processed/foundation/20260911T194849Z/aviation-taf.json)
- [84e7ee7f633c529f9a22857cc4e54a0772330f64c769f8aa3c690cec9b54c26e.bin](../../data/runtime/blobs/84e7ee7f633c529f9a22857cc4e54a0772330f64c769f8aa3c690cec9b54c26e.bin)
- [47d3adee96e8c8e608e54a05d5e377042a355ab2854cef17333db07322c1d5f7.bin](../../research/implementation/conversation-engine-20260912/verified-evidence/47d3adee96e8c8e608e54a05d5e377042a355ab2854cef17333db07322c1d5f7.bin)

**Review:** pending · **Production:** not_validated

## S20 — NOAA AWC airport station metadata

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://aviationweather.gov/api/data/stationinfo?ids=VAAH&format=json

**Geography:** VAAH / WMO 42647, latitude 23.077, longitude 72.635; station elevation 52 m in sample

**Time:** See documented/observed metadata; retrieval date is not weather validity.

**Fields/units:** Station IDs, name, coordinates, elevation

**First task:** Create the station identity record with source-specific IDs; retain city and district as separate entities.

**Unresolved:** Confirm update and revision behavior Confirm suitability for intended location and question

**Terms:** Production integration and redistribution terms not established in this sample test

**Questions:** Q01, Q15, Q21

**Evidence files:**

- [awc-station.response](../../research/discovery/evidence/broad-20260911T160113Z/awc-station.response)
- [broad-sample-audit.json](../../research/discovery/broad-sample-audit.json)
- [manifest.json](../../research/discovery/evidence/broad-20260911T160113Z/manifest.json)
- [S20.response](../../research/discovery/evidence/recheck-20260911T185811Z/S20.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)
- [payload-checks.json](../../research/discovery/evidence/recheck-20260911T185811Z/payload-checks.json)
- [aviation-stationinfo.json](../../data/processed/foundation/20260911T194849Z/aviation-stationinfo.json)
- [ec46f4110f08e812da0d446a31d431906593b8e441489237b6ec10c94dcb755e.bin](../../data/runtime/blobs/ec46f4110f08e812da0d446a31d431906593b8e441489237b6ec10c94dcb755e.bin)
- [6d2a746215bc3a44b93f6478c89d904580ccab1a138c34ed24a55aee080cc3be.bin](../../research/implementation/conversation-engine-20260912/verified-evidence/6d2a746215bc3a44b93f6478c89d904580ccab1a138c34ed24a55aee080cc3be.bin)

**Review:** pending · **Production:** not_validated

## S21 — Open-Meteo GFS forecast delivery

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://api.open-meteo.com/v1/gfs?latitude=23.02579&longitude=72.58727&hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m&forecast_days=3&timezone=Asia%2FKolkata

**Geography:** Requested city point 23.02579,72.58727; returned grid 23.019852,72.53906

**Time:** 72 hourly records, 11–13 September 2026; Asia/Kolkata

**Fields/units:** temperature_2m °C; relative_humidity_2m %; precipitation mm; wind_speed_10m km/h

**First task:** Preserve requested and returned points, provider/model and intervals; validate precipitation semantics and record absent run identity.

**Unresolved:** Served GFS and direct GFS are not independent model votes. Exact forecast run identity absent in sampled response. Confirm update and revision behavior Confirm suitability for intended location and question

**Terms:** Hosted free tier for non-commercial prototyping, subject to limits; data attribution required; review product-specific upstream and commercial terms

**Questions:** Q02, Q07, Q18

**Evidence files:**

- [openmeteo-gfs.response](../../research/discovery/evidence/numeric-20260911T160221Z/openmeteo-gfs.response)
- [broad-sample-audit.json](../../research/discovery/broad-sample-audit.json)
- [manifest.json](../../research/discovery/evidence/numeric-20260911T160221Z/manifest.json)
- [S21.response](../../research/discovery/evidence/recheck-20260911T185811Z/S21.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)
- [payload-checks.json](../../research/discovery/evidence/recheck-20260911T185811Z/payload-checks.json)
- [forecast-mumbai.json](../../data/processed/foundation/20260911T194849Z/forecast-mumbai.json)
- [d5fe3212057abd3d68a677ca6b6372d2799358c091a3c756654214604b4105f4.bin](../../data/runtime/blobs/d5fe3212057abd3d68a677ca6b6372d2799358c091a3c756654214604b4105f4.bin)
- [forecast-ahmedabad.json](../../data/processed/foundation/20260911T194849Z/forecast-ahmedabad.json)
- [ccfb46b4c954cb12be2758e55bb71b9be5733d23ef9f3508a12f47a92556ad72.bin](../../data/runtime/blobs/ccfb46b4c954cb12be2758e55bb71b9be5733d23ef9f3508a12f47a92556ad72.bin)
- [forecast-delhi.json](../../data/processed/foundation/20260911T194849Z/forecast-delhi.json)
- [6fdb3bde42b3219cc5efd22625a8cfa85c5ece095a95a95067db374401dd40d5.bin](../../data/runtime/blobs/6fdb3bde42b3219cc5efd22625a8cfa85c5ece095a95a95067db374401dd40d5.bin)
- [forecast-srinagar.json](../../data/processed/foundation/20260911T194849Z/forecast-srinagar.json)
- [d7d1c10dcb00c6db73106382c59541ba6a98cb730adb27b47878797050e80687.bin](../../data/runtime/blobs/d7d1c10dcb00c6db73106382c59541ba6a98cb730adb27b47878797050e80687.bin)
- [forecast-guwahati.json](../../data/processed/foundation/20260911T194849Z/forecast-guwahati.json)
- [c26a0903d69bff9b81329b2b22eaacfcd9a22f71107c9e13535d654a3696f277.bin](../../data/runtime/blobs/c26a0903d69bff9b81329b2b22eaacfcd9a22f71107c9e13535d654a3696f277.bin)
- [forecast-chennai.json](../../data/processed/foundation/20260911T194849Z/forecast-chennai.json)
- [9ccf745080071bc3ec3bf5dfe87b45d06a287114444a2059a45cc9d6a280e838.bin](../../data/runtime/blobs/9ccf745080071bc3ec3bf5dfe87b45d06a287114444a2059a45cc9d6a280e838.bin)

**Review:** pending · **Production:** not_validated

## S22 — Open-Meteo ERA5 historical delivery

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** next

**Where:** https://archive-api.open-meteo.com/v1/archive?latitude=23.02579&longitude=72.58727&start_date=2025-07-01&end_date=2025-07-07&daily=precipitation_sum,temperature_2m_max,temperature_2m_min&models=era5&timezone=Asia%2FKolkata

**Geography:** Returned sample grid 23.0,72.5

**Time:** Seven local calendar days, 1–7 July 2025, Asia/Kolkata

**Fields/units:** Daily precipitation sum mm; daily maximum/minimum temperature °C

**First task:** Preserve model selection, day timezone, grid and aggregation; do not compare to UTC daily data without harmonisation.

**Unresolved:** An Open-Meteo sample does not establish direct CDS access or long-period completeness. Reanalysis is not an archived pre-event forecast. Confirm update and revision behavior Confirm suitability for intended location and question

**Terms:** Hosted free tier for non-commercial prototyping, subject to limits; data attribution required; review product-specific upstream and commercial terms

**Questions:** Q10, Q11, Q13

**Evidence files:**

- [openmeteo-era5.response](../../research/discovery/evidence/numeric-20260911T160221Z/openmeteo-era5.response)
- [broad-sample-audit.json](../../research/discovery/broad-sample-audit.json)
- [manifest.json](../../research/discovery/evidence/numeric-20260911T160221Z/manifest.json)
- [history-ahmedabad.json](../../data/processed/foundation/20260911T194849Z/history-ahmedabad.json)
- [4714bf17589474f1714777338677b9864c0f6dddc79f2e8d6fbb74650a2fff42.bin](../../data/runtime/blobs/4714bf17589474f1714777338677b9864c0f6dddc79f2e8d6fbb74650a2fff42.bin)
- [history_local.json](../../research/implementation/point-tools-20260912/live-sources/history_local.json)
- [d328dcf011dfcdf085d42e5a99dc8692bf9889710265fed8d47469c99f89027f.bin](../../research/implementation/point-tools-20260912/live-sources/raw/4827bc45b591615ba396fe5081c6d764382b8108d49bb622b72340d0fdadf26c/58de344670a74a52ae7f1dcf5f9624cb/blobs/d328dcf011dfcdf085d42e5a99dc8692bf9889710265fed8d47469c99f89027f.bin)

**Review:** pending · **Production:** not_validated

## S23 — NASA POWER daily point delivery

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** next

**Where:** https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR&community=AG&longitude=72.58727&latitude=23.02579&start=20250701&end=20250707&format=JSON&time-standard=UTC

**Geography:** Point request with MERRA2 lineage; representative grid metadata must be preserved

**Time:** Seven UTC days, 1–7 July 2025

**Fields/units:** T2M °C; PRECTOTCORR mm/day; fill value -999

**First task:** Map -999 to missing with original token retained; preserve UTC day and parameter definitions.

**Unresolved:** UTC day differs from S22 local day. Model-derived point output is not a local rain gauge measurement. Confirm update and revision behavior Confirm suitability for intended location and question

**Terms:** Production integration and redistribution terms not established in this sample test

**Questions:** Q10, Q11, Q13

**Evidence files:**

- [nasa-power-daily.response](../../research/discovery/evidence/numeric-20260911T160221Z/nasa-power-daily.response)
- [broad-sample-audit.json](../../research/discovery/broad-sample-audit.json)
- [manifest.json](../../research/discovery/evidence/numeric-20260911T160221Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S24 — Open-Meteo GeoNames place search

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://geocoding-api.open-meteo.com/v1/search?name=Ahmedabad&count=3&language=en&format=json

**Geography:** Three Ahmedabad alternatives in India and Pakistan; place points, not boundaries

**Time:** See documented/observed metadata; retrieval date is not weather validity.

**Fields/units:** GeoNames-linked identity, country/admin labels, coordinates, timezone

**First task:** Require country/state disambiguation; record selected place separately from station/grid/district.

**Unresolved:** Place IDs are not official LGD IDs. Confirm update and revision behavior Confirm suitability for intended location and question

**Terms:** Hosted free tier for non-commercial prototyping, subject to limits; data attribution required; review product-specific upstream and commercial terms

**Questions:** Q01, Q15

**Evidence files:**

- [openmeteo-geocode.response](../../research/discovery/evidence/broad-20260911T160113Z/openmeteo-geocode.response)
- [broad-sample-audit.json](../../research/discovery/broad-sample-audit.json)
- [manifest.json](../../research/discovery/evidence/broad-20260911T160113Z/manifest.json)
- [place-ahmedabad.json](../../data/processed/foundation/20260911T194849Z/place-ahmedabad.json)
- [685e84c92f03f83f3973dab54a09b38a0af79c3e459d201603f71b7a2d72eb7a.bin](../../data/runtime/blobs/685e84c92f03f83f3973dab54a09b38a0af79c3e459d201603f71b7a2d72eb7a.bin)

**Review:** pending · **Production:** not_validated

## S25 — IMD All India historical rainfall table (supplied CSV)

**Evidence:** sample_inspected · **Processing:** processed_snapshot · **Priority:** first

**Where:** https://dsp.imdpune.gov.in/home_ogd_rainfall.php

**Geography:** All India aggregate; cannot represent Ahmedabad

**Time:** 1901–2024; 124 annual rows, monthly/seasonal/annual measures

**Fields/units:** Rainfall mm; 17 measures per year

**First task:** Completed v1 normalisation and exact source-cell round-trip; expose a structured query adapter and preserve period/geography limits.

**Unresolved:** Source numeric comparison passed for 2,108 values; structural consistency is not scientific homogeneity. Published totals sometimes differ from monthly sums; preserve both and flag, never silently repair. Monthly data cannot support daily dry-spell questions.

**Terms:** Redistribution and product integration terms not established; no licence inferred from public availability.

**Questions:** Q10, Q13

**Evidence files:**

- [rainfall.csv](../../research/discovery/evidence/pasted-climate-check/rainfall.csv)
- [rainfall-selected.html](../../research/discovery/evidence/pasted-climate-check/rainfall-selected.html)
- [source-comparison.json](../../research/discovery/evidence/pasted-climate-check/source-comparison.json)
- [audit-results.json](../../research/discovery/evidence/pasted-climate-check/audit-results.json)
- [national-climate-audit.ipynb](../../research/discovery/national-climate-audit.ipynb)

**Review:** pending · **Production:** not_validated

## S26 — IMD All India historical mean temperature table (supplied CSV)

**Evidence:** sample_inspected · **Processing:** processed_snapshot · **Priority:** first

**Where:** https://dsp.imdpune.gov.in/home_ogd_temp.php

**Geography:** All India aggregate; cannot represent Ahmedabad

**Time:** 1901–2024; 124 annual rows, monthly/seasonal/annual measures

**Fields/units:** Mean temperature °C; 17 measures per year

**First task:** Completed v1 normalisation and exact source-cell round-trip; expose a structured query adapter and preserve period/geography limits.

**Unresolved:** 2,108 numeric values matched saved official table. Do not sum temperatures or assume an unweighted mean reproduces published annual values. No local temperature or heatwave-event history established.

**Terms:** Redistribution and product integration terms not established; no licence inferred from public availability.

**Questions:** Q10, Q13

**Evidence files:**

- [temperature.csv](../../research/discovery/evidence/pasted-climate-check/temperature.csv)
- [temperature-selected.html](../../research/discovery/evidence/pasted-climate-check/temperature-selected.html)
- [source-comparison.json](../../research/discovery/evidence/pasted-climate-check/source-comparison.json)
- [audit-results.json](../../research/discovery/evidence/pasted-climate-check/audit-results.json)
- [national-climate-audit.ipynb](../../research/discovery/national-climate-audit.ipynb)

**Review:** pending · **Production:** not_validated

## S27 — Supplied district historical rainfall collection (32 CSVs)

**Evidence:** sample_inspected · **Processing:** processed_snapshot · **Priority:** first

**Where:** https://imdpune.gov.in/library/public/e-book110.pdf

**Geography:** 640 historical district series in 32 files; boundary vintage unresolved

**Time:** 1901–2010 overall, uneven per series; Ahmedabad has 110 complete monthly years

**Fields/units:** Monthly, seasonal and annual rainfall mm, series IDs, page references and quality flags

**First task:** Local historical index and full source transcription audit complete; resolve reuse, missingness, source inconsistencies and historical geography gates before broader use.

**Unresolved:** 60,568 rows; 5,018 rows have missing months, 15,817 missing monthly cells. Kendrapada 1920 has annual and OND discrepancies of 12.5 mm beyond rounding bounds. Do not map historical district names automatically to modern boundaries. 1981–2010 baseline is covered for Ahmedabad; 1991–2020 is not. All 640 historical series and 1,029,656 cells including blanks matched the original PDF in the extensive 12 September audit; transcription agreement does not establish scientific accuracy, current boundaries or reuse rights.

**Terms:** Original IMD publication page 3 restricts copying, storage, transmission and redistribution without prior permission; local research checkpoint only, release permission unresolved.

**Questions:** Q10, Q13

**Evidence files:**

- [andhra_pradesh.csv](../../data/raw/imports/2026-09-11/states/andhra_pradesh.csv)
- [arunachal_pradesh.csv](../../data/raw/imports/2026-09-11/states/arunachal_pradesh.csv)
- [assam.csv](../../data/raw/imports/2026-09-11/states/assam.csv)
- [bihar.csv](../../data/raw/imports/2026-09-11/states/bihar.csv)
- [chhattisgarh.csv](../../data/raw/imports/2026-09-11/states/chhattisgarh.csv)
- [delhi.csv](../../data/raw/imports/2026-09-11/states/delhi.csv)
- [goa.csv](../../data/raw/imports/2026-09-11/states/goa.csv)
- [gujarat.csv](../../data/raw/imports/2026-09-11/states/gujarat.csv)
- [haryana.csv](../../data/raw/imports/2026-09-11/states/haryana.csv)
- [himachal_pradesh.csv](../../data/raw/imports/2026-09-11/states/himachal_pradesh.csv)
- [islands.csv](../../data/raw/imports/2026-09-11/states/islands.csv)
- [jammu_kashmir.csv](../../data/raw/imports/2026-09-11/states/jammu_kashmir.csv)
- [jharkhand.csv](../../data/raw/imports/2026-09-11/states/jharkhand.csv)
- [karnataka.csv](../../data/raw/imports/2026-09-11/states/karnataka.csv)
- [kerala.csv](../../data/raw/imports/2026-09-11/states/kerala.csv)
- [madhya_pradesh.csv](../../data/raw/imports/2026-09-11/states/madhya_pradesh.csv)
- [maharashtra.csv](../../data/raw/imports/2026-09-11/states/maharashtra.csv)
- [manipur.csv](../../data/raw/imports/2026-09-11/states/manipur.csv)
- [meghalaya.csv](../../data/raw/imports/2026-09-11/states/meghalaya.csv)
- [mizoram.csv](../../data/raw/imports/2026-09-11/states/mizoram.csv)
- [nagaland.csv](../../data/raw/imports/2026-09-11/states/nagaland.csv)
- [orissa.csv](../../data/raw/imports/2026-09-11/states/orissa.csv)
- [punjab.csv](../../data/raw/imports/2026-09-11/states/punjab.csv)
- [rajasthan.csv](../../data/raw/imports/2026-09-11/states/rajasthan.csv)
- [sikkim.csv](../../data/raw/imports/2026-09-11/states/sikkim.csv)
- [tamil_nadu.csv](../../data/raw/imports/2026-09-11/states/tamil_nadu.csv)
- [telangana.csv](../../data/raw/imports/2026-09-11/states/telangana.csv)
- [tripura.csv](../../data/raw/imports/2026-09-11/states/tripura.csv)
- [union_terr.csv](../../data/raw/imports/2026-09-11/states/union_terr.csv)
- [uttar_pradesh.csv](../../data/raw/imports/2026-09-11/states/uttar_pradesh.csv)
- [uttarakhand.csv](../../data/raw/imports/2026-09-11/states/uttarakhand.csv)
- [west_bengal.csv](../../data/raw/imports/2026-09-11/states/west_bengal.csv)
- [states-folder-audit.json](../../research/discovery/states-folder-audit.json)
- [states-folder-audit.ipynb](../../research/discovery/states-folder-audit.ipynb)
- [imd-110-year-rainfall.pdf](../../research/discovery/evidence/foundation-20260912/imd-110-year-rainfall.pdf)
- [rainfall-download.json](../../research/discovery/evidence/foundation-20260912/rainfall-download.json)
- [ahmedabad-reconciliation.json](../../research/discovery/evidence/foundation-20260912/ahmedabad-reconciliation.json)
- [build-manifest.json](../../data/processed/districts/district-v1-c8b978172b77182e/build-manifest.json)
- [audit.json](../../data/processed/districts/district-v1-c8b978172b77182e/audit.json)

**Review:** pending · **Production:** not_validated

## S28 — Indian Astronomical Ephemeris 2026 (supplied PDF)

**Evidence:** sample_inspected · **Processing:** deferred · **Priority:** optional

**Where:** https://packolkata.imd.gov.in/indian-astronomical-ephemeris.php

**Geography:** Astronomical reference with selected Indian city tables; Ahmedabad not directly in inspected sunrise table

**Time:** 2026 edition; some calendar material extends into 2027

**Fields/units:** Sunrise/sunset/twilight and astronomical tables; time standards vary by section

**First task:** Keep as optional daylight-method reference; extract only relevant sections with page and time-standard citations.

**Unresolved:** 481 pages; UT, TT, IST and local mean time must not be conflated. Inspected sunrise table lists Kolkata, Varanasi, Chennai, Delhi and Mumbai. Provides no weather forecast, rainfall observation or flood warning.

**Terms:** Redistribution and product integration terms not established; no licence inferred from public availability.

**Questions:** Optional supporting reference

**Evidence files:**

- [IAE 2026.pdf](../../data/raw/imports/2026-09-11/IAE%202026.pdf)

**Review:** pending · **Production:** not_validated

## S29 — ECMWF open forecast subset

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://www.ecmwf.int/en/forecasts/datasets/open-data

**Geography:** Global; exact model/grid/member selection pending

**Time:** Forecast runs; subset and retention need product selection

**Fields/units:** GRIB2 fields, ensemble members where offered

**First task:** Select an exact open product and small forecast run subset.

**Unresolved:** Open subset does not establish access to every ECMWF product. Catalogue lead only; no data payload or production integration validated.

**Terms:** Redistribution and product integration terms not established; no licence inferred from public availability.

**Questions:** Q12, Q18

**Evidence files:**

- [broad-spectrum-analysis.md](../../research/discovery/broad-spectrum-analysis.md)

**Review:** pending · **Production:** not_validated

## S30 — MOSDAC satellite catalogue and download service

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://mosdac.gov.in/downloadapi-manual

**Geography:** Product, satellite, footprint and processing level not selected

**Time:** Acquisition time and product latency not sampled

**Fields/units:** Product-specific radiances/retrievals or imagery

**First task:** Choose one weather question and exact satellite product; inspect metadata and download requirements.

**Unresolved:** Catalogue search and account-based downloads have different access requirements. Catalogue lead only; no data payload or production integration validated.

**Terms:** Redistribution and product integration terms not established; no licence inferred from public availability.

**Questions:** Q19

**Evidence files:**

- [broad-spectrum-analysis.md](../../research/discovery/broad-spectrum-analysis.md)

**Review:** pending · **Production:** not_validated

## S31 — NASA GPM IMERG precipitation products

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://gpm.nasa.gov/data/imerg

**Geography:** Gridded satellite precipitation; selected version/grid pending

**Time:** Early/Late/Final are distinct latency and revision products

**Fields/units:** Precipitation and quality fields; product-specific units

**First task:** Select version and run class, obtain a small sample, and validate interval and quality semantics.

**Unresolved:** Satellite precipitation is not a local rain gauge or flood-impact prediction. Catalogue lead only; no data payload or production integration validated.

**Terms:** Redistribution and product integration terms not established; no licence inferred from public availability.

**Questions:** Q11, Q19, Q20

**Evidence files:**

- [broad-spectrum-analysis.md](../../research/discovery/broad-spectrum-analysis.md)

**Review:** pending · **Production:** not_validated

## S32 — CWC flood forecasting portal — exact feed pending

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://ffs.india-water.gov.in/

**Geography:** Station/basin; Ahmedabad-relevant stations not established

**Time:** Gauge/forecast issue and validity not sampled

**Fields/units:** Water level/discharge/thresholds as available; no schema inspected

**First task:** Identify relevant Sabarmati basin stations and a permitted machine-readable product.

**Unresolved:** Portal discovery does not demonstrate a reusable API or local inundation model. Catalogue lead only; no data payload or production integration validated.

**Terms:** Redistribution and product integration terms not established; no licence inferred from public availability.

**Questions:** Q20

**Evidence files:**

- [broad-spectrum-analysis.md](../../research/discovery/broad-spectrum-analysis.md)

**Review:** pending · **Production:** not_validated

## S33 — INCOIS marine services — exact product pending

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://incois.gov.in/

**Geography:** Sea/port/offshore location; separate coastal demonstration required

**Time:** Product-specific forecast/warning validity not sampled

**Fields/units:** Waves, swell, currents or official marine warning, product selection pending

**First task:** Choose one coastal location and exact service, then inspect its permitted feed and units.

**Unresolved:** Ahmedabad district is not a valid marine sample; service catalogue alone is insufficient. Catalogue lead only; no data payload or production integration validated.

**Terms:** Redistribution and product integration terms not established; no licence inferred from public availability.

**Questions:** Q03, Q18

**Evidence files:**

- [broad-spectrum-analysis.md](../../research/discovery/broad-spectrum-analysis.md)

**Review:** pending · **Production:** not_validated

## S34 — ICAR-CRIDA district crop contingency plans

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://www.icar-crida.res.in/Crop_Contingency_Plan.html

**Geography:** District plan coverage and Ahmedabad edition pending

**Time:** Edition-based planning guidance, not a live weather advisory

**Fields/units:** Crop/activity/contingency guidance with conditions

**First task:** Locate the applicable district plan, edition and crop context; cite original conditions.

**Unresolved:** Static contingency plans cannot be presented as newly issued operational advice. Catalogue lead only; no data payload or production integration validated.

**Terms:** Redistribution and product integration terms not established; no licence inferred from public availability.

**Questions:** Q04, Q05

**Evidence files:**

- [broad-spectrum-analysis.md](../../research/discovery/broad-spectrum-analysis.md)

**Review:** pending · **Production:** not_validated

## S35 — Local Government Directory catalogue

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** first

**Where:** https://data.gov.in/catalog/local-government-directory-lgd

**Geography:** Official administrative codes/hierarchy; exact export not sampled

**Time:** Version/date and boundary changes must be preserved

**Fields/units:** District/village identifiers and names; geometry not established

**First task:** Obtain a dated code/hierarchy export and link it explicitly to a separately validated boundary dataset.

**Unresolved:** Administrative codes do not supply boundary polygons or guarantee cross-provider ID compatibility. Catalogue lead only; no data payload or production integration validated.

**Terms:** Redistribution and product integration terms not established; no licence inferred from public availability.

**Questions:** Q03, Q08, Q15

**Evidence files:**

- [broad-spectrum-analysis.md](../../research/discovery/broad-spectrum-analysis.md)

**Review:** pending · **Production:** not_validated

## S36 — Open-Meteo single forecast runs

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://open-meteo.com/en/docs/single-runs-api

**Geography:** Model/grid selection pending

**Time:** Run-specific horizons; archive and access coverage not sampled

**Fields/units:** Pre-event predictions indexed by run and lead time

**First task:** Test permitted run retrieval and metadata; retain forecasts issued before the target event.

**Unresolved:** A stitched historical forecast series cannot substitute blindly for individual forecast runs. Catalogue lead only; no data payload or production integration validated.

**Terms:** Redistribution and product integration terms not established; no licence inferred from public availability.

**Questions:** Q06, Q07, Q12

**Evidence files:**

- [broad-spectrum-analysis.md](../../research/discovery/broad-spectrum-analysis.md)

**Review:** pending · **Production:** not_validated

## S37 — Open-Meteo GloFAS river discharge delivery

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** later

**Where:** https://flood-api.open-meteo.com/v1/flood

**Geography:** River grid/river-network mapping; local suitability untested

**Time:** Seven daily values sampled; arbitrary request support bounded to 30 days.

**Fields/units:** Daily modeled river discharge, m³/s; UTC date.

**First task:** Check river-cell selection and compare an appropriate sample with observed gauge evidence.

**Unresolved:** River discharge is not street-level flooding, reservoir operations or household exposure.

**Terms:** Hosted free tier for non-commercial prototyping, subject to limits; data attribution required; review product-specific upstream and commercial terms

**Questions:** Q20

**Evidence files:**

- [broad-spectrum-analysis.md](../../research/discovery/broad-spectrum-analysis.md)
- [river-ahmedabad.json](../../data/processed/foundation/20260911T194849Z/river-ahmedabad.json)
- [f5717ccf09e64ce6d841b6e8017411c233947bc1e37c2fed529690299e352b54.bin](../../data/runtime/blobs/f5717ccf09e64ce6d841b6e8017411c233947bc1e37c2fed529690299e352b54.bin)

**Review:** pending · **Production:** not_validated

## S38 — BHASHINI speech and translation service catalogue

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://dibd-bhashini.gitbook.io/bhashini-apis/available-models-for-usage

**Geography:** Gujarati/Hindi/English and local names require chosen models and evaluation

**Time:** Model/version and access terms not sampled

**Fields/units:** Speech recognition, translation and speech synthesis capabilities

**First task:** Establish free access for specific models and create local place-name/weather-term test cases.

**Unresolved:** This is an enabling service, not meteorological evidence; current access and quality are unverified. Catalogue lead only; no data payload or production integration validated.

**Terms:** Redistribution and product integration terms not established; no licence inferred from public availability.

**Questions:** Q14, Q15

**Evidence files:**

- [broad-spectrum-analysis.md](../../research/discovery/broad-spectrum-analysis.md)

**Review:** pending · **Production:** not_validated

## S39 — IMD AWS/ARG station data

**Evidence:** access_blocked · **Processing:** sample_missing · **Priority:** next

**Where:** https://api.imd.gov.in/api/v1/aws_data?sid=9

**Geography:** Gujarat state filter 9 documented; station coverage not obtained

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Automatic-station weather fields; units and reporting intervals still require verification

**First task:** Resolve authorised access; inspect Gujarat stations and rainfall field availability.

**Unresolved:** Do not infer a complete Ahmedabad sensor network from a state filter. API documentation sample does not establish a daily rainfall archive.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q01, Q11, Q12

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)
- [imd-aws.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-aws.response)

**Review:** pending · **Production:** not_validated

## S40 — IMD AWS/ARG station mapping

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** next

**Where:** https://api.imd.gov.in/api/v1/aws_data_mapping

**Geography:** Station identifiers and locations; actual metadata not sampled

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Mapping schema not inspected

**First task:** Obtain station metadata and map source IDs without equating them to village/district IDs.

**Unresolved:** No mapping payload obtained; pair with S39.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q01, Q15

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S41 — IMD district rainfall monitoring

**Evidence:** access_blocked · **Processing:** sample_missing · **Priority:** next

**Where:** https://api.imd.gov.in/api/v1/districtrainfall

**Geography:** District aggregation; ID and boundary version unresolved

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Daily/weekly/monthly/cumulative actual, normal and departure fields documented

**First task:** Inspect interval definitions, normal reference period and district identity after access.

**Unresolved:** Daily/weekly/monthly/cumulative fields overlap and must not be added together. No archive coverage established.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q10, Q11, Q13

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)
- [imd-district-rainfall.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-district-rainfall.response)

**Review:** pending · **Production:** not_validated

## S42 — IMD basin quantitative precipitation forecast

**Evidence:** access_blocked · **Processing:** sample_missing · **Priority:** next

**Where:** https://api.imd.gov.in/api/v1/basinqpf

**Geography:** Basin/sub-basin; Ahmedabad relevance not mapped

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Day-labelled basin precipitation fields and average areal precipitation

**First task:** Confirm units, intervals and basin geometry; distinguish rainfall input from hydrological prediction.

**Unresolved:** Rainfall forecast alone does not establish river level or inundation.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q18, Q20

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)
- [imd-qpf.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-qpf.response)

**Review:** pending · **Production:** not_validated

## S43 — IMD cyclone observed and forecast track

**Evidence:** access_blocked · **Processing:** sample_missing · **Priority:** next

**Where:** https://api.imd.gov.in/api/v1/cyclone_track

**Geography:** Cyclone positions and track; coastal applicability not sampled

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Observed versus forecast positions, storm identity, issue/valid time and wind fields

**First task:** Resolve authorised access and inspect a named-storm snapshot with track revisions.

**Unresolved:** Documentation example is historical, not evidence of an active cyclone.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q03, Q07, Q18

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)
- [imd-cyclone-track.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-cyclone-track.response)

**Review:** pending · **Production:** not_validated

## S44 — IMD cyclone wind warning polygons

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** next

**Where:** https://api.imd.gov.in/api/v1/cyclone_wind

**Geography:** Wind-threshold polygons, not district boundaries

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Polygon groups by wind threshold, units and validity requiring verification

**First task:** Inspect storm/time identity and geometry, retaining threshold namespaces.

**Unresolved:** Cannot infer household damage or a fixed impact probability.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q03, Q08

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S45 — IMD cyclone cone of uncertainty

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** next

**Where:** https://api.imd.gov.in/api/v1/cyclone_cou

**Geography:** Cyclone uncertainty geometry; meaning and valid horizon need documentation

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Cone geometry with product metadata

**First task:** Confirm cone definition and validity before explaining it.

**Unresolved:** A cone must not be interpreted as the full area of hazardous weather.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q03, Q08, Q18

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S46 — IMD radar image product — index lead

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** Source not selected

**Geography:** Radar station coverage and exact imagery/numeric product unresolved

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Image listed in API index; no usable route/schema in inspected body

**First task:** Find a supported exact radar product with timestamp, coverage and projection.

**Unresolved:** An index label or radar image is not proof of accessible calibrated radar volumes.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q19

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S47 — IMD lightning data — index lead

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** Source not selected

**Geography:** Detection/forecast product and geographic coverage unselected

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Lightning listed in API index; no tested route/schema

**First task:** Identify whether the product is detection or forecast and inspect event time, coverage and access.

**Unresolved:** Nowcast lightning wording does not establish access to strike-level observations.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q03, Q19

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S48 — IMD product-specific codes and definitions

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://api.imd.gov.in/public/api_reference.html

**Geography:** Definitions are scoped to an IMD product, not global weather conventions

**Time:** Definition page retrieved in September 2026; version history not established.

**Fields/units:** District warning and nowcast colour codes; rainfall categories and field definitions

**First task:** Use namespaced code dictionaries; confirm applicability to each payload before decoding.

**Unresolved:** District-warning colour numbering differs from nowcast numbering. Code documentation alone does not resolve lifecycle or geographic applicability.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q03, Q09, Q14, Q17

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)
- [imd-code-namespaces.json](../../data/reference/imd-code-namespaces.json)

**Review:** pending · **Production:** not_validated

## S49 — User-provided field and activity context

**Evidence:** lead · **Processing:** source_missing · **Priority:** first

**Where:** Source not selected

**Geography:** User-selected field/location; no actual user records collected

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Crop, stage or sowing date, intended activity/time; soil/irrigation context if advice requires it

**First task:** Define optional and required inputs per advisory question; ask only for missing decision-relevant context.

**Unresolved:** A weather API cannot supply an individual farmer’s actual field conditions. Context requirements depend on the specific guidance method.

**Terms:** No external dataset acquired; establish data collection/usage requirements during implementation.

**Questions:** Q04, Q05, Q06

**Evidence files:**

- No local sample.

**Review:** pending · **Production:** not_validated

## S50 — Terrain, drainage, exposure and vulnerability inputs

**Evidence:** lead · **Processing:** source_missing · **Priority:** later

**Where:** Source not selected

**Geography:** Exact basin/urban area and spatial resolution unselected

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Terrain, drainage, assets/population and vulnerability as required by a chosen impact method

**First task:** Select an impact question and method before choosing datasets; preserve a warning-only initial scope.

**Unresolved:** These inputs are needed for validated local flood-impact claims, not simply relaying an official warning. No impact model or input dataset validated.

**Terms:** No external dataset acquired; establish data collection/usage requirements during implementation.

**Questions:** Q20

**Evidence files:**

- No local sample.

**Review:** pending · **Production:** not_validated

## S51 — Gujarati/Hindi language and voice evaluation set

**Evidence:** lead · **Processing:** source_missing · **Priority:** first

**Where:** Source not selected

**Geography:** Indian language terms and ambiguous local place names

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Representative utterances, expected intents/place/time, warning terminology and negation cases

**First task:** Create labelled test cases and explicitly record synthetic versus human-reviewed examples.

**Unresolved:** Speech-service access does not prove reliable interpretation. No beneficiary recordings or expert language validation collected.

**Terms:** No external dataset acquired; establish data collection/usage requirements during implementation.

**Questions:** Q14, Q15

**Evidence files:**

- No local sample.

**Review:** pending · **Production:** not_validated

## S52 — IMD port warning

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://api.imd.gov.in/api/v1/portwarning

**Geography:** Port/sea/coastal area; choose a coastal sample distinct from Ahmedabad

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Marine warning/bulletin text with issue and validity metadata

**First task:** Inspect a permitted exact product sample, its area identifiers and validity.

**Unresolved:** Documented route only; no access or weather payload tested in this pass.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q03, Q08, Q14

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S53 — IMD sea-area bulletin

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://api.imd.gov.in/api/v1/seabulletin

**Geography:** Port/sea/coastal area; choose a coastal sample distinct from Ahmedabad

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Marine warning/bulletin text with issue and validity metadata

**First task:** Inspect a permitted exact product sample, its area identifiers and validity.

**Unresolved:** Documented route only; no access or weather payload tested in this pass.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q03, Q08, Q14

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S54 — IMD coastal bulletin

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** https://api.imd.gov.in/api/v1/coastalbulletin

**Geography:** Port/sea/coastal area; choose a coastal sample distinct from Ahmedabad

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Marine warning/bulletin text with issue and validity metadata

**First task:** Inspect a permitted exact product sample, its area identifiers and validity.

**Unresolved:** Documented route only; no access or weather payload tested in this pass.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q03, Q08, Q14

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S55 — IMD fishermen warning — index lead

**Evidence:** catalogue_or_page_inspected · **Processing:** sample_missing · **Priority:** later

**Where:** Source not selected

**Geography:** Marine region; exact product and distribution unresolved

**Time:** Product issue/validity, cadence and archive coverage require a representative payload.

**Fields/units:** Fishermen warning listed in index; exact callable route not established

**First task:** Locate a current official bulletin/feed and inspect the relevant coastal region.

**Unresolved:** Catalogue listing is not a working API.

**Terms:** Access, supported integration and redistribution terms unresolved.

**Questions:** Q03, Q14

**Evidence files:**

- [imd-reference.response](../../research/discovery/evidence/recheck-20260911T185811Z/imd-reference.response)
- [manifest.json](../../research/discovery/evidence/recheck-20260911T185811Z/manifest.json)

**Review:** pending · **Production:** not_validated

## S56 — Open-Meteo marine wave delivery

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://marine-api.open-meteo.com/v1/marine

**Geography:** Three sea-grid points; wider geographic capability not exhaustively validated.

**Time:** Current-page/forecast sample at recorded fetch timestamp; runtime freshness and PDF validity are distinct.

**Fields/units:** Wave height m, direction degrees, period seconds; hourly UTC.

**First task:** Use the implemented adapter; resolve the documented operational gates before decision support.

**Unresolved:** Reference/information prototype; not operational clearance or independently validated warning dissemination. Operational validity, domain interpretation, geographic completeness and sustained service behavior require validation.

**Terms:** Hosted free tier for non-commercial prototyping, subject to limits; data attribution required; review product-specific upstream and commercial terms

**Questions:** Q16, Q22

**Evidence files:**

- [marine-arabian-sea.json](../../data/processed/foundation/20260911T194849Z/marine-arabian-sea.json)
- [c64730c7d57fa8b38c0d7e3ad9692e9a401b8796b6ef023ef5d44631ed5dedd4.bin](../../data/runtime/blobs/c64730c7d57fa8b38c0d7e3ad9692e9a401b8796b6ef023ef5d44631ed5dedd4.bin)
- [marine-andaman-sea.json](../../data/processed/foundation/20260911T194849Z/marine-andaman-sea.json)
- [832ccd12a570620af9d484c8ffa9195d00b40d9d3607afa286691bda05d8f009.bin](../../data/runtime/blobs/832ccd12a570620af9d484c8ffa9195d00b40d9d3607afa286691bda05d8f009.bin)
- [marine-bay-of-bengal.json](../../data/processed/foundation/20260911T194849Z/marine-bay-of-bengal.json)
- [d9f3283166c64ae156f315c0bef744822327191c15afbbf654f3722e2d7008c4.bin](../../data/runtime/blobs/d9f3283166c64ae156f315c0bef744822327191c15afbbf654f3722e2d7008c4.bin)

**Review:** pending · **Production:** not_validated

## S57 — IMD district farmer bulletin delivery (English and local language)

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://mausam.imd.gov.in/responsive/agromet_adv_ser_district_current_en.php

**Geography:** 36 source-listed regions and 698 district entries in the directory snapshot. Crop retrieval inspected in Ahmedabad, Coimbatore, Kamrup and Dibrugarh (56 passages); Surat and Madurai samples held. Not national document acceptance.

**Time:** Current-page/forecast sample at recorded fetch timestamp; runtime freshness and PDF validity are distinct.

**Fields/units:** Publisher selector IDs and PDF pages; meteorological/crop text retained.

**First task:** Use the implemented adapter; resolve the documented operational gates before decision support.

**Unresolved:** Reference/information prototype; not operational clearance or independently validated warning dissemination. Crop indexing does not include every general or warning section of a bulletin; cross-section contradictions are not automatically resolved. Growth-stage filtering uses explicit row labels; conditions in source paragraph bodies are retained but not inferred as universal stage metadata. Operational validity, domain interpretation, geographic completeness and sustained service behavior require validation.

**Terms:** Official public delivery; automated use and redistribution rights require product-specific review. No unrestricted licence inferred.

**Questions:** Q04, Q06, Q14

**Evidence files:**

- [advisory-ahmedabad.json](../../data/processed/foundation/20260911T194849Z/advisory-ahmedabad.json)
- [653f005c5eb6069e2d4b21afb2700b993f7d1d0699781876d698ef553811cd90.bin](../../data/runtime/blobs/653f005c5eb6069e2d4b21afb2700b993f7d1d0699781876d698ef553811cd90.bin)
- [f2c3924fa398b55ac80313583b682e5680868313b7ac425e87a66a5627da13b3.bin](../../data/runtime/blobs/f2c3924fa398b55ac80313583b682e5680868313b7ac425e87a66a5627da13b3.bin)
- [advisory-kamrup.json](../../data/processed/foundation/20260911T194849Z/advisory-kamrup.json)
- [f5e9fbe91b5fe14b3b9a3290517696b279cf93b327c4067b9c7ee0225df71e07.bin](../../data/runtime/blobs/f5e9fbe91b5fe14b3b9a3290517696b279cf93b327c4067b9c7ee0225df71e07.bin)
- [b3c30de0f6c92294e140f478a748eef7c39cccb24b821fe6b17090743797a72f.bin](../../data/runtime/blobs/b3c30de0f6c92294e140f478a748eef7c39cccb24b821fe6b17090743797a72f.bin)
- [advisory-directory.json](../../data/processed/foundation/20260911T194849Z/advisory-directory.json)
- [1f9de548ac30e07ea7154282bb29c9599b6a2827ea884c24992cf6301e57f74a.bin](../../data/runtime/blobs/1f9de548ac30e07ea7154282bb29c9599b6a2827ea884c24992cf6301e57f74a.bin)
- [03a2ef4a1a6b8f84c76cc8ae30d792d30c250ae40055ae16648e47bf48e47aa8.bin](../../data/runtime/blobs/03a2ef4a1a6b8f84c76cc8ae30d792d30c250ae40055ae16648e47bf48e47aa8.bin)
- [4a8331f4ea823a381a6579f029661fb2f964ad930b0833d0bab14abaafc72af6.bin](../../data/runtime/blobs/4a8331f4ea823a381a6579f029661fb2f964ad930b0833d0bab14abaafc72af6.bin)
- [86b914598b7e299e97fd92dc20636e3c0a4b7a74b076a78a0bebe722c977a48a.bin](../../data/runtime/blobs/86b914598b7e299e97fd92dc20636e3c0a4b7a74b076a78a0bebe722c977a48a.bin)
- [8e0c32c7e73799686f1886feb6dfc4105e45a56963e9dc51f57464347ed45570.bin](../../data/runtime/blobs/8e0c32c7e73799686f1886feb6dfc4105e45a56963e9dc51f57464347ed45570.bin)
- [c39751ef59094e7877c15e0d3670b5316a6ff346a3e5eb3de305f54d67f7fa85.bin](../../data/runtime/blobs/c39751ef59094e7877c15e0d3670b5316a6ff346a3e5eb3de305f54d67f7fa85.bin)
- [08723e094183b2661336d343d9bc3d0433b9b2247b763f1477dc7c339ae8d771.bin](../../data/runtime/blobs/08723e094183b2661336d343d9bc3d0433b9b2247b763f1477dc7c339ae8d771.bin)
- [e9c546456ad59688ec411b2cb047fba419b1d9d40a23bbe801ff368d01d4aa46.bin](../../data/runtime/blobs/e9c546456ad59688ec411b2cb047fba419b1d9d40a23bbe801ff368d01d4aa46.bin)
- [ea7f8f554c9a9c03cb2f4b89281049266262112eec16263f15ef19eeaa02648e.bin](../../data/runtime/blobs/ea7f8f554c9a9c03cb2f4b89281049266262112eec16263f15ef19eeaa02648e.bin)
- [b7cdfc0ad78948d837bb9fdd5a36353f3222a553011f1c8caf8b79f16c82bdc6.bin](../../data/runtime/blobs/b7cdfc0ad78948d837bb9fdd5a36353f3222a553011f1c8caf8b79f16c82bdc6.bin)
- [1c37a1f0d2f0daa204307ccb2140dd28d732a58e4f4e3245d8ff163c33dab26e.bin](../../data/runtime/blobs/1c37a1f0d2f0daa204307ccb2140dd28d732a58e4f4e3245d8ff163c33dab26e.bin)
- [40f22e74f947c532eac467a0bf76d0712cf843ef08d49cdd82c6570581170ff2.bin](../../data/runtime/blobs/40f22e74f947c532eac467a0bf76d0712cf843ef08d49cdd82c6570581170ff2.bin)
- [4d94c3c8ee6a75d5b55884a8308ea8f8b90cbda6ba639b6d82df0c4307828855.bin](../../data/runtime/blobs/4d94c3c8ee6a75d5b55884a8308ea8f8b90cbda6ba639b6d82df0c4307828855.bin)
- [881867d07db24eb59e7bcc98e0748e7096b105238deb4f34b03ee299d9193099.bin](../../data/runtime/blobs/881867d07db24eb59e7bcc98e0748e7096b105238deb4f34b03ee299d9193099.bin)
- [98913037032a78293029114ff2a1a7d4ddbca2b84b126c780923674611677429.bin](../../data/runtime/blobs/98913037032a78293029114ff2a1a7d4ddbca2b84b126c780923674611677429.bin)
- [56aa6e1e875f5e2d2268972507de2b782b824c1a86946af1ae4c62aa9d9714a3.bin](../../data/runtime/blobs/56aa6e1e875f5e2d2268972507de2b782b824c1a86946af1ae4c62aa9d9714a3.bin)
- [e73a048050602bfd05fade1bcd7e013f8c10c5281a71bdedf55436b15e9ce3a5.bin](../../data/runtime/blobs/e73a048050602bfd05fade1bcd7e013f8c10c5281a71bdedf55436b15e9ce3a5.bin)
- [8778052f32989753f7990e7fd08350b403ebbc81a8116f4d0747043ac254e7ed.bin](../../data/runtime/blobs/8778052f32989753f7990e7fd08350b403ebbc81a8116f4d0747043ac254e7ed.bin)
- [60452323ecf86a4d5948bfb96fcec34e785e611da1ae2aa8695e8ef2f7780107.bin](../../data/runtime/blobs/60452323ecf86a4d5948bfb96fcec34e785e611da1ae2aa8695e8ef2f7780107.bin)
- [586ca0bb81502c929c1e3d0d2b32f16c4d7b882b86f99693ff83970d53f22b4c.bin](../../data/runtime/blobs/586ca0bb81502c929c1e3d0d2b32f16c4d7b882b86f99693ff83970d53f22b4c.bin)
- [5d46eb24caf9e231a943310814b321007b2b26cedb29fc88062d2d3381036781.bin](../../data/runtime/blobs/5d46eb24caf9e231a943310814b321007b2b26cedb29fc88062d2d3381036781.bin)
- [33ed7048f39eb081dfe9b65d39bcbb7fa8a62c5415d11c5e1d44c9a2f5bc2135.bin](../../data/runtime/blobs/33ed7048f39eb081dfe9b65d39bcbb7fa8a62c5415d11c5e1d44c9a2f5bc2135.bin)
- [f262d4dde93f23b406912747a0af630dc491b3d3b4937a01aaf5e65170b8eea7.bin](../../data/runtime/blobs/f262d4dde93f23b406912747a0af630dc491b3d3b4937a01aaf5e65170b8eea7.bin)
- [23a35e008076236a93ec62b95647be21ecd8d07623a20d773aa97fbe7bc694d8.bin](../../data/runtime/blobs/23a35e008076236a93ec62b95647be21ecd8d07623a20d773aa97fbe7bc694d8.bin)
- [9499bcd6c1a0d4b2d55d7d9c7bbee5d71244e674aafcfbacb62b3e7a8c29bf5d.bin](../../data/runtime/blobs/9499bcd6c1a0d4b2d55d7d9c7bbee5d71244e674aafcfbacb62b3e7a8c29bf5d.bin)
- [25133c0bfd098857ef1505acf2eae9eb6759934b1fe637ab8a6b100ae660aedf.bin](../../data/runtime/blobs/25133c0bfd098857ef1505acf2eae9eb6759934b1fe637ab8a6b100ae660aedf.bin)
- [8ed6d568fe51d1d25bce026fbb8bbb934006db89b2a0ec4b8f083b8c249b47e5.bin](../../data/runtime/blobs/8ed6d568fe51d1d25bce026fbb8bbb934006db89b2a0ec4b8f083b8c249b47e5.bin)
- [20a8d83c13587875b1a3377cf2fbf148187b13f116b1f25fc5060c33b391de52.bin](../../data/runtime/blobs/20a8d83c13587875b1a3377cf2fbf148187b13f116b1f25fc5060c33b391de52.bin)
- [c2dc438d95e870bc466731104d0fa71889bb1723a2471d0a66ad4d2121a226ff.bin](../../data/runtime/blobs/c2dc438d95e870bc466731104d0fa71889bb1723a2471d0a66ad4d2121a226ff.bin)
- [6ecf3ec63903834eca990a3ba345ba206a1858cab1b4f70f2b9042bbd83a8f8c.bin](../../data/runtime/blobs/6ecf3ec63903834eca990a3ba345ba206a1858cab1b4f70f2b9042bbd83a8f8c.bin)
- [c822401b77da2b9896a5027b0e4a20b88dc04953587deef150aea9e066a3cf11.bin](../../data/runtime/blobs/c822401b77da2b9896a5027b0e4a20b88dc04953587deef150aea9e066a3cf11.bin)
- [138d5e2aac6049bd1843e7d58b160e8793f2638e2a9e6b4e45e871ebb76da2b8.bin](../../data/runtime/blobs/138d5e2aac6049bd1843e7d58b160e8793f2638e2a9e6b4e45e871ebb76da2b8.bin)
- [4731d0c2311768cdf3a2bf71cb37a299cad55665b2cb7db34b5c5be21c8f4fb1.bin](../../data/runtime/blobs/4731d0c2311768cdf3a2bf71cb37a299cad55665b2cb7db34b5c5be21c8f4fb1.bin)
- [d9e6cc9e4c8344c21ed8321a43919e487624b80fcf9e42da1cc357289fb6b020.bin](../../data/runtime/blobs/d9e6cc9e4c8344c21ed8321a43919e487624b80fcf9e42da1cc357289fb6b020.bin)
- [bd21a43acde8ab270139dbda229debcdb3903a816d6d17d298cd693bbd65cf0f.bin](../../data/runtime/blobs/bd21a43acde8ab270139dbda229debcdb3903a816d6d17d298cd693bbd65cf0f.bin)
- [c9b510f7d5c91a2f19f1329719c4f2b9576d6f61c02f992a38e1c0b9503fc4a1.bin](../../data/runtime/blobs/c9b510f7d5c91a2f19f1329719c4f2b9576d6f61c02f992a38e1c0b9503fc4a1.bin)
- [0789f600dc4f172d4ed0b83acd06275492ca92ea4b096d2facb9646341ebdbec.bin](../../data/runtime/blobs/0789f600dc4f172d4ed0b83acd06275492ca92ea4b096d2facb9646341ebdbec.bin)
- [advisory-ahmedabad-gujarati.json](../../data/processed/foundation/20260911T194849Z/advisory-ahmedabad-gujarati.json)
- [34ce38e2c5d7c4daf0ebc595274a1f2398de2f477386c755c0cad6463956eaea.bin](../../data/runtime/blobs/34ce38e2c5d7c4daf0ebc595274a1f2398de2f477386c755c0cad6463956eaea.bin)
- [658e09d09f652ee7723739386ae7e0c611babc7e30fd30ca187632a4a6cd923d.bin](../../data/runtime/blobs/658e09d09f652ee7723739386ae7e0c611babc7e30fd30ca187632a4a6cd923d.bin)
- [advisory-coimbatore.json](../../data/processed/foundation/20260911T194849Z/advisory-coimbatore.json)
- [99b77dc84e6bec60bfe3a5cd64b0d8247761b43abed6af3a63b056b0edfe7b9f.bin](../../data/runtime/blobs/99b77dc84e6bec60bfe3a5cd64b0d8247761b43abed6af3a63b056b0edfe7b9f.bin)
- [3d004ae0499c6c6bce001b931e726e451df0155c923a83aab848f9a3b526e997.bin](../../data/runtime/blobs/3d004ae0499c6c6bce001b931e726e451df0155c923a83aab848f9a3b526e997.bin)
- [18-bulletin-retrieval-and-warning-lifecycle.md](../../docs/18-bulletin-retrieval-and-warning-lifecycle.md)
- [acceptance.json](../../research/implementation/evidence-retrieval-20260913/acceptance.json)
- [2a5c1798e89380e862a2c429522f7a1c18b459f912bf600c1d449c787954b730.pdf](../../research/implementation/context-and-retrieval-20260913/source-pdfs/2a5c1798e89380e862a2c429522f7a1c18b459f912bf600c1d449c787954b730.pdf)
- [57e47b6892371cb3a87f9aa9ca648deee8adaa055f5bc36f7c935b00263ec8ee.pdf](../../research/implementation/context-and-retrieval-20260913/source-pdfs/57e47b6892371cb3a87f9aa9ca648deee8adaa055f5bc36f7c935b00263ec8ee.pdf)
- [5e8120cf3b228944634faa709f524f3a76c0c4e043635e4a3fce7b4739bcf9bb.pdf](../../research/implementation/context-and-retrieval-20260913/source-pdfs/5e8120cf3b228944634faa709f524f3a76c0c4e043635e4a3fce7b4739bcf9bb.pdf)
- [source-review.json](../../research/implementation/context-and-retrieval-20260913/source-review.json)
- [dibrugarh.json](../../research/implementation/context-and-retrieval-20260913/districts/dibrugarh.json)

**Review:** pending · **Production:** not_validated

## S58 — RSMC official sea-area bulletin delivery

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://rsmcnewdelhi.imd.gov.in/sea-area-bulletin.php

**Geography:** Two current-page listed sea-area PDFs sampled.

**Time:** Current-page/forecast sample at recorded fetch timestamp; runtime freshness and PDF validity are distinct.

**Fields/units:** Original PDF pages; wind knots, visibility, sea condition and validity as publisher text.

**First task:** Use the implemented adapter; resolve the documented operational gates before decision support.

**Unresolved:** Reference/information prototype; not operational clearance or independently validated warning dissemination. Operational validity, domain interpretation, geographic completeness and sustained service behavior require validation.

**Terms:** Official public delivery; automated use and redistribution rights require product-specific review. No unrestricted licence inferred.

**Questions:** Q16, Q22

**Evidence files:**

- [marine-bulletin-sea-0.json](../../data/processed/foundation/20260911T194849Z/marine-bulletin-sea-0.json)
- [2112af9f4b548e80fad2851f2ae5363a097aa82e0749d5a029204ccb08247a49.bin](../../data/runtime/blobs/2112af9f4b548e80fad2851f2ae5363a097aa82e0749d5a029204ccb08247a49.bin)
- [da7a8c3bfe5e281e2b1aed06d74b5ccc44238a2663ede8faf1ba6a02a129a7ec.bin](../../data/runtime/blobs/da7a8c3bfe5e281e2b1aed06d74b5ccc44238a2663ede8faf1ba6a02a129a7ec.bin)
- [marine-bulletin-sea-1.json](../../data/processed/foundation/20260911T194849Z/marine-bulletin-sea-1.json)
- [f9761b0f1d633a55f22d010c1feb7ced67f30b7b47a18951e665d76f75019cd3.bin](../../data/runtime/blobs/f9761b0f1d633a55f22d010c1feb7ced67f30b7b47a18951e665d76f75019cd3.bin)
- [marine-catalog-sea.json](../../data/processed/foundation/20260911T194849Z/marine-catalog-sea.json)

**Review:** pending · **Production:** not_validated

## S59 — RSMC official coastal bulletin delivery

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://rsmcnewdelhi.imd.gov.in/coastal-weather-bulletin.php

**Geography:** 15 current-page listed PDFs; Gujarat bulletin sampled.

**Time:** Current-page/forecast sample at recorded fetch timestamp; runtime freshness and PDF validity are distinct.

**Fields/units:** Original PDF pages; regional wind, weather, port signals and validity as publisher text.

**First task:** Use the implemented adapter; resolve the documented operational gates before decision support.

**Unresolved:** Reference/information prototype; not operational clearance or independently validated warning dissemination. Operational validity, domain interpretation, geographic completeness and sustained service behavior require validation.

**Terms:** Official public delivery; automated use and redistribution rights require product-specific review. No unrestricted licence inferred.

**Questions:** Q16, Q22

**Evidence files:**

- [marine-bulletin-coastal-11.json](../../data/processed/foundation/20260911T194849Z/marine-bulletin-coastal-11.json)
- [65be240fa76b093ecb8d0757e276dcbe738ef970b036defaf40938287a5842a4.bin](../../data/runtime/blobs/65be240fa76b093ecb8d0757e276dcbe738ef970b036defaf40938287a5842a4.bin)
- [f6531b835e142d269dcdfd67117fb68310cf63d2536c039c9a8c54f322c3afd3.bin](../../data/runtime/blobs/f6531b835e142d269dcdfd67117fb68310cf63d2536c039c9a8c54f322c3afd3.bin)
- [marine-catalog-coastal.json](../../data/processed/foundation/20260911T194849Z/marine-catalog-coastal.json)

**Review:** pending · **Production:** not_validated

## S60 — IMD CityWx responsive portal and station-search/data routes

**Evidence:** sample_inspected · **Processing:** deferred · **Priority:** next

**Where:** https://city.imd.gov.in/citywx/responsive/

**Geography:** City/station portal; Ahmedabad search yielded 11 candidates, with main station ID 42647. Nationwide inventory not obtained.

**Time:** Checks on 2026-09-11 UTC / 2026-09-12 IST; weather observation and forecast validity not established.

**Fields/units:** Verified search fields: station_id and station (strings). Weather fields inferred from client code only; units and temporal semantics require payload validation.

**First task:** Resolve portal integrity and supported weather access; then validate station identity and observation/forecast contracts. Station-search sample may be reviewed as identity evidence only.

**Unresolved:** Only station-search JSON obtained: 11 Ahmedabad-related candidates; no weather payload obtained. Weather features are visible in application code but current station-level completeness and correctness are unverified. Returned HTML contains unrelated code attempting recurring external window openings on Android; cause and wider scope are unknown. Remote JavaScript was not executed. City/station IDs and search labels are not district or LGD identifiers. Establish supported access to city weather data; current sampled requests returned 403. Resolve unexplained Android external-window script before recommending or embedding the portal. Validate source observation time, rainfall interval, units, sentinel values and forecast issue/validity against a real payload. Confirm station coordinates, representation, nationwide inventory and cross-product ID compatibility. Establish reuse terms and documented integration support.

**Terms:** Automated integration and redistribution terms unresolved; HTTP 200 on station search does not establish permission or a supported API.

**Questions:** Q01, Q02, Q03

**Evidence files:**

- [access-errors.json](../../research/discovery/evidence/citywx-20260912/access-errors.json)
- [ahmedabad-city-fetch.json](../../research/discovery/evidence/citywx-20260912/ahmedabad-city-fetch.json)
- [ahmedabad-city.response](../../research/discovery/evidence/citywx-20260912/ahmedabad-city.response)
- [app-fetch.json](../../research/discovery/evidence/citywx-20260912/app-fetch.json)
- [app.js](../../research/discovery/evidence/citywx-20260912/app.js)
- [assessment.json](../../research/discovery/evidence/citywx-20260912/assessment.json)
- [index-fetch.json](../../research/discovery/evidence/citywx-20260912/index-fetch.json)
- [index.html](../../research/discovery/evidence/citywx-20260912/index.html)
- [manifest.json](../../research/discovery/evidence/citywx-20260912/manifest.json)
- [search-ahmedabad-fetch.json](../../research/discovery/evidence/citywx-20260912/search-ahmedabad-fetch.json)
- [search-ahmedabad.json](../../research/discovery/evidence/citywx-20260912/search-ahmedabad.json)
- [citywx-assessment.md](../../research/discovery/citywx-assessment.md)
- [citywx-assessment.ipynb](../../research/discovery/citywx-assessment.ipynb)

**Review:** registry inclusion authorized by user on 2026-09-12; operational suitability not approved · **Production:** not_validated

## S61 — GeoNames India downloadable gazetteer and local place index

**Evidence:** sample_inspected · **Processing:** processed_snapshot · **Priority:** first

**Where:** https://download.geonames.org/export/dump/IN.zip

**Geography:** 549021 indexed source settlement records across the India extract; shared names, incomplete aliases and unresolved locations remain explicit. Not a count of official villages.

**Time:** Downloaded 2026-09-12; per-record modification dates retained. No historical boundary validity inferred.

**Fields/units:** GeoNames ID, source/alternate names, latitude/longitude WGS84 degrees, source feature/admin labels, modification date

**First task:** Completed exact/alias index; approximate names require user confirmation; preserve point versus administrative area distinction.

**Unresolved:** GeoNames IDs and source administrative labels are not official LGD IDs or dated boundary crosswalks. Missing settlements/aliases and duplicate names require clarification or explicit pins. One point does not establish village-wide or district-wide weather. Evaluate regional and local-language matching on held-out names. Acquire authoritative dated administrative mappings separately.

**Terms:** GeoNames CC BY 4.0; attribution required. Source provided as-is without assurance of accuracy, timeliness or completeness. This is a downloaded national extract, not a public geocoding API workload.

**Questions:** Q02, Q03, Q04, Q08, Q15, Q21, Q22

**Evidence files:**

- [IN-20260912.zip](../../data/raw/geonames/IN-20260912.zip)
- [manifest.json](../../data/processed/geography/geonames-india-20260912/manifest.json)
- [build-manifest.json](../../data/processed/geography/geonames-india-20260912/build-manifest.json)
- [state-aliases.json](../../data/processed/geography/geonames-india-20260912/state-aliases.json)

**Review:** pending · **Production:** not_validated

## S62 — Open-Meteo best-match extended hourly forecast

**Evidence:** sample_inspected · **Processing:** sample_ready_for_processing · **Priority:** first

**Where:** https://api.open-meteo.com/v1/forecast

**Geography:** Selected India settlement points; requested and returned grids retained, not area averages.

**Time:** Governed 1–7 UTC forecast days; conversation hourly detail limited to 48 hours per task.

**Fields/units:** Temperature/apparent temperature °C; relative humidity/probability %; precipitation mm; wind/gusts km/h; visibility m

**First task:** Implemented governed normalized publication, raw-evidence verification and typed hourly conversation facts. Broader model/area/scientific validation remains open.

**Unresolved:** Default best-match selection can differ by variable; upstream models and runs unspecified. Not exclusively GFS. Hourly precipitation probabilities apply to >0.1 mm in the preceding hour, never an aggregate period probability. Point grid estimates are not official warnings, observations or district averages. Measure regional/model representativeness, calibration, updates and sustained availability.

**Terms:** Open-Meteo hosted free tier for non-commercial prototyping subject to limits; attribution and upstream terms apply. No SLA.

**Questions:** Q02, Q07, Q18

**Evidence files:**

- [extended_forecast.json](../../research/implementation/point-tools-20260912/live-sources/extended_forecast.json)
- [569c5612afbdd2695f510b2b7e90ef964f2ed126c13c662c375a7b85e166c683.bin](../../research/implementation/point-tools-20260912/live-sources/raw/96c2c9d9df0847b7e859d366972284d7695a804df3f9a75f554167c0b9f4d651/e8b3f8cbd7424220a4e79af5eba30a97/blobs/569c5612afbdd2695f510b2b7e90ef964f2ed126c13c662c375a7b85e166c683.bin)
- [da565bb0deee599eca9ee740741897a2c85f579d149021cadb7bab634d1b99ca.bin](../../research/implementation/context-and-retrieval-20260913/verified-evidence/da565bb0deee599eca9ee740741897a2c85f579d149021cadb7bab634d1b99ca.bin)

**Review:** pending · **Production:** not_validated
