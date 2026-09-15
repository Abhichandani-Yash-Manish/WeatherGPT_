# A unified user workspace — 15 September 2026

## Verdict

The architecture has produced practical capabilities. The product was making people discover them through
separate screens, example phrases and answer-menu actions. The right next step was to connect those capabilities
into explicit tasks and outputs while keeping the numerical and provenance foundation.

This batch makes that connection. It does not establish full PS compliance or operational acceptance.
Desktop remains the delivery surface; hosting and sharing remain on hold.

## What the audit found

| Finding | Evidence and consequence | Change |
|---|---|---|
| The running app did not match the checkout | Port 8765 returned 404 for `/home.js`, despite the file and route being present in the checkout. The opening warning panel could not run there. | Verified a fresh process on port 8766. A local preview must be restarted for backend changes; a file on disk is not a delivered capability. |
| Discovery depended on knowing a question or opening many screens | Blank chat entry, four generic example buttons, a long undifferentiated navigation list; model comparison, ensemble spread and saved outputs were hard to discover. | A default Workspace with independent weather sections, searchable/category-filtered tools, guided questions, saved briefs and plans. |
| The old welcome warning renderer used a nonexistent field | `home.js` read `data.severity`; `warnings.place` returns dated rows and no such field. Missing severity could become “No warning in this product”. | The replacement reads today's actual row. An absent/expired day is missing coverage; only explicit `quiet` becomes the product's no-warning wording. |
| A place already selected in the page could fail in chat | The generated “Vadodara, Vadodara, State of Gujarāt” question asked for a settlement in Vadodara rather than Gujarat. | Guided questions use the source name and state without the repeated district. The full source label stays in the workspace. The corrected question and its afternoon follow-up both answered. |
| A model comparison silently became one forecast | The first live comparison was labelled `answered`, but the task operation was `lookup` and only S21 returned. | Named GFS/best-match comparison recognition repaired. The uppercase GFS acronym is not treated as an omitted place after “and”. Regression cases retain the multi-place omission guard. |
| A screen-to-chat handoff lost selected context | Airport handoff used VAAH regardless of selected airport. Advisory handoff omitted the state; an old chat could contribute pending slots. | Airport code/report and climate district/state/years are retained; advisory district/state are explicit. Guided tasks start a new conversation with an editable draft; ordinary chat follow-ups keep their conversation. |
| Slow reads could leave an indefinite spinner | The live warning-brief read waited beyond repeated 25-second browser waits. The warning snapshot downloads the national geometry (the inspected cached response was 18,937,972 bytes). | Source sections load separately and remain usable during other reads. Read-only page requests stop waiting at 45 seconds with an honest recovery message. This does not cancel server work or fix the upstream delay. |
| Late drawer responses could replace a newer task | Asynchronous callbacks held the shared drawer body. | Each opening owns a new content element. A late response updates detached content, not the next task. |

## The delivered experience

1. **Open Workspace.** The selected place leads. Published district guidance, a nearby observation and upcoming
   model hours load independently, each with its own source, issue/observation/validity time, retrieval time,
   coverage and unknown states. Forecast precipitation keeps its interval; unstated observation units remain
   unstated. The observation summary prefers a usable fresh report and names its station and distance.
2. **Choose an outcome.** Fourteen tools cover current conditions, a forecast window, model comparison,
   ensemble spread, warning brief, plan watch, crop advisory, published bulletin search, rainfall history,
   daily reanalysis, airport reports, waves, river discharge and a dated briefing. Search and category filters
   narrow the choices. Existing Map, Forecast, Observations and other evidence views remain reachable.
3. **Review the request.** A guided tool exposes its relevant inputs: place, date/window, crop/stage, topic,
   historical range or airport/report. It previews the exact question and opens it in Ask. It does not submit
   automatically. Brief actions use the existing server composition routes.
4. **Continue and keep.** Follow-ups retain the conversation. Saved briefs and plans are visible from the
   workspace; the Briefcase reopens and exports stored outputs. Plan delivery still depends on the local
   process and its actual inbox state; no source registration is presented as an active subscription.

The visual system reuses the product's teal/slate palette, source-only hazard colours, readable typography,
and existing charts/receipts. Desktop source cards have stable height with scrollable evidence so slow reads
cannot keep moving the tool actions under the pointer. More specialised navigation is grouped; persona
sorting preserves that group. Navigation returns to the top of the newly opened view.

## Acceptance evidence

Directory: `research/implementation/unified-workspace-20260915/`.

- `journeys-first-run.json` preserves the successful Vadodara morning/afternoon conversation **and the failed
  comparison**, even though its engine status says answered. This is why status labels alone are insufficient.
- `journeys-after.json`: the repaired comparison returns seven facts and two calculations, including GFS and
  best-match values for the same afternoon; the national bulletin returns ten passages; the Nashik grape
  question keeps the live-reader refusal and indexed-edition fallback explicit. The fallback does not claim
  crop/stage extraction or personalized field advice.
- The airport browser handoff was changed to VABB and produced `Show the latest METAR for VABB and explain it.`
  It was not silently switched to VAAH.
- `saved-brief-open.png` records reopening an existing dated brief; its old day remains explicit. Export was
  invoked through its normal browser button. The warning-brief cold run and retry are recorded separately in
  `acceptance.json`; a failed wait is not counted as a successful save. The later retry composed the Vadodara
  brief, saved entry `431bf10c-a7ad-446c-ac57-721eb14cbbd0`, reopened it and exported its Markdown through the
  normal UI. `warning-brief-saved.png`, `vadodara-brief-reopened.png` and `export.json` record that full path.
- The final workspace axe scan records zero violations and one incomplete contrast rule for content clipped
  inside scrollable source panels; it is not counted as a contrast pass. The guided drawer records zero
  violations and zero incomplete checks. Filter-group semantics and duplicate evidence-region labels were
  repaired; earlier failed reports remain alongside `a11y-workspace-recheck.json`.
- Viewports 1440×1000, 768×1024 and 390×844 had no horizontal page overflow. This is a local Chromium layout
  check, not mobile-platform or screen-reader acceptance. Escape closes the task drawer.
- Final Python run: **991 passed**, three dependency warnings, 31.28 seconds. All eight JavaScript suites
  passed. These counts are regression evidence, not product-completion measures.
- The workspace component suite checks explicit quiet versus missing/expired warnings, network-shaped
  observation data, zero/unknown units, independent failures, search, place snapshotting, late drawer isolation
  and the honest timeout message. Existing UI suites and the Python suite are recorded separately.

## Finding continuity and next work

Relevant standing findings: **P03/P08/P12/P13/P15**, **R02/R04/R06/R11/R12**, **F01/F02/F03/F05/F07/F10**,
and **A01/A03/A06/A07/A08**. These repairs add scoped evidence; no historical finding is universally closed.
P01/P02's earlier verification and all other P/R/F statuses are preserved. The current hardening registry
points here without rewriting historical acceptance.

Remaining priorities, ordered by their impact on completing a user task:

1. Bound server-side source reads and lock waits, and avoid repeated national geometry transfer for a
   point warning read using the existing validated geometry/attribute contracts. A page timeout alone does
   not solve cold latency. Preserve validity and degraded delivery when reusing a snapshot.
2. Independently evaluate the generated tool questions across places and changed editions, including every
   specialist, ensemble and plan lifecycle. This batch does not claim a new nationwide or domain-reviewed
   acceptance result just because the tools are discoverable.
3. Improve advisory explanation and applicability while preserving original excerpts, unresolved conditions,
   language gates and source ownership. A browsable corpus is not a personalized agronomy adviser.
4. Complete language/native-speaker, real-device voice, mobile, warning-delivery and operational acceptance.
   The narrower tests here do not replace those gates.

Other backend language/rendering work was occurring in the shared checkout during this batch and a concurrent
commit included part of this UI work. That work and existing user changes were retained. Evidence describes
this local checkout and running process, not a separately deployed release.

The port 8766 preview is the QA process, with its background plan watcher disabled to avoid duplicate
background work beside the existing workspace process. Normal startup enables the watcher; this preview
does not establish a new plan-monitoring acceptance result.

## Integration follow-up

[The integrated PS review](72-integrated-status-and-ps-review.md) supersedes this batch's current-state
summary. Air quality, brought in from the concurrent GitHub work, makes the catalog fifteen tools. This
batch's original fourteen-tool acceptance remains a historical result. Supplemental screenshots and
exports named above are retained locally under `data/runtime/review-private/unified-workspace-20260915/`;
`local-capture-manifest.json` records their hashes. They are not newly published runtime session material.
The original committed journey captures are preserved byte-for-byte; parsed local copies remain in that
archive. The reviewed desktop workspace screenshot and automated reports are included with the source.
