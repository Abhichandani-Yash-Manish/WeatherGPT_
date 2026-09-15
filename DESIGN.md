# DESIGN.md — the WeatherGPT instrument

This is the design system the frontend overhaul commits to. It is a working document for whoever
touches `web/`: the tokens in `web/tokens.css` are the vocabulary, `web/style.css` is the only place
that consumes them, and `web/viz.js` is the chart language. Read it before adding a surface.

## The idea

**A field instrument, not a dashboard.** The product measures published and modelled weather for one
place at one time, and every value carries where it came from. The interface should feel like a
well-made instrument: quiet chrome, precise type, a surface you can read at a glance and inspect on
demand. Beauty comes from arranging real facts — a validity ruler, a member plume, a district matrix,
a printed issue date — never from decoration.

## Colour

- **Hazard colour belongs to hazards.** `--red`, `--orange`, `--yellow`, `--green` are IMD hazard
  colours. They may appear only on hazard chips, hazard days and hazard text read from a source.
  Interface state never uses them: a loading state is not amber, an error is not red, a success is not
  green.
- **Interface state is carried by wording, weight, position and monochrome glyphs.** The one accent is
  `--data` (measured paths, links, focus). `--slate` structures, `--sand` rules and eyebrows.
- **Chart colour is its own palette** (`--viz-*`): line, model, observed, band, band-line, rain, wind,
  grid, axis, missing, crosshair, night. A chart never uses a hazard colour, because a spread or a
  model value is not a warning.
- **Two themes, same semantics.** Light and dark define the same token names with equal contrast; a
  surface must never hard-code a colour.

## Type

- Families: `--sans` for interface text, `--serif` for the hero/welcome voice, `--mono` for values,
  locators, timestamps and axis labels.
- Scale: `--step--1` (labels, notes) → `--step-0` (body) → `--step-1` (card titles) → `--step-2`
  (block titles) → `--step-3` (surface titles) → `--step-4` (hero) → `--step-5` (hero numerals).
- Every number is tabular (`font-variant-numeric: tabular-nums`) so columns do not shimmy.
- Eyebrows and units are uppercase with `--track-wide`; display lines use `--track-tight`.
- Line length is bounded by `--measure` (74ch) for prose; tables and charts may run wider.

## Space, shape, elevation

- Spacing is the 4px scale `--space-1…7`. Cards are separated by `--space-4/5`, sections by `--space-6`.
- Radii: `--r` (controls), `--r-card` (surfaces), `--r-pill` (chips).
- Three elevations only: `--lift-1` (hairline on a surface), `--lift-2` (drawer, palette), `--lift-3`
  (modal moments). Most surfaces use a hairline (`--hairline`) instead of a shadow.

## Motion

- Durations: `--motion-fast` 120ms (state), `--motion-base` 200ms (hover, focus), `--motion-slow` 320ms
  (surface entry), `--motion-slower` 520ms (chart draw). Easings: `--ease-out`, `--ease-in-out`,
  `--ease-spring` for a single emphasis.
- **Motion explains.** It may show where a surface came from (view transition), that new evidence
  arrived (row/block rise), or how a line was drawn (stroke draw-in). It may not loop, bounce for
  decoration, animate a number to a *different* number, or delay reading a value.
- `prefers-reduced-motion: reduce` collapses every duration to 1ms in `tokens.css`; nothing may depend
  on an animation having run.

## Components

| Component | Rule |
|---|---|
| `block` (card) | One idea per card; a title that states the claim, a note that states the limit. |
| `stateBlock` | Four voices: plain, loading, error, down. Each names what is missing and whether it is a source state or a local fault. |
| `chip` | Small, monochrome by default; hazard chips only from source data. |
| `data-table` | Headers are nouns, cells are values or explicit absences; a missing value prints as `missing`, `not stated` or `—`, never as 0. |
| `disclosure` | Secondary detail (exact values, provenance, method) lives here, never hidden entirely. |
| `ruler` | The validity ruler: covered hours in `--data`, uncovered hours as a hairline, model hours dashed. |
| `receipt` | The evidence artifact: entity, window, method, source, retrieval time, locator, hash. Copyable. |
| `rail` | Sectioned navigation; every item keyboard reachable; hints must match the handler. |
| `palette` | Every surface and action is reachable from ⌘K; the palette is the power-user's rail. |
| `drawer` | Evidence in context, dismissible with Escape, focus returned to the opener. |
| `viz-matrix` | District x day grid. A cell carries the colour the source printed; an unknown code is flagged, never dropped; rows are ordered by the product own colour rank and the ordering is stated. |
| `viz-card` | A corpus edition as a card: family rail, printed issue date, currency, pages and passages, and the state of its saved body. Only a held body offers a file. |
| `ruler-readout` | The validity ruler is inspectable: every covered span and every gap is focusable and says what it is, including that a gap is never interpolated. |
| `now-band` | Three products on one axis. An instant is a tick, a window is a span, a published colour is the colour the source printed, and the read-at marker is the payload own instant. |
| `pinned-place` | A local shortlist of places. A pin is refused unless it carries a label and two real coordinates; the topbar chip switches the working place without re-resolving it. |
| `skeleton` | A loading state reserves the shape of the answer — bars and a chart frame — and carries no number, because it has no source. |
| `receipt-actions` | The receipt copies itself as text and prints; a refused clipboard says so rather than claiming success. |
| `compare-column` | One place per column, each with its own timestamps and sources. No difference, ranking or average is computed between columns. |

## Chart language (`viz.js`)

1. **A mark exists only where the engine returned a value.** A missing hour splits a line, leaves a bar
   out, and prints as `missing` in the exact-value table. Nothing is interpolated or zero-filled.
2. **Every drawn point carries its `source_locator`** into the readout and the table.
3. **Encodings:** solid line = observation or published series; dashed = model or mean; shaded band =
   p10–p90 member spread; thin rule = min–max; bars = accumulation; arrows = direction; night = a shaded
   hour band derived from the source timestamp.
4. **Direct reading first, exact reading always.** A hover/focus readout names the value, its unit and
   its locator; every chart has an `Exact values and evidence` table below it.
5. **Hit targets.** In-chart hit areas are 10–12px wide with ≥44px effective spacing on touch, and are
   focusable with Enter/Space producing the same readout as hover.
6. **No chartjunk.** No 3D, no gradients for their own sake, no dual axes without an explicit unit
   label, no smoothing that implies measured continuity.

## Accessibility

- Text contrast ≥ 4.5:1, large text ≥ 3:1, in both themes.
- `:focus-visible` is always a 2px `--data` outline with 2px offset.
- Charts are `role="group"` with an `aria-label`; readouts are `aria-live="polite"`.
- Keyboard: every surface reachable from the rail and the palette; drawers return focus; Escape closes.
- Nothing depends on colour alone: state is always also a word.

## Anti-patterns (refused by review)

- A gauge, dial or needle for a quantity that has no threshold (feels-like temperature has no scale).
- A confidence, risk or skill score the engine does not compute.
- A colour implying severity the source did not publish.
- A spark or pulse animation on a product whose whole ethic is that a quiet day is not an all-clear.
- A chart that draws a value the engine did not return, including a zero for a gap.

## Files

| File | Role |
|---|---|
| `web/tokens.css` | Every colour, type, space, elevation, motion and chart token, light and dark. |
| `web/style.css` | Structure and surfaces; consumes tokens only, no raw colour. |
| `web/viz.js` | Chart engine v2: ensemble plume, meteogram, shared scales/axes/readouts. |
| `web/charts.js` | The original single-series chart (annual series, hourly readings). |
| `web/panels.js`, `web/views.js`, `web/shell.js` | Surfaces, answer rendering, shell and transport. |
