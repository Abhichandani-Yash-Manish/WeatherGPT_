/* The home rail.
   ============================================================================
   Four homes, 56px, pinned to the left of everything else. It is deliberately not the conversation rail:
   that one lists what a reader has said, this one lists where they can be, and collapsing the two is what
   left nineteen surfaces sharing a reading column built for prose.

   It does not introduce a second router. The address stays #/<view> — deep links, the port ledger and the
   surface registry all depend on that — and the current home is derived from the current view. Choosing a
   home opens that home's own landing surface. */

import { MessageSquare, TriangleAlert, History, LayoutGrid } from 'lucide-react';
import { HOMES, type HomeId } from './homes';

const GLYPH: Record<HomeId, typeof MessageSquare> = {
  ask: MessageSquare,
  warnings: TriangleAlert,
  history: History,
  board: LayoutGrid,
};

export function HomeRail({ current, onOpen }: { current: HomeId | null; onOpen: (viewId: string) => void }) {
  return (
    <nav className="h-rail" aria-label="Sections">
      {HOMES.map(home => {
        const Glyph = GLYPH[home.id];
        const here = home.id === current;
        return (
          <button
            key={home.id}
            type="button"
            className="h-rail-item"
            aria-current={here ? 'page' : undefined}
            /* The name is the accessible name and the tooltip both: an icon rail with no name is a
               guessing game, and title alone is invisible to a screen reader. */
            title={home.label + ' — ' + home.blurb}
            onClick={() => onOpen(home.views[0])}
          >
            <Glyph size={19} aria-hidden="true" />
            <span className="h-rail-label">{home.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
