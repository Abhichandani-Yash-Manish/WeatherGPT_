/* The bar above the thread.
   ============================================================================
   It carries what this thread IS and what can be done to the whole of it — not navigation, which lives in
   the rail, and not settings, which live in the reading panel. "Watch" used to sit here as well as in the
   rail, which put the same action on screen twice.

   The skyline is a statement, not a control: the place the answers are about and what the nearest station
   last printed there, with the station, its id and its read time in the title. The panel beside this bar
   is where a place is changed. */

import { useTranslation } from 'react-i18next';
import { Download, PanelLeft, SlidersHorizontal } from 'lucide-react';
import { istStamp } from '../lib/time';
import { SkyGlyphIcon } from '../shell/icons';
import type { SkyReading } from './sky';

export type TopBarProps = {
  /** The question this conversation opened with, which is the only name it has ever had. */
  title: string;
  chatting: boolean;
  sky: SkyReading | null;
  panelOpen: boolean;
  onTogglePanel: () => void;
  onToggleRail: () => void;
  /** Absent until there is something to export. */
  onExport: (() => void) | null;
};

export function TopBar({ title, chatting, sky, panelOpen, onTogglePanel, onToggleRail, onExport }: TopBarProps) {
  const { t } = useTranslation();
  const hasSky = Boolean(sky?.place || sky?.temperature || sky?.condition);

  return (
    <header className="g-top">
      <div className="g-top-left">
        <button type="button" className="g-act g-rail-toggle" onClick={onToggleRail} aria-label={t('rail.conversations')}>
          <PanelLeft size={17} aria-hidden="true" />
        </button>
        {/* The page's h1 only once a conversation exists: on the welcome the greeting is the heading, and
            two h1s on one page is a structure a screen reader has to guess at. */}
        {chatting
          ? <h1 className="g-top-title" title={title}>{title}</h1>
          : <p className="g-top-title" title={title}>{title}</p>}
      </div>

      {hasSky ? (
        <p
          className="g-skyline"
          data-testid="skyline"
          title={[sky?.place, sky?.station, sky?.sourceId, sky?.observedAt ? 'read ' + istStamp(sky.observedAt) : null]
            .filter(Boolean).join(' · ')}
        >
          {sky?.glyph ? <SkyGlyphIcon glyph={sky.glyph} size={15} strokeWidth={1.5} aria-hidden="true" /> : null}
          {sky?.place ? <span className="g-skyline-place">{sky.place}</span> : null}
          {sky?.temperature ? <span className="g-skyline-value">{sky.temperature}{sky.unit || ''}</span> : null}
          {sky?.condition ? <span className="g-skyline-cond">{sky.condition}</span> : null}
        </p>
      ) : null}

      <div className="g-top-left">
        {/* The whole exchange, not one turn: the per-turn actions live under each answer, and a reader
            exporting a conversation should not have to do it one card at a time. */}
        {onExport ? (
          <button
            type="button"
            className="g-act"
            onClick={onExport}
            /* The WHOLE exchange, which is a different action from the per-turn save under each answer.
               Sharing a label with it made two different things claim to be the same one. */
            aria-label={t('answer.saveConversation')}
            title={t('answer.saveConversation')}
          >
            <Download size={16} aria-hidden="true" />
          </button>
        ) : null}
        {/* The panel holds the three things an answer depends on — place, language, persona — which used
            to sit in this bar as two native selects. */}
        <button
          type="button"
          className="g-act"
          aria-pressed={panelOpen}
          aria-label={panelOpen ? t('panel.close') : t('panel.open')}
          title={t('panel.title')}
          onClick={onTogglePanel}
        >
          <SlidersHorizontal size={16} aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}
