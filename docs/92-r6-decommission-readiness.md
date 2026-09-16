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
| Port ledger | **33 of 110** vanilla checks carry a React spec | `research/reviews/frontend-react-r2-20260917/check-port.json` |

### Still missing on the React side

| Item | Why it blocks R6 | Owner |
| --- | --- | --- |
| The plans / watches / inbox panel | the vanilla frontend reaches watch state, delivery rows and the push control; the React frontend has no equivalent yet (in flight: `src/plans/PlanWatch.tsx`) | this batch |
| A saved-document viewer | the vanilla frontend opens a stored PDF in place and states a pruned body; the React documents surface lists editions only (in flight: `src/modules/DocumentViewer.tsx`) | this batch |
| The service worker | `web/sw.js` gives the vanilla frontend an offline shell. Either port it against the built manifest or drop offline deliberately and say so; **this decision is not made** | R6 |
| Mobile layout | the rail is a fixed 224 px column; at a 390 px viewport the conversation is cramped. FE01 (mobile reachability) has no React equivalent yet | R6 or a mobile batch |
| The remaining 77 checks | deleting the vanilla suites without them removes the regression net | port batches |
| Regenerated `docs/images/` | the README's gallery is still the vanilla build's screenshots | R6 |
| An R6 browser acceptance run | R5 measured accessibility, not the whole product on a React-only tree | R6 |

## 3. The frontend audit (FE01–FE11), mapped

`scripts/audit_workspace_frontend.py` reads the served vanilla files. Each of its checks has to be either ported to
the React build or shown to be held by an existing React check. The mapping as it stands:

| Check | What it holds | Where it stands for React |
| --- | --- | --- |
| FE01 mobile reachability | the question box is not below a competing form | **open** — no React equivalent; needs a narrow-viewport check on the built page |
| FE02 bounded collection reachable | a refresh can be asked for from the page | held by the answer card's "Collect fresh evidence" control; **not yet a check** |
| FE03 no unreachable renderer | no renderer wired to a request the server rejects | held in spirit by `scripts/audit_surface_registry.py` (every surface's route is served); a renderer-level check is **open** |
| FE04 task accounting | a task count is not a bare affirmative | held by the answer card's task-coverage sentence and its check in `src/chat/chat.test.tsx` |
| FE05 scope and language | the scope text names the connected tools and a language control exists | held by the topbar's language control and each module's limits section; **no single check reads both** |
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
2. **The service worker.** Offline behaviour was never measured for the React build. The honest options are to port
   `sw.js` against the built manifest with a measured offline run, or to drop offline and state it in the README's
   limits. Porting it without measuring the result would be the one option this repository does not take.

## 5. The order this suggests

1. Finish the two in-flight pieces (the plans panel, the document viewer) and port the checks they are written
   against (notify, bulletin, briefcase and the remaining suite checks).
2. Port the remaining view/conversation/voice checks, then take the ledger to 110 of 110.
3. Close the four FE gaps, including the narrow layout for FE01.
4. Decide §4 (viz, service worker) in writing.
5. Only then flip the default, delete the vanilla tree, and run the whole gate on the React-only tree.
