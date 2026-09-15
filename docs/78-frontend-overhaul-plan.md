# Frontend overhaul: from working prototype to flagship instrument

15 September 2026. The user asked for a major frontend overhaul with flagship ambition, creative and
technical freedom, and a phased plan. This document is the plan; [DESIGN.md](../DESIGN.md) is the
design system it commits to. Nothing here relaxes the standing rules: no invented number, score,
confidence or source, credentials stay local, hosting stays held, and every claim keeps its entity,
window, unit and provenance.

## 1. What is actually wrong today (measured, not vibes)

| Observation | Measurement |
|---|---|
| The surface is functionally complete and visually flat. | 6,883 lines across `web/`; 67 CSS custom properties; 18 media queries; one dark theme. |
| There is exactly **one** chart primitive. | `web/charts.js` is 31 lines and renders a single series with clickable points; meteogram, fan/plume, matrix and sparkline do not exist. |
| The strongest asset — provenance — is rendered as a receipt *and* a disclosure list. | Every answer already carries facts, citations, locators and limits; none of it is choreographed. |
| Navigation is a rail of 17 views with no spatial memory. | `VIEWS` list + static rail; no pinned places, no recent evidence, no cross-surface continuity. |
| Motion is absent outside the drawer. | No view transitions, no chart draw-in, no skeletons beyond a text label. |
| The wow ceiling is set by the old chart engine, not by the data. | The engine returns ensemble member statistics, hourly multi-parameter series, district-day warning matrices and a 588-document corpus — all of it rendered as tables and single lines. |

**Conclusion.** The gap is not the data platform; it is the visual and interaction layer. That is where
the overhaul spends its effort.

## 2. The stack question, answered with numbers

| Option | What it buys | What it costs here |
|---|---|---|
| **A. Keep the no-build runtime** (Python-stdlib server + hand-written ES5-era modules) and invest everything in design, charts and shell. | No build step, no npm, offline by construction, CSP `script-src 'self'` already satisfied, all 1,139 Python tests, nine component suites, the DOM shim and the static serve-contract audit keep working unchanged. | Nothing structurally; the ceiling is our own craft. |
| **B. Migrate to a bundled framework** (Vite + React/Svelte). | Familiar component model, ecosystem. | A full rewrite of 6,883 lines of working product UI; a build toolchain and lockfile in a repo whose whole story is 'clone, venv, run'; the served-asset contract, the DOM-shim suites, the static audit and the CSP story all rewritten; and **no user-visible capability that option C cannot deliver**. |
| **C. No-build, modern platform** (chosen): keep the runtime, adopt tokens, CSS container queries, `view-transition` API with fallback, Web Animations, ES modules where they help, and build our own chart engine. | Flagship visual quality, motion and signature charts with zero new dependencies; every existing verification stays meaningful. | We own the component and chart layers — that is the work this plan budgets for. |

**Decision: option C, with the framework path left open.** A framework migration is a *presentation-layer*
choice that would cost the repo its verifiability and gain nothing the platform APIs do not already give.
If a framework is ever wanted for collaboration reasons, it becomes its own documented batch with a
compatibility shim for the served-asset contract and a measured before/after on the component suites.

## 3. Design principles

1. **An instrument, not a dashboard.** The surface should feel like a well-made measuring device: quiet
   chrome, precise type, data that is legible at a glance and inspectable on demand.
2. **Evidence is the ornament.** No decorative gradients or invented gauges. The beauty comes from
   arranging real facts: the validity ruler, the member plume, the district matrix, the printed issue date.
3. **Model output looks modelled.** Solid strokes for observations and published text, dashed for model
   output, banded for member spread, straight to gaps where a value is missing — never interpolated.
4. **Unknown is a first-class state.** Every surface must be able to say 'not read', 'not connected',
   'unknown' as attractively as it says a value.
5. **Motion explains, never decorates.** Transitions show where a surface came from or that new evidence
   arrived. Reduced-motion users get the same information instantly.
6. **Keyboard first, pointer optional.** Every surface is reachable and operable from the palette.

## 4. The wow inventory (what 'flagship' means here)

| Signature moment | Built from (already in the engine) |
|---|---|
| **Ensemble plume** — a fan of p10–p90 around the median with min/max whiskers and member count. | `/api/ensemble` parameters (`*_mean`, `*_spread`, `*_p10`, `*_p50`, `*_p90`, `*_min`, `*_max`) and `member_total`. |
| **Meteogram** — one stacked timeline: temperature line, precipitation bars, wind arrows, humidity band, day/night shading, hover crosshair with exact source values. | Hourly forecast parameters from `/api/forecast`. |
| **District warning matrix** — the national product as a colour grid over district-days, click to a district sheet. | `/api/warnings/national` day rows and colours. |
| **Interactive validity ruler** — the existing ruler becomes a scrubber: drag the window and watch which source hours are covered, which are missing, and where the model begins. | Answer windows and covered-hour lists already returned with facts. |
| **Corpus library** — the 588 indexed editions as cards with printed issue date, family ribbon, page count and body state; opening one shows the reader pane and the retained pages. | `/api/corpus` and `/api/documents/<sha>`. |
| **Radar constellation** — the 39-station status board drawn as a map with verbatim status and remarks. | `/api/radar` stations (coordinates repaired in docs/76). |
| **Receipt as artifact** — a designed evidence receipt with copy, print and JSON download, and hover-linked provenance from any number to its source row. | Facts, citations, locators already attached to answers. |
| **Place memory** — pinned places with a small 'last read' sparkline, and a compare tray that puts two places' windows side by side. | Conversation ledger, forecast points, `/api/places/search`. |

## 5. Phases, deliverables and exit criteria

### P0 — Direction and decision (this batch)
Deliverables: this plan, `DESIGN.md`, the goal record. Exit: the stack decision and the design system are
written down and reviewable.

### P1 — Foundation: tokens, type, chrome, motion
Deliverables: `web/tokens.css` (colour, type, space, radius, elevation, motion, chart palette); a
restructured `style.css` consuming tokens; shell chrome (context bar with place, freshness and planner
chip; sectioned rail; view transitions with a reduced-motion fallback); skeletons for every surface;
focus-visible and contrast pass. Exit: all nine component suites and the static audit green, the page
renders on tokens alone, text contrast ≥ 4.5:1 measured, and no surface regresses in its component check.

### P2 — Signature visuals (chart engine v2)
Deliverables: `web/viz.js` — SVG primitives (axes, bands, bars, lines, day/night shading, crosshair,
annotation); composites: meteogram, ensemble plume, warning matrix, sparkline; wired into Forecast,
Ensemble, Warnings and the new surface. Exit: node suites assert that a chart never invents a value, gaps
stay gaps, and every drawn point carries its `source_locator`; a component check fails if an interpolated
point appears.

### P3 — Command-centre shell
Deliverables: a 'Now' hero surface (place, sky state, warning ribbon, next hours, pinned memory);
map-centric exploration (hover readouts, click-to-pin, layer legend, basin/radar overlays); a unified
timeline across warnings, observations and model hours; palette actions (pin place, compare, open
evidence, jump to corpus). Exit: every action is keyboard-reachable; the palette lists them; the surface
still states what is not connected.

### P4 — Craft and trust polish
Deliverables: designed empty/error/loading states; the receipt artifact (copy/print/JSON) with hover-linked
provenance; print stylesheet; micro-interactions (chart draw-in, crosshair, staggered rows) all under
reduced-motion rules; performance budget measured (first paint, layout stability, animation frame time).
Exit: the budget is recorded with its numbers or with an honest 'not measured'.

### P5 — Acceptance and evidence
Deliverables: live browser journeys with light/dark screenshots at three viewports; a11y scan; updated
README screenshot and capability text; registry and doc updates; a stated list of what none of it proves.
Exit: recorded evidence exists for each surface, or the record says the sandbox blocked the run — as it
did for the last two batches, where Chrome could not be launched.

## 6. Risks and how they are handled

- **Charm over claim.** Every visual is a transformation of returned fields. A chart that would need a
  number the engine does not return gets a designed *absence*, not an estimate.
- **Regression risk.** The component suites are the contract; each phase must keep all of them plus the
  static audit green, and new suites are added for new primitives.
- **Performance risk.** Hand-rolled SVG can be slow at 600 points; the chart engine caps rendered points
  and keeps exact values in the table, so nothing is lost when a series is decimated.
- **Browser verification.** This sandbox cannot launch Chrome, so phases are verified by component suites
  plus loopback checks until a browser-capable environment exists; the record says which.
- **Scope creep.** Each phase ships a reviewable artefact and its own evidence; the plan can stop after any
  phase without leaving the product in a half-state.

## 7. What this plan does not do

It does not change the engine, the sources, the evidence rules or the deployment model. It does not
promise mobile or hosted delivery, does not add a framework, and does not turn a prototype check into a
skill claim. The product remains a local-first desktop prototype whose limits are part of the interface —
it will simply look and feel like something you would want to use every morning.

## 8. Delivered in the first batch (15 September 2026)

**P0 — complete.** This plan and [DESIGN.md](../DESIGN.md) are committed, and the stack decision is
recorded above with its measurements.

**P1 — foundation, first slice.** `web/tokens.css` is now the single token layer: colour, type, space,
shape, elevation, motion and the chart palette, in both themes, with every duration collapsing to 1ms
under `prefers-reduced-motion`. `style.css` no longer declares a colour or a type value of its own and
consumes the tokens; the page loads the token layer before the sheet. Motion primitives (surface rise,
chart draw-in, view transitions) and a `:focus-visible` ring are in place. The static audit's serve
contract and FE01–FE06 are green and ten Node component suites pass.

**P2 — first signature visuals.** `web/viz.js` is the chart engine v2, with two primitives wired into
the product:

- **Ensemble plume** (Ensemble surface): the shaded p10–p90 band, the median as its own heavy line, the
  mean dashed, min–max whiskers, a focusable hour for every drawn point, and an exact-value table with
  the member count and the method definitions.
- **Meteogram** (Forecast surface): temperature line, precipitation bars, wind arrows, a night band
  derived from the source timestamps, and a readout that names each value with its source locator.

`tests/test_viz.js` pins the honesty rules: a missing hour splits a line or leaves a bar out, a returned
zero is never drawn as a gap and a gap is never drawn as a zero, an isolated hour cannot form a band,
and every readout carries its locator. Live record:
`research/reviews/frontend-overhaul-20260915/live-http-checks.json` — the page references the token
layer before the sheet and loads the engine; `/tokens.css` (5,826 bytes) and `/viz.js` (19,805 bytes)
are served; the ensemble route returns the eight member series the plume draws (30 members).

**P2 — signature visuals, delivered.** Three more primitives are in the engine and wired into the product:

- **District x day warning matrix** (Warnings surface): the published national product as a colour grid.
  Every cell carries the colour the source printed, an unknown hazard code is flagged rather than dropped, and
  a day the product left uncoloured reads as not stated. Rows are ordered by the product own colour rank, which
  the panel states; the engine itself never ranks a district. Live product drawn: 756 districts x 5 days, with
  green, yellow, orange and red observed in the payload.
- **Corpus library cards** (Published-documents surface): each indexed edition as a card with its family rail,
  printed issue date, retrieval date, measured currency, page and passage counts and body state. Only a held
  body offers the saved file; a pruned edition says what survives instead.
- **Inspectable validity ruler** (every answer with a window): each covered span and each gap is focusable and
  reads out exactly what it covers, including that a gap is drawn as a gap and never interpolated. The ruler
  stops being a picture of coverage and becomes a statement of it.

`tests/test_viz.js` and `tests/test_views.js` pin all three: a cell cannot exist without a returned day, an
uncoloured day cannot borrow a colour, a pruned card cannot offer a file, and every ruler segment must read out.
Live record: `research/reviews/frontend-overhaul-20260915/live-http-checks-p2.json` — the engine is served with
both new primitives, the renderer with the ruler hits, and the national route answers with 756 districts x 5 days
while the corpus route answers with 588 editions of which 584 still hold their body.


**P3 — command-centre shell, first slice.** The Today surface now opens with the **Now band**: one row per
 product on a single time axis. A station report is an instant and is drawn as a tick; the published district
 day is a window and is drawn in the colour the source printed; the model hours are a dashed span between the
 first and last returned hour. The read-at marker comes from the payload own generated instant, never from the
 reader clock, and every lane is focusable and reads out its values with its source.

The shell also has **place memory**: pin the working place from the command palette, switch back from a chip in
 the topbar, and the shortlist is a small local list of place records. A pin is refused unless it carries a
 label and two real coordinates — the test that caught this found `Number(null) === 0`, which would have stored
 a null pin as the Gulf of Guinea.

**Performance budget, measured as far as this host allows.** Served frontend assets total **434.6 KiB**
 (11 files; `panels.js` 106 KiB, `shell.js` 64 KiB, `viz.js` 33 KiB, `tokens.css` 5.7 KiB). Browser paint,
 layout shift and animation frame time are recorded as **not measured**: this sandbox cannot launch Chrome,
 and a number invented here would be worse than the gap.

Live record: `research/reviews/frontend-overhaul-20260915/live-http-checks-p3.json` — the page serves the
 pinned strip, the shell carries place memory with its routable guard, the engine carries the band, and
 `/api/now` returns all three lanes (observed station, published yellow day, six model hours).

**Next (not started).** A compare tray and map exploration; the rest of the command-centre shell
craft polish (loading skeletons, the receipt artifact); and browser-level acceptance, which this sandbox still cannot run.
