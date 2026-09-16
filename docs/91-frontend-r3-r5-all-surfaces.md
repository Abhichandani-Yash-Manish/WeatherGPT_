# 91 — Every surface ported, R4 finished, and the accessibility pass measured in a browser

17 September 2026. The user asked for the whole React overhaul to reach a flagship standard and for no detail
to be left out. [docs/90](90-frontend-r2-flagship-transcript.md) recorded the transcript, the first ten surfaces,
the chart block and the front door. This document records the rest: the eight remaining surfaces, which
together make every one of the nineteen surfaces a real module; the end of R4 (charts, print parity, and the
chart engine served to the built page); the R5 accessibility work with a **real browser** measurement; one
engine repair the surface work exposed; and what is still open.

## 1. What this batch delivers

| Deliverable | Where | State |
| --- | --- | --- |
| The eight remaining surfaces | `frontend/src/modules/` | climate records, aviation, ensemble spread, forecast verification, compare places, sea and rivers, briefcase and the workspace builder |
| Every surface served from a real module | `modules/registry.ts` | **18 of 19** surfaces have a module; the nineteenth is Ask, which is the conversation itself. `scripts/audit_surface_registry.py` reports the count and refuses a module key that is not a declared surface |
| Print parity | `styles/print.css`, `chat/print.test.tsx` | a printed card keeps the receipt, the window and the sources and drops the composer, the action row and the raw machine record; the markup and the stylesheet are checked together |
| The chart engine on the React side | `/viz.js`, `tests/test_react_vendor_assets.py` | served from its one tracked copy, pinned by three Python checks, so the vanilla geometry checks keep covering the code a React surface draws with |
| Accessibility measured in a browser | `research/reviews/frontend-react-r5-20260917/axe-browser.json` | **15 surfaces, 0 violations, 391 rules passed** under wcag2a/2aa/21a/21aa at 1440×900 on the served build |
| Accessibility measured in jsdom | `research/reviews/frontend-react-r5-20260917/axe-report.json` | 5 surfaces, 0 violations, with the colour-contrast rule named as not measurable without a layout engine |
| Keyboard acceptance | `shell/keyboard.test.tsx` | the skip link reaches the question box, Alt+1…9 opens a surface, Alt+K opens the palette and focuses its search field, and Enter opens the chosen surface |
| Direction of a written answer | `chat/AnswerTurn.tsx` | the answer sentence carries `dir="auto"`, so an Urdu or mixed-script answer is laid out by its own first strong character before the shell is mirrored |
| An engine repair the surfaces exposed | `product_api._grid_distance` | the marine and river point products now name the answering grid cell **and its distance**, computed with the same great-circle helper every other point product uses, instead of returning a blank |

## 2. Measured

| Measure | Value | How it was measured |
| --- | --- | --- |
| Frontend component checks | **26 files, 135 checks** | `cd frontend && npx vitest run` |
| TypeScript | **0 errors** | `npx tsc --noEmit` |
| Initial bundle graph | **108 KB gzip** against the 312 KB budget | `scripts/audit_react_build.py` |
| Built-output audit | 11 of 11 | the same script, reading the built files |
| Surface registry audit | 10 of 10, with **18 of 19** surfaces carrying a module | `scripts/audit_surface_registry.py` |
| Port ledger | 5 of 5, **33 of the 110** vanilla checks named and 41 test names verified to exist | `scripts/audit_check_port.py` |
| Python tests | **1302** (7 added by this batch) | `pytest tests/ -q` |
| Browser accessibility | 15 surfaces, 0 violations, 391 passes | axe-core injected into the served page and run over CDP |
| Pictures of this build | 25 captures at 1440×900 | headless Chrome against `--frontend react` on a throwaway store |

## 3. What the browser measurement found that jsdom could not

jsdom has no layout engine, so the accessibility run there can only record the colour-contrast rule as *not
measurable*. The browser run measured it, and the first pass found three real defects:

1. **The active rail row read muted ink on the full sand rule colour** — 2.29:1, far below the 4.5:1 a 12 px
   label needs. The rail highlight is now a sand **wash** with ink on it, and the shortcut hint is legible on it.
2. **The service-state chip read soft ink on sand** — 3.3:1. It now sits on the sunken surface.
3. **A surface taller than the viewport scrolled but could not take focus** (`scrollable-region-focusable`), so a
   keyboard reader could not reach the rest of it. The surface container and the transcript log are now focusable
   regions with names.

All three were fixed at their cause and the sweep was re-measured from a freshly fetched bundle: **0 violations on
15 surfaces**. The sweep also records what it did not do — it is the light theme at one viewport width, and it does
not cover the dark theme, reduced motion, zoom or a screen reader.

## 4. The engine repair

The marine and river point products are required to name the answering grid cell **and its distance** from the
requested point, because a discharge belongs to a river cell and a wave height to a sea cell. The routes read that
distance out of the packet's coverage block, and the hourly and daily adapters behind them never set it, so the
payload carried a blank where the interface promises a number. The route now computes it — with the same
great-circle helper the point, specialist, ensemble, air-quality and verification modules already use — and
returns nothing rather than a guess when the read states no returned cell. `tests/test_grid_distance_naming.py`
pins all three behaviours: a stated distance is passed through untouched, an unstated one is computed from the
requested point and the returned cell, and a read with no cell yields nothing. Seven Python checks.

## 5. Defects found by the surface work

- **"The the national overview read failed."** The shared `Failure` component prefixed "The" to a subject some
  callers already pass with an article. It now strips a leading article, so both conventions read as one sentence;
  `Reading` does the same.
- **A kept-brief source list typed as registry rows.** `/api/briefs` returns source *identifiers* (`"S63"`), not
  `{source_id, product, …}` rows, and the type promised the latter. The type now says both, and the surface states
  which fields the entry did not record.
- **`NowReading['in_force']` had no `why`.** The right-now view sets that field when part of the reading cannot be
  produced, so the workspace surface declares the intersection locally and renders the reason rather than dropping
  it. The shared type should carry it in the next batch.

## 6. What the module authors reported and did not change

Each surface agent read the route it renders before writing anything. Four findings are recorded here because they
are engine gaps, not interface choices:

- `series_from_packet` drops the per-record `member_count`, `exceedance_count` and `threshold` that the ensemble
  adapter produces, so member counts can only be stated per variable from `coverage.member_total`, not per point.
- `product_api.ensemble` derives the envelope status from whether any parameter came back, so the adapter's own
  `stale`/`partial` status never reaches a client.
- The marine route asks upstream for a **sea** cell, so a coastal or inland point can be answered by a different
  cell than the one asked about; the surface names the returned cell and says plainly when the two reads differ.
  There is no distance guard on that path, which is the next repair if the sea products become load-bearing.
- `raw_fields.fltCat` (VFR/IFR/MVFR) is deliberately **not** rendered on the aviation surface: a flight category is
  the closest thing in the payload to an operational determination, and the product does not make one.

## 7. What is not done

- **R6 (decommission) has not started.** The vanilla frontend is still the default and still serves; it is removed
  only once `verify_all.py` passes on a React-only tree, and that is the next stage.
- **77 of the 110 vanilla checks are still only in the vanilla suites.** They remain the regression net, and the
  ledger records which ones a React spec now carries (33).
- **The browser accessibility pass is one theme at one width**, and it is a rule engine, not a screen reader. It
  does not cover the dark theme, reduced motion, zoom, or a real assistive-technology walkthrough.
- **RTL is not mirrored.** An answer sentence now carries `dir="auto"`; the shell, the rail and the forms are still
  left-to-right.
- **The language path is unmeasured in the React interface.** The selector is wired to `output_language` and the
  downgrade is stated, but no React-language run has been recorded against the hosted service; the delivered and
  refused languages are still the vanilla measurements.
- **Voice has interface coverage only.** No real-audio or field acceptance has been recorded.
- **Mobile and hosting are unchanged**: desktop web is the surface, hosting is held, and the owner gate is still
  described as an interface lock rather than authentication.

## 8. Evidence

- `research/reviews/frontend-react-r5-20260917/axe-browser.json` — the browser sweep, with the three defects it
  found recorded as fixed, and what it did not cover.
- `research/reviews/frontend-react-r5-20260917/axe-report.json` — the jsdom sweep and the rule it could not measure.
- `research/reviews/frontend-react-r2-20260917/check-port.json` — the port ledger, now 33 of 110 with 41 verified
  test names.
- `research/reviews/frontend-react-r2-20260917/shots-clean/` — 25 captures at 1440×900, including every surface
  ported in this batch.
- `tests/test_grid_distance_naming.py`, `tests/test_react_vendor_assets.py` — the Python checks added here.

## 9. What comes next

1. **R6**: build the React-only tree, run `verify_all.py` against it, remove `web/*.js` and the DOM shim, and point
   the default at the React build, with the vanilla suites deleted only after their checks are named in the ledger.
2. The remaining check port, suite by suite, with the ledger as the record.
3. The dark-theme, reduced-motion and zoom measurements on the browser sweep, and a real screen-reader walkthrough.
4. The React language run against the hosted service, so the delivered and refused languages are measured on the
   interface that ships.
5. The engine gaps in §6: per-record member counts, the ensemble status, and the sea-cell distance guard.
