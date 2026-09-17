# Final feature verification matrix

18 September 2026. One row per feature area, with the columns the brief asks for. "API works" was measured by
calling the route; "Playwright verified" by opening the route in the browser and checking the heading, the
section and table counts, the failed requests and the console (0 for every route); "AI verified" by the
100-question run. A blank cell is a thing that does not apply, not a thing that passed.

| feature | backend exists | API works | frontend exists | real data connected | Playwright verified | AI verified | responsive verified | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Current conditions (right now) | yes `/api/now` | yes | Dashboard, Today, Map | yes | yes (3 routes) | yes (categories A–C) | yes | **working** |
| Point forecast (hourly, days) | yes `/api/forecast` | yes | Forecast, Dashboard | yes | yes | yes (32 questions) | yes | **working** |
| Hourly forecast beyond 48 h | yes (daily product) | yes | Forecast | yes | yes | yes ("next three days" now answers) | yes | **working** |
| District warnings (national) | yes `/api/warnings/national` | yes | Warnings, Today, Dashboard | yes | yes | yes (category F) | yes | **working** |
| Place warning view | yes `/api/warnings/place` | yes | Warnings, Today | yes | yes | yes | yes | **working** |
| CAP relay assessment | yes `/api/warnings/cap` | yes | Warnings | yes | yes | yes (refuses with the reason) | yes | **working** |
| Alert brief | yes `/api/warnings/alert-brief` | yes | Warnings | yes | yes | yes | yes | **working** |
| Observations network | yes `/api/observations/network`, `/near` | yes | Observations | yes | yes | yes | yes | **working** |
| Radar status | yes `/api/radar` | yes | Observations | yes | yes | yes | yes | **working** |
| Air quality | yes `/api/air-quality` | yes | Air quality, Dashboard | yes | yes | yes (category C, H) | yes | **working** |
| Aviation METAR/TAF | yes `/api/aviation` | yes | Aviation | yes | yes | yes (asks for the ICAO code when it needs one) | yes | **working** |
| Marine waves and river discharge | yes `/api/marine`, `/api/river`, `/api/basins` | yes | Sea and rivers | yes | yes | yes (category F) | yes | **working** |
| Ensemble spread | yes `/api/ensemble` | yes | Ensemble spread, with the **member-distribution figure** | yes | yes | yes (category F, H) | yes | **working** |
| Forecast verification | yes `/api/verification` | yes | Forecast verification | yes | yes | yes (asks for the place it needs) | yes | **working** |
| Compare places | composed client-side from other routes | yes | Compare places | yes | yes | yes (category D) | yes | **working** |
| Forecast changes between retrievals | yes `/api/forecast/changes` | yes | What changed | yes | yes | **partial**: the router answers inventory questions as conversation instead of calling the route (open, recorded) | yes | **working with an open routing gap** |
| Climate records (district rainfall 1901–2010) | yes `/api/climate/index`, `/series` | yes | Climate records, Dashboard | yes | yes | yes (category E, after the default-range fix) | yes | **working** |
| Historical lookups (annual, monthly, seasonal) | yes, published tables | yes | Climate records | yes | yes | yes (category E) | yes | **working** |
| Farm advisories (directory + brief) | yes `/api/advisories/states`, `/districts`, `/holdings`, `/brief` | yes | Farm advisories | yes | yes | yes (category A) | yes | **working** |
| Published documents and the viewer | yes `/api/corpus`, `/api/documents/<sha>` | yes | Published documents, with the **library figure** | yes | yes | yes (category F) | yes | **working** |
| Map layers and geometry | yes `/api/map/layers`, `/static/*` | yes | Map | yes | yes | yes | yes | **working** |
| Places search and the catalogue | yes `/api/places/search` | yes | every place picker | yes | yes | yes | yes | **working** |
| Assistant (multi-turn, multilingual) | yes `/api/chat` | yes | Ask | yes | yes | **95 of 100 questions pass**, 5 recorded as open | yes | **working, with five recorded gaps** |
| Conversation preview, cancel, stored conversations | yes | yes | Ask | yes | yes | yes | yes | **working** |
| Plans, watches, notifications (local) | yes | yes | plans panel, Dashboard | yes | yes | yes (the "notify me" path) | yes | **working** |
| Briefcase (kept briefs) | yes `/api/briefs` | yes | Briefcase, Dashboard | yes | yes | yes | yes | **working** |
| Sources and settings | yes `/api/settings/capabilities`, health | yes | Sources and settings | yes | yes | yes (the router answers the inventory from context; route-level answer is the open gap) | yes | **working** |
| Speech (transcribe / speak) | yes (needs the Sarvam key) | untested without a key | composer voice path | blocked on the key | no | no | — | **blocked: key not present in this environment** |
| Fixed figures from the served engine | the engine is served and pinned | yes | Forecast, Warnings, Ensemble, Today, Documents | yes | yes (113 marks drawn on the forecast figure) | — | yes | **restored** |
| Published-day timeline figure | spec exists | — | **not mounted** | — | no | — | — | **available, not mounted**: its read (the overview place strip) carries no days in this build |
| ZIP design's top navigation and atmosphere | — | — | not adopted | — | — | — | — | **reviewed and not adopted** (the running shell already has the glass topbar and the aurora field); the files were removed rather than left as dead code |

## Completion criteria, answered honestly

| criterion | state |
| --- | --- |
| Backend starts, frontend starts, database works, APIs work | yes — measured in this session on 8765 and 8790 |
| Real data reaches the frontend, no fake data | yes — every value in the API↔UI record came from a read; absences show as absences |
| All major backend features represented in the UI | yes for every route in the inventory; the settings/changes *chat* routing gap is recorded |
| Previous frontend features preserved or restored | see the old→new mapping: 11 preserved, 6 restored, 8 intaken, 2 copied-not-mounted with reasons |
| All routes work, navigation works, search works, maps work, charts work | 19 of 19 routes with 0 failed requests and 0 console errors; five figures verified drawing |
| Weather, forecast, climate, warnings, agriculture, travel | working; the four categories were exercised by the 100-question set |
| AI assistant works with the local model; failure states work | the assistant works with no provider (template answers) and with a provider; a provider failure falls back rather than inventing |
| 100 AI questions tested; failures fixed and retested | 100 run, 95 pass, 4 causes fixed and retested, 5 open and recorded |
| Multilingual, hallucination tests | 12 multilingual and 6 adversarial questions run; the adversarial ones refuse |
| Desktop, tablet, mobile; no horizontal overflow | 1440 / 1024 / 768 / 390 measured, overflow 0 after the clip fix |
| Console errors, network failures investigated | 0 across the route sweep; the two crashes found in the question run were fixed |
| Frontend tests pass, backend tests pass, typecheck, build | 1351 Python, 339 React, `tsc` clean, build clean, gate 20/20 |

**Not claimed:** production readiness, operational clearance, nationwide coverage, forecast skill, or that every
button on every surface was clicked. The open items above are the honest remainder.
