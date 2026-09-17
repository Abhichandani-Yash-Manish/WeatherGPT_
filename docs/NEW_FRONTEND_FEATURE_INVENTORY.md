# New frontend feature inventory

The React surface as it stands in this workspace **after the intake from the ZIP**: 18 registry surfaces, 53 components and 63 spec files, read from the registry, the views table and the navigation model rather than from prose.

## Routes (18)

| route | surface | module | stage |
| --- | --- | --- | --- |
| #/overview | Today | TodaySurface | R3 |
| #/warnings | Warnings | WarningsSurface | R3 |
| #/map | Map | MapSurface | R3 |
| #/changes | What changed | ChangesSurface | R3 |
| #/forecast | Forecast | ForecastSurface | R3 |
| #/observations | Observations | ObservationsSurface | R3 |
| #/advisories | Farm advisories | AdvisoriesSurface | R3 |
| #/air-quality | Air quality | AirQualitySurface | R3 |
| #/documents | Published documents | DocumentsSurface | R3 |
| #/climate | Climate records | ClimateSurface | R3 |
| #/ensemble | Ensemble spread | EnsembleSurface | R4 |
| #/verification | Forecast verification | VerificationSurface | R4 |
| #/compare | Compare places | CompareSurface | R3 |
| #/briefcase | Briefcase | BriefcaseSurface | R3 |
| #/marine | Sea and rivers | MarineSurface | R4 |
| #/workspace | Dashboard | WorkspaceSurface | R3 |
| #/aviation | Aviation | AviationSurface | R3 |
| #/settings | Sources and settings | SettingsSurface | R3 |

## Navigation groups (from shell/navigation.ts)

- **Dashboard** - workspace
- **Forecast** - forecast, changes, ensemble, verification, compare
- **Climate** - climate, marine
- **Insights** - observations, air-quality, advisories, documents
- **AI Assistant** - assistant
- **Map** - map, warnings, overview
- **More** - aviation, briefcase, settings

## Shell
- Rail (icons, shortcut on hover, drawer under 64rem), glass topbar (store state, per-product health, reading position, answer language, plans, commands, theme, new, lock), command palette (Alt+K), toasts, pinned places, landing page and owner gate.
- Design layer `web/tokens-v2.css` (glass, aurora, motion) over `web/tokens.css`; component kit in `frontend/src/ui/`.

## Figures and maps

| figure | drawn by | mounted on |
| --- | --- | --- |
| Meteogram | served engine /viz.js (VizFigure + vizSpecs) | Forecast |
| District x day matrix | served engine | Warnings |
| Member distribution (ensemble fan) | served engine | Ensemble spread |
| Now band (three lanes) | served engine | Today |
| Library cards | served engine | Published documents |
| Evidence series (ChartBlock) | React SVG from the returned points | surfaces with charts |
| District choropleth | DistrictRiskMap (React SVG) | Today |
| India warning map | IndiaWarningMap (React SVG) | Dashboard |
| Map deck: layers, zoom, find, inspector, legend | MapSurface + mapFigure | Map |
| Published-day timeline | dayTimelineSpec exists | **not mounted** - its read (the overview place strip) is empty in this build |

## Components (53)

- `App.tsx`
- `charts/ChartBlock.tsx`
- `charts/VizFigure.tsx`
- `chat/AnswerTurn.tsx`
- `chat/AskSurface.tsx`
- `chat/Composer.tsx`
- `chat/ConversationRail.tsx`
- `chat/Passages.tsx`
- `chat/Transcript.tsx`
- `chat/Welcome.tsx`
- `chat/WorkingTurn.tsx`
- `chat/parts.tsx`
- `landing/Landing.tsx`
- `landing/OwnerGate.tsx`
- `main.tsx`
- `modules/AdvisoriesSurface.tsx`
- `modules/AirQualitySurface.tsx`
- `modules/AviationSurface.tsx`
- `modules/BriefcaseSurface.tsx`
- `modules/ChangesSurface.tsx`
- `modules/ClimateSurface.tsx`
- `modules/CompareSurface.tsx`
- `modules/DashboardCharts.tsx`
- `modules/DistrictInspector.tsx`
- `modules/DistrictRiskMap.tsx`
- `modules/DocumentViewer.tsx`
- `modules/DocumentsSurface.tsx`
- `modules/EnsembleSurface.tsx`
- `modules/Evidence.tsx`
- `modules/ForecastSurface.tsx`
- `modules/IndiaWarningMap.tsx`
- `modules/MapSurface.tsx`
- `modules/MapTip.tsx`
- `modules/MarineSurface.tsx`
- `modules/ObservationsSurface.tsx`
- `modules/SettingsSurface.tsx`
- `modules/TodaySurface.tsx`
- `modules/VerificationSurface.tsx`
- `modules/WarningsSurface.tsx`
- `modules/WorkspaceSurface.tsx`
- `plans/PlanWatch.tsx`
- `probe.tsx`
- `shell/AtmosphericBackground.tsx`
- `shell/Aurora.tsx`
- `shell/ErrorBoundary.tsx`
- `shell/Palette.tsx`
- `shell/Rail.tsx`
- `shell/SkyBackground.tsx`
- `shell/SurfaceHost.tsx`
- `shell/TopNav.tsx`
- `shell/Topbar.tsx`
- `shell/icons.tsx`
- `ui/kit.tsx`
