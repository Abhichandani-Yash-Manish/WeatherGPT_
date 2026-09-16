/* Which module fills which surface, and how it is loaded.

   A surface that is not ported yet says so, with the stage it arrives in and the questions it will answer,
   and offers to ask one of those questions in the conversation instead. That keeps a placeholder from
   passing as a working surface while still making the route useful. */

import type { ViewId } from '../shell/views';

export type ModuleSurface = { Surface: () => JSX.Element; intents?: string[] };

type Entry = { load: () => Promise<ModuleSurface>; stage: string };

export const MODULES: Partial<Record<ViewId, Entry>> = {
  overview: { load: () => import('./TodaySurface'), stage: 'R3' },
  warnings: { load: () => import('./WarningsSurface'), stage: 'R3' },
  map: { load: () => import('./MapSurface'), stage: 'R3' },
  changes: { load: () => import('./ChangesSurface'), stage: 'R3' },
  forecast: { load: () => import('./ForecastSurface'), stage: 'R3' },
  observations: { load: () => import('./ObservationsSurface'), stage: 'R3' },
  advisories: { load: () => import('./AdvisoriesSurface'), stage: 'R3' },
  'air-quality': { load: () => import('./AirQualitySurface'), stage: 'R3' },
  documents: { load: () => import('./DocumentsSurface'), stage: 'R3' },
  settings: { load: () => import('./SettingsSurface'), stage: 'R3' },
};

export function moduleFor(id: ViewId): Entry | undefined {
  return MODULES[id];
}
