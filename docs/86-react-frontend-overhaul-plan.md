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
