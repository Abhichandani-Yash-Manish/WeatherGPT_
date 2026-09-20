/* The wait's orb: what it is showing, and the two things it must not invent.
   ============================================================================
   The wait already stated the engine's own stage in words. The orb is the same statement drawn, from
   thinking-orbs (MIT, Jakub Antalik): a dotted canvas animation with nine states, two tuned sizes, and
   disciplines this product already keeps - a per-state aria-label, a static frame under prefers-reduced-motion,
   and a pause when the tab is hidden or the orb scrolls out of view.

   It is wired here rather than dropped in, because two of its defaults are wrong for this product:

   1. ITS STATE IS A VERB, so it is read from the engine's own vocabulary and never invented. A stage this
      build does not recognise shows the neutral state, not a guess at what the engine is doing. Every key of
      STAGE_LABELS is answered below, and frontend/src/gpt/orb.test.tsx fails when a stage is added without an
      answer - which is the only thing that keeps a table like this from going stale in silence.
   2. ITS THEME DEFAULTS TO THE OPERATING SYSTEM, and this product's ground is chosen by the HOUR. The two
      disagree exactly when they matter: a reader whose OS is dark, at daybreak, would get light dots on a
      near-white page. So the theme is passed explicitly, from the same attribute the ground is painted from.

   Nothing here decides whether the orb is honest about progress: it says a stage is running, never how far
   along it is. The product's rule that no turn may fabricate a stage, a percentage or an ETA is unchanged and
   is held where it always was, in the stage word beside it. */

import type { OrbState } from 'thinking-orbs';
import { STAGE_LABELS } from '../chat/model';

/* The engine's stages, one answer each. The reason for each pairing is the animation's own meaning rather
   than a synonym hunt: 'searching' sweeps a scan meridian over a globe, which is reaching for published
   evidence; 'connecting' wires a constellation, which is fixing a name to a point; 'weaving' plaits three
   strands into one, which is what assembling an answer from several tools is; 'shaping' morphs a dotted
   outline until it holds a form, which is the last check. */
export const STAGE_ORB: Record<string, OrbState> = {
  started: 'working',
  planned: 'solving',
  resolving: 'connecting',
  retrieving: 'searching',
  assembling: 'weaving',
  finalising: 'shaping',
  'task boundary': 'breathing',
};

/* What a stage this build cannot name shows. It says something is running without claiming what - which is
   the true statement about a stage we do not know. */
export const ORB_FALLBACK: OrbState = 'working';

export function orbStateFor(stage?: string | null): OrbState {
  if (!stage) return ORB_FALLBACK;
  return STAGE_ORB[stage] || ORB_FALLBACK;
}

/* The hours whose ground is light. This list is not a preference: it is the two selectors the tokens key on,
   '[data-hour="daybreak"], [data-hour="noon"]' in tokens.css. Everything else is the night-flight ground, and
   so is an hour we have not seen yet - which is also the stylesheet's own default. */
export const LIGHT_GROUND_HOURS = ['daybreak', 'noon'];
export type GroundTheme = 'light' | 'dark';

export function groundThemeFor(hour?: string | null): GroundTheme {
  return LIGHT_GROUND_HOURS.indexOf(String(hour || '')) >= 0 ? 'light' : 'dark';
}

/* Read from the attribute, not recomputed from the clock: the attribute is what painted the ground, so the
   orb cannot disagree with the page it is drawn on - including in the minutes either side of an hour change. */
export function currentGroundTheme(): GroundTheme {
  if (typeof document === 'undefined') return 'dark';
  return groundThemeFor(document.documentElement.dataset.hour);
}

/* An exported list of the engine's stage names, so a spec can assert the table answers all of them. */
export const ENGINE_STAGES = Object.keys(STAGE_LABELS);
