# Fresh conversational checks

39 API conversation attempts, including one explicitly excluded harness follow-up. App status is reported separately from the audit judgement. No overall pass percentage is calculated.

| Test | Question | App status | Seconds | Audit interpretation |
|---|---|---|---:|---|
| forecast | Will it rain in Ahmedabad, Gujarat tomorrow morning? | answered | 0.796 | SCOPED PASS: saved raw response hash and rainfall sum checked. |
| followup_time | And what about the afternoon? | HTTP 400 | 0.03 | BLOCKED: follow-up needs the unavailable configured model. |
| followup_measure | Instead, show temperature for that same place and time. | needs_clarification | 0.057 | HARNESS LIMIT: conversation id absent after prior error; superseded by correct-thread follow-up. |
| gfs_comparison | Compare the models for rainfall in Ahmedabad tomorrow morning. | answered | 0.712 | SCOPED RETRIEVAL: returned evidence for this request; no scientific accuracy claim. |
| gfs_explicit | Use GFS for rainfall in Ahmedabad tomorrow morning. | HTTP 400 | 0.004 | BLOCKED: phrasing needs unavailable model; default GFS query works. |
| wrf_explicit | Use WRF for rainfall in Ahmedabad tomorrow morning. | HTTP 400 | 0.003 | BLOCKED: phrasing needs unavailable model; WRF integration also absent. |
| history_trend | Show the annual rainfall trend for Ahmedabad district, Gujarat from 1981 to 2010. | answered | 0.553 | SCOPED PASS: 30 source values and slope independently checked. |
| history_multi | Show India annual rainfall and mean temperature for 2024. | answered | 0.018 | FAIL: rainfall omitted; completion label is wrong. |
| reanalysis | What was the daily mean relative humidity in Ahmedabad from 1 through 3 July 2024? | unavailable | 6.558 | SOURCE FAILURE: HTTP 502 recorded; no data invented. |
| reanalysis_unsupported | ERA5-Land daily rainfall in Ahmedabad from 5 through 7 August 2024. | unavailable | 0.041 | EXPECTED REFUSAL: requested model does not carry rainfall. |
| national_bulletin | What does the latest all India weather bulletin say about heavy rainfall? | unavailable | 0.08 | UNAVAILABLE: no matching runtime corpus. |
| crop_bulletin | What does the Ahmedabad district agromet advisory say for cotton? | unavailable | 3.233 | BLOCKED: missing document-search dependency. |
| crop_decision | Can I irrigate cotton in Ahmedabad, Gujarat this week? | unavailable | 0.567 | BLOCKED: missing document-search dependency; no field recommendation. |
| hindi | कल अहमदाबाद, गुजरात में सुबह बारिश होगी? | answered | 0.103 | SCOPED PASS: Hindi template, matching English date/window; not fluent review. |
| gujarati | અમદાવાદમાં આવતીકાલે સવારે વરસાદ થશે? | answered | 0.095 | SCOPED PASS: Gujarati template, matching English date/window; not fluent review. |
| tamil_output | Will it rain in Ahmedabad tomorrow morning? | partial | 0.094 | EXPECTED DOWNGRADE: requested writing unavailable; English retained and partial status. |
| ambiguity | Will it rain in Sultanpur tomorrow? | needs_selection | 0.093 | SCOPED PASS: asks for place selection. |
| typo | Will it rain in Ahmedbad, Gujrat tomorrow? | needs_selection | 0.113 | SCOPED RETRIEVAL: returned evidence for this request; no scientific accuracy claim. |
| warning | Is any warning in force for Patna, Bihar today? | answered | 11.096 | SCOPED RETRIEVAL: returned evidence for this request; no scientific accuracy claim. |
| now | What is it like right now in Ahmedabad? | answered | 3.969 | SCOPED RETRIEVAL: returned evidence for this request; no scientific accuracy claim. |
| airport | What is the current weather at VOBL? | answered | 3.326 | SCOPED RETRIEVAL: returned evidence for this request; no scientific accuracy claim. |
| marine | What are the wave conditions off Kochi tomorrow? | answered | 4.207 | SCOPED PASS: 24 wave-model samples, cell and distance in receipt. |
| river | What is the river discharge near Patna, Bihar tomorrow? | answered | 1.159 | SCOPED PASS: modeled cell only, two UTC daily values; not a named river/gauge. |
| water_level | What is the observed water level near Patna, Bihar now? | answered | 2.811 | FAIL: ordinary weather substituted for the requested water-level information. |
| tide | What is the tide at Kochi tomorrow? | unavailable | 0.041 | EXPECTED UNAVAILABLE: unsupported data not fabricated. |
| notification | Notify me if a cyclone warning is issued for Kochi. | needs_selection | 1.154 | FAIL: Notify became another place; no watch registered. |
| novel_llm | My clothes are drying outside in Ahmedabad; which hours tomorrow would be better for bringing them inside? | HTTP 400 | 0.003 | BLOCKED: novel wording needs unavailable model. |
| context_measure_correct_thread | Instead, show temperature for that same place and time. | HTTP 400 | 0.005 | BLOCKED: configured model unavailable; same conversation id supplied. |
| history_rain_alone | Show India annual rainfall for 2024. | answered | 0.038 | SCOPED RETRIEVAL: returned evidence for this request; no scientific accuracy claim. |
| history_two_reversed | Show India annual mean temperature and rainfall for 2024. | answered | 0.027 | FAIL: repeats the missing rainfall despite reversing measure order. |
| warning_forecast | Will it rain in Patna tomorrow, and is there any warning? | answered | 2.157 | SCOPED RETRIEVAL: returned evidence for this request; no scientific accuracy claim. |
| water_level_control | What is the river water level at Patna tomorrow? | HTTP 400 | 0.003 | BLOCKED: interpretation fails; no invented water level. |
| current_water_level_repeat | What is the observed water level near Patna, Bihar now? | answered | 1.177 | FAIL: same wrong-product routing reproduced. |
| hourly | Show hourly rainfall probability and temperature in Ahmedabad tomorrow morning. | answered | 0.1 | SCOPED RETRIEVAL: returned evidence for this request; no scientific accuracy claim. |
| strict_window | How much rain is forecast for Ahmedabad tomorrow from 09:15 to 12:15? | partial | 0.096 | EXPECTED PARTIAL: whole source hours only, missing fractional interval disclosed. |
| long_horizon | Will it rain in Ahmedabad 30 days from now? | needs_clarification | 0.09 | INCOMPLETE: asks for time although 30 days from now was specified. |
| daily_temperature | What was the ERA5-Land daily mean temperature in Ahmedabad from 5 through 7 August 2024? | answered | 0.688 | SCOPED PASS: ERA5-Land values match saved provider response. |
| notify_known_place | Notify me if there is a weather warning for Ahmedabad, Gujarat. | needs_selection | 1.276 | FAIL: known Ahmedabad request becomes a Noti place choice; no watch registered. |
| nonenglish_clarify | सुल्तानपुर में कल बारिश होगी? | needs_selection | 0.114 | PARTIAL: Hindi clarification; geography candidates differ from English spelling. |
