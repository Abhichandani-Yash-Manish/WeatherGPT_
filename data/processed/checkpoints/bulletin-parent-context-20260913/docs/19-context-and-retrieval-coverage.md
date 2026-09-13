# Context and retrieval coverage — 13 September 2026

This batch repairs reproduced conversation failures and expands inspected agricultural evidence. The current local app is at http://127.0.0.1:8765. Reload an older tab. Hosting/sharing remains on hold. This is a scoped engine improvement, not nationwide or operational acceptance.

## What changed for the user

| Request | Reproduced failure | Current behavior |
| --- | --- | --- |
| “Can I spray tomorrow?” → “Ahmedabad, Gujarat” → “cotton” → “flowering stage” | Lost missing-field context; sometimes HTTP 400 or a generic forecast substituted for the activity question | Keeps tomorrow and the district, fills only the pending crop/stage, retrieves cotton source passages, and leaves field suitability explicitly unresolved |
| Cotton **and** groundnut pests in Ahmedabad | Duplicate-clause guard rejected two crop tasks | Each explicitly named crop has its own retrieval task and passage attribution |
| “Show all the matching passages, not just three.” | Repeated the same three excerpts | Returns all four matching indexed groundnut passages, including the page-four continuation |
| “Not rice, maize at sowing stage.” | Needed protection against treating a negated crop as a positive request | Preserves district, replaces rice with maize, and filters on sowing |
| Cotton **and** wheat in Ahmedabad | Needed an explicit incomplete-task check | Returns cotton passages and separately reports no indexed wheat match; overall status is partial |
| A source advisory followed by a general explanation task | The general branch copied already accumulated passage metadata | General explanation no longer inherits another task's passages, retrieval coverage or pending fields |

Literal pending-field replies and the bounded “show all passages” command use no model call. Extra clauses and ambiguous targets still go through normal planning. A small explicit activity grammar protects questions such as “Can I spray tomorrow?” from becoming weather-only requests; it is not a claim of universal intent recognition. Crop recognition and negation guards cover a bounded vocabulary, not arbitrary language.

“All” means all matching **indexed** passages, not every relevant statement in the original PDF. The response reports matched/returned/omitted counts. A 20-passage limit protects a single response; exceeding it produces a partial result with an explicit omitted count. Whole-document context and pagination remain further work.

## What was actually verified

[Acceptance summary](../research/implementation/context-and-retrieval-20260913/acceptance.json) and [replay script](../research/implementation/context-and-retrieval-20260913/verify_acceptance.py):

- **18 real HTTP turns on the standard app port**, with Ollama: 7 answered, 5 partial, 2 needs clarification, 1 needs place selection, 3 unavailable. These are different outcomes, not 18 fully answered questions.
- **26 displayed passage instances** re-extracted from saved originals and compared for text, crop, stage, page, document identity and citation binding.
- **50 hourly forecast values** replayed against original JSON, including parameter, unit and interval endpoints. The full-day probability request remains partial where the source cannot cover the exact requested IST interval; the evening follow-up answers its supported interval.
- Three cited PDF downloads returned HTTP 200 and exactly matched their recorded SHA-256 hashes. The route opens the saved edition, not a changing publisher URL.
- **340 automated tests passed**, including 21 new tests for this batch. These test contracts and regressions; they do not establish forecast skill, ranking recall or agronomic validity.
- Recorded median turn latency: **5.68 seconds**, maximum **15.4 seconds**. The first crop retrieval after restart took 8.7 seconds; subsequent stage and all-passages replies took roughly 0.9 seconds. This small local sample is not a load or latency benchmark.

The final HTTP set also checks the original Hinglish rain-probability question, “Gujarat wala”, “aur shaam ko?”, a mixed forecast/advisory request, a changed district and unsupported evidence. No passage from the advisory task appears under the forecast task.

The initial failures are preserved in `baseline/`. `iteration-1/`, `iteration-2/` and `acceptance-pre-routing/` preserve intermediate results, including a repeat run where the model misclassified the spraying question. The final result is in `acceptance-final/`; passing reruns do not erase earlier failures. Broader adversarial and held-out semantic evaluation is still needed. Browser automation remains blocked by the existing tool policy; browser interaction and visual QA are not asserted by HTTP tests.

## Broader source inspection

The original IMD directory/selection adapter, request budgets, raw evidence store, pinned local multilingual E5 embeddings and hybrid retrieval index are reused. No new account or paid API was required. [Source review](../research/implementation/context-and-retrieval-20260913/source-review.json) records the accepted and held editions.

| District | Result | Implication |
| --- | --- | --- |
| Dibrugarh, Assam | Eight source passages; original pages 1–3 visually inspected; issued 11 September, forecast dates 12–16 September | Adds another inspected district, using the existing GKMS family. Rice has no stage label in the row, so a tillering-filtered request does not borrow Kamrup's label. The panicle-initiation condition inside a rice paragraph remains in the original text. |
| Surat, Gujarat | Entire edition held | Compound crop aliases and an unbound split row fail the new layout gates. Manual review also found general heavy-rain/withhold-irrigation guidance conflicting with a banana dry-weather irrigation instruction, and a castor row referring to maize. The initial 36 extracted passages are rejected evidence, not accepted coverage. |
| Madurai, Tamil Nadu | Unsupported header/date family held | The document text does name Madurai. The parser's failure to recognize its heading does not prove that the publisher returned the wrong district. Error wording now preserves that distinction. |

Together with Ahmedabad, Coimbatore and Kamrup, this gives **four inspected district editions, three extraction families and 56 indexed passages**, with the previous single Ahmedabad crop mismatch still quarantined. Surat and Madurai do not increase the accepted count. The original 48 accepted passages remain unchanged. Extraction validation was tightened without changing their chunk identities or silently republishing rejected content.

Forecast-table dates remain forecast context, not a claim that every crop recommendation has that exact validity interval. Rice stage filtering currently uses explicit row metadata; it does not infer stage applicability from every sentence. Source quotations retain conditions and quantities, and are not converted into individualized chemical instructions.

## Review checkpoint and next work

P03, P07, P08 and P12 remain **partial** in the [standing product plan](../data/registry/product-progress.json). R09 and R12 are updated in the [living review](08-hardening-progress.md). Registry revision 11 adds evidence under the existing source identities, with no operational promotion; all 230 prior registered asset fingerprints were checked before adding six new batch assets. Two already referenced historical artifacts also enter the generated inventory, giving 238 registered assets. The previous report matches its earlier delivery hash. Earlier frozen checkpoints remain historical records.

The most important next retrieval work is **whole-document context**. Crop-row retrieval can miss general rain warnings, field-wide restrictions or guidance elsewhere in the bulletin. Dibrugarh itself has warning and general sections outside this index. We must bind relevant parent sections to crop excerpts, expose conflicts, review split rows/compound headings and measure retrieval recall before expanding claims about agricultural decisions. Automatically rejecting one observed layout is not an automatic contradiction detector.

In parallel with that engine work, the standing gaps remain: broader natural-language and transliteration handling, source publication transitions and refresh jobs, official-warning origin/geography/completeness, marine and river conversational identities, and independent domain/language evaluation. Do not substitute more sources indiscriminately for the right source, place, time and question coverage.

This batch advances the PS's conversational querying, location context and meteorological-data integration. It does not complete national source coverage, current operational warnings, validated field decisions, multilingual voice, mobile accessibility or full SIH26068 compliance. Desktop is the present surface; mobile and voice remain requirements. No keys are needed to continue the next local engine batch.
