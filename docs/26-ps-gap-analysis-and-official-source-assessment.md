# WeatherGPT: what is actually achieved against SIH26068, and what needs major work

Recorded 14 September 2026. This is an assessment document, not a status promotion. It changes no finding status in either registry; the status changes it proposes are listed for separate verification.

It answers a direct challenge: *"I think nothing substantial has been done towards the solution of the problem statement."* The honest reply has two halves, and both are true.

## 1. The blunt answer

**A large amount of real engineering exists, and it is not the problem statement.** The evaluated core of SIH26068 is a *disaster-management* product: real-time observations, official alerts and dissemination, nationwide location-based advisories, Indian-language output, and voice for rural accessibility. What has been built is an unusually careful **evidence and retrieval foundation** with a working conversational desktop surface over *forecast, historical and bulletin* data. Those are different things, and the second does not deliver the first.

**The challenge is still substantially right.** Of the eight named features, the three that carry the PS's own theme — real-time observations (1), extreme-weather alerts and dissemination (4), and location-based advisories at national scale (5) — are absent or non-functional. Multilingual output (6) is understood but not written. Voice (8) does not exist. Mobile (the expected solution) does not exist. On the criteria the PS lists, *accuracy and relevance* and *grounding* are genuinely strong; *integration with real-time meteorological systems*, *voice*, and *UI and accessibility for low-connectivity rural users* are weak or absent.

**But one previously assumed blocker is now falsified.** Until this assessment, official Indian source access was treated as unresolved, and docs/21 A05 recorded that catch-up as an external blocker. That is no longer accurate. This machine reaches the official sources, they serve current data, and the project has already registered three of them. The largest remaining obstacle for the disaster-management core is now **engineering, not access**.

## 2. Feature-by-feature against the eight named features

| # | Feature | Real state | Evidence |
|---|---|---|---|
| 1 | Real-time weather information retrieval | **Absent as observations.** Chat retrieves *forecasts* only. Two official live observation layers were found today and are unconnected: imd:metar_data_layer (145 stations, current to 14 Sep 14:00 UTC) and imd:aws_data_layer (2,071 stations). docs/21 A05: "General live station observations/nowcasts are not connected to chat. Refreshing a forecast is not observing current conditions." | capabilities.py contains no observation tool at all; GAPS['observation'] is returned instead |
| 2 | Natural-language forecasting | **Works, scoped.** Multi-turn, corrections, hourly probability, feels-like, gusts, visibility, source crosscheck. Known engine defects remain, including A01 where context retention can defeat an explicit change, and A03 explanation tasks. | 13 client and 14 view component checks; four recorded journeys |
| 3 | NWP integration (GFS/WRF) | **Partly.** External GFS and best-match products through governed adapters. The review records that broad model, variable and horizon coverage, run lineage and independent skill evaluation are missing. Running WRF is not established as required. | S21 and S62 registry entries; prototype_adapter_tested |
| 4 | Extreme-weather alerts and early-warning dissemination | **Non-functional, and now clearly fixable.** execute_warning returns unavailable unconditionally: no area resolution, no applicability, no delivery. The official IMD CAP feed is live and reachable; the nationwide district warning layer is live and updated today; the lifecycle engine already validates update, cancel and expiry, but is never given a resolved area. | warning_tools.py lines 8-24; cap_lifecycle.py lines 21-66; section 3 below |
| 5 | Location-based forecasting and advisories | **Point forecasts only.** No district or area product in chat, no advisory crosswalk. Authoritative district geometry carrying state, subdivision, region, area and the owning Meteorological Centre was found today (imd:india_districts, 741 districts). | docs/21 A04 and P08: "authoritative crosswalks are missing" |
| 6 | Multilingual support | **Understood, not produced.** Hindi and Hinglish scoped dialogue works; output language is expressible and now honestly disclosed as a downgrade. No fluent Hindi or Gujarati output exists. The one second-language official feed is Urdu, not Hindi. | docs/21 A02; docs/25 batch record |
| 7 | Climate trends and historical analysis | **Works, scoped.** Published district and national records, comparisons, totals, charts with exact-value and evidence-id inspection, and a short ERA5 window labelled as modeled. Renamed-district mapping and boundary comparability remain open. | docs/15 and docs/25 |
| 8 | Voice for rural accessibility | **Absent.** No speech input, no speech output, no transcript correction, no noisy-input testing. | docs/14 stage 6; the S6 registry stage is still proposed |

Against the expected solution: **mobile** is absent (responsive web only), **backend integration** is partly real (adapters, provenance and governed acquisition), **LLM query understanding** is real and working locally, and **scalable real-time ingestion** has real infrastructure but is request-driven behind a single lock.

## 3. What this assessment newly established about official access

All of the following was measured live today, from this machine.

**Reachable official sources (HTTP 200):** mausam.imd.gov.in, imdagrimet.gov.in, sachet.ndma.gov.in, reactjs.imd.gov.in (GeoServer), and cap-sources.s3.amazonaws.com.

**IMD CAP feed** (in-imd-en, already registered as source S06): nine alerts, all status Actual, severity Severe, certainty Likely, event "Extremely heavy", areaDesc ODISHA, generated by the National Weather Forecasting Centre. **Every alert has expired**; the newest expired at 07:00 IST on 10 September 2026. So the correct current answer for anywhere in India is "no active IMD CAP alert in this feed" — an explicit no-notification state, which is not an all-clear.

**The NDMA feed is corrupt and must be quarantined.** The feed in-ndma-en presents itself as "Latest alerts from National Disaster Management Authority", but its six items are 2013 and 2015 Rwanda flood warnings authored by Meteo Rwanda, with a channel publication date of December 2018. Any naive ingestion would publish foreign, decade-old flood warnings as Indian official alerts. This is exactly the failure mode the project's prohibitions exist for.

**India has four feed slugs:** in-imd-en, in-imd-ur, in-ndma-en and in-ndma-ur. There is no Hindi CAP feed.

**IMD GeoServer WFS** at reactjs.imd.gov.in/geoserver/wfs, already registered as source S15 for district_warnings_india, exposes 29 layers. These include imd:district_warnings_india (764 features, 740 dated today, updated_at spread across today), imd:NowcastWarningDistrict (764 features, 65 carrying IMD message text, updated 19:13 IST today), imd:aws_data_layer (2,071 stations), imd:metar_data_layer (145 current stations), imd:india_districts (741), imd:india_state, imd:indian_river_basin, imd:coastal_sf, imd:radar_station_status and imd:Cyclone_Track_V.

**The named blocker "WFS day semantics" is now resolved, from IMD's own code.** The next action recorded against finding R02 requires verification of "origin, geographic applicability, feed completeness, real update/cancel editions and WFS day semantics". The district warning page's own script defines how the day fields must be read:

    warnings_arr = nc['Day_' + day].split(",");   // Day_1..Day_5 are HAZARD CODE LISTS
    if (warnings_arr[i] > 1) { ... category[warnings_arr[i]] ... }
    category = { "1":"No Warning", "2":"Heavy Rain", "3":"Heavy Snow",
                 "4":"Thunderstorms & Lightning, Squall etc", "5":"Hailstorm", "6":"Dust Storm",
                 "7":"Dust Raising Winds", "8":"Strong Surface Winds", "9":"Heat Wave", "10":"Hot Day",
                 "11":"Warm Night", "12":"Cold Wave", "13":"Cold Day", "14":"Ground Frost", "15":"Fog",
                 "16":"Very Heavy Rain", "17":"Extremely Heavy Rain" }

This matters because the obvious reading is wrong. Day_1 is **not** a severity level, and Day1_Color is **not** the public colour code: it is only a WMS env style parameter that the page passes to the imd:Warnings_StateDistrict_Merged layer. The public four-term legend on that page is No Warning, Watch, Alert, Warning, and it is rendered server-side by WMS; it is *not* carried in the WFS attributes. A correct implementation may therefore state the **official hazard name** verbatim, and must **not** infer a colour level from the Day*_Color numbers. Reading those numbers as severity would fabricate a warning severity.

The live national picture for Day 1, 14 September, is: Thunderstorms 439 districts, No Warning 312, Strong Surface Winds 202, Heavy Rain 46, Very Heavy Rain 16, Extremely Heavy Rain 3.

**A real place now resolves.** Patna maps to authoritative PATNA / BIHAR, subdivision BIHAR, region EAST AND NORTH EAST INDIA, 3,260.7 square kilometres, owning centre MC PATNA. Its official day row for 2026-09-14, updated 18:05 IST, reads: Day 1 No Warning, Day 2 Thunderstorms and Lightning with Squall, Day 3 No Warning, Day 4 Thunderstorms, Day 5 No Warning. That is a current, place-specific, official warning answer carrying an explicit no-warning state — the exact artefact docs/21 A05 says is missing.

**Affected-area mapping is solvable and its residual is finite.** Joining the warning layer's 755 district names to the 741 authoritative districts gives 610 exact matches after normalisation, or 80.8 per cent. The 145 unmatched are not noise; they are a bounded, reviewable set: renamed districts such as BELGAUM to BELAGAVI and BELLARY to BALLARI, transliterations such as AHMADABAD to AHMEDABAD, AURANGABAAD to AURANGABAD and ANUGUL to ANGUL, IMD's own typos such as BANGLORERURAL and BANGLOREURBAN, suffixed splits such as BALRAMPURCG and BALRAMPURUP, and merged names such as ALLURISITHARAMARAJU. This is the dated-alias work docs/21 section 3 already calls for, and it is finite rather than open-ended.

**SACHET** at sachet.ndma.gov.in is a client-rendered Next.js application. Its /CapFeed page is reachable, but no JSON data endpoint was found, so it is not yet usable as a machine feed.

**Terms remain unresolved.** S06 carries usage_terms "Not established for production redistribution", and every source is selection "proposed; no production source selected" with user_review "pending". Nothing here changes that, and it is the reason the work below stays local.

## 4. What needs major work, in dependency order

1. **Official warning applicability and one complete alert journey.** This is the PS theme and the project's own step 2, and it is now unblocked: a real feed, a real district layer, resolved day semantics, a resolved owning centre per district, and a lifecycle engine that is already written but starved of a location. It requires a district resolver (point-in-polygon plus a reviewed alias table), the hazard-code reading above, explicit active, expired, update, cancel and no-warning states, and a delivery mechanism with duplicate and update handling — the piece docs/21 A05 records as never built, quoting the probe result "It did not create delivery behavior or explicitly resolve the request to be notified".
2. **Live observations distinct from forecasts.** This is feature 1 and the second half of A05. Two official layers are available. It requires an observation tool that states station, distance, observation time and representativeness, and that never lets a forecast stand in for an observation or an airport station for a city.
3. **National-scale location-based advisories.** Feature 5. District warnings plus the agromet bulletin path, where imdagrimet.gov.in responds correctly to a browser-like Referer. The earlier "You are not Authorised" response was a header check, not a wall.
4. **Indian-language output.** Feature 6. The gap is production of Hindi and Gujarati, not understanding of them. A deterministic, reviewed localised renderer for typed answer shapes would beat model translation for numbers and caveats.
5. **Voice.** Feature 8 and the social-impact hook. No local speech input is installed; the options are macOS "say" for output plus typed input, or a hosted speech API with a key supplied locally.
6. **Mobile.** The expected solution. Realistically a progressive web app and a measured low-bandwidth journey, not a native rewrite.
7. **Source terms and production selection.** Every source is user_review pending. This constrains what may be shown or shared, and it needs a user decision rather than more code.

## 5. What must not change while doing this

The prohibitions already recorded stay in force: never fabricate an active warning; never treat old bulletin text, model rain or a resolved hash as alert eligibility; never infer a colour level this feed does not carry; treat a reachable feed or an empty eligible set as neither an alert nor an all-clear; keep observations, forecasts, official warnings and source advisories distinct; and keep each claim attached to its entity, time, parameter, unit and source.

## 6. Decisions taken on 14 September 2026

1. **Official source use: approved.** Live local adapters may be built against the registered official endpoints, with attribution, and with the unresolved usage_terms recorded as a blocker for any sharing. Source terms remain the user's decision before anything is shared.
2. **Priority: confirmed.** Warnings first, then observations, then national advisories, then language, then voice, then mobile.
3. **Voice: hosted API with a user-supplied key.** Credentials belong in local backend configuration only and must never reach browser code or the conversation. The key is still to be supplied.

## 7. Decisions this assessment originally asked for

1. **Official source use.** May live adapters be built against the registered official endpoints (IMD CAP S06, IMD GeoServer S15 and S04, IMD AWS and METAR), used locally with attribution and with the unresolved usage_terms recorded as a blocker for any sharing? Or should this stay on already-saved evidence only?
2. **Priority.** The proposal above is order 1 warnings, 2 observations, 3 advisories, 4 language, 5 voice, 6 mobile. Confirm or re-rank.
3. **Voice approach.** macOS "say" output with typed input, needing no key and no network but limited to this machine; or a hosted speech API with a key supplied locally?
