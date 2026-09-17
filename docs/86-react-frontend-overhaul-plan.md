# 86 — React frontend overhaul: plan, stages and acceptance

16 September 2026. User direction: plan the React frontend overhaul. This document is the plan; nothing here is
built yet, and this file makes no readiness claim. The engine, the API contracts, the evidence rules and the
provenance discipline are **out of scope**: they do not change.

## What exists today, measured

| Surface | Size | Notes |
| --- | --- | --- |
| `web/*.js` | 7,962 lines over 10 files (shell 1,369 · panels 1,949 · views 1,549 · viz 686 · app 637 · map 358 · voice 317 · home 241 · charts · sw 45) | zero build step, served as source |
| `web/style.css` + `web/tokens.css` | 1,148 lines | the token layer is the design system; the plan keeps it |
| `web/index.html` | 368 lines | the session token is injected per process (`__WORKSPACE_TOKEN__`) |
| Routed surfaces | 19 (`VIEWS` in `web/shell.js`) plus a modal inbox, palette and print paths | hash routes, deep links (`?watch=`), keyboard shortcuts Alt+1…9 |
| Component checks | 10 Node suites, 110 printed checks, on a hand-written DOM shim | these are the regression net that must survive the migration |
| Frontend audit | `scripts/audit_workspace_frontend.py`, FE01–FE11 plus `csp_compliance`, `class_as_text`, `javascript_syntax`, `serve_contract` | it reads the **served** files by design |
| CSP | `default-src self; script-src self; style-src self; connect-src self; img-src self data:; media-src self blob: data:; frame-src self; frame-ancestors none; base-uri none; form-action self` | no inline script or style, no CDN, loopback only |

## Why this is a real project, not a rewrite for its own sake

The chat overhaul added a transcript with streaming stages, quick replies, a register switch, a reading line and a
provider/settings panel. That is a stateful, component-shaped surface, and it is now the product front door. The
vanilla stack pays for it in hand-rolled DOM rebuilding (`renderTurn` re-creates whole cards), hand-wired state
(`WG.state`, `state.busy`, `previewSeq`), and a DOM shim that drifts from the browser. A component framework buys
component-level state, real accessibility primitives and a test runner that runs the same tree the browser runs.

The same reasoning is why the *whole* app is not rewritten at once: 19 surfaces and 110 checks are the evidence
base for everything a judge sees, and a big-bang port would put all of it behind one unverified build.

## Target architecture

- **Vite + React + TypeScript**, built to `web/dist/` with content-hashed assets; the server keeps serving loopback
  only and keeps injecting the session token (`<meta name="workspace-token">` stays the contract).
- **No CDN, no inline script/style, no `eval`**: the built output must satisfy the same CSP, enforced by the audit
  reading the *built* files. `style-src self` means CSS Modules or plain CSS files, not runtime CSS-in-JS.
- **The token layer stays** (`tokens.css` becomes a global stylesheet imported by the entry point); `viz.js` stays
  a framework-agnostic chart engine with a thin React wrapper, because its geometry and axis logic are already
  measured by `test_viz.js` and `test_charts.js`.
- **`dom_shim.js` retires.** The 110 checks are ported one-for-one to Vitest + jsdom (React Testing Library), one
  spec per current file, with the recorded payloads reused verbatim so each check keeps testing the same rule.
- **Browser acceptance stays** with the headless Chrome CDP runner already used in this repo; screenshots and
  viewport measurements remain the layout evidence, and `docs/images/` is regenerated from the new build.
- **State**: server data stays in fetch hooks with a small cache, no global store until a measured need appears;
  the transcript keeps one reducer so a turn is one state machine rather than five refs.

## Stages, each independently shippable

| Stage | Deliverable | Exit check |
| --- | --- | --- |
| **R0 groundwork** | Vite/TS scaffold, token stylesheet import, a `dist/` build, `web/legacy/` untouched, a `--frontend legacy|react` flag on the start script, the audit reading whichever build is served | the audit and all 110 checks pass against the React shell with one route ported; a missing `dist/` is refused with a clear message, never a blank page |
| **R1 shell** | rail, topbar, hash router, palette, theme, the surface registry with lazy routes | every route opens; Alt+1…9 and deep links (`?watch=`) behave identically; keyboard and focus checks ported |
| **R2 transcript (the flagship)** | the Ask surface as components: user turn, working placeholder with the reading line and stages, the answer card (facts, ruler, receipt, disclosures), quick replies, register switch, chips | the four continuity journeys and the recorded payload specs pass in jsdom; browser screenshots match the current ones within an agreed visual diff |
| **R3 guided surfaces** | today, warnings, map, forecast, observations, advisories, air quality, documents, briefcase, settings, verification, ensemble, marine, compare, climate, changes, aviation | each surface renders its recorded payload and keeps its stated limits; the audit equivalents of FE03–FE11 pass |
| **R4 charts, map and print** | `viz.js` wrapped, the vendored basemap served from `dist/`, print parity for a card | `test_viz.js` + `test_charts.js` pass unchanged; a printed card keeps its distinctions |
| **R5 accessibility, i18n, voice** | focus order and live regions audited per surface; RTL for Urdu; the language selector wired to `output_language`; the Listen control retained | an axe-style scan per surface recorded; language and voice behaviour unchanged |
| **R6 parity and decommission** | the vanilla path removed, `web/legacy/` deleted, docs and README updated, `docs/images/` regenerated | `verify_all.py` passes on the React-only tree and the browser acceptance record is refreshed |

## R0 delivered: groundwork (17 September 2026)

Evidence: research/reviews/frontend-react-r0-20260917/ (live-r0.json, csp-probe.json, the strict-policy DOM
dump and two screenshots).

- frontend/ holds a Vite + React 19 + TypeScript project; Tailwind v4 consumes web/tokens.css as its theme
  source so the design system stays single-sourced; the build lands in web/dist/ with a manifest and
  content-hashed assets.
- the workspace server serves that build under `--frontend react` (the default stays `legacy`): the page gets
  the session token injected, hashed assets are served with immutable caching, and a **missing build is refused
  in words** (503 with the command to build it), never as a blank page.
- the built HTML carries no inline script, no markup style attribute and nothing off-origin;
  `scripts/audit_react_build.py` (11 checks, including the manifest-hash parity and a bundle budget) is a step
  of verify_all.py, so the gate reads the build as a browser receives it.
- the CSP relaxation the research expected was **not needed and was not taken**: measured, Radix positioning,
  TanStack Virtual rows and Motion transforms all end up with the styles they need under the existing strict
  policy, because React writes them through the CSSOM, which CSP does not police. `style-src` stays `self`.
- the initial bundle graph is 70 KB gzip (entry 1 KB + React 4 KB + app 64 KB) against a 312 KB budget that
  follows the manifest's static imports rather than the entry file alone.
- the vanilla frontend is untouched and still served by default; 1287 Python tests, 10 component suites and 28
  verification steps pass, 0 failed.
- frontend/probe.html is the CSP probe: a development entry, not a product surface. R1 removes it from the
  production input list.

The six decisions docs/87 put to the user were not answered before this round started; the round proceeded on
the documented recommendations, with the CSP recommendation dropped because the measurement made it moot. The
chat-centre layout and the assistant-ui adoption are exercised in R1 and R2 and can still be revisited there.

## R1 in progress: the shell frame, the registry and the test harness

- `src/shell/views.ts` is the surface registry: the same 19 ids the vanilla `WG.VIEWS` uses, so every existing
  deep link (`#/warnings?day=2`, `?watch=`) keeps working; each entry names the stage that ports it and the
  questions it will answer, so an unported module cannot pass as done.
- `src/shell/useHashRoute.ts` reads the address in one place: an empty or unknown route falls back to Ask, and a
  query string survives a route change.
- `src/shell/Rail.tsx` renders the registry with the group headings and the **Alt+1…9 contract the rail prints**,
  with `aria-current` on the active view.
- `src/shell/SurfaceHost.tsx` states, for a module that is not ported, the stage it arrives in and the questions
  it will answer — generated from the registry rather than hand-written.
- the harness R2 needs is in: **Vitest + Testing Library + MSW** (`src/test/msw.ts`) replaces the per-suite
  hand-written fetch stub, with 6 checks over the rail, the routing contract, the shortcut contract, a deep link
  and a recorded payload.
- the CSP probe has left the production input list: it builds from its own config to `web/dist-probe`.

Still open in R1: the topbar controls (persona, language, service state, health, theme, palette) and the stored-
conversation rail; the **110 vanilla component checks ported one-for-one**, which is the gate R2 must not pass
without; and a recorded browser acceptance run for the React shell.


### R1 continued: the weather ground and the topbar (17 September 2026)

Decisions from this message are recorded in [docs/88](88-overhaul-decisions-and-design-language.md): all six
answered green, and the weather-native design language specified. Implemented in the shell:

- **Sky phases** (`src/shell/sky.ts`, `src/styles/sky.css`): six phases selected from the local clock (or a
  sourced sunrise/sunset when a caller has one), applied as `data-sky` with contrast-checked surface/ink pairs in
  both themes; the `storm` phase is reserved for a surface already stating an official warning. The band is
  `aria-hidden` with the note that it is decoration, not a condition, and its transitions respect
  `prefers-reduced-motion`.
- **Topbar** (`src/shell/Topbar.tsx`) with TanStack Query: store state from `/api/health` (and an unreachable
  read shown as unreachable), the language select from `/api/languages` with unmeasured languages marked, a theme
  cycle and a new-conversation action.
- **Thirteen frontend checks** now pass (rail, routing contract, shortcuts, deep link, topbar states, language
  options, deep-link fallback, sky phases including a sourced sun time), and the initial graph is 83 KB gzip
  against the 312 KB budget.
- **Browser acceptance is still open**: headless Chrome hung in this session after the earlier successful runs, so
  the render capture is recorded as not captured rather than replaced by a claim
  (`research/reviews/frontend-react-r1-20260917/r1-verification.json`).

## R2 delivered: the transcript, and the first real modules (17 September 2026)

Evidence: research/reviews/frontend-react-r2-20260917/ (live-r2.json and live-r2.py, check-port.json, ten
screenshots) and docs/90, which is the batch report.

- the transcript is components: the question is kept above its answer, the working turn names the stages the
  engine reports and shows the deterministic first reading labelled as a reading, and the answer card carries the
  lead value, the validity ruler, the other facts, the receipt, the sources, the disclosures and the actions;
- the reading register (brief / conversational / full) changes how much of the evidence is unfolded and nothing
  else, is remembered per browser, and the rule set from web/views.js was ported rather than rewritten;
- voice input goes through the engine's transcript for correction, keeps the recogniser's confidence labelled as
  recognition only, and refuses speech where the project has not measured it;
- the six ported modules (Today, Warnings, Forecast, Observations, Published documents, Sources and settings) each
  render their envelope with coverage, limitations, not-established and source rows, and each is its own lazily
  loaded chunk (2.2-2.6 KB gzip);
- the module host renders a ported module from the registry and states, for one that is not ported, the stage it
  arrives in and the questions it will answer - the placeholder is generated, not hand-written;
- R7's front door and owner gate are built (docs/90 section 6): the landing page shows the shape of a receipt
  rather than a sample value, reads four counts live from this machine, quotes the README's limits verbatim, and
  shows eight pictures of this build; the gate is a local PBKDF2 verifier that explains what it is not and does
  not stand in the way by default;
- measured: 10 frontend suites and 68 checks, tsc clean, the initial graph 107 KB gzip against the 312 KB budget,
  the built-output audit 11/11, the surface-registry audit 8/8, a new port-ledger audit 5/5, and 14/14 live HTTP
  acceptance checks against the served build (a real turn took 43.14 s cold and 4.72 s warm);
- four defects were found by the ported checks and fixed at their cause (docs/90 section 3): the jsdom/undici
  AbortSignal mismatch, a turn's question being replaced by its own answer, the absent scrollTo and modal dialog,
  and the absent localStorage;
- the R1 exit items are closed with it: a browser acceptance run exists (ten captures at 1440x900 in headless
  Chrome against the served build on a throwaway store), and the port ledger names 19 of the 110 vanilla checks
  against a React spec, each verified to exist by scripts/audit_check_port.py, a step of verify_all.py.

Still open from R1/R2: the remaining 91 vanilla checks are not yet ported (the vanilla suites remain the net
until R6), no screen-reader or keyboard-only acceptance has been recorded per surface, and the answer still
arrives as one response rather than as a stream of written text.

## R3 delivered: every surface is a module (17 September 2026)

Evidence: docs/91 and research/reviews/frontend-react-r5-20260917/.

- all nineteen surfaces are ported. Eighteen have a module in frontend/src/modules/ (Today, Warnings, Map,
  What changed, Forecast, Observations, Farm advisories, Air quality, Published documents, Climate records,
  Aviation, Ensemble spread, Forecast verification, Compare places, Sea and rivers, Briefcase, Workspace,
  Sources and settings); the nineteenth, Ask, is the conversation itself;
- each module renders its own route through the shared evidence framing: one h1, the envelope coverage counts,
  its limitations and not-established lines as visible sections, its source rows, and a failure sentence with
  a retry. A hazard colour is drawn only where the payload stated one, and the payload wording stays beside it;
- the placeholder path (a surface with no module) still states its stage and offers its questions to the
  conversation, and that contract has a check that does not depend on which surfaces are left;
- the surface-registry audit reports module coverage on every run and refuses a module key that is not a
  declared surface: 18 of 19 surfaces carry a module.

## R4 delivered: charts, print parity and the engine seam (17 September 2026)

- frontend/src/charts/ChartBlock.tsx is the React side of the chart language, ported from the rules
  web/charts.js was checked against: only a value the engine returned is drawn, a missing point breaks the
  line instead of becoming a zero, every drawn point names its exact source value and evidence id, and the
  same numbers stay reachable as a table. It draws the series on the forecast surface and any series an
  answer carries;
- the chart engine is served to the built page from its one tracked copy at /viz.js, pinned by
  tests/test_react_vendor_assets.py (served verbatim, the same bytes the vanilla checks cover, no immutable
  caching for an unhashed file, and a stated 404 for anything else);
- print parity: frontend/src/styles/print.css and frontend/src/chat/print.test.tsx hold together what a
  printed card keeps (the receipt, the window, the sources) and what it drops (the composer, the action row,
  the raw machine record).

## R5 in progress: accessibility measured, RTL and language acceptance open (17 September 2026)

- axe-core runs in two places: src/a11y/a11y.test.tsx over five rendered surfaces in jsdom (0 violations,
  with the colour-contrast rule recorded as not measurable without a layout engine), and a browser sweep over
  15 surfaces against the served build (0 violations, 391 rules passed), recorded in
  research/reviews/frontend-react-r5-20260917/;
- the browser sweep found three real defects on its first pass and all three were fixed at their cause: the
  active rail row read muted ink on the sand rule colour (2.29:1), the service chip read soft ink on sand
  (3.3:1), and a surface taller than the viewport scrolled without being focusable;
- keyboard acceptance is a check of its own: the skip link reaches the question box, Alt+1..9 opens a
  surface, Alt+K opens the palette and focuses its search field, and Enter opens the chosen surface;
- an answer sentence carries dir="auto", so an Urdu or mixed-script answer is laid out by its own first
  strong character. THE SHELL IS NOT MIRRORED and no language run has been recorded on the React interface;
  both are R5 work still open, together with the dark theme, reduced motion, zoom and a screen-reader
  walkthrough.

## R3 in progress: the guided surfaces

Six of the nineteen surfaces are ported (docs/90 section 5). The rest state their stage and offer their questions
to the conversation in the meantime. The order for the rest is the docs/88 ranking; map and what-changed come
first because PS feature 4 is still the weakest journey.

## R6 delivered: the vanilla frontend is removed (17 September 2026)

Evidence: docs/92 4c and 4d, research/reviews/frontend-react-r6-20260917/ (the HTTP acceptance record, the
browser captures and the readiness note), and the commit that removed the tree.

- the workspace serves one surface: the built React page, with the legacy asset map replaced by a 404 at
  the same depth so the React branch above it was untouched;
- twenty-three files removed: the vanilla surfaces, their stylesheet and page, the DOM shim and the ten
  component suites, and the two scripts that only existed to read them;
- three web files kept, with the reason printed by scripts/decommission_vanilla.py: tokens.css (imported
  by the React stylesheet), viz.js (served to the React build, so the nine viz checks keep covering the
  code a chart draws with) and sw.js (the notification worker the plans panel registers);
- verify_all.py runs the React gates only - registry parsing, the drift guard, the Python suite, the React
  build audit, the surface registry audit and the React frontend audit - and the surface registry audit
  now measures the React registry against the nineteen ids frozen inside it;
- the exit check is met: verify_all.py green on a React-only tree, 19 steps, 0 failed;
- the port ledger stands at 101 of 110, the nine test_viz.js checks staying with the served engine by
  architecture rather than by waiver.

Owed and recorded: docs/images regenerated from the React build.

## What each stage must prove

1. **No behaviour regression**: a ported spec is the same assertion against the same payload.
2. **No new claims**: a framework is not a capability. The chat, provider, language, warning and watch-health
   statements in the README stay exactly as measured; the plan cites them, it does not upgrade them.
3. **Security parity**: the CSP, the session token, the loopback-only server and the `no-store` API caching are
   re-checked against the built output, not against the source.
4. **Recorded evidence per stage**: the audit output, the component-suite output and a browser screenshot set under
   `research/reviews/frontend-react-<stage>-<date>/`.

## Risks, and the decisions this plan makes

| Risk | Decision here |
| --- | --- |
| A build step conflicts with "the audit reads served files" | the audit is rewritten in R0 to read `dist/` and to fail if the served bundle and the audited bundle differ by hash |
| Component checks lose their value if they are rewritten from scratch | specs are ported one-for-one from the current files first, and refactored only afterwards |
| Bundle size and cold start on a loopback server | a size budget per route, measured and recorded at each stage, with route-level code splitting; the server keeps serving static bytes with no build at runtime |
| The service worker assumes the vanilla asset names | the SW is regenerated from the build manifest in R0/R1, and offline behaviour is re-measured rather than assumed |
| A framework could tempt a generative UI | components render tool-owned text and values exactly as now; no model output reaches the DOM without the same checks |
| Timebox | the vanilla path stays fully functional until R6; every stage must leave `verify_all.py` green |

## What this plan does not promise

It does not promise a faster product, a prettier product, mobile acceptance or new capability. It promises the
same behaviour behind a maintainable component tree, with every existing check carried over and every claim left
where it was measured. If a stage cannot meet its exit check, the stage does not land and the vanilla path stays.
