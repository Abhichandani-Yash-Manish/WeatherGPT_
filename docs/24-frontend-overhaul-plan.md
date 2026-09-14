# WeatherGPT: frontend overhaul plan

Plan date: 14 September 2026. Baseline commit: `e2042c9`. Surface: the loopback desktop workspace served by `weathergpt_data.workspace` on `127.0.0.1:8765`.

This is a plan, not an implementation record and not a readiness claim. No finding status in `data/registry/hardening-progress.json` or `data/registry/product-progress.json` is changed by this document; statuses move only after a batch is verified and recorded, as `AGENTS.md` requires.

## 1. What this overhaul is, and what it is not

`docs/21-full-solution-critical-review.md` explicitly rules out "redesign the landing page" as a milestone, and rules out rewriting the system. It also states, in the same trajectory, what this plan must therefore be:

> **4. Complete accessible product behavior and dependable operation** — Add concise answer-first presentation with expandable original evidence; full claimed-language output; usable clarification, retry/cancel and source inspection.

`data/registry/product-progress.json` already carries the owning stage: **S5 "Language, resilience and desktop usability"**, status `hinglish_context_and_hindi_lookup_repairs_verified_scoped_broader_languages_resilience_and_ui_open`, with deliverables "Desktop answer charts and source inspection" and "Queue, cancel, progress and recovery", and exit checks "Representative sustained run measured", "No lost correction context", "Fluent review and desktop journey checks pass". `docs/14-product-review-and-progress-plan.md` stage 5 adds "short answers/charts/source inspection; stage progress, cancel/retry, bounded model queue; offline last-view labels".

So this overhaul is scoped as **delivery of accessible product behavior and evidence inspection**, with the visual work gated behind it. Concretely:

- In scope: the served page, its request/response handling, its rendering of the existing conversation packet, its accessible and mobile reachability, its honest presentation of uncertainty and limits, and the small bounded server changes those require.
- Out of scope: replacing the numerical/provenance foundation, changing the planner or the tool contracts, adding model providers, voice, native mobile, hosting or sharing.
- Not a claim: a responsive page is not mobile PS compliance (P13), a redesigned shell is not answer-quality improvement, and browser captures are not fluent-language review.

## 2. The frontend is small, and it is served by an explicit allowlist

| Asset | Lines | Notes |
|---|---|---|
| `web/index.html` | 33 | token placeholder `__WORKSPACE_TOKEN__` substituted at serve time |
| `web/style.css` | 5 | one minified line plus appended chart rules |
| `web/app.js` | 145 | two renderers, one of them unreachable |
| `web/charts.js` | 31 | SVG line chart with exact-value and evidence-ID inspection |

214 lines total, no build step, no `package.json`. Three constraints follow, and any batch below must respect them:

1. **The asset map is a hardcoded dict** in `make_server(...).Handler.do_GET` in `weathergpt_data/workspace.py`. A new frontend file is a 404 until it is added there. This is deliberate hardening, not an oversight.
2. **The Content-Security-Policy is strict**: `default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`. No inline script or style, no CDN, no external font or image origin. There is no `font-src`, so a webfont must be a same-origin file served from an added route.
3. **The server is loopback-only and CSRF-guarded**: `Host` must be `127.0.0.1:<port>`, `Origin` must match, and `X-WeatherGPT-Token` must equal the per-process token in `index.html`. Request bodies are capped at 8192 bytes. `/api/chat`, `/api/answer`, `/api/refresh` are the only POST routes; `/api/documents/<sha256>` serves verified saved PDFs.

### The packet the frontend must render

`POST /api/chat` always returns `schema_version: "weather-conversation-v1"` with the accepted request keys exactly `{question, conversation_id, selection_id, coordinates}`. Always present: `conversation_id, question, status, answer, facts, citations, notes, choices, follow_up, operational_eligible, answered_at_utc, expires_at_utc, trace`. Present when applicable: `charts, calculations, airport_reports, passages, document_evidence, retrieval_coverage, task_results, task_coverage, resolved_points, refresh`.

`status` is the honest state machine the UI should be built around: `answered, partial, needs_selection, needs_clarification, unavailable, explanation, outside_validity, stale, degraded, prototype_answer`. `expires_at_utc` means a rendered answer is a timestamped receipt, not a perpetually current answer.

## 3. Measured baseline

Frozen at `research/reviews/frontend-overhaul-20260914/baseline/`. Captures: `desktop-1440.png`, `mobile-390.png`, `desktop-1440-answer.png` (one real model turn). Measurements and adjudication in `baseline.json`. Reproduce with:

```sh
python3 scripts/audit_workspace_frontend.py --baseline
```

| ID | Severity | Measured state |
|---|---|---|
| FE01 | high | At 390×844 the question input begins at 2009px in a 2344px document (2.4 viewports down); the structured panel alone ends at 945px, past the 844px fold. |
| FE02 | high | `send(body, refresh=false, showQuestion=true)` never reads `refresh`; `web/app.js` contains zero references to `/api/refresh`. The only refresh button sits in unreachable code. A user cannot request a bounded collection. |
| FE03 | medium | The dispatch ternary `schema_version==='weather-conversation-v1' ? renderConversation : render` can never select `render()`, because the engine always emits `weather-conversation-v1`. That dead region also posts `entity_id`, a key `ConversationEngine.ask` rejects. |
| FE04 | medium | The UI prints "{completed} of {requested} requested tasks completed" as affirmative text from `task_coverage`, the counter `docs/21` A07 records as counting an empty or contradictory explanation task as completed. |
| FE05 | medium | The "What this version can answer" block omits marine wave, river discharge, airport METAR/TAF, CAP warning lifecycle and saved-PDF download, all of which are connected per `docs/13`, `docs/18` and `docs/23`. No control can express a requested output language, though `docs/21` A02 shows free-text language requests are not honoured. |
| FE06 | medium | A structured builder and a free-text composer both submit, and the builder overwrites the composer with a synthesised English sentence. Marketing hero and an example-chip row sit between the user and the product on every turn. |

Two further structural facts:

- **Conversations persist but cannot be reached.** `data/runtime/ingestion/conversations.sqlite` holds a `conversations(id, payload, updated)` table with 272 rows and there is no list, restore or delete route. There is therefore no retention journey, which `docs/21` A08 and P14 leave open. `data/runtime/` is git-ignored, so this store is correctly outside curated evidence.
- **One finding of the standing blocker is removed.** `hardening-progress.json` → `product_workspace.browser_visual_qa` reads `unverified_prior_admin_policy_verification_failure`. A working local capture recipe now exists (Chrome `--headless=new --no-sandbox --disable-gpu --user-data-dir=<tmp> --remote-debugging-port=9222`, then `agent-browser connect 9222`). This removes the *tooling* blocker only. Browser and mobile acceptance are still unperformed, and the registry field should change only when a recorded acceptance batch exists.

## 4. Design direction

Per `docs/21`, aesthetics are not the milestone, so this section is deliberately gated to batch F4 and written now only so F1–F3 do not bake in a shell that F4 must tear out.

**The subject.** An Indian meteorological evidence desk: station logs, printed agromet bulletins, IST source-hour windows, withheld and quarantined records, model cells with distances, and hashes. The product's distinguishing content is provenance itself. The page has one job: let a person ask in their own words and then inspect entity, time, parameter, unit and source on the answer.

**Direction: instrument logbook.** Keep the existing identity family (it is specific and already earned) and make one real risk: the evidence receipt becomes a dark instrument artifact on a cool working surface, so "the answer" is visually separable from "the workspace".

Color tokens:

| Token | Value | Role |
|---|---|---|
| `--ink` | `#0F2C38` | body text, deepened from the current `#153c4e` |
| `--sea` | `#176E86` | retained accent; the identity colour |
| `--ground` | `#EDF1F0` | working surface; deliberately a cool paper-grey, not a warm cream |
| `--paper` | `#FFFFFF` | panels |
| `--log` | `#0B222C` | the evidence receipt ground |
| `--log-ink` / `--log-mute` | `#DCE8EC` / `#7E9AA6` | data and captions on the receipt |
| `--signal` | `#B4551A` | withheld, stale, quarantined, reference-only |

Type roles, with an honest constraint: this environment cannot fetch a webfont and the CSP allows same-origin files only. So unless the user approves vendoring font files and adding a route, the overhaul uses deliberate system stacks rather than pretending to a typographic identity it cannot ship.

- Display / logbook headings: `'Trebuchet MS', 'Segoe UI', sans-serif`, retained for continuity, re-set with a real scale and tighter tracking.
- Body and UI: system UI stack (`-apple-system, 'Segoe UI', Roboto, sans-serif`).
- Data: `ui-monospace, Menlo, Consolas, monospace` for every reading, source ID, hash, distance and time.

Layout, replacing hero-plus-duplicate-form with three regions:

```
desktop                                   mobile (390)
+---------+---------------------------+   +---------------------------+
| rail    |  desk                     |   | masthead        [rail]    |
| ledger  |                           |   +---------------------------+
|         |  question bubble          |   | thread (conversation      |
| convos  |  +---------------------+  |   |  first, answer-first)     |
| health  |  | answer lead line    |  |   |                           |
| scope   |  | validity ruler      |  |   | answer card + ruler       |
|         |  | dark receipt        |  |   |                           |
|         |  +---------------------+  |   +---------------------------+
|         |                           |   | composer (pinned, in the  |
|         |  composer                 |   |  first viewport)          |
|         |  [ ask with fields  v ]   |   | [ ask with fields  v ]    |
+---------+---------------------------+   +---------------------------+
```

- The structured builder becomes a disclosure **inside** the composer, not a competing first-class column. It stops overwriting the composer.
- The hero shrinks to a one-line masthead. The page's thesis is the answer and its receipt.
- Example chips move into the empty composer state, where an example is useful, and out of the transcript.

**Signature: the validity ruler.** The current welcome card already draws a decorative `09:30 ─── 12:30` device. Generalize it into the spine of every answer: a labelled IST interval ruler showing the exact requested window, the source hours actually covered, gaps drawn as unfilled segments, and the answering cell with its distance as a labelled guard tick. This is the one memorable element, and it encodes true things the product already guarantees — exact-interval contracts, `:30` IST source-hour boundaries, the 50 km cell guard, and explicit missingness. Numbered markers, gradient badges and decorative dividers are dropped.

**Self-critique.** A full-page pale-blue wash with a soft accent bar is the generic weather-app default, and the current hero-plus-window-line is the templated version of it. A warm cream ground with a high-contrast serif and terracotta accent would be the current AI default instead, so it is avoided. The boldness is spent in exactly one place, the dark receipt with its ruler; the rail, masthead and composer stay quiet. Reduced motion is respected, and the ruler's interval is treated as data, so it must remain readable in text form for assistive technology.

## 5. Batches

Each batch states deliverables and exit checks in the style of `docs/14`. A batch is not recorded as verified until its journeys are replayed and the failures are preserved alongside the passes.

### F0 — Instrument the surface (no product change)

- Deliverables: the frozen baseline record and captures; `scripts/audit_workspace_frontend.py`, which reproduces FE01–FE06 from the served files; a documented browser launch recipe; a journey harness that loads the real page, asks a real question and captures at 1440×1200 and 390×844.
- Exit: the audit deterministically reproduces FE01–FE06 and exits non-zero only if the page cannot be served consistently. The harness completes a load, an ask and a capture at both viewports. Deliberate failures are kept, not cleaned up.

### F1 — Make the live path honest and complete

Highest product value, no visual dependency. Directly owns FE02, FE03 and FE04.

- Delete the unreachable legacy renderer and its rejected `entity_id` request shape.
- Honour refresh: a control that POSTs `/api/refresh` with the same question plus an explicit selection, and renders `refresh.state`, `job_id`, `worker_state`, `claims_this_action`, `job_provider_attempts` and `retry_due_utc_epoch`, including the policy refusals verbatim (choose a future interval, within seven UTC days, collection disabled by source policy, already fresh). It must never imply that a background worker is running: the refresh contract states plainly that none is.
- Replace the single completion counter with **requested / planned / executed / answered**, counting abstentions and clarifications separately, per `docs/21` repair item 1. If a count cannot be derived from the packet, show the task list with its own statuses instead of a total.
- Output language: add an explicit control that sets the requested language, and when the engine records that the requested language was not written, render the answer as degraded with the engine's own note. Never show a language-mismatched answer as answered.
- Request lifecycle: real in-flight state with elapsed time; a cancel that aborts the fetch and states truthfully that the server may still be working and that one conversation lock applies; and distinct handling for token/Origin 403, 400 validation, 503 store-unavailable and the lock-busy rejection string from `CHAT_LOCK`.
- Exit: recorded journeys for a mismatch-language turn, a lock collision, a 503, a policy-refused refresh, a successful refresh and a cancel. No state may be labelled answered while `status` says otherwise.

### F2 — Answer-first presentation and usable evidence inspection

Owns FE01 and the "source inspection" deliverable of S5.

- One scannable lead line: place · window · parameter · value or range · unit · source. Detail below it.
- Replace the raw-JSON `<details>` dump with a structured inspector: entity, time, parameter, unit, value or range, source ID, retrieval time, validity, cell distance, citation, the original record, and the raw packet retained for audit.
- Extend the existing chart contract to comparison and trend, keeping exact source values and evidence IDs keyboard-inspectable, and keeping missing intervals as gaps.
- Mobile reachability: the composer must be inside the first viewport at 390×844, measured, not asserted.
- Accessibility floor: focus order, `:focus-visible`, live-region discipline on the transcript, reduced motion, contrast, and a check that an interval or distance is never conveyed by colour alone.
- Exit: measured composer position inside the first viewport at 390×844; the recorded a11y check; no regression in the eight existing JavaScript component checks.

### F3 — Surfaces for capabilities that are connected but invisible

Owns FE05's first half.

- Marine wave and river discharge (`docs/23`): show the answering cell and its distance, and the clause that neither stands in for an observed water level, gauge reading, danger level, flood extent, tide or current.
- Airport METAR/TAF: observation versus forecast typing and the valid times, visible without opening a disclosure.
- Warning and CAP states (`docs/18`): render reference-only, quarantined, expired, cancelled and test states as such. No subscription or delivery affordance until a delivery journey exists, because `docs/21` A05 shows none does.
- Bulletins: passage-first reading with general/warning context held separate from crop matches, preserving page locators and the saved-PDF download.
- Exit: one recorded journey per capability that names its limit in the interface, with the limit text traceable to the document that established it.

### F4 — Visual direction and shell

Gated behind F1–F3 so the shell is built against real states.

- Apply the token, type, three-region layout and validity-ruler signature; retire the hero, the duplicate form and the stray example-chip row.
- Add any new asset to the server asset map; keep the page free of inline style and script so it stays within the served CSP.
- Exit: desktop and mobile captures for welcome, answer, clarification, partial, error and expired states; `scripts/audit_workspace_frontend.py` clean; no journey regression from F1–F3.

### F5 — Retention, health and recovery surface

Depends on bounded server work; the frontend cannot deliver this alone.

- Conversation list, restore and delete over the 272-row store, with the existing loopback, `Origin` and token checks, and with no question text written to logs (`log_message` already suppresses this and must stay suppressed).
- A source-health and job-state panel read from the existing ingestion database: freshness, job state, retry due times, budgets exhausted. Read-only, and no invented score, index or confidence value.
- Offline and last-view labels, and a bounded-queue status so a rejected concurrent question is explainable rather than merely an error.
- Exit: a retention/restore/delete rehearsal, an outage rehearsal, and a recorded concurrency measurement that distinguishes measured latency from a claim about capacity.

## 6. Server changes the plan requires

These are small, bounded and local, but they are not frontend-only, and the plan should not pretend otherwise:

| Change | Batch | Note |
|---|---|---|
| New asset entries in the `assets` dict, or a small static route | F4 | keep the explicit allowlist; do not serve a directory |
| Optional vendored webfont route | F4 | user decision; CSP has no `font-src`, so same-origin only |
| `GET` conversation list, restore and delete | F5 | bounded, loopback and token guarded, no question text in logs |
| Health/job-state read endpoint | F5 | read-only projection of existing tables |

`POST /api/refresh` already exists and needs no server change; F1 only gives it a caller.

## 7. What this plan must never claim

- A responsive layout is not mobile PS compliance. Desktop web remains the current surface and P13 stays open.
- Browser screenshots at two viewports are not browser, mobile, load or cold-start acceptance.
- A clearer interface does not make an answer more accurate. A01–A04 remain engine findings; a redesign does not touch them.
- No confidence score, risk index, suitability verdict or probability is to be invented for display. The UI shows what a source states and what it does not.
- Reference-only CAP material, model rain or a resolved document hash must never render as a current official warning.
- Registering a source, passing the 374-test suite or rendering a receipt is not evidence of usefulness; only recorded user journeys are.
- Language understanding is not language output. A control that requests Gujarati output must show the engine's honest downgrade until fluent output is verified.

## 8. Verification strategy

1. `python3 scripts/audit_workspace_frontend.py --baseline` reproduces the structural findings before and after each batch.
2. `python3 -m pytest tests/ -q` (374 passing at baseline) plus the eight JavaScript component checks via `node tests/test_charts.js`, `node tests/test_conversation_ui.js`, `node tests/test_bulletin_ui.js`. Note that `test_conversation_ui.js` slices `web/app.js` between the literal markers `$('history-example')` and `function renderConversation(`; F1 must update that region and its test together, never quietly.
3. Real-model journeys through the actual page over CDP at 1440×1200 and 390×844, recorded under `research/reviews/frontend-overhaul-20260914/`, with failed and repeated runs preserved.
4. Adjudication recorded separately from application status, as `docs/21` does.

## 9. Recorded artifacts and continuity

| Artifact | Role |
|---|---|
| `docs/24-frontend-overhaul-plan.md` | this plan; sets no status |
| `research/reviews/frontend-overhaul-20260914/baseline/baseline.json` | frozen pre-overhaul measurements, captures, commit and environment |
| `research/reviews/frontend-overhaul-20260914/baseline/*.png` | desktop 1440×1200, mobile 390×844, and one real model turn |
| `scripts/audit_workspace_frontend.py` | reproduces FE01–FE06 from the files the server actually serves |

This plan changes no file under `web/` and no status in either registry. FE01–FE06 are new frontend findings that attach to existing tracked work (P10, P11, P12, P13, P14, and `docs/21` A02, A07, A08) rather than replacing it. Historical P01–P15, R01–R12 and F01–F11 evidence is unchanged. The browser tooling blocker recorded in `hardening-progress.json` → `product_workspace.browser_visual_qa` is no longer a tooling limitation, but that field should be updated only alongside a recorded browser acceptance batch, not by this document.

## 10. Decisions needed before starting

1. **Scope confirmation.** This plan treats the overhaul as `docs/14` stage 5 / `docs/21` trajectory item 4, not as a landing-page redesign. Confirm, or say what should change.
2. **Fonts.** Approve vendoring one or two same-origin webfont files plus an asset route, or keep the deliberate system stacks above.
3. **F5 endpoints.** Include the conversation list/restore/delete and health endpoints now, or keep this batch frontend-only and leave retention where A08/P14 currently sit.
4. **Order.** If time is short, F1 and F2 carry the product requirement; F3 and F4 are the visible ones. Say which to protect.
