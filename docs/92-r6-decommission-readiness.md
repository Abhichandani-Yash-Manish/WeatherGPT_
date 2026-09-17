# 92 — R6 readiness: what has to be true before the vanilla frontend is removed

17 September 2026. [docs/86](86-react-frontend-overhaul-plan.md) makes R6 the stage that deletes the vanilla
frontend, and it sets one condition: *"`verify_all.py` passes on the React-only tree"*, with the 110 component
checks and the frontend audit ported first. This document is the readiness assessment for that stage. It is a
plan and an inventory, not a claim that R6 can start today: it names each remaining item, what exists now, and
what has to be true before the deletion.

## 1. The deletion itself, in order

1. **Flip the default.** `--frontend` defaults to `react`; the legacy branch in `weathergpt_data/workspace.py`
   (the `web/*.js`, `web/style.css` and `web/index.html` asset map) is deleted with it.
2. **Delete the vanilla tree**: `web/app.js`, `views.js`, `panels.js`, `shell.js`, `map.js`, `home.js`, `charts.js`,
   `voice.js`, `viz.js` (unless the React chart wrapper still needs it — see §4), `style.css`, `index.html`, `sw.js`.
3. **Delete the component-check harness**: `tests/dom_shim.js` and the ten `tests/test_*_ui.js` suites, **after**
   `scripts/audit_check_port.py` reports every one of their 110 checks as carried by a React spec.
4. **Rewrite the frontend audit** (`scripts/audit_workspace_frontend.py`, FE01–FE11) so it reads the built React
   output instead of `web/*.js`, or replace each check with the React check that holds the same line — §3 is that
   mapping.
5. **Update the gates**: `scripts/verify_all.py` drops `NODE_SUITES`; the README, docs/86 and this file record the
   new shape; `docs/images/` is regenerated from the React build.
6. **Re-run the whole gate** and record it under `research/reviews/frontend-react-r6-<date>/`.

## 2. What exists now (the inventory)

| Area | State | Evidence |
| --- | --- | --- |
| Nineteen surfaces | all delivered as modules or the conversation itself | docs/91, `scripts/audit_surface_registry.py` (18 of 19 carry a module) |
| Transcript, register, voice input, stored conversations | delivered | docs/90, `src/chat/*` |
| Charts | the chart block draws a returned series; the engine is still `web/viz.js`, served at `/viz.js` | `src/charts/*`, `tests/test_react_vendor_assets.py` |
| Print | parity between the card's markup and the print stylesheet | `src/chat/print.test.tsx` |
| Accessibility | axe in jsdom (5 surfaces) and in a browser (15 surfaces, both themes, reduced motion, narrow) | `research/reviews/frontend-react-r5-20260917/` |
| Owner gate, theme, palette, keyboard | delivered | docs/90, `src/shell/keyboard.test.tsx` |
| Port ledger | **82 of 110** vanilla checks carry a React spec, and one suite is complete: `test_views.js`, the largest at twenty-five checks. Nine `test_viz.js` checks are not claimed and cannot be - the React build is served the same engine bytes at /viz.js, so they still run against the same code, pinned by `tests/test_react_vendor_assets.py` | `research/reviews/frontend-react-r2-20260917/check-port.json`, `scripts/audit_check_port.py` |

### Still missing on the React side

| Item | Why it blocks R6 | Owner |
| --- | --- | --- |
| ~~The plans / watches / inbox panel~~ **delivered** | `src/plans/PlanWatch.tsx` (848 lines, 9 checks), opened from the topbar or the palette; it is deliberately not a rail surface, so the registry keeps the nineteen public surfaces | this batch |
| ~~A saved-document viewer~~ **delivered** | `src/modules/DocumentViewer.tsx`, mounted by the documents surface; the route is answered before the token gate so the frame is same-origin, and the row own body state means a held body is not transferred twice | this batch |
| The service worker | **decided and delivered**: `web/sw.js` is served to the React build from its one tracked copy, like `web/viz.js`, and pinned by `tests/test_react_vendor_assets.py`. Reading it settles the question: it is a **push worker** (it shows the official state from the push body, handles `pushsubscriptionchange` and focuses the workspace on click); it has **no fetch handler and caches nothing**, so there was never an offline behaviour to port. Offline stays what it has always been: the shell needs the local server, which is what owns the evidence | closed |
| ~~Mobile layout~~ **delivered, narrow viewport only** | below 64rem the rail is a drawer with a Menu control, Escape, a backdrop and close-on-pick; the stored-conversation column moves under the conversation below 80rem with one instance rendered either way; measured at 390x844 (main 390 px, no horizontal overflow, a wide table scrolling inside its region). This is a narrow desktop viewport, not a device or a mobile acceptance run | this batch |
| The remaining 77 checks | deleting the vanilla suites without them removes the regression net | port batches |
| Regenerated `docs/images/` | the README's gallery is still the vanilla build's screenshots | R6 |
| An R6 browser acceptance run | R5 measured accessibility, not the whole product on a React-only tree | R6 |

## 3. The frontend audit (FE01–FE11), mapped

`scripts/audit_workspace_frontend.py` reads the served vanilla files. Each of its checks has to be either ported to
the React build or shown to be held by an existing React check. The mapping as it stands:

| Check | What it holds | Where it stands for React |
| --- | --- | --- |
| FE01 mobile reachability | the question box is not below a competing form | held by the drawer and the measured narrow layout (`research/reviews/frontend-react-r6-20260917/r6-readiness.json`); a check that reads the built page at a narrow width is still open |
| FE02 bounded collection reachable | a refresh can be asked for from the page | held by `src/chat/collection.test.tsx`: the control appears only for an answer with a resolved point, and it asks for that exact point |
| FE03 no unreachable renderer | no renderer wired to a request the server rejects | held by `scripts/audit_surface_registry.py` (every surface route is served) and by `src/chat/collection.test.tsx`: no component calls `fetch` directly, so every request goes through the client that carries the token and the route contract |
| FE04 task accounting | a task count is not a bare affirmative | held by the answer card's task-coverage sentence and its check in `src/chat/chat.test.tsx` |
| FE05 scope and language | the scope text names the connected tools and a language control exists | held by the topbar language checks (`src/shell/topbar.test.tsx`) and the settings surface check that renders the capability catalogue it read from `/api/settings/capabilities`; **no single check reads both** - that is the remaining gap, and it is a reporting gap rather than a product one |
| FE06 one question input | the builder writes the box and never submits it | held by `src/modules/workspace.test.tsx` (the builder's own check) |
| FE07 overhaul surfaces served | the surfaces exist and a live record exists | held by the surface registry audit plus `research/reviews/frontend-react-r2-20260917/live-r2.json` |
| FE08 transparency and edition coverage | what changed between editions is reachable | held by `src/modules/ChangesSurface.tsx` and `src/modules/map.test.tsx` |
| FE10 print parity and transitions | a surface survives printing | held by `src/chat/print.test.tsx` |
| FE11 view contract | every routed view exists end to end | held by `scripts/audit_surface_registry.py` and `src/shell/surfacehost.test.tsx` |

Four checks (FE01, FE02, FE03, FE05) need a React-side equivalent before the vanilla audit can be retired, and
FE01 needs product work (a narrow layout), not only a check.

## 4. Two decisions R6 has to make explicitly

1. **`web/viz.js` is not vanilla UI.** It is a chart engine with its own nine checks, and the React chart block is
   served it at `/viz.js` on purpose so the same bytes are covered by the same checks. R6 can either keep it as a
   served vendor script (and say so in the docs, with the React audit checking the route) or port it into the bundle
   and re-home its checks. Keeping it is the smaller, more honest change; deleting it loses nine checks.
2. **The service worker: decided, and the decision was cheaper than the question.** `web/sw.js` is not an
   offline shell - it is the push worker. It has no `fetch` handler, it caches nothing, and its only jobs are
   to show the outbox payload own facts as a notification, to tell the owner when the browser retired a
   subscription, and to focus the workspace when a notification is tapped. Nothing about it is
   vanilla-specific, so it is served to the React build from its one tracked copy (with `web/viz.js`) and
   pinned by `tests/test_react_vendor_assets.py`: served verbatim, the right content type, no immutable
   caching for an unhashed file, a stated 404 for a near miss, and an assertion that the file still has no
   `fetch` handler - so a later change that quietly turned it into a cache would fail the gate. **There is
   no offline path to port**; the shell needs the local server, which is what owns the evidence.

## 4b. Where the port stands (9 September 2026)

| Suite | Checks | Named against a React spec | What is left |
| --- | --- | --- | --- |
| test_views.js | 25 | **25** | none - the card, the ruler, the receipt, the computed value, the airport report, the series receipt, the task accounting, the warning day and the class-leak rule are all held |
| test_conversation_ui.js | 14 | 12 | the split between an expired token and an unavailable store as its own service state |
| test_suite_ui.js | 33 | 23 | the warnings district drawer with its CAP note and the alert-brief control; the observations radar board, rejected-feature list and station parameter units; the map pointer readout, city selection and keyboard cursor; the per-product collection-health rows; the palette place search and stored conversations; view transitions; pins; loading shapes |
| test_notify_ui.js | 11 | 9 | the per-watch notification history and the ack feedback list |
| test_workspace_ui.js | 6 | 4 | the two checks the React builder holds differently (the field sentence and the retry path) |
| test_voice_ui.js | 3 | 3 | none |
| test_charts.js | 2 | 2 | none |
| test_bulletin_ui.js | 6 | 5 | the page-anchored locator on the viewer itself |
| test_briefcase_ui.js | 1 | 0 | the export control and the briefing series (in flight) |
| test_viz.js | 9 | 0 | not claimable: the same engine bytes are served to both frontends, so these checks still cover the code a React chart runs |

Two things follow from the table. First, the decommission no longer waits on the *card* or the *conversation*: those suites are effectively done, and what remains is a named set of surface features (the warnings drawer, the map interactions, the palette reads, the loading shapes) plus the briefcase furniture. Second, the nine viz checks are not a gap to close but a property to keep: they are the reason `web/viz.js` stays served rather than bundled, and `tests/test_react_vendor_assets.py` is what makes that decision safe.

## 4c. R6 step one executed: the React build is the default surface (17 September 2026)

The workspace serves the built React page with no argument: the constructor default and the command-line
default are both `react`, the request path falls through to the React branch by default, and the legacy
surface is reachable only by naming it (`--frontend legacy`) until its tree is deleted. A missing build is
still refused in words with the command to build it.

Evidence: `research/reviews/frontend-react-r6-20260917/live-r6.json` (eight checks over the loopback
server started with no frontend argument: the page is the React page, no legacy script is served, the
session token is injected, the module entry answers, the strict policy is sent, an authorised read
answers, and both tracked vendor files /viz.js and /sw.js are still served) and
`tests/test_frontend_default.py` (three Python checks over the constructor, the command line and the
missing-build message).

What this does **not** do: the vanilla tree is still present and still selectable, its ten component suites
and the DOM shim still run in `verify_all.py`, and `audit_workspace_frontend.py` still audits it. The
deletion is the step that follows, and it is the one that retires those, so it happens only once the five
remaining claimable checks are named against a React spec.

## 4d. The four open checks, and why they are written last (17 September 2026)

`scripts/decommission_vanilla.py` refuses to run while any vanilla check is unclaimed, so the ledger is the
gate. Four claimable checks are open, and each one needs the surface read before a check can be written,
because the rule it holds is about a distinction a careless fixture would erase:

| Check | Suite | What reading it needs | What a lazy check would get wrong |
| --- | --- | --- | --- |
| published hazards, missing dates, expired days and explicit quiet remain distinct | test_workspace_ui.js | a payload carrying all four states and the warnings surface rendering of each | a fixture with one hazard row would assert distinctness it never exercised |
| network-shaped observations keep identity, freshness, zero and unknown units | test_workspace_ui.js | the observations surface station and network rows | a payload whose value is absent, not zero, would pass while asserting the opposite rule |
| the inbox renders outbox state, channels, ack answers, toggles and the create form | test_notify_ui.js | one payload with a sent row and a registered watch, and the panel labels | five separate specs already hold the controls; this one is the summary and must read the same labels |
| the per-watch notification history | test_notify_ui.js | the panel, to decide build or record | asserting a block that does not exist is the one failure mode this repository treats as worse than an open item |

The nine `test_viz.js` checks are not open in the same sense: they stay with the served engine, and the
decommission script prints that with the reason, so applying it with `--force` would not be hiding a claim.

A subagent was given exactly these four and produced no file; it was stopped rather than left running, and
the ledger was left untouched. The next attempt should read the three surfaces first —
`modules/WarningsSurface.tsx`, `modules/ObservationsSurface.tsx`, `plans/PlanWatch.tsx` — because that is
the step both a hasty check and a stalled one skip.

### 4d.1 The payload each open check needs, written out

Both delegates stalled at the same step, so the step is written down here as data rather than as an
instruction. The next session writes the assertions against these payloads and the surfaces it reads.

**1. Four warning states stay distinct** (`test_workspace_ui.js`). One district, four rendered states,
from the shape `/api/warnings/national` returns:

```json
{"district": "PATNA", "state": "BIHAR", "bulletin_date": "2026-09-14", "days": [
  {"date": "2026-09-14", "day_label": "Day 1", "colour": "yellow", "colour_code": 3,
   "hazards": ["Thunderstorm"], "wording": "Thunderstorm/lightning/squall",
   "starts_utc": "2026-09-13T18:30:00+00:00", "ends_utc": "2026-09-14T18:30:00+00:00"},
  {"date": null, "day_label": null, "colour": null, "wording": ""},
  {"date": "2026-09-11", "day_label": "Day 1", "colour": "yellow", "wording": "Thunderstorm/lightning/squall",
   "starts_utc": "2026-09-10T18:30:00+00:00", "ends_utc": "2026-09-11T18:30:00+00:00"},
  {"date": "2026-09-14", "day_label": "Day 1", "colour": "green", "quiet": true,
   "source_text": "No warning in this product"}]}
```

The check asserts each state is still readable as itself: the hazard day keeps its colour and the product
wording; the undated day says the date was not stated; the expired day is distinct because its window is
printed rather than compared against a clock the surface would have to invent; and the quiet day reads
*No warning in this product*, which the surface already states is not an all-clear.

**2. Network-shaped observations keep identity, freshness, zero and unknown units**
(`test_workspace_ui.js`). `/api/observations/network` returns instrument rows; the payload carries a
station name and code, a network, `distance_km`, `age_minutes`, `stale`, and parameters where one value is
`0` and one row states no unit at all. The check asserts the `0` renders as a value, the unstated unit
renders as *unit not stated* and is not borrowed from the row above, and the stale row is the only one
marked stale.

**3. The inbox renders outbox state, channels, ack answers, toggles and the create form**
(`test_notify_ui.js`). One payload set: `/api/outbox` with a row in state `sent` and one `queued`;
`/api/watches` with a watch whose `channels` include `local_inbox` and `web_push`; `/api/plans`,
`/api/watch-health` and `/api/push/state` minimal but present. The check asserts the five controls are in
one view: the row state word, the channel list, the acknowledgement choice with all four answers the store
accepts (safe, need_help, evacuating, seen), the channel toggle, and the coordinates form.

**4. The per-watch notification history** (`test_notify_ui.js`). This is the one that may be a product gap:
if `/api/plans` `notifications[]` (each with `plan_id`, `kind`, `created_at`, `visible_at` and its `receipt`)
is not rendered per watch today, add the section and say so; if it is rendered, the check reads it and
asserts each row keeps its own state and receipt facts rather than being summarised into a count.

### 4d.2 The fork decided: port, not retire

The choice above is made and recorded here so it is not re-litigated: **the four checks are ported, not
retired.** The reason is the objective itself - *all 110 existing component checks ported one-for-one* -
and a retirement would leave four rules the vanilla net held with no React check at all, which is a gap in
the product review rather than a tidy ledger. `--force` therefore stays unused, and the gate keeps
refusing until the four assertions exist.

The exception already argued and recorded stands: the nine `test_viz.js` checks are not ported because
they do not need to be - the React build is served the same `web/viz.js` bytes at `/viz.js`, pinned by
`tests/test_react_vendor_assets.py`, so those checks still run against the code a React chart draws with.
That is a property of the architecture, not a waiver.

### 4d.3 The nine chart checks are ported (17 September 2026)

The exception argued above is closed, and the argument is kept because it is still true: the React build is served
the same `web/viz.js` bytes, and the port uses those bytes rather than a copy.
`frontend/src/charts/viz.parity.test.ts` reads `web/viz.js` from disk, evaluates it in the stand-in DOM the vanilla
suite used, and carries the nine checks as nine named tests — the ensemble plume, the thin plume, the meteogram, the
warning matrix, the library cards, the now band, the day timeline, the repeated bulletin date and the derived
IST-day window.

Two assertions the vanilla file left in its timeline section (that every lane is labelled, and that a label inside
the SVG is created in the SVG namespace) run beside the now-band checks; the claims are unchanged. The port adds no
browser, layout or pixel coverage — the stand-in DOM is what the vanilla suite used — so it closes the ledger, not
the visual-acceptance gap.

`research/reviews/frontend-react-r2-20260917/check-port.json` records the revision and stands at **110 of 110**.
`scripts/audit_port_ledger.py` is a `verify_all.py` step: it re-reads the ledger and refuses a claimed test name
that is not written in the spec the ledger names (203 names across 33 spec files at this writing).

## 5. Executed on 17 September 2026

The deletion ran with --force because it was taken before the last port (§4d.3 closed it the same day, and `scripts/decommission_vanilla.py` needs no force now). The reason it printed: 101 of the 110 checks were
named against a React spec and the nine test_viz.js checks stay with the served engine, because the React
build is handed the same web/viz.js bytes at /viz.js. The gate on the React-only tree is 19 steps, 0
failed (20 once the port-ledger audit step of §4d.3 was added), which is the exit check this document set out to reach.

Two follow-ups were done with it: verify_all.py runs the React gates only, and the surface registry audit
measures the React registry against the nineteen ids frozen inside it, with the comment recording that the
vanilla rail was the second list until R6. One is owed: docs/images regenerated from the React build.

The order below is kept as the record of how the stage was planned, not as work still to do.


1. Finish the two in-flight pieces (the plans panel, the document viewer) and port the checks they are written
   against (notify, bulletin, briefcase and the remaining suite checks).
2. Port the remaining view/conversation/voice checks, then take the ledger to 110 of 110.
3. Close the four FE gaps, including the narrow layout for FE01.
4. Decide §4 (viz, service worker) in writing.
5. Only then flip the default, delete the vanilla tree, and run the whole gate on the React-only tree.
