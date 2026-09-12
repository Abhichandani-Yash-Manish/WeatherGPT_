# Conversational recovery: audit, implementation and measured results

12 September 2026. The user's assessment was correct: the previous implementation protected a small numeric contract but was not a usable natural-language product. Passing its 194 tests did not establish that people could get answers to ordinary questions. The main missing piece was orchestration between language, location, available tools, acquisition and response—not a shortage of vector embeddings.

This batch implements a local Ollama language layer, structured retrieval, automatic bounded forecast acquisition, place clarification, conversation follow-ups and cited responses. It preserves the deterministic numerical engine and original operational holds.

## Start and use the actual conversational entry point

```sh
python3 scripts/start_weather.py
```

Open [WeatherGPT](http://127.0.0.1:8765) and reload any older tab. The launcher starts installed Ollama if needed and then runs the loopback workspace. This machine already has `qwen3.6:latest`; that is the selected model. No model was downloaded or API credits purchased. The initial configured gateway test returned HTTP 402, so runtime model calls use local Ollama only.

Try these ordinary questions:

- “Will it rain in Ahmedabad, Gujarat tomorrow morning?”
- “And tomorrow afternoon?” in the same conversation.
- “What was Ahmedabad district rainfall in 2010?”
- “What was the rainfall in Kendrapada, Odisha in 1920?”
- “What will the weather be like in Khonoma tomorrow morning?”
- “અમદાવાદ, ગુજરાતમાં કાલે સવારે વરસાદ પડશે?”

Ahmedabad without a state has multiple source matches. Confirm the Gujarat candidate; the next question can refer to the same place. An approximate spelling match always needs confirmation, even when only one suggestion is returned. Missing places require another spelling, district/state or a pin, rather than substitution with a nearby city.

The terminal now has the same natural-language path:

```sh
python3 -m weathergpt_data chat "What was Ahmedabad district rainfall in 2010?"
```

Use `--json` for the full evidence packet, `--conversation-id` for a follow-up and `--selection-id` for a returned place choice. The older `answer`/`rag-context` commands remain exact, read-only internal tools. The new web UI uses **`POST /api/chat`**; evaluating only `AnswerService` still evaluates the old low-level grammar, not the new product path.

## What now happens for a question

1. Ollama extracts a validated plan: intent, places, interval, variables, historical period and missing context. It cannot provide executable SQL, endpoint URLs or coordinates.
2. Place names search a local GeoNames index. Coordinates come from a source record or an explicitly supplied pin. The model's invented state/district qualifiers are removed unless supported by the conversation or source-backed script aliases.
3. Historical requests call the existing typed national/district lookup tools. Forecast requests first check the existing store; missing, stale or insufficient evidence can trigger a targeted collection under the existing request budgets, leases, retry timing and source policy.
4. Calculations remain deterministic. Rain totals use complete source accumulation intervals; other variables report ranges of hourly samples. A longer request is partitioned into explicitly labelled intervals; unavailable portions remain missing.
5. Local synthesis explains the retrieved facts. The response retains facts, citations, assumptions, missing capabilities, model/lookup traces and expiry. Model-generated measurements are checked against source numbers, units and evidence IDs. A rejected synthesis falls back to the deterministic answer. This is useful checking, not proof of full semantic faithfulness.
6. Conversation state persists locally, including the previous question, accepted plan and pending place choices. A choice is bound to its question. Multi-endpoint clarification retains both endpoints.

This is retrieval-augmented answering over structured evidence. Numerical records are not embedded in place of SQL/calculation. There is no unrestricted document index, external embedding service or general-purpose research crawler.

## Audit against the user's eleven findings

| Finding | Repair or current disposition | Remaining limit |
|---|---|---|
| F01 rigid grammar | Real local model planning, ordinary questions, explicit defaults and follow-ups now precede the numeric tools. The new UI/CLI use this route. | Model interpretation remains fallible; coverage and semantic evaluation need expansion. |
| F02 brittle keyword routing | Semantic intent extraction distinguishes warning plurals, flooded-road travel and sowing questions. Six separate wording checks reached the expected intents. | This measured subset is not universal paraphrase/language coverage. |
| F03 missing village/small-town resolver | Downloaded and indexed the GeoNames India extract: **660,026 features**, **549,021 source settlement records**, **581,131 normalized name/alias records**. Exact and approximate matches have distinct behavior. | Missing names and duplicate/spelling-variant places remain. Counts are not an official village denominator or proof of complete coverage. |
| F04 names/types | Search retains source IDs, place/admin distinctions, source modification dates and state/district labels. Approximate names require confirmation; source-backed state aliases handle scripts. | GeoNames is not a reviewed LGD crosswalk or historical boundary equivalence. A district cannot silently become a city forecast. |
| F05 probability absent | Recognizes probability requests and separates available modeled rainfall amount from unavailable probability. | No probability adapter/calibration was added. Such requests remain partial, not completed percentage answers. |
| F06 route feasibility | Recognizes travel and can retrieve weather for separately resolved endpoints; preserves route/closure limitations. | Endpoint weather is not route-segment coverage, live service status, road opening or safety clearance. |
| F07 agriculture | Recognizes crop questions and requests crop/stage/activity or symptom context, with weather evidence when applicable. | No validated crop diagnosis, pesticide dosage or field-operation recommendation. Advisory applicability remains open. |
| F08 research disconnected | Natural requests reach national rainfall/temperature and historical district rainfall. Ahmedabad 2010 returns **1096.8 mm**; national 2024 rainfall returns **1206.6 mm**. | Daily dry spells, arbitrary new datasets and unavailable years are still unsupported. |
| F09 demographic/environmental datasets | Gives a domain-specific coverage explanation instead of forecast syntax. | No demographic/groundwater/soil/quality pipeline was invented. Several of these asks extend beyond the PS's direct weather/climate requirements. |
| F10 local languages | Ollama interprets tested Hindi/Gujarati questions. Forecast values use controlled Hindi/Gujarati wording after a real Gujarati synthesis error was found. | Fluent human review, other languages, general multilingual dialogue and voice remain open. Do not treat numeric agreement as translation validation. |
| F11 research metadata | Distinguishes unknown district, unsupported range, missing year and absent value. New response metadata references the prior full source audit and compares the relevant source hash; legacy index status is explicitly historical. | Source transcription agreement does not resolve rights, missingness, homogeneity or current-boundary compatibility. |

## Further problems found and repaired during this batch

- A model-generated state could hide a same-name settlement in another state. State qualifiers now require textual/source-alias support; otherwise users see the ambiguity.
- Resolving the first ambiguous endpoint initially dropped the second. Pending plans now retain separately resolved endpoints across selections.
- A seven-day request could exceed the provider's seven UTC-calendar-day window and raise an API error. It now preserves available periods and reports the missing portion.
- A numeric guard initially considered numbers in the user's question as allowable evidence. Those numbers are now excluded: a request to invent `9999 mm` does not authorize that value. Measurement-unit pairs are also checked.
- Partial answers with some complete variables could bypass a failed-refresh hold. Each admitted subset now additionally requires healthy snapshot status; stale/degraded values stay outside synthesis.
- The model produced an incorrect Gujarati qualification despite preserving the number. Controlled forecast wording now replaces unrestricted Hindi/Gujarati forecast synthesis. This avoids claiming that a prompt alone validates translation.
- Place-database mutation after initial verification is now rejected. Gazetteer builds publish a complete database atomically and do not leave a partial final database after invalid input.

## What the tests actually establish

The attachment is **truncated during IN-026**, ending with “126 KB left”. Its linked scenario JSON and results directories were not supplied in this workspace. Therefore this batch does **not** claim to rerun the missing 111-case suite or the 84 natural questions in full. The report excerpt is preserved in the review directory.

The initial live evaluation ran the **26 included questions plus 10 additional authored questions**, against the actual local model and current-clock data paths. Its measured results were:

| Initial live outcome | Count |
|---|---:|
| Answered | 6 |
| Partial | 5 |
| Place selection required | 13 |
| Other targeted clarification | 8 |
| Unavailable | 3 |
| Error | 1 |
| Responses containing numeric evidence | 10 |
| Old generic forecast-format responses | **0** |

These results are retained unchanged in [the initial summary](../research/reviews/conversational-recovery-20260912/live-evaluation/summary.json). Clarification and partial evidence are **not** counted as completed tasks. Current-clock results also cannot be treated as a forecast-accuracy comparison with the user's earlier replay clock.

The error and Gujarati state-matching issue were then repaired. Separate [HTTP journeys](../research/reviews/conversational-recovery-20260912/final-journeys/) demonstrated:

- Ordinary question → ambiguous place choices → confirmed Ahmedabad → grounded morning answer.
- “And tomorrow afternoon?” → retained location and a different, grounded interval.
- Gujarati query with Gujarat → retrieved forecast; its initial free-form translation was subsequently replaced by controlled wording.
- Aizawl week request → available forecast periods and an explicit partial result, with no exception.
- An adversarial request to invent rainfall/warnings → retrieved values or a deterministic fallback, not the requested invented number.
- Kendrapada/Orissa historical lookup → published value with the existing discrepancy flags.
- Crop-symptom request → relevant context/diagnostic limitation rather than weather syntax.

After the final code restart, [four fresh HTTP checks](../research/reviews/conversational-recovery-20260912/final-code-checks/summary.json) all returned `answered`: controlled Gujarati forecast, English morning forecast, retained-location afternoon follow-up, and the Ahmedabad 2010 historical lookup. Measured response times were 7.24, 8.92, 8.46 and 3.27 seconds respectively. The tested 13 September forecast windows returned 3.5 mm in the morning and 11.0 mm in the afternoon; these are timestamped model outputs, not observed rainfall or a scientific accuracy result. The final Gujarati response no longer contains the earlier erroneous qualification.

**213 automated tests pass**: the existing 194 plus 16 conversation/grounding regressions and three gazetteer integrity/identity tests. These deterministic tests are separate from the live model checks. The code also passes Python compilation, JavaScript syntax validation and registry checks. The registry now has **61 entries**; no official weather or specialist operational readiness was promoted.

Browser visual/click-through QA remains unverified. The prior browser attempt failed admin-policy verification, and no browser interaction tool is callable in this turn. The local HTTP application and actual chat endpoint were exercised; that does not establish visual/mobile quality. No bypass was attempted.

## Sources and running costs

GeoNames publishes country extracts, including source names, aliases, coordinates, feature types, administrative labels and record modification dates, under CC BY 4.0. Attribution and the “as-is” limitations are retained. Runtime lookups are local, not a public geocoding API workload. [GeoNames extract documentation](https://download.geonames.org/export/dump/readme.txt).

Ollama's local chat API supports JSON-schema constrained responses; the application also validates the returned plan before dispatch. No schema or model prompt is treated as proof of factual correctness. [Ollama structured-output documentation](https://docs.ollama.com/capabilities/structured-outputs).

We investigated Nominatim's policy but did not integrate or call its public search endpoint. No bulk public geocoding workload was created. New forecast calls use the existing governed Open-Meteo pathway. The local model consumes this machine's memory/compute; there is no recurring automation, paid API fallback or deployment.

## Next acceptance work

The immediate product target is now measurable: ordinary questions and useful clarification journeys across declared places, with source-correct answers. Prioritize completion quality and wrong-answer detection over the number of registry rows or unit tests.

1. Validate more held-out questions, selected places and multi-turn corrections; include fluent Hindi/Gujarati reviewers and browser/mobile checks.
2. Add a separately sourced and validated probability contract before percentage answers.
3. Complete official warning time/lifecycle and dated administrative mapping work, then retrieve applicable warnings through the same conversation layer.
4. Review contextual advisory extraction before crop-specific recommendations; keep travel closures and marine/aviation briefing evidence separate.
5. Measure sustained source freshness, latency and footprint before scheduling broader ingestion. Preserve all R01–R12 items in the living checklist.
