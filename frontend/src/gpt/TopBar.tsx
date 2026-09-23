/* The bar above the thread.
   ============================================================================
   It carries what this thread IS and what can be done to the whole of it — not navigation, which lives in
   the rail, and not settings, which live in the reading panel. "Watch" used to sit here as well as in the
   rail, which put the same action on screen twice.

   The skyline is a statement, not a control: the place the answers are about and what the nearest station
   last printed there. It states the source line too, under the value rather than in a title attribute: a
   reading is the one number in this bar, and a tooltip is not provenance for a reader who never hovers.
   The panel beside this bar is where a place is changed. */

import { useTranslation } from 'react-i18next';
import { Download, PanelLeft, SlidersHorizontal, Wind } from 'lucide-react';
import { SkyGlyphIcon } from '../shell/icons';
import type { SkyReading } from './sky';
import { stationSource } from './Welcome';
import { shortPlace } from '../lib/locale';

export type TopBarProps = {
  atmosphere?: boolean;
  onToggleAtmosphere?: () => void;
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

export function TopBar({ atmosphere, onToggleAtmosphere, title, chatting, sky, panelOpen, onTogglePanel, onToggleRail, onExport }: TopBarProps) {
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
        <div className="g-top-identity"><span className="g-wordmark">WeatherGPT</span>
        {chatting
          ? <h1 className="g-top-title" title={title}>{title}</h1>
          : <p className="g-top-title" title={title}>{title}</p>}
        </div>
      </div>

      {/* The value and the line that owns it, in one region the audit checks by content. `data-lead` is the
          product's own reset for a claim that is a statement on the ground rather than a card in a grid —
          no border, no fill, no shadow — and the two inline properties put the source line on its own row
          under the reading instead of beside it in the 264px the rail takes. */}
      {hasSky ? (
        <p
          className="g-skyline g-claim"
          data-lead="true"
          data-testid="skyline"
          title={sky ? stationSource(sky) : undefined}
          style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'flex-end', columnGap: '7px', rowGap: '2px', padding: 0 }}
        >
          {sky?.glyph ? <SkyGlyphIcon glyph={sky.glyph} size={15} strokeWidth={1.5} aria-hidden="true" /> : null}
          {sky?.place ? <span className="g-skyline-place" title={sky.place}>{shortPlace(sky.place)}</span> : null}
          {sky?.temperature ? <span className="g-skyline-value">{sky.temperature}{sky.unit || ''}</span> : null}
          {sky?.condition ? <span className="g-skyline-cond">{sky.condition}</span> : null}
          {/* The station's source line, here ONLY while the front door is not on screen.

              It used to be on three surfaces at once - this bar, the rail's place block, and under the
              reading on the welcome - so somebody opening the product met the same monospace string
              three times before they met a single sentence of weather. Provenance that repeats stops
              reading as rigour and starts reading as instrumentation left switched on.

              Deleting it outright was the wrong correction and a spec caught it: during a conversation
              the welcome is gone, so the bar would have been showing a value with its source nowhere
              on the page but a tooltip. A value whose provenance is only reachable by hovering is a
              value a reader has to take on trust, which is the one thing this product does not ask.

              So it is stated exactly once, and which surface says it depends on which surface is
              there: the welcome owns it on the front door, the bar owns it once a conversation
              starts. */}
          {sky && chatting ? (
            <span className="g-claim-source g-skyline-source">{stationSource(sky)}</span>
          ) : null}
        </p>
      ) : null}

      <div className="g-top-left">
        {onToggleAtmosphere ? <button type="button" className="g-act" onClick={onToggleAtmosphere} aria-pressed={atmosphere} aria-label={atmosphere ? 'Pause background motion' : 'Resume background motion'} title={atmosphere ? 'Pause background motion' : 'Resume background motion'}><Wind size={17} aria-hidden="true" /></button> : null}
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
