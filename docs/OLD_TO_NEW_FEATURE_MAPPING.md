# Old to new feature mapping

The ZIP carries three generations of frontend in one tree: the **vanilla frontend** that R6 removed
(`web/*.js`, deleted in commit `486c403`), the **React frontend this workspace built** (the running design),
and the **parallel React redesign inside the ZIP** (`WeatherGPT_/frontend/src`, another session's work). This
document maps what the old frontend had to where it lives now, and records what was intaken from the ZIP's
redesign. Nothing was dropped silently: a feature that is not mounted says so.

## 1. Vanilla features and their new home

| old feature | old location | new location | backend route | status |
| --- | --- | --- | --- | --- |
| Meteogram | `web/panels.js` (viz.meteogram) | Forecast → **Meteogram** | `/api/forecast` | **RESTORED** (the engine was served but never mounted; now drawn: 113 marks) |
| District × day warning matrix | `web/panels.js` (viz.warningMatrix) | Warnings → **District × day matrix** | `/api/warnings/national` | **RESTORED** (420 cells over 5 days) |
| Now band (observation / published day / model hours on one axis) | `web/home.js` | Today → right-now card | `/api/now`, `/api/overview` | **RESTORED** |
| Published-day timeline | `web/home.js` | — | `/api/overview` → `places[].days` | **not mounted**: the overview place strip is empty in this build, so the spec returns nothing; the figure is available the moment that read carries days |
| Ensemble fan | `web/panels.js` (viz.ensembleFan) | Ensemble spread → **Member distribution** | `/api/ensemble` | **RESTORED** |
| Library cards | `web/panels.js` (viz.libraryCards) | Published documents → **The library** | `/api/corpus` | **RESTORED** |
| Field builder that writes a question and sends nothing | `web/home.js` | Dashboard → **Ask a question** (the builder writes the editable box; sending is a separate button) | `/api/chat` | **RESTORED** (in the intaken dashboard; its own check pins "sends nothing") |
| Place-centred now desk | `web/home.js` | **Dashboard** (`#/workspace`) | `/api/now`, `/api/forecast`, `/api/warnings/place`, `/api/air-quality`, `/api/climate/*`, `/api/briefs`, `/api/plans` | **RESTORED** (966-line surface; this workspace's placeholder is gone) |
| Working place carried across surfaces | `web/state.js` | `Evidence.readWorkingPlace`/`rememberPlace`/`useWorkingPlace` + the picker's quick choices | `/api/places/search` | **RESTORED** |
| "Refresh from the source" on a product read | `web/*.js` (`refresh=1`) | `Evidence.useSourceRefresh` + `RefreshButton` on the product surfaces | every product route | **RESTORED** |
| Warning strip with the colour the product printed | `web/warnings.js` | Warnings → district-days table + matrix + place view | `/api/warnings/national`, `/api/warnings/place` | **PRESERVED** |
| Map with layers and a schematic figure | `web/map.js` | Map → layer deck, zoom, find, legend, inspector | `/api/map/layers`, `/api/map/static/*` | **PRESERVED and extended** (a district join, a tip and an inspector were added) |
| Stored conversations, pins, plans panel, command palette | `web/*.js` | `ConversationRail`, pinned places, `PlanWatch`, `Palette` | conversation, plans, watches routes | **PRESERVED** |
| Sky-phase background | `web/sky.js` + `sky.css` | `SkyBackground` + the aurora field | none (local clock) | **PRESERVED** |

## 2. What the ZIP's redesign added, and where it landed

| ZIP file | capability | landed as | status |
| --- | --- | --- | --- |
| `charts/VizFigure.tsx`, `vizSpecs.ts`, `viz.css` | The mount and the specs for the six served figures | `frontend/src/charts/` | **INTAKEN**, five figures mounted |
| `charts/ChartBlock.tsx` (newer) | Returned-series chart with the gap rules | replaced the older copy | **INTAKEN** |
| `modules/WorkspaceSurface.tsx` | The real place dashboard | `modules/WorkspaceSurface.tsx` (replaces the placeholder) | **INTAKEN** |
| `modules/dashboard.ts` + tests | Series helpers for the dashboard | same path | **INTAKEN** |
| `modules/IndiaWarningMap.tsx` | India district warning map | same path, drawn by the dashboard | **INTAKEN** |
| `shell/icons.tsx` | Dashboard glyphs | same path | **INTAKEN** |
| `shell/navigation.ts` + test | The top-navigation model and per-surface notes | same path; the rail now labels `#/workspace` **Dashboard** | **INTAKEN** |
| Evidence helpers, MSW defaults, IntersectionObserver harness | Working place, source refresh, dashboard reads in tests | `modules/Evidence.tsx`, `test/msw.ts`, `test/setup.ts` | **INTAKEN** |
| `shell/TopNav.tsx`, `shell/AtmosphericBackground.tsx`, `assets/atmosphere*.svg` | The ZIP design's top navigation and atmosphere | — (removed after review) | **NOT ADOPTED**: this workspace's shell already carries the glass topbar and the aurora field; mounting both would double the chrome. Named here so nothing looks silently missing |

## 3. Features the ZIP's frontend did not have, kept from this workspace

| capability | where | why it stays |
| --- | --- | --- |
| Component kit (`ui/kit.tsx`) with Button/Card/Badge/Stat/Toast/Modal | every surface | the ZIP's redesign styles ad hoc; the kit is what the running design is built from |
| Dashboard charts (`DashboardCharts.tsx`), district map (`DistrictRiskMap`), map tip and inspector, matrix geometry checks | Today, Map | these carry the dashboard batches already verified in earlier rounds |
| Aurora field, glass rail/topbar, toasts | shell | the design the user has been reviewing |
| `mapFigure.ts` shared projection | Map + Today | one fit for two surfaces |

## 4. Status vocabulary used above

**PRESERVED** — existed, still exists, same meaning. **RESTORED** — existed in the vanilla frontend, was
missing from the React port, and is now reachable again. **INTAKEN** — came from the ZIP's redesign and is now
in the running tree. **NOT MOUNTED / not mounted** — the code exists (or the spec exists) and nothing renders
it; the reason is stated next to it. **MISSING** — would be a real gap; nothing in this mapping is MISSING.
