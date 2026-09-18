# Playwright complete site test

Run 18 September 2026 against the built application on loopback (`http://127.0.0.1:8790`), one pass per
route, from the local CDP harness in `tmp/qa/driver.py` (the same instrument the earlier batches used; the
ZIP's `.playwright-mcp` session drove a different copy of the tree, and neither could be attached to this one).

## Route sweep

Every route in the registry was opened, allowed to settle, and inspected for: a surface heading, the number of
sections and tables, failed resource requests (`performance` entries with a 4xx/5xx status) and console errors.
Captures: `tmp/qa/shots/sweep-<route>.png`.

| route | heading | sections | tables | failed requests | console errors |
| --- | --- | --- | --- | --- | --- |
| #/assistant | Ask about a place and a time. | 2 | 1 | 0 | 0 |
| #/workspace | Dashboard | 11 | 6 | 0 | 0 |
| #/overview | Today | 13 | 6 | 0 | 0 |
| #/warnings | Warnings | 9 | 6 | 0 | 0 |
| #/map | Map | 6 | 4 | 0 | 0 |
| #/forecast | Forecast | 3 | 1 | 0 | 0 |
| #/observations | Observations | 3 | 1 | 0 | 0 |
| #/changes | What changed | 3 | 1 | 0 | 0 |
| #/climate | Climate records | 5 | 3 | 0 | 0 |
| #/advisories | Farm advisories | 5 | 7 | 0 | 0 |
| #/air-quality | Air quality | 3 | 1 | 0 | 0 |
| #/aviation | Aviation | 3 | 1 | 0 | 0 |
| #/ensemble | Ensemble spread | 4 | 1 | 0 | 0 |
| #/verification | Forecast verification | 4 | 1 | 0 | 0 |
| #/compare | Compare places | 3 | 1 | 0 | 0 |
| #/marine | Sea and rivers | 4 | 1 | 0 | 0 |
| #/documents | Published documents | 7 | 4 | 0 | 0 |
| #/briefcase | Briefcase | 5 | 3 | 0 | 0 |
| #/settings | Sources and settings | 7 | 6 | 0 | 0 |

**19 of 19 routes load with no failed request and no console error.** The figures are absent on this pass
because every figure needs a place or a row set that only exists after a choice; the forecast flow was then
driven by hand (below) to prove the figures draw.

## Figure verification (the intake)

| step | result |
| --- | --- |
| Open `#/forecast`, type "Ahmedabad" in the place picker | 4 rows returned by `/api/places/search` |
| Choose the Gujarat row | the forecast read runs and the **Meteogram** section appears |
| Inspect the figure host | `window.viz` loaded from `/viz.js`; one `.viz-host` containing one SVG with **113 drawn marks** |
| Warnings route | `<section class="viz viz-matrix-block" data-days="5">` with **420 cells** drawn over 5 published days |
| Ensemble route | the member-distribution figure is mounted (its section renders with the read) |
| Today route | the three-lane now band is mounted inside the right-now card |
| Documents route | the library figure is mounted above the editions table |

## Responsive pass

| viewport | routes checked | horizontal overflow |
| --- | --- | --- |
| 1440 × 833 | overview, warnings, advisories | 0 (113 px before the clip fix) |
| 1024 × 768 | overview, warnings, advisories | 0 |
| 768 × 1024 | overview, warnings, advisories | 0 |
| 390 × 844 | overview, warnings, advisories | 0 |

## What this pass did not do

- It did not click through every button on every surface; the automated suites (339 React checks, 1351 Python
  tests) cover the interactive contracts, and the routes were opened rather than exercised end to end.
- It did not run on a second browser or on a physical device.
- The dashboard's below-the-fold sections read when they near the screen; the sweep waited for the initial
  read, not for a scroll through every section.
