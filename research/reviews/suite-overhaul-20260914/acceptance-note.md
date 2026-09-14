# Suite overhaul acceptance note

Recorded 14 September 2026 against the working tree that produced `desktop-journey.json` in this directory.

## What was run

A real browser (Chrome 152 headless over CDP) loaded the served workspace at http://127.0.0.1:8765, and a script walked all eleven hash surfaces, waiting for each to settle, then recorded per-surface state and called eight product views directly. Mobile captures were taken at 390x844 for three surfaces.

## Per-surface result, desktop 1440x1200

| Surface | Characters | Tables | Charts | Colour chips | District paths | Loading left | Error states |
|---|---|---|---|---|---|---|---|
| Overview | 2,455 | 1 | 0 | 9 | 0 | 0 | 0 |
| Warnings | 22,003 | 4 | 0 | 2,000 | 0 | 0 | 0 |
| Map | 51,600 | 2 | 1 | 5 | 756 (1 placeholder) | 0 | 0 |
| Observations | 5,848 | 9 | 0 | 0 | 0 | 0 | 0 |
| Forecast | 10,025 | 2 | 1 | 0 | 0 | 0 | 0 |
| Climate | 4,854 | 3 | 1 | 0 | 0 | 0 | 0 |
| Advisories | 2,158 | 2 | 0 | 0 | 0 | 0 | 0 |
| Aviation | 2,237 | 7 | 0 | 0 | 0 | 0 | 0 |
| Marine | 11,726 | 6 | 1 | 0 | 0 | 0 | 0 |
| Assistant | conversation thread and ledger, not the panel body | - | - | - | - | - | - |
| Settings | 6,425 | 3 | 0 | 0 | 0 | 0 | 0 |

No surface was left in a loading state and no surface rendered an error state.

## Product views called from the page

All eight returned HTTP 200 with status ok and their own sources and limitations attached: /api/overview (2 sources, 4 limitations), /api/warnings/national (1, 4), /api/radar (1, 2), /api/basins (1, 3), /api/map/layers (1, 2), /api/warnings/cap (1, 3), /api/settings/capabilities (0, 2), /api/climate/index (1, 2).

## Checked by hand in the same session

- Place resolution is geometric. Patna resolved to PATNA, BIHAR and Ahmedabad to AHMADABAD, GUJARAT despite the source spelling difference; an Arabian Sea point resolved to no district and said so.
- The warning table and the map agree because both read one key space; 756 districts carry a row and 8 source features without a name are listed rather than dropped.
- Placeholder geometry is labelled, drawn as an outline and described as a source bounding box rather than a coastline.
- The CAP relay stays separate from district guidance in both the surface and the payload.
- Station freshness is per row: a current METAR beside a stale AWS station shows current and stale respectively, and an unstated unit is shown as not stated by the source.
- The context bridge works: "Ask about this" from Warnings moved to the Assistant with the place carried and the question pre-filled.
- Mobile: the navigation becomes a horizontal scroller, the document does not scroll behind the surfaces, and the map still draws 756 districts at 390 wide.

## What was not run

No screen-reader, keyboard-only, contrast or cross-browser audit; no load, cold-start or concurrency measurement; no mobile platform acceptance; no fluent Hindi or Gujarati review; no source-terms review; no watch or notification journey, because that mechanism does not exist yet.
