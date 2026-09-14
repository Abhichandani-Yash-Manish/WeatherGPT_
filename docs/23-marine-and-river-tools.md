# Marine wave and river discharge tools — 14 September 2026

Two specialist adapters that existed only behind the command line are now answerable in conversation. This follows step three of [the critical full-solution review](21-full-solution-critical-review.md), which asks for marine and river chat built on the existing adapters and verified cell identities. It adds two bounded model products. It does not add official marine or flood warnings, observed gauges, or any operational clearance. Desktop work continues; hosting and sharing remain on hold.

## What changed

**Marine waves.** “How high will the waves be off Chennai tomorrow afternoon?” now returns significant wave height, and wave direction or period when asked, for the sea grid cell the provider selects. The request travels through the same governed ingestion pipeline as the land forecast: fixed request contract, hash-checked raw payload, values rebuilt from those bytes before use, and the existing 50 km sampling guard. Because the guard applies, marine values are served only where a sea cell lies near the named place; an inland place is reported as having no verified sea cell rather than being answered from a distant one. The answering cell and its distance are named in the answer and recorded with the citation.

**River discharge.** “What is the modelled river discharge near Patna tomorrow?” returns GloFAS daily discharge for the selected river cell. Each value covers a whole UTC calendar day, which is stated, because it does not align with an Indian calendar day.

**Neither product is allowed to stand in for a different quantity.** This mattered immediately. Asked for “the water level of the Ganga at Patna”, the planner rewrote the request as `river_discharge` — the one hydrological parameter it knows. A prompt instruction did not prevent it. A deterministic check on the user's own clause now refuses the request, names the quantity that was asked for, and makes no source call. The same applies to danger and warning levels, flood extent, tides, sea currents and sea-surface temperature. When a clause asks for both a supported and an unsupported measure, the supported one is answered and the gap is stated separately.

**Place resolution for point products.** A district named in a marine or river request is now resolved to a settlement point, as it already was for forecasts, instead of asking which village inside the district to use. Saying “district” explicitly still keeps the district reading.

**One status-fidelity fix.** A single task whose window lies in the past reported `outside_validity`, but the response as a whole was downgraded to `unavailable`, which reads as a missing source rather than a window the user can correct. A response whose tasks are all `outside_validity` now keeps that status.

Implementation: `weathergpt_data/specialist_tasks.py` (new), `point_tasks.py`, `task_dispatch.py`, `capabilities.py`, `dialogue.py`, `adapters.py`, `foundation.py`, `language.py` and `data/registry/point-tool-policy.json`.

## Acceptance evidence

Evidence directory: [specialist-tools-20260914](../research/implementation/specialist-tools-20260914/).

- **374 automated tests pass** (362 before), including twelve new ones covering wave and discharge retrieval, the answering cell and its distance, UTC day handling, the substitution refusals, the parameter fallback rule, past windows, distant cells, district resolution and task-level evidence ownership beside a land forecast.
- **Nine recorded local-model HTTP turns** against the live provider endpoints: two answered, one unavailable, four needing place selection, two needing clarification.
- Chennai returned **0.52 m** significant wave height across six hourly samples from sea cell **13.125, 80.375015**, recorded **11.243 km** from the requested point.
- A selected place named Patna returned **10.56–11.19 m³/s** across two UTC daily values from cell **25.075005, 83.375**.
- The water-level request was refused with its distinct quantity named, and no source call was made. An earlier probe, taken before the clause check existed, shows the planner's renamed parameter being accepted; both are kept.

## What remains open

- No named sea area or river basin identity. The official sea-area and coastal bulletins (S58, S59) remain unconnected, so no official marine warning exists in chat.
- The river cell is not matched to a named river, reach or gauge. A discharge value cannot be compared with a gauge reading or a published danger level, and no flood forecast is implied.
- Observed water levels, danger thresholds, inundation extent, tides, currents and sea-surface temperature are refused, not supplied.
- Only `lookup` is supported for both products. No trend, comparison or timeline operation exists for them.
- No marine or hydrological domain review has taken place, and no forecast skill is measured for either product.
- Coastal and riverside place ambiguity is unchanged; several probes correctly ended in place selection rather than an answer.
- Everything the previous batch left open — official warnings and observations, historical aliases, agricultural depth, concurrency, voice, mobile and language output — is untouched here.
