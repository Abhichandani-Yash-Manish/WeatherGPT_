# The product, walked through: thirteen journeys, what a user gets, and what is still slow — 15 September 2026

This is the round where the work is judged as a product rather than as an engine. Thirteen journeys were run
against the live workspace, the first-run screen was rebuilt around what this build does best, and the results
were recorded. Eleven of thirteen answer, one asks an honest question back, and one states that the product it
would need is not connected.

## What a user gets in five minutes

1. Open the workspace. It shows the working place (Ahmedabad by default), the published district warning days,
   and a composer that asks *What is it like right now in Ahmedabad?*
2. Ask it. The answer leads with the freshest station report (name, distance, age), then the published district
   day with its issue instant and source, then the next six model hours, then one line listing what is not
   connected (radar and satellite imagery, sub-hourly refresh, push).
3. Follow up in the same conversation: *and what about the afternoon?* — the place and day are kept, only the
   window changes.
4. Ask *Is any warning in force for Patna, Bihar today?* and use **Write the alert brief** in the answer's
   actions: the drawer shows the district, the day, the hazards as published, the issuer and retrieval
   instants, the CAP relay reported separately, and the limits — with **Save to briefcase**.
5. Ask *What does the Ahmedabad district agromet advisory say for cotton?* and use **Write the advisory brief**:
   the edition read, the passages quoted, the conditions the source itself names, the forecast kept apart, and
   the non-prescription limits.
6. Put the artefact somewhere: the Briefcase lists kept briefs, exports Markdown, and **Write a briefing for the
   working place** writes a dated briefing into the local series and shows it with its change reading.

## The thirteen journeys, measured

| Journey | Status | Evidence returned | Time |
|---|---|---|---|
| What is it like right now in Ahmedabad? | answered | 6 observed facts + day + 6 hours | 146 s cold, 3 s warm |
| What is it like right now in Kochi? (shared name) | answered | 6 facts, Kerala resolved and disclosed | 3.5 s |
| Will it rain in Ahmedabad, Gujarat tomorrow morning? | answered | 1 forecast fact | 1.4 s |
| कल अहमदाबाद, गुजरात में सुबह बारिश होगी? | answered | 1 fact, same window as the English ask | 0.1 s |
| અમદાવાદમાં આવતીકાલે સવારે વરસાદ થશે? | answered | 1 fact, same window | 0.1 s |
| Is any warning in force for Patna, Bihar today? | answered | 5 warning facts, bulletin identity | 67 s cold |
| What does the Ahmedabad district agromet advisory say for cotton? | answered | 5 published passages | 11 s |
| Kya main Ahmedabad me cotton me irrigation kar sakta hoon is hafte? | **partial** | 4 passages + *growth stage is not yet supplied* | 40 s |
| What does the latest all India weather bulletin say about heavy rainfall? | answered | 10 passages with saved PDFs | 0.5 s |
| Show the annual rainfall trend for Ahmedabad district, Gujarat from 1981 to 2010. | answered | 30 values + chart + trend calculation | 0.7 s |
| What are the wave conditions off Kochi tomorrow? | answered | 24 model hours, place decided by the product | 8.8 s |
| What is the current weather at VOBL? | answered | 2 observed airport facts | 2.1 s |
| What is the tide at Kochi tomorrow? | **unavailable** | the gap answer: tide is not connected | 0.0 s |

Recorded in `research/implementation/product-review-20260915/journeys.json` with the packets' own numbers.

## What the review changed

| Found | Changed |
|---|---|
| The first-run screen sold a weather chat: rain, probability, trend, airport | It now leads with what this build does best — right now, today's published warning, the farm advisory, a trend, an airport report — and the composer asks the right-now question |
| The welcome implied more is connected than is | One honest line naming radar and satellite imagery, sea-area and coastal bulletins, flood extent and delivery as *not* connected, and one naming what is answering and how to add a key |
| Two cold reads are slow: the station layers on first ask (146 s) and the district warning layer (67 s) | Recorded as a known limit rather than smoothed over; warm reads are 0.1–11 s |

## What is still not product-grade

- **Cold-start latency.** First reads of the station and warning layers take 67–146 seconds on this machine. Warm
  reads are fast, and there is no progress bar beyond the engine's own stage readout; a user on a slow link will
  notice. Caching and per-source timing are the obvious next work.
- **No hosting, no accounts, no mobile.** The surface is a loopback desktop page by the user's own instruction;
  sharing is on hold, and mobile and screen-reader acceptance are untested.
- **Coverage is uneven.** District agromet editions are broad (571 districts), state editions are five, and
  national products hold one edition each; a question about a state edition that is not held gets an honest
  absence, not an answer.
- **Two of five promised PS features have unconnected parts**: radar/satellite imagery, sea-area and coastal
  bulletins, flood extent, and any form of delivery or push.
- **No native-speaker review** of the Hindi, Gujarati and other rendered output, and the free-model ranking
  stays a stated judgement until a valid OpenRouter key is probed.

## Evidence

`research/implementation/product-review-20260915/`: `journeys.json` (the table above with statuses and timings),
`first-run-welcome.png` and `welcome-first-run.json` (the rebuilt first-run screen and the starters it offers).
The chat-surface evidence in `research/implementation/chat-surface-20260915/` carries the alert-brief, advisory
and settings screenshots from the same workspace.
