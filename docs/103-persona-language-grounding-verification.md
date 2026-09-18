# Persona and language grounding verification

18 September 2026. Twenty-four questions across four reading positions and seven languages were put through the
**real conversation engine** on loopback, and every answer was checked for three things: who answered it (the
model or a typed renderer), where each value came from (the configured reads), and whether the reader's
language and role were honoured.

Raw records: `tmp/qa/persona-language-results.json` (24 turns), `tmp/qa/ai100-results.json` (the earlier
100-question run), `tmp/qa/shots/` (captures).

## 1. What "from the model" and "from integrated data" mean here, measured

| layer | who produced it | evidence |
| --- | --- | --- |
| The plan for every turn | **the model** — `deepseek-chat`, the provider configured in this machine's local backend configuration under the `deepseek_first` policy | `trace.planning = {provider: deepseek, model: deepseek-chat, planner_policy: model}` on **24 of 24** turns |
| The numbers | **typed task renderers** — the value is placed into the sentence by the code that read it, so a number cannot drift in prose | `trace.generation.provider = typed_task_renderers` |
| The prose of a narrative or point answer | **the model** | `trace.generation.provider = deepseek` on the three control turns |
| A non-English rendering | **the gated translation layer** — deterministic translation with a post-translation invariant check over numbers, units, dates, places and negations; a failed check keeps the source-language sentence | `trace.generation.provider = gated_translation`, `language_adherence = rendered_with_protected_values` |
| Every fact | **a governed source read** | each fact carries `source_id`, and a point or day total carries its `source_locators` (e.g. 24 hourly indices) |

So the model **plans and writes**; it does not supply values. That is the architecture the workspace claims,
and it is what the trace shows on every turn.

## 2. The matrix

| # | role | language | question (short) | status | planner | writer | facts | script | invented |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | farmer | en | rain over my cotton field, next two days | partial | deepseek | deepseek | 2 | — | 0 |
| 2 | farmer | hi | वही प्रश्न, हिंदी में | answered | deepseek | verified_fact_renderer | 2 | devanagari | 0 |
| 3 | farmer | gu | વરસાદ પડશે? | partial | deepseek | typed_task_renderers | 2 | gujarati | 0 |
| 4 | farmer | hi-Latn | Hinglish, roman script | answered | deepseek | gated_translation | 2 | latin | 0 |
| 5 | farmer | mr | पाऊस पडेल का? | partial | deepseek | gated_translation | 2 | devanagari | 0 |
| 6 | district officer | en | current official warnings for Patna | answered | deepseek | typed_task_renderers | 2 | — | 0 |
| 7 | district officer | hi | आधिकारिक चेतावनी | partial | deepseek | typed_task_renderers | 2 | devanagari | 0 |
| 8 | district officer | bn | সরকারি সতর্কতা | partial | deepseek | typed_task_renderers | 2 | bengali | 0 |
| 9 | district officer | en | what changed since the previous edition | needs_clarification | deepseek | typed_task_renderers | 0 | — | 0 |
| 10 | traveller | en | nearest airport to Ahmedabad | needs_clarification | deepseek | typed_task_renderers | 0 | — | 0 |
| 11 | traveller | hi | हवाई अड्डा रिपोर्ट | needs_clarification | deepseek | typed_task_renderers | 0 | devanagari | 0 |
| 12 | traveller | gu | એરપોર્ટ શું જણાવે છે | needs_clarification | deepseek | typed_task_renderers | 0 | gujarati | 0 |
| 13 | traveller | ta | அடுத்த சில மணிநேரம் | answered | deepseek | gated_translation | 4 | tamil | 0 |
| 14 | traveller | en | next few hours in Manali | needs_selection | deepseek | typed_task_renderers | 0 | — | 0 |
| 15 | researcher | en | published district series, Nashik | answered | deepseek | typed_task_renderers | 30 | — | 0 |
| 16 | researcher | hi | प्रकाशित वर्षा श्रृंखला | answered | deepseek | gated_translation | 30 | devanagari | 0 |
| 17 | researcher | en | archived runs vs the reanalysis | answered | deepseek | typed_task_renderers | 56 | — | 0 |
| 18 | researcher | en | editions held, passages about Surat | answered | deepseek | typed_task_renderers | 0 (1 passage) | — | 0 |
| 19 | researcher | en | ensemble spread, Nashik | answered | deepseek | typed_task_renderers | 144 | — | 0 |
| 20 | none | en | rain in Nashik, next three days | answered | deepseek | **deepseek** | 3 | — | 0 |
| 21 | farmer | en | the same question | answered | deepseek | **deepseek** | 3 | — | 0 |
| 22 | researcher | en | the same question | answered | deepseek | **deepseek** | 3 | — | 0 |
| 23 | district officer | te | హైదరాబాద్‌లో నేటి వాతావరణం | answered | deepseek | gated_translation | 4 | telugu | 0 |
| 24 | traveller | kn | ಬೆಂಗಳೂರಿನಲ್ಲಿ ಮಳೆ | partial | deepseek | typed_task_renderers | 6 | **english** | 0 |

"script" says whether the answer was in the script the reader asked for. "invented" is the count of numbers in
the prose that appear nowhere in the returned payload — re-run against **every** returned field, which is the
honest form of the check; the first pass compared only four fields and flagged fragments of ISO timestamps
(`04`, `12`, `30.`, `00.`), which the corrected check clears.

## 3. The value-level proof (not just "the number is in the payload")

The engine's day total for Ahmedabad, 20 September 2026, was **7.4 mm**, cited to source **S21 "GFS forecast
delivery"** with **24 source locators** (`$.hourly.precipitation[68]` … `[91]`).

The cited product URL was then re-read directly and the **24 cited hours summed**: **7.4 mm** — an exact match
against the configured source, hour by hour. Nothing was invented, and the locators are precise enough for a
reader to repeat the sum.

One disclosure worth recording: the same day read from the **S62 extended forecast** hourly series sums to
0.8 mm. These are **two different configured forecast products**, not a fabrication — the day-total answer names
its own product in prose ("Source: GFS forecast") and in its citation, and the Forecast surface carries its own
source. The workspace does not claim the two are the same run, but it also does not cross-state them, so a
reader comparing the surface with the assistant will see two numbers. Recorded as an open disclosure item.

## 4. The reading positions

The catalogue had three positions (farmer, district officer, traveller). The brief that asked for this
verification names **farmers, civilians and researchers**, so a fourth position was registered:
**Researcher or analyst** — the record rather than the moment: the published district series, archived runs and
their verification, the observation network, and the editions this machine holds; six surfaces; its own three
starters; and two limits it keeps in view (a trend describes the published series and is not a forecast; a run
compared with reanalysis measures that comparison, not future skill). Its check passes and the selector, which
reads the catalogue from the API, offers it without a frontend change.

**The control experiment.** The same question — "Is rain expected in Nashik in the next three days?" — was put
under no position, under farmer, and under researcher. All three were **model-written** (`deepseek`), all
three carried the same three rainfall facts from the same source, and the prose differed in framing only.

**The variance it exposed.** On the farmer turn the planner chose the window 18–21 Sep while the other two
turns chose 19–22 Sep: the *same question* retrieved a **shifted, still-defensible** window, because the plan
comes from a model and "the next three days" has two readings at 02:00 IST. Two consequences are recorded
rather than hidden:

1. An identical question can retrieve a different window between turns.
2. The window a model-written narrative states is **not** among the fields the prose validator checks (it
   checks numbers, units, place and evidence ids), and one turn's third window came out as
   "20 Sep 2026 03:30-21 Sep 2026 00:30" — a pair that appears in no read. The values were grounded; the
   window label was the model's.

## 5. Languages

23 languages are listed with declared support kept apart from measured support, and the selector labels the
four whose writing is not measured (`mni`, `sat`, `sd`, `ta`).

| language | requested | rendered | state recorded |
| --- | --- | --- | --- |
| English | 13 turns | answered | `not_applicable` (no rendering needed) |
| Hindi | 4 | in Devanagari | `written_in_requested_script` / `gated_translation` |
| Gujarati | 2 | in Gujarati script | `written_in_requested_script` |
| Marathi | 1 | in Devanagari | `gated_translation` |
| Bengali | 1 | in Bengali script | templated, values intact |
| Tamil | 1 | in Tamil script | `rendered_with_protected_values` (gated translation) |
| Telugu | 1 | in Telugu script | `rendered_with_protected_values` |
| Hinglish (hi-Latn) | 1 | romanised | `gated_translation` |
| **Kannada** | 1 | **English** | `values_did_not_survive` — the gate refused the rendering because a protected value (`8.62 km`) came back duplicated, so the source-language answer was kept |

The Kannada case is the gate working as designed: a partly rewritten answer is never shipped. But the reader
was **not told**: the engine's sentence ("This answer was not rewritten in the requested language because some
of its values did not survive the rendering intact…") was in the payload, and the card looked only for the one
wording "output language could not be rendered", so it matched none of the other five downgrade states.

**Fixed in this batch:** the card now reads the structured state (`language_adherence`) and falls back to the
engine's own sentence, covering `values_did_not_survive`, `rendered_in_another_script`, `render_failed`,
`no_language_service`, `language_service_unavailable` and `unverifiable_script`. A check reproducing the Kannada turn is in `frontend/src/chat/chat.test.tsx`, the built bundle served to the browser carries the new sentence (`web/dist/assets/main-*.js`), and the researcher position is returned by `/api/personas` on the running server. The browser-level capture of that card was **not** completed in this pass: the harness waits on the surface's own reply marker and the Kannada turn, which runs the translation gate, outlasted it. The unit check and the served bundle are the evidence recorded here; the browser capture stays open.

## 6. What this does not claim

- It is 24 turns plus the earlier 100, not a language or accuracy certification.
- Kannada, Bengali, Telugu and Hinglish were exercised once each; the states recorded are the engine's own.
- The model was **not** asked to be the source of any value, and the checks above are what keeps that true;
  a provider outage changes the prose, never the numbers.
