# IMD CityWx responsive portal — inspected 12 September 2026 IST

Verdict: valuable candidate for official city/station reports, seven-day city forecasts and station identity, but **not a validated working weather connector**. Keep on hold alongside S10 (the previously discovered Ahmedabad CityWx link); do not treat this assessment as closure of the official-observation access gap.

## Direct checks

| Request | Result |
|---|---|
| Portal HTML | HTTP 200, 1,073 bytes |
| Referenced application JavaScript | HTTP 200, 696,544 bytes; inspected as text only |
| GET station search, query Ahmedabad | HTTP 200 JSON: 11 station candidates; Ahmedabad ID 42647 |
| GET station directory | HTTP 403 |
| GET default city data | HTTP 403 |
| POST city data with multipart ID 42647, matching the application's request method | HTTP 403; weather payload not obtained |

The application code contains components for maximum/minimum temperature and departures, rainfall, humidity at 08:30 and 17:30, seven-day forecasts, warning text/colours, sunrise/sunset and moon times, temperature-versus-normal charts and a climatology/extremes link. These are **code-observed capabilities**, not claims that every station currently has all these fields. Rainfall accumulation periods, issuance/validity, units, sentinel values, update cadence and reuse permissions still need a real payload and documentation. The client treats several values, including 99.9/999/999.00 strings, as unavailable; do not apply a generic numeric conversion without field-specific validation.

The successful search identifies Ahmedabad, airport and neighbourhood-labelled stations, including locations labelled Gandhi Nagar. These are source labels, not a verified district membership or official administrative crosswalk. The 11 search results do not establish nationwide inventory size or station-level coverage.

## Page-integrity concern

The returned HTML contains a script outside the React application that checks for Android and periodically attempts to open an unrelated external domain (`filmm.me`) in a new window. The loop checks every 10 seconds and attempts an opening once in each odd-numbered minute. This behavior is unrelated to weather and warrants caution. No remote JavaScript was executed and the destination was not visited. Browser popup blocking may prevent the opening; the code's presence alone does not prove successful execution, device infection, the cause of the script, or compromise of all IMD services.

Do not embed this page in the product or ask users to rely on it until this behavior is resolved. Evaluate any data endpoint separately; public availability does not establish an integration contract or data integrity. No report was sent to anyone.

## Product value and next gate

1. Station discovery can improve city/airport/neighbourhood selection.
2. A validated station report could supply official observations needed to compare model forecasts with measured weather.
3. A validated seven-day official city forecast could supplement the existing GFS delivery as a separately identified product.
4. Climatology and normal-temperature context could support local climate explanations if its period and source are established.

Next gate: resolve the page-integrity concern through an official support channel and establish supported access to city weather payloads; then reconcile observation timing, station identity, missing values and forecast validity. HTTP 403 is an observed restriction, not a reason to bypass it.

Evidence: `evidence/citywx-20260912/manifest.json` includes hashes; `citywx-assessment.ipynb` records the executed checks. No existing registry readiness claim or frozen foundation checkpoint was upgraded.

Source: https://city.imd.gov.in/citywx/responsive/
