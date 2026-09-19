/* The reading panel: how this conversation is being read.
   ============================================================================
   Codex keeps its environment in a panel on the right — the branch, the changes, the commit — and the shape
   is right for a product whose every answer depends on three things the reader sets once: the place, the
   language and the persona. Those three used to sit in the top bar as two native selects and a chip, which is
   where the page's machinery showed through. Here they are one panel that opens when a reader wants it and is
   out of the way when they do not.

   Nothing in it is a control for its own sake. The place can be changed, the language and the persona are
   chosen, and the reading is stated exactly as the station printed it — with its distance, its age and its
   staleness, because a reading without those is not the reading this product promises. */

import { useQuery } from '@tanstack/react-query';
import { MapPin, X } from 'lucide-react';
import { getJson } from '../api/client';
import type { Languages } from '../api/types';
import { allLanguages, measuredFor } from '../chat/voice';
import { useSky } from './sky';
import { istStamp } from '../lib/time';
import { SkyGlyphIcon } from '../shell/icons';
import { useWorkingPlace } from '../modules/Evidence';
import type { Persona } from '../api/types';

export type ReadingPanelProps = {
  language: string;
  onLanguage: (code: string) => void;
  persona: string;
  onPersona: (id: string) => void;
  personas: Persona[];
  onFindPlace: () => void;
  onOpenView: (viewId: string) => void;
  onClose: () => void;
};

export function ReadingPanel({
  language, onLanguage, persona, onPersona, personas, onFindPlace, onOpenView, onClose,
}: ReadingPanelProps) {
  const place = useWorkingPlace();
  const sky = useSky();
  const reading = sky.data;
  const languages = useQuery({ queryKey: ['languages'], queryFn: () => getJson<Languages>('/api/languages'), staleTime: 300_000 });
  const live = allLanguages(languages.data);

  return (
    <aside className="g-panel-side" aria-label="How this conversation is read">
      <header className="g-side-head">
        <h2 className="g-side-title">Reading</h2>
        <button type="button" className="g-act" onClick={onClose} aria-label="Close the reading panel" title="Close">
          <X size={15} aria-hidden="true" />
        </button>
      </header>

      <section className="g-side-block">
        <p className="g-side-label">Place</p>
        <p className="g-side-place">
          <MapPin size={14} aria-hidden="true" />
          <span>{place?.label || 'No place held'}</span>
        </p>
        <button type="button" className="g-quiet" onClick={onFindPlace}>
          {place ? 'Change the place' : 'Set a place'}
        </button>
        <p className="g-side-note">
          {place
            ? 'The place is held in this browser and answers about it are read from the sources nearest to it.'
            : 'With no place held, the sun and the hour are read at the centre of the country. Nothing about a place is inferred from anywhere.'}
        </p>
      </section>

      <section className="g-side-block">
        <p className="g-side-label">The nearest station</p>
        {sky.isPending ? <p className="g-side-note">Reading the nearest station report…</p> : null}
        {sky.isError ? <p className="g-side-note">The station read did not answer. Nothing is shown rather than a value being filled in.</p> : null}
        {!sky.isPending && !sky.isError && !reading ? (
          <p className="g-side-note">No place is held, so no station was read.</p>
        ) : null}
        {reading ? (
          <>
            <p className="g-side-reading">
              {reading.glyph ? <SkyGlyphIcon glyph={reading.glyph} size={22} strokeWidth={1.5} aria-hidden="true" /> : null}
              {reading.temperature ? (
                <span className="g-side-temp">
                  {reading.temperature}
                  {reading.unit ? <span className="g-side-unit">{reading.unit}</span> : null}
                </span>
              ) : null}
              {reading.condition ? <span className="g-side-cond">{reading.condition}</span> : null}
            </p>
            <p className="g-side-source">
              {[reading.station, reading.sourceId,
                reading.observedAt ? 'read ' + istStamp(reading.observedAt) : null,
                reading.distanceKm !== null ? reading.distanceKm.toFixed(1) + ' km away' : null,
                reading.temperature && !reading.unit ? 'no unit in the source' : null,
              ].filter(Boolean).join(' · ')}
            </p>
            {reading.stale ? <p className="g-side-warn">The source marks this report stale.</p> : null}
          </>
        ) : null}
      </section>

      <section className="g-side-block">
        <label className="g-side-label" htmlFor="answer-language">Answer language</label>
        <select
          id="answer-language"
          className="g-side-select"
          value={language}
          onChange={event => onLanguage(event.target.value)}
        >
          <option value="">Match my question</option>
          {live.map(entry => (
            <option key={entry.code} value={entry.code}>
              {entry.english_name}{measuredFor(entry, 'write') !== 'verified' ? ' — writing not measured' : ''}
            </option>
          ))}
        </select>
        <p className="g-side-note">
          Understanding a language and being able to write it are measured separately, and the list says which
          is which. A request this machine cannot answer honestly is refused in words rather than attempted.
        </p>

        <label className="g-side-label" htmlFor="reading-persona">Reading as</label>
        <select
          id="reading-persona"
          className="g-side-select"
          value={persona}
          onChange={event => onPersona(event.target.value)}
        >
          <option value="">Default reading</option>
          {personas.map(entry => <option key={entry.id} value={entry.id}>{entry.label}</option>)}
        </select>
      </section>

      <section className="g-side-block">
        <p className="g-side-label">Ways in</p>
        <div className="g-side-links">
          <button type="button" className="g-quiet" onClick={() => onOpenView('overview')}>Today across India</button>
          <button type="button" className="g-quiet" onClick={() => onOpenView('warnings')}>Warnings in force</button>
          <button type="button" className="g-quiet" onClick={() => onOpenView('sources')}>Sources this machine reads</button>
        </div>
      </section>
    </aside>
  );
}
