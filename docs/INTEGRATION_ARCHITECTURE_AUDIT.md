# Integration architecture audit — the ZIP, the workspace, and what was intaken

Audited 18 September 2026, against the extracted `weathergptfinal/WeatherGPT_` tree (repo clone at commit
`e7247bd` with a parallel frontend redesign) and this workspace (`/Users/yashabhichandani/Desktop/WeatherGPT`,
the same repo plus this session's work). Written from the code and from live runs, not from the README.

## 1. What the ZIP contained, and what could be written

| Part | Finding |
| --- | --- |
| `weathergptfinal/WeatherGPT_/` | A clone of this repository at `e7247bd` with an uncommitted, parallel **frontend redesign** (`frontend/src` + 14 files this workspace did not have) and its own docs/audit edits |
| `weathergptfinal/audit/`, `.playwright-mcp/`, `explore-routes.json`, `vm-*.png` | The other session's Playwright captures (dashboards, maps, meteogram, warnings matrix, assistant, air quality, climate) and its route exploration |
| `WeatherGPT_/CONTEXT_HANDOFF.md` (142 KB) | A read-only audit of the *backend* for a teammate: stack, routes, providers, psi of the query path, and the open defects list |
| Write access | The extracted tree sits under `~/Downloads`, which this session may **read but not write** (`Operation not permitted`). All work therefore happened in the workspace tree, and the ZIP's unique work was **intaken file by file** |

**Decision (free hand, per the brief's rule "preserve the new frontend's visual design while connecting it to
the real backend"):** keep this workspace's running design (the one already reviewed, pushed and audited in
earlier batches) and **intake every capability the ZIP's redesign added**, rather than swapping trees. Each
intake is listed in §4 with its verification.

## 2. The architecture (unchanged by the intake)

**Backend** — Python 3.9+ standard library only.
- `weathergpt_data/workspace.py`: `ThreadingHTTPServer` on loopback, per-process session token in the served
  page (`workspace-token` meta), strict CSP (`script-src 'self'`, `style-src 'self'`), the POST route table at
  module scope (`post_routes()`) so routes are enumerable and auditable.
- Product read model: `weathergpt_data/product_api.py` — `PRODUCT_PATHS` is the single list of 28 read routes
  (`/api/overview`, `/api/warnings/national`, `/api/forecast`, `/api/advisories/holdings`, …); each view
  returns the same envelope (`schema_version, view, status, data, sources, coverage, limitations,
  not_established`).
- Conversation engine: `weathergpt_data/conversation.py` (+ `task_dispatch.py`, `document_tools.py`,
  `corpus_tools.py`, `advisory.py`, `warning_tools.py`, …). A turn is planned into typed tasks, each task is
  executed by a governed tool, and the answer is assembled with facts, citations, passages, coverage and
  notes. Providers: local Ollama, DeepSeek, OpenRouter free, or the deterministic rules planner.
- Storage: raw SQLite under `data/runtime/` (ingestion, conversations, watches, plans, briefcase) plus the
  corpus index (`data/runtime/ingestion/bulletins/bulletin-grid-v2/index.sqlite`) that holds documents,
  passages and their embeddings.
- External data: Open-Meteo (S21 forecast, S62 hourly, ERA5 history), IMD (S15 district warnings, S57 district
  agromet, S07 state agromet, GeoServer geometry), GeoNames catalogue, aviationweather.gov, CAP relay.

**Frontend** — React 19 + Vite 6 + TypeScript + Tailwind v4 + TanStack Query + Motion, built to `web/dist` and
served by the same Python process (no dev proxy; the token comes from the served page).
- Shell: rail + topbar + command palette + toasts, glass/aurora design layer (`web/tokens-v2.css`,
  `frontend/src/ui/kit.tsx`).
- 19 registry surfaces loaded lazily by `shell/SurfaceHost.tsx` from `modules/registry.ts`.
- Charts: the served engine `web/viz.js` (pinned by nine checks) wrapped by `charts/VizFigure.tsx` and fed by
  `charts/vizSpecs.ts`; the surface-local `charts/ChartBlock.tsx` draws returned series without inventing a
  point.
- Maps: `modules/MapSurface.tsx` (layer deck + inspector), `modules/DistrictRiskMap.tsx` (district choropleth
  joined to warning rows), `modules/IndiaWarningMap.tsx` (the intaken India map used by the dashboard).

## 3. Data flow

```
question ─▶ conversation engine ─▶ typed plan ─▶ task dispatch
                                                   ├─ governed tool ─▶ source adapter ─▶ cache/runtime store
                                                   └─ document corpus (index.sqlite) ─▶ passages
        ─▶ facts / citations / passages / coverage ─▶ answer (template or validated written prose) ─▶ UI card
```

A surface follows the same shape: `getJson('/api/<view>')` → envelope → sections that render only returned
values, with the envelope's own `coverage`, `limitations`, `not_established` and `sources` in the footer.

## 4. What was intaken from the ZIP, and how it was verified

| Intaken | Why it matters | Verification |
| --- | --- | --- |
| `charts/VizFigure.tsx`, `charts/vizSpecs.ts`, `charts/viz.css`, newer `ChartBlock.tsx`/`charts.css` | The served engine was **never mounted** in React, so six figures the vanilla frontend drew (meteogram, district × day matrix, now band, published-day timeline, ensemble fan, library cards) were unreachable while their code stayed served and tested | `window.viz` loads from `/viz.js`; the mounted meteogram draws **113 marks** in one SVG in a live browser; 339 React checks pass |
| Mounts: Forecast (meteogram), Warnings (district × day matrix), Ensemble (member distribution), Today (now band), Published documents (library) | Each figure now sits above the tables that carry the same numbers | section present per surface; typecheck + suites green |
| `modules/WorkspaceSurface.tsx` (966 lines) | Replaces this workspace's **placeholder** Dashboard with the real place-centred desk: forecast hours/days, right-now station + published day, the India warning map, air quality, the climate record, briefs and plans, each reading its own route with its own loading/error state | its own 5 checks pass (port + parity), the route sweep shows 11 sections / 6 tables on `#/workspace` |
| `modules/dashboard.ts` (+ `dashboard.test.ts`) | The series helpers the dashboard reads (`currentIndex`, `dayRows`, `valueAt`, `windowOf`) | its unit checks pass |
| `modules/IndiaWarningMap.tsx` | The India district warning picture on the dashboard | rendered by the dashboard; no console errors on the route |
| `shell/icons.tsx` | The dashboard's own glyphs (droplet, thermometer, wind, sky) | typecheck |
| `shell/navigation.ts` (+ test), view label "Dashboard" | The top-navigation information architecture: which surface belongs to which group, with a note per surface | its check passes; the rail now labels the place dashboard "Dashboard" |
| `charts/viz.parity.test.ts` (newer), `charts/charts.test.tsx` (newer) | The engine-parity checks | pass |
| Evidence helpers: working place (`readWorkingPlace`/`rememberPlace`/`useWorkingPlace`), `useSourceRefresh`, `RefreshButton`, richer `PlacePicker` | One working place across surfaces; "refresh from the source" on the product reads | picked up by the forecast flow (place chosen → read → figure drawn) |
| Test harness: `IntersectionObserver` stub, MSW defaults for the dashboard routes | The dashboard reads only when a section nears the screen; the harness must model that | 339 checks pass |
| `shell/AtmosphericBackground.tsx`, `assets/atmosphere*.svg`, `shell/TopNav.tsx` | The other design's atmosphere and top navigation | **reviewed and not adopted**: this workspace's shell already carries the aurora field and the glass topbar, so mounting both would double the chrome. The files were removed again after the review rather than left as dead code, and the decision is recorded here |

## 5. Known risks

1. **Two parallel redesigns.** The ZIP's frontend and this workspace's diverge in shell and styling. The intake
   took the ZIP's *capabilities*, not its chrome; a reader switching trees will see the same features in a
   different frame.
2. **The extracted tree is read-only here.** Its `audit/` captures and `explore-routes.json` could not be
   refreshed in place.
3. **The figures depend on `/viz.js`.** If the file is missing the figure is absent and the tables still carry
   every value (by design), so a missing engine degrades quietly — the parity test and this audit are what keep
   that honest.
4. **The dashboard reads many routes.** Each has its own loading/error state, but a slow store makes the first
   paint slower than the single-read surfaces.
5. **The engine's providers.** A model provider that is slow or absent changes answer *wording*, never the
   facts: the validators fall back to template text (documented in `CONTEXT_HANDOFF.md` and unchanged here).

## 6. Integration points (where the next change goes)

- A new backend read: add the path to `PRODUCT_PATHS` and `dispatch_extra`, declare it in
  `scripts/audit_surface_registry.py` (`SURFACE_ROUTES` or `SUBROUTE_REASONS`), then read it from a surface.
- A new figure: build the spec in `charts/vizSpecs.ts` from the read's own fields and mount
  `<VizFigure kind="…" spec={…} />`, with the table alternative that already exists beside it.
- A new surface: register it in `shell/views.ts`, `modules/registry.ts` and the surface-registry audit.
