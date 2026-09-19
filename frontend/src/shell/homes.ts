/* The four homes.
   ============================================================================
   Until now every surface opened as a sheet inside the conversation column, because the governing idea was
   that the conversation is the whole product. That idea cost the scanning surfaces their measure: a
   district-by-day matrix and a widget board were being drawn inside a 740px reading column built for
   prose, and the result was cramped in the middle of the window with empty space either side.

   So the product has four homes, and each one gets the measure and the furniture its job needs:

     ask        one conversation, a reading measure, nothing else on the screen
     warnings   the live hazard picture, full width
     history    what happened, and how good the forecasts turned out to be
     board      widgets: what this machine can read, at a glance

   An answer does not lose its evidence to this. The claim, the source and the retrieval time still arrive
   inside the reply — that chain of custody is the product — and gain a link to the home that holds more of
   the same. A home is where you go to browse; an answer is still where you go to know. */

import type { ViewEntry } from './views';
import { VIEWS } from './views';

export type HomeId = 'ask' | 'warnings' | 'history' | 'board';

export type Home = {
  id: HomeId;
  label: string;
  /** What the section rail offers once you are inside. The first is the home's own landing surface. */
  views: string[];
  blurb: string;
};

export const HOMES: Home[] = [
  {
    id: 'ask',
    label: 'Ask',
    views: ['assistant'],
    blurb: 'One conversation, with every value carrying where it came from.',
  },
  {
    id: 'warnings',
    label: 'Warnings',
    views: ['overview', 'warnings', 'map', 'changes', 'advisories'],
    blurb: 'What is in force right now, as the bulletins published it.',
  },
  {
    id: 'history',
    label: 'History',
    views: ['climate', 'verification', 'compare', 'documents'],
    blurb: 'The record: what was published, what happened, and how the forecasts did.',
  },
  {
    id: 'board',
    label: 'Board',
    views: ['workspace', 'forecast', 'observations', 'air-quality', 'aviation', 'marine', 'ensemble', 'briefcase', 'settings'],
    blurb: 'Every source this machine reads, at a glance.',
  },
];

export const homeById = (id: string): Home | undefined => HOMES.find(home => home.id === id);

/** Which home a surface belongs to. Every registered view has exactly one, and this is checked. */
export function homeOf(viewId: string): Home | undefined {
  return HOMES.find(home => home.views.includes(viewId));
}

/** The surfaces of a home, as registry entries, in the order the rail should list them. */
export function viewsOf(home: Home): ViewEntry[] {
  return home.views
    .map(id => VIEWS.find(view => view.id === id))
    .filter((view): view is ViewEntry => Boolean(view));
}

/** Every registered view is placed in exactly one home — no orphans, no duplicates. */
export function unplacedViews(): string[] {
  return VIEWS.filter(view => !homeOf(view.id)).map(view => view.id);
}
