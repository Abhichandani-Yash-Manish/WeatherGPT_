# Bulletin context and qualified guidance — 13 September 2026

Crop retrieval now brings separately labelled general and warning sections from the same saved bulletin edition into the answer. This closes a demonstrated omission in the four inspected district editions, not whole-document or nationwide acceptance. The critical review, user-supplied SIH26068 scope, and engine-first priority remain in force. Desktop work continues; hosting and sharing remain on hold.

## What changed

The Dibrugarh edition demonstrates the problem: its page-two general advisory permits ongoing farm operations, while the page-three impact advice restricts field work during thunderstorms and postpones sowing. A rice-row answer previously omitted both sections. The new answer preserves them, identifies opposing sowing wording as unresolved, and shows their source pages. It does not decide which conditions apply to the user's field.

- Recognized forecast summaries, warning headings and bodies, general advisories, SMS sections and impact sections retain page rectangles, original text and the source PDF hash. A heading at the end of one page can own a body on the next page without absorbing browser-print headers or crop tables.
- General table rows reuse the existing verified extraction. They remain separate from crop matches, with their original source chunk identity retained. Existing immutable crop publications, embeddings and 56 accepted crop/index passages are unchanged.
- Parent context is attached after crop/stage/topic filtering. A missing wheat match still returns unavailable; unrelated general text cannot fill it. The crop matched/returned/omitted counts exclude the separate context sections.
- Explicit opposing sowing, irrigation or spraying wording can produce a source-linked qualification flag. This is a small deterministic wording check, not comprehensive contradiction detection. Different dates and conditions may reconcile the passages; no automatic resolution or agronomic conclusion is asserted.
- Unreadable, empty, oversized or missing expected context is disclosed and leaves the response partial. Dibrugarh's general impacts section contains unreadable glyphs and is withheld; its readable impact-advice section is retained.
- Printed warning headings and dates remain reference text. A bulletin's five-day forecast period does not extend a next-day warning heading. Source text such as dated “No Warning” and “NA” is not an independently verified all-clear. No warning dissemination eligibility is granted.
- Re-explanation now preserves structured retrieval coverage, omissions and qualification flags alongside the passages, status and original expiry. Expired responses clear that coverage with the underlying evidence.
- The desktop displays distinct context cards with page links and a direct saved-PDF download. The latter works when the browser's PDF viewer fails.

Implementation: `weathergpt_data/bulletin_context.py`, `document_tools.py`, `dialogue.py`, `conversation.py`, `briefing.py` and `web/app.js`.

## Verified editions and limits

| Edition, issued 11 September | Added context | Remaining limitation |
| --- | --- | --- |
| Dibrugarh, Assam | Six readable sections, including the page-three restriction | One unreadable impacts section withheld; opposing sowing wording unresolved; rice row still has no stage label |
| Kamrup, Assam | Seven sections, including the next-day warning heading | Three source `NA` bodies are preserved as unknown/reference text; no current warning verification |
| Coimbatore, Tamil Nadu | Five sections/rows, including separately dated warning and agriculture-warning text | Regional and crop conditions remain verbatim; no individual-field inference |
| Ahmedabad, Gujarat | Weather summary and existing general-advice row | The original crop mismatch remains quarantined; district forecast is not a field forecast |

These are 20 distinct context sections/rows in four already inspected editions. No additional district is accepted. Source pages were visually inspected: Dibrugarh 1–3, Kamrup 1–3, Coimbatore 1–3, Ahmedabad 1–2. Original source wording, including errors and limitations, was not corrected.

The Nagpur test now has a concrete outcome: its retrieved edition fails the existing unbound table-continuation gate. “Can I spray tomorrow?” → “Nagpur, Maharashtra” → “cotton” → “flowering stage” retains the requested place, date, crop and stage, but returns unavailable evidence. Surat and Madurai also remain held by their earlier layout gates. None is silently replaced by another district.

## Acceptance evidence

- Baseline: 340 automated tests passed before changes. Final: **356 tests passed**, including 16 new source/context regressions. Existing chart and citation component tests and JavaScript syntax checks passed; a new component check covers the download fallback.
- **16 recorded final HTTP turns using local Ollama:** four answered, five partial, two needs clarification and five unavailable. These are 16 checked outcomes, not 16 completed information requests.
- Source replay verified **23 crop-passage instances, 53 parent-section instances and three hourly probability facts**, including task/citation ownership, document identity, time and units. **50 parent instances** were independently read from their saved page rectangles, separate from the heading parser. General rows reuse the source-verified crop-table extractor.
- All four cited PDFs returned HTTP 200 and exactly matched their recorded SHA-256 values.
- An explicit mixed request uses Dibrugarh **district** for bulletins and Dibrugarh **city** for point weather. It returns three hourly probabilities in the forecast task with no bulletin passages attached to that task. The earlier district-only forecast probe correctly asks for a town; it is not a missing-value or wrong-city failure.
- Final HTTP median was **6.56 seconds**, maximum **20.28 seconds**. This is a small mostly warm local sample, not a latency or load guarantee.
- Two desktop browser journeys checked submission and visible partial/context presentation. The final journey expanded the page-three context card, inspected its link, and received an actual browser download event from “Download saved PDF.” The embedded PDF viewer failed to render the original open-link destination; the download fallback is verified, but in-browser PDF rendering remains unresolved. This is narrow desktop acceptance, not full browser/mobile QA.
- All **238 registered assets and ten earlier frozen checkpoints** matched their original hashes. No earlier accepted/failed journeys or source publications were overwritten.

The first live set exposed lost structured coverage on “Explain that”; it is preserved in `live-1` with `initial-verification-failure.json`. `live-final` verifies the repair. The verifier's initial incorrect expectation of a point forecast for a district is recorded separately in `verification-expectation-correction.json`; the explicit-city probe is retained in `live-point`.

Evidence: [acceptance summary](../research/implementation/bulletin-parent-context-20260913/acceptance.json), [replay verifier](../research/implementation/bulletin-parent-context-20260913/verify_acceptance.py), [tests](../research/implementation/bulletin-parent-context-20260913/tests-final.txt), [browser check](../research/implementation/bulletin-parent-context-20260913/browser-check.json), [preservation](../research/implementation/bulletin-parent-context-20260913/preservation-check.json).

## Current review mapping and next gates

P07/R09/F07 remain **partial**: parent retrieval has advanced, but full-document recall, general conditional reasoning, source-layout coverage, language quality and personalized advice remain unvalidated. P03/P08 and F01/F02 gain scoped follow-up/task-isolation evidence; they do not become universally solved. P12/R11/R12 gain the recorded source and desktop checks. P06/R02 remain partial with no new current-warning eligibility. F10 remains partial: source excerpts are still English, without validated advisory translation. All other P01–P15, R01–R12 and F01–F11 findings retain their standing status and historical evidence.

Next work, in dependency order:

1. Review Nagpur's continuation rows and the held Surat/Madurai families against their original pages. Preserve quarantine until the full row, crop, stage and conditions are verified.
2. Build a reviewed retrieval benchmark for omitted sections, cross-section qualifications, dates, crop stage and terminology. Measure recall before adding more automatic layout coverage or claiming comprehensive contradiction detection.
3. Verify official-warning origin, applicable geography, lifecycle and completeness separately from advisory warning quotations.
4. Continue held-out conversations, Indian-language validation, specialist marine/river workflows and resilience. Voice, mobile and dissemination remain incomplete final PS requirements.

No new paid API or credentials were needed. This batch does not establish forecast skill, operational clearance, nationwide coverage, agronomic validity or full SIH compliance.
