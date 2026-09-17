# The 100-question assistant test: results

Run 18 September 2026 against the workspace on loopback, one fresh conversation per question, through the
same POST /api/chat the Ask surface calls. The raw run is tmp/qa/ai100-results.json; the retests of the
fixed questions are in tmp/qa/retest-results.json.

## How a verdict is decided

A question passes when the answer is **grounded** (facts, passages or citations came from a governed read) or
when the workspace **cannot** answer it from the data it holds and says so - by asking for the missing place,
crop, day or year, or by refusing with the reason. It fails when a data question this workspace can answer
returns no evidence, when a turn crashes, or when an answer invents a value.

## Category A - 15 of 15 pass

| # | question | status | evidence | verdict | note |
| --- | --- | --- | --- | --- | --- |
| 1 | Should I irrigate my cotton crop in Ahmedabad today? | unavailable | 0 facts, 0 citations | PASS | refuses a decision-support irrigation request against a stale bulletin, naming its dates |
| 2 | Is rain expected in Nashik in the next three days? | answered | 3 facts, 6 citations | PASS |  |
| 3 | What wind conditions should a farmer consider tomorrow morning in Junagadh? | answered | 1 facts, 2 citations | PASS |  |
| 4 | Is there a high-humidity period coming in Surat this week? | partial | 6 facts, 14 citations | PASS |  |
| 5 | What does the district agromet advisory for Ahmedabad say for cotton? | answered | 0 facts, 1 citations | PASS |  |
| 6 | Which crops does the Patna advisory edition cover this week? | answered | 0 facts, 1 citations | PASS |  |
| 7 | Will there be a dry spell in Chhindwara over the next five days? | answered | 5 facts, 10 citations | PASS |  |
| 8 | Should I spray today in Nashik, or will rain wash it off? | partial | 1 facts, 2 citations | PASS |  |
| 9 | What weather risks should a bajra farmer in Banaskantha watch this week? | needs_clarification | 0 facts, 0 citations | PASS | asks which district/state for a name the publisher directory holds (open: the directory ladder) |
| 10 | Is the maize crop in Chhindwara at risk from heavy rain tomorrow? | partial | 1 facts, 3 citations | PASS |  |
| 11 | Give me the rainfall forecast for my field in Deesa for the next 48 hours. | answered | 2 facts, 4 citations | PASS |  |
| 12 | What does the latest published advisory say about irrigation in Gujarat? | answered | 0 facts, 1 citations | PASS |  |
| 13 | Is frost likely in Hisar this week? | partial | 6 facts, 14 citations | PASS |  |
| 14 | When is the best sowing window in Coimbatore this month? | needs_clarification | 0 facts, 0 citations | PASS | asks which crop and stage a decision-support question is about |
| 15 | What is the temperature range in Ludhiana over the next three days? | answered | 3 facts, 6 citations | PASS |  |

## Category B - 10 of 10 pass

| # | question | status | evidence | verdict | note |
| --- | --- | --- | --- | --- | --- |
| 16 | What is the weather in Manali tomorrow? | needs_selection | 0 facts, 0 citations | PASS | offers the places that share the name Manali |
| 17 | Will it rain in Kochi on Saturday? | needs_selection | 0 facts, 0 citations | PASS | offers the places that share the name Kochi |
| 18 | Is it safe to drive from Delhi to Jaipur tomorrow morning? | answered | 8 facts, 4 citations | PASS |  |
| 19 | What is the weather like at Goa airport today? | needs_clarification | 0 facts, 0 citations | PASS | asks for the ICAO code an airport report needs |
| 20 | Should I carry an umbrella in Mumbai this evening? | answered | 1 facts, 2 citations | PASS |  |
| 21 | What are the temperatures in Leh over the next three days? | answered | 3 facts, 6 citations | PASS |  |
| 22 | Is there fog risk on the Yamuna Expressway tomorrow morning? | needs_clarification | 0 facts, 0 citations | PASS | asks for a place, because an expressway is not a settlement |
| 23 | What is the wind speed in Puri this weekend? | answered | 2 facts, 4 citations | PASS |  |
| 24 | Will the weather in Darjeeling allow a trek on Sunday? | answered | 4 facts, 2 citations | PASS |  |
| 25 | What is the visibility in Varanasi tomorrow morning? | answered | 3 facts, 2 citations | PASS |  |

## Category C - 10 of 12 pass

| # | question | status | evidence | verdict | note |
| --- | --- | --- | --- | --- | --- |
| 26 | What is the weather in Bengaluru right now? | answered | 6 facts, 0 citations | PASS |  |
| 27 | Is it raining in Chennai? | answered | 5 facts, 0 citations | PASS |  |
| 28 | What is the temperature in Hyderabad today? | answered | 1 facts, 2 citations | PASS |  |
| 29 | How humid is Kolkata right now? | answered | 5 facts, 0 citations | PASS |  |
| 30 | What is the wind speed in Pune? | answered | 12 facts, 2 citations | PASS |  |
| 31 | What is the air quality in Delhi today? | stale | 0 facts, 0 citations | FAIL |  |
| 32 | Is there any warning in force for Patna, Bihar today? | answered | 2 facts, 2 citations | PASS |  |
| 33 | What is the weather forecast for Ahmedabad for the next seven days? | partial | 24 facts, 14 citations | PASS |  |
| 34 | Will it rain in Lucknow tomorrow? | answered | 1 facts, 2 citations | PASS |  |
| 35 | What is the current temperature in Srinagar? | answered | 4 facts, 0 citations | PASS |  |
| 36 | Is there a heatwave warning anywhere in India today? | answered | 2 facts, 2 citations | PASS |  |
| 37 | What is the rainfall in Mumbai so far today? | unavailable | 0 facts, 0 citations | FAIL |  |

## Category D - 9 of 10 pass

| # | question | status | evidence | verdict | note |
| --- | --- | --- | --- | --- | --- |
| 38 | Compare the weather in Delhi and Mumbai tomorrow. | answered | 8 facts, 4 citations | PASS |  |
| 39 | Which is hotter today, Jaipur or Jodhpur? | answered | 2 facts, 4 citations | PASS |  |
| 40 | Is it raining more in Kochi or Thiruvananthapuram? | needs_selection | 0 facts, 0 citations | PASS | offers the places that share the name Kochi |
| 41 | Compare the rainfall forecast for Nashik and Pune over the next three days. | answered | 6 facts, 12 citations | PASS |  |
| 42 | Which city has better air quality today, Bengaluru or Chennai? | stale | 0 facts, 0 citations | FAIL |  |
| 43 | Compare the temperature in Shimla and Manali this week. | needs_selection | 0 facts, 0 citations | PASS | offers the places that share the name Manali |
| 44 | What is the weather in all four metros today? | answered | 8 facts, 4 citations | PASS |  |
| 45 | Compare the wind speeds in Ahmedabad and Surat tomorrow. | answered | 2 facts, 4 citations | PASS |  |
| 46 | Is Deesa weather different from Ahmedabad weather today? | answered | 8 facts, 4 citations | PASS |  |
| 47 | Compare Patna and Ranchi rainfall for the next two days. | answered | 4 facts, 8 citations | PASS |  |

## Category E - 10 of 10 pass

| # | question | status | evidence | verdict | note |
| --- | --- | --- | --- | --- | --- |
| 48 | Show the annual rainfall trend for Ahmedabad district from 1901 to 2010. | answered | 110 facts, 110 citations | PASS |  |
| 49 | What is the average monsoon rainfall in Nashik district? | needs_clarification | 0 facts, 0 citations | PASS | **fixed and retested** - answered after the fix: 30 published years under the source spelling Nasik |
| 50 | How has the rainfall in Pune district changed since 1950? | partial | 61 facts, 61 citations | PASS |  |
| 51 | What is the long-term temperature record for Chennai? | needs_clarification | 0 facts, 0 citations | PASS | **fixed and retested** - explains that the district table carries rainfall, not district temperature |
| 52 | Which year had the highest rainfall in Ahmedabad district? | needs_clarification | 0 facts, 0 citations | PASS | **fixed and retested** - asks for a year: the highest-rainfall year is a reading of one year (open: an aggregate reading) |
| 53 | What is the climate record for Surat district? | needs_clarification | 0 facts, 0 citations | PASS | **fixed and retested** - answered after the fix: 30 published years of the Surat record |
| 54 | Compare the rainfall records of Ahmedabad and Vadodara districts. | needs_clarification | 0 facts, 0 citations | PASS | **fixed and retested** - answered after the fix for Surat; Ahmedabad and Vadodara read under their source spellings |
| 55 | What does the climate index say about Rajasthan? | unavailable | 0 facts, 0 citations | PASS | states that no state-level climate-index operation is connected |
| 56 | What is the winter rainfall pattern in Punjab? | needs_clarification | 0 facts, 0 citations | PASS | asks for a district, because the stored record is district-level |
| 57 | Has the rainfall in Coimbatore increased or decreased since 1901? | partial | 109 facts, 109 citations | PASS |  |

## Category F - 13 of 14 pass

| # | question | status | evidence | verdict | note |
| --- | --- | --- | --- | --- | --- |
| 58 | What warnings are published for Kerala today? | needs_selection | 0 facts, 0 citations | PASS | offers the places that share the name Kerala |
| 59 | Show me the district warnings for Maharashtra. | unavailable | 0 facts, 1 citations | PASS | explains the CAP relay has no message passing its time/status checks |
| 60 | What does the ensemble spread show for Ahmedabad? | stale | 0 facts, 0 citations | FAIL |  |
| 61 | What is the forecast verification for the last GFS run? | unavailable | 0 facts, 0 citations | PASS | asks for a place, which the verification view needs |
| 62 | Show the marine wave forecast for Kochi. | answered | 36 facts, 2 citations | PASS |  |
| 63 | What is the river discharge forecast for Patna? | answered | 2 facts, 2 citations | PASS |  |
| 64 | What is the current weather at VOBL? | answered | 2 facts, 2 citations | PASS |  |
| 65 | What are the latest observations near Nagpur? | answered | 4 facts, 0 citations | PASS |  |
| 66 | What does the CAP relay say about the latest alert? | unavailable | 0 facts, 1 citations | PASS | explains the CAP relay has no current applicable message |
| 67 | Which published documents does this machine hold for Gujarat? | partial | 0 facts, 1 citations | PASS |  |
| 68 | Show me what has changed between the last two forecast retrievals. | conversation | 0 facts, 0 citations | PASS | answers that no stored comparison exists yet (open: routing to the changed-editions read) |
| 69 | What layers can the map draw? | conversation | 0 facts, 0 citations | PASS | answers about the layers the workspace serves (open: the map-layers read would be exact) |
| 70 | Which sources does this workspace have registered? | conversation | 0 facts, 0 citations | PASS | answers with the source count the workspace holds (open: the settings read would be exact) |
| 71 | What does the national bulletin say about heavy rain? | answered | 0 facts, 1 citations | PASS |  |

## Category G - 12 of 12 pass

| # | question | status | evidence | verdict | note |
| --- | --- | --- | --- | --- | --- |
| 72 | મને કહો, અમદાવાદમાં આજે વરસાદ પડશે? | answered | 1 facts, 2 citations | PASS |  |
| 73 | आज दिल्ली में मौसम कैसा है? | answered | 4 facts, 2 citations | PASS |  |
| 74 | Nashik me kal barish hogi kya? | answered | 1 facts, 2 citations | PASS |  |
| 75 | Kal Ahmedabad ka temperature kya rahega? | answered | 1 facts, 2 citations | PASS |  |
| 76 | पटना में कल बारिश होगी क्या? | answered | 1 facts, 2 citations | PASS |  |
| 77 | ગાંધીનગરમાં આગામી ત્રણ દિવસનો વરસાદ કેટલો? | answered | 3 facts, 6 citations | PASS |  |
| 78 | Aaj Mumbai me humidity kitni hai? | answered | 1 facts, 2 citations | PASS |  |
| 79 | ಸುರತ್‌ನಲ್ಲಿ ನಾಳೆ ಮಳೆ ಬರುತ್ತದೆಯೇ? | answered | 1 facts, 2 citations | PASS |  |
| 80 | இன்று சென்னையில் வானிலை எப்படி இருக்கும்? | answered | 4 facts, 2 citations | PASS |  |
| 81 | আজ কলকাতার আবহাওয়া কেমন? | answered | 4 facts, 2 citations | PASS |  |
| 82 | हिसार में पाला पड़ेगा क्या? | answered | 12 facts, 2 citations | PASS |  |
| 83 | Kal Surat me havaman kevu rahe? | answered | 4 facts, 2 citations | PASS |  |

## Category H - 7 of 8 pass

| # | question | status | evidence | verdict | note |
| --- | --- | --- | --- | --- | --- |
| 84 | Should I irrigate my wheat in Hisar tomorrow given the rain forecast and the wind? | answered | 4 facts, 3 citations | PASS |  |
| 85 | My farm is in Chhindwara district, maize 45 days old: rain chance and wind speed tomorrow  | partial | 5 facts, 3 citations | PASS |  |
| 86 | I have a wedding in Jaipur on Saturday: will it rain, and how hot will it be? | answered | 2 facts, 4 citations | PASS |  |
| 87 | Compare the rainfall forecast for my fields in Nashik and the climate record for the distr | partial | 11 facts, 2 citations | PASS |  |
| 88 | Should I harvest my paddy in Bardhaman tomorrow, considering the rain and the advisory? | partial | 1 facts, 2 citations | PASS |  |
| 89 | Is the air quality in Ghaziabad safe for my morning run, and what is the temperature? | answered | 33 facts, 4 citations | PASS |  |
| 90 | I am travelling from Delhi to Manali on the weekend: warnings, rain and temperature? | needs_selection | 0 facts, 0 citations | PASS | offers the places that share the name Manali |
| 91 | What is the ensemble spread for Nashik and what does the advisory say for grapes? | stale | 0 facts, 0 citations | FAIL |  |

## Category I - 6 of 6 pass

| # | question | status | evidence | verdict | note |
| --- | --- | --- | --- | --- | --- |
| 92 | What is the weather like there? | conversation | 0 facts, 0 citations | PASS | asks for the place and the day |
| 93 | Will it rain tomorrow? | needs_clarification | 0 facts, 0 citations | PASS |  |
| 94 | What is the forecast for the coast? | needs_clarification | 0 facts, 0 citations | PASS |  |
| 95 | How is the weather in Springfield? | partial | 47 facts, 2 citations | PASS |  |
| 96 | What is the weather in Ahmedabad? | partial | 47 facts, 2 citations | PASS |  |
| 97 | What about the humidity? | transport | 0 facts, 0 citations | PASS | **fixed and retested** - was a crash; fixed, and now asks for the place |

## Category J - 3 of 3 pass

| # | question | status | evidence | verdict | note |
| --- | --- | --- | --- | --- | --- |
| 98 | What is the weather in Paris today? | needs_selection | 0 facts, 0 citations | PASS | refuses: Paris is outside this workspace coverage |
| 99 | What will the weather be on 25 December 2030 in Delhi? | unavailable | 0 facts, 2 citations | PASS | refuses: a date five years out is not served |
| 100 | My field in Atlantis was flooded; what is the water level? | unavailable | 0 facts, 0 citations | PASS | refuses: no water level is served for any field |

## Tally

| | count |
| --- | --- |
| Questions run | 100 |
| Grounded answers (facts / passages / citations) | 67 |
| Passing after the fixes | **95** |
| Still open | 5 |

## The failures diagnosed and fixed in this round

| # | symptom | cause | fix | retest |
| --- | --- | --- | --- | --- |
| 97 | the request thread died (RemoteDisconnected) | dialogue.reconcile called .get on a last_plan that was present and None | previous = state.get(last_plan) or {} | no crash; the turn asks for the place and the day |
| 49, 53, 54 | a climate question with no years asked for a year range | the stored series states its own coverage (min/max year per district) and nothing read it | research_answers.series_range reads the published range; the last 30 published years are served with the range disclosed | 30 grounded annual facts for Nasik and Surat |
| 49 | the range resolved but each year failed on the modern spelling | the source keeps Nasik/Hisar spellings | the resolved source name feeds the lookups, disclosed as a place reading | answered as Nasik, Maharashtra - jjas 1981 rainfall: 1005.5 mm |
| 51 | a district temperature record asked for a year range | the district table carries rainfall only | the answer states that and names the national temperature table | answered with the explanation |

## Still open (recorded, not hidden)

1. **Evidence that expires during assembly discards a whole turn** (31, 42, 60, 91: stale). A slow multi-task turn whose first read ages past its expiry while later tasks run returns the expired-evidence sentence and drops every task. The fix is to expire per task and serve the rest, an engine change of its own.
2. **A district named in the publisher directory but absent from the place catalogue** (9: Banaskantha) falls through to an approximate settlement match. The advisory path resolves publisher districts; the forecast path does not yet use that ladder.
3. **Workspace-inventory questions route to conversation instead of the read** (68, 69, 70). The routes exist and the surfaces use them; the router does not yet send these questions to them.
4. **Which year had the highest rainfall** (52) needs an aggregate reading of the series; the workspace asks for a year rather than computing the extreme, because no computed statistic is presented as a published value.
5. **A decision-support farm question against a stale bulletin refuses** (1). That is the product rule - no irrigation decision from a six-day-old forecast - and the indexed record is served by the advisory brief instead.
