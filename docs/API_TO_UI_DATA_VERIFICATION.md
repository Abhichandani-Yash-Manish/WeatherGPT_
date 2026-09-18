# API to UI data verification

Measured 18 September 2026 against the workspace on loopback (`http://127.0.0.1:8790`) with the React build
served by the same process. Each row compares a value the read returned with the value on the screen; a
mismatch would be a defect, and an intentional transformation is stated as one.

## 1. Today — the four KPI cards

| KPI | API source | API value | value on screen | match |
| --- | --- | --- | --- | --- |
| Districts in this read | `/api/overview` → `data.national.districts` | 756 | `today-kpi-districts` = "756 districts" | exact |
| District-days with a published colour | `/api/overview` → `data.national.tally` (red+orange+yellow+green) | 1865 | `today-kpi-district-days` = "1865 district-days" | exact |
| Editions behind the newest in this read | `/api/warnings/national` → `districts_behind_the_newest_edition` | 14 | `today-kpi-editions` = "14 districts" | exact |
| Radar stations reporting a status | `/api/overview` → `data.radar.reported` | 39 of 39 | `today-kpi-radar` = "39 of 39 returned" | exact |

Two reads feed one card row on purpose, and the card states which read each count came from. The overview read
carries the same national fields in milliseconds; the 1.65 MB district-row read is the slower source for the
per-district day rows.

## 2. Farm advisories — the holdings view

| Value | API source | API value | value on screen | match |
| --- | --- | --- | --- | --- |
| Regions held | `/api/advisories/holdings` → `data.counts.regions` | 571 | "Regions held 571" | exact |
| Documents held | `data.counts.documents` | 571 | "Documents held 571" | exact |
| Indexed passages | `data.counts.passages` | 6187 | "Indexed passages 6187" | exact |
| States named by the editions | `data.counts.states_named` | 29 | "States named by the editions 29" | exact |
| First held region, newest printed issue and passages | `data.regions[0]` | Surguja, 2026-09-13, 20 passages | first table row "Surguja · Chhattisgarh · 2026-09-13 · not recorded · 1 · 20" | exact |

The age column shows "not recorded" for that region because its edition states no retrieval instant — an
absent value is shown as absent, never as a number.

## 3. Warnings — the district × day matrix

| Value | API source | API value | value on screen | note |
| --- | --- | --- | --- | --- |
| District rows returned | `/api/warnings/national` → `data.districts` | 756 | the district-days table lists them | exact |
| District-day cells in the read | sum of `days` over all rows | 3780 | — | the matrix draws a bounded view |
| Cells drawn in the matrix | — | — | 420 cells over 5 day columns | **bounded by design**: `MATRIX_ROWS_SHOWN = 60` districts × 5 days + headers, with the full table beneath it. The surface states the figure is a scan view of the same rows. |
| Matrix figure drawn by | `web/viz.js` (the served engine) | — | `<section class="viz viz-matrix-block" data-days="5">` | the engine builds an HTML grid for this figure, not an SVG |

## 4. Forecast — the meteogram

| Value | API source | API value | value on screen | match |
| --- | --- | --- | --- | --- |
| Hourly temperature, rain, wind for the chosen point | `/api/forecast` → `data.parameters` | 3 series over the requested days | 1 `.viz-host` holding 1 SVG with **113 drawn marks**, and the parameter tables below | exact, by construction: the figure and the tables are built from the same payload |

The figure is absent until a place is chosen (the read needs coordinates), and the surface says so rather than
drawing an empty frame.

## 5. Responsive overflow (the one defect this pass found and fixed)

At 1440 × 833 every route reported **113 px of horizontal overflow** although the aurora field is fixed,
`inset: 0`, `overflow: hidden` — a blurred blob counts in the scrollable overflow. `[data-shell='react']`
now carries `overflow-x: clip` at every width (the narrow-width rule already did this), which removes the
overflow without creating a scroll container, so the sticky rail and topbar keep working.

| viewport | route | clientWidth | scrollWidth | overflow |
| --- | --- | --- | --- | --- |
| 1440 × 833 | overview, warnings, advisories | 1440 | 1440 | 0 |
| 1024 × 768 | overview, warnings, advisories | 1024 | 1024 | 0 |
| 768 × 1024 | overview, warnings, advisories | 768 | 768 | 0 |
| 390 × 844 | overview, warnings, advisories | 390 | 390 | 0 |

## 6. What is not claimed here

- These are value-level checks on five surfaces, not a proof that every surface renders every field.
- The matrix draws 60 districts at a time by design; the rest are in the table, and the surface says so.
- A value that a read did not return is shown as absent ("not recorded", a gap) — the checks above confirm the
  absent case appears as absent in the advisories age column.
