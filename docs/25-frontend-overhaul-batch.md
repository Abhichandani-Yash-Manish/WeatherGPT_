# WeatherGPT: frontend overhaul batch

Recorded 14 September 2026; a historical record. The current surface and its evidence are [docs/46](46-frontend-instrument-desk.md). Baseline commit `e2042c9`, working tree after the batch described here. Plan: [docs/24](24-frontend-overhaul-plan.md). Frozen pre-batch measurements: [baseline](../research/reviews/frontend-overhaul-20260914/baseline/baseline.json).

## Scope of this batch

This is the delivery of trajectory item 4 of [the critical full-solution review](21-full-solution-critical-review.md) and stage **S5 "Language, resilience and desktop usability"** of the [product plan](../data/registry/product-progress.json): accessible product behavior, honest state reporting and usable source inspection. It is not a landing-page redesign, and it does not touch the numerical, provenance or planning foundation.

What changed: the served workspace surface (`web/`), the asset route and two bounded local read models in `weathergpt_data/workspace.py`, and the frontend verification suites. What did not change: every adapter, source registry, numerical contract, planner behavior, retrieval path and finding status outside the six frontend findings below.

## The six findings, and their state after this batch

All six were measured on the pre-batch surface and are reproducible from the frozen baseline.

| ID | Pre-batch state | State now | Evidence |
|---|---|---|---|
| FE01 | At 390×844 the question box began 2009px down a 2344px document; the structured panel alone exceeded the fold | **verified live** | composer pinned inside the first viewport at 390×844, 768×1024 and 1440×1100, measured and recorded in [live-checks.json](../research/reviews/frontend-overhaul-20260914/after/live-checks.json) |
| FE02 | `send()` declared a `refresh` flag and never read it; zero references to `/api/refresh`; the only refresh control sat in unreachable code | **resolved** | a resolved point offers "Collect fresh evidence"; it posts the packet's own coordinates to `/api/refresh` and reports state, provider claims and retry timing |
| FE03 | The dispatch ternary could never select `render()`; that dead region also posted `entity_id`, which the engine rejects | **resolved** | one render path; the client sends only `question`, `conversation_id`, `selection_id`, `coordinates` |
| FE04 | The page printed "{completed} of {requested} requested tasks completed" as affirmative text | **resolved** | asked, answered and incomplete are reported separately, with the engine's own per-task id, kind, operation and status |
| FE05 | Scope text omitted marine wave, river discharge, airport, warning and saved-PDF capabilities; no control could express a requested output language | **resolved** | scope names METAR/TAF, wave height, discharge, bulletins and the unconnected limits; an output-language control with an honest downgrade disclosure exists |
| FE06 | A structured builder and a composer both submitted, and the builder overwrote the composer | **resolved** | one question input; the field builder writes into it and never submits by itself |

Reproduce any of them with `python3 scripts/audit_workspace_frontend.py --baseline`.

## Capabilities added

**Answer presentation.** An answer-first headline carrying the exact retrieved value and unit; a **validity ruler** drawing the covered source hours and gaps as real geometry with a text description; a structured dark **evidence receipt** holding measure, value, method, place, entity, window, observation time, evidence kind, source with a link, retrieval time, page/row/column locator, evidence id, task id and record paths; separate handling for series answers, which are never headlined by one arbitrary member; a series receipt for charted answers; per-answer actions (collect fresh evidence, copy, print, save as Markdown, download JSON); a print stylesheet that strips the workspace chrome so an answer and its receipt survive on paper.

**Honest state.** Task accounting by asked/answered/incomplete; an explicit disclosure when the engine reports that the requested output language was not written; held styling for unverified, expired and partial states; refusals, lock collisions, an unavailable store and an expired token each given their own accurate message and header chip; a serving-lifetime notice that expires the receipt in place.

**Conversation control.** A bounded run of one question at a time with a real elapsed-time indicator; a stop control that states plainly that stopping the page request does not cancel the server work and that nothing is queued behind it; the opening card retired on the first question; the newest card revealed from its top so a clarification's choices are reachable; a new-conversation control; jump-to-newest.

**Retention and health.** A conversation ledger listing bounded excerpts of the stored conversations, a search over the stored questions, restore of a stored transcript with a link, and deletion through the local route. A read-only collection-health panel naming the products collected, their job states, the newest committed evidence, requests in flight and provider cooldowns. Streams are pseudonymous point identities in this store, so the panel reports products and commit times and never a requested location.

**Accessibility and policy.** One question input with a label on every control, an accessible name on every button, a skip link, five live regions, keyboard support (⌘/Ctrl+Enter to ask, ⌘/Ctrl+K to focus, Escape to close the ledger), a reduced-motion and forced-colors path, and no inline style or script anywhere, so the page stays inside the served Content-Security-Policy.

## Server changes in this batch

| Change | Why |
|---|---|
| `/views.js` added to the explicit asset map | the page needs the renderers as a separate same-origin file, and the allowlist is deliberate |
| `GET /api/conversations`, `GET /api/conversations/<id>`, `DELETE /api/conversations/<id>` | retention, restore and deletion over the store that already existed, behind the loopback Host check and the session token |
| `GET /api/health` | a read-only projection of the ingestion store: products, job states, newest commit, leases, cooldowns |
| A missing served file now answers 404 instead of dropping the connection | a missing asset could previously close the socket |
| Unknown API GET paths keep returning 404 | the private routes are listed explicitly rather than guarded by a broad prefix, so existing behavior is preserved |

A defect found while building this is worth recording: `Workspace.conversation` is the conversation-engine attribute, so the transcript reader could not use that name; the method is `conversation_transcript`. The first version of the route crashed the server on a malformed identifier because `SourceError` was only imported locally in another method; it is now a module-level import.

## Verification

- **374 Python tests pass** (`python3 -m pytest tests/ -q`), unchanged in count, and passing after the server changes above.
- **34 JavaScript component checks pass** across four suites, run individually with `node tests/<suite>.js`: `test_charts.js` 2, `test_views.js` 14, `test_bulletin_ui.js` 5, `test_conversation_ui.js` 13. A shared DOM shim (`tests/dom_shim.js`) replaces the previous source-slicing harness, which broke whenever the renderer moved.
- **`scripts/audit_workspace_frontend.py`**: serve contract, pinned composer, refresh wiring, single render path, task accounting, scope and language control, CSP compliance, no class-name-as-text, and JavaScript parse checks.
- **Four real model journeys** were run through the actual page and are recorded in `live-checks.json` with screenshots: a point forecast, a follow-up in the same conversation, a historical trend, and an ambiguous place at mobile width. A retention journey (list, search, delete) was exercised in the browser and in component checks.
- **Real answer behavior**, not just structure: the trend card leads with the computed 54.654 mm/decade and its stated method rather than one year; a clarification offers every candidate; a series receipt states that a descriptive slope is not a projection or a validated trend.
- Three defects were found by this verification and fixed rather than papered over: two renderers passed a stylesheet class as element text, column-flex items silently squashed a tall answer instead of scrolling it, and a chart point was promoted to the headline of a series answer.

## What this batch does not establish

- **P10** remains partial: collection is still request-driven and narrow. It is reachable and its cost is now visible; it is not scheduled.
- **P11** remains open: there is still **no bounded model queue and no stage streaming**. The server holds one non-blocking conversation lock; a second question is refused, and stopping a turn does not stop the server work. The page now says so instead of implying otherwise, which is not the same as fixing it.
- **P12** remains partial: no user-level acceptance benchmark exists for all promised operations or languages.
- **P13** remains partial: this is still a desktop web surface with a better small-screen layout. A responsive layout is not mobile platform compliance, and no mobile acceptance journey has been run.
- **P14** remains open: reproduction and deployment packaging are untouched.
- **Language output is not achieved.** A requested output language is now expressible and its failure is disclosed, but fluent Hindi or Gujarati output has not been produced or reviewed.
- **Accessibility is not audited.** Labels, names, a skip link and live regions are present and measured, and no inline style is used, but contrast, focus order, screen-reader behavior and keyboard-only journeys have not been independently tested.
- **No sustained-load, cold-start or concurrency measurement** was taken.
- Official warning applicability, dissemination and subscriptions are untouched, as are all engine findings A01–A08 in `docs/21`.

## Not claimed

No operational readiness, forecast skill, coverage or completeness is claimed here. The 34 frontend checks are component-level, not browser or visual acceptance. Four recorded journeys are not a benchmark and are not unseen holdouts. The screenshots are one browser build at three viewports, not visual-regression or cross-browser evidence.
