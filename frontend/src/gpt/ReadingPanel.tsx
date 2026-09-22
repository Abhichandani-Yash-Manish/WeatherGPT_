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

import { useSyncExternalStore } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MapPin, X } from 'lucide-react';
import { getJson, withQuery } from '../api/client';
import type { Envelope, Languages } from '../api/types';
import { failureSentence } from '../modules/Evidence';
import { allLanguages, measuredFor } from '../chat/voice';
import { useSky } from './sky';
import { placeHref } from '../place/place';
import { stationSource } from './Welcome';
import { istClock, istStamp, istWindow } from '../lib/time';
import { SkyGlyphIcon } from '../shell/icons';
import { useWorkingPlace } from '../modules/Evidence';
import type { Persona } from '../api/types';
import { SITE_LANGUAGES, readSiteLanguage, subscribeSiteLanguage, writeSiteLanguage } from '../i18n/siteLanguage';
import type { ChromeLanguage } from '../i18n';

/* ---- what is published for this district, and what is coming --------------------------------------
   The panel states the place; these two blocks say what the product holds for it. Both read the same governed
   routes the surfaces read, both keep their own source line, and both say what they did not get: a district
   with nothing published is not a quiet district, and a missing hour is not a zero.

   The forecast block is a strip of the first hours the read returned, not a chart: the panel is 300px, and a
   300px chart is a decoration. Every number keeps the unit and the source the payload stated.

   The station, the district and the hours are exported because the place's own page (src/place/PlacePage.tsx)
   is the destination this glance points at: the page renders these same blocks for its own point rather than
   a second rendering of the same reads, so a fix here reaches both, and the panel and the page cannot state
   the same read differently. */

type PlaceWarningDay = { date_local?: string; colour?: string | null; hazards?: string[]; quiet?: boolean; source_text?: string; label?: string };
type PlaceWarnings = { district?: string; state?: string; issued_at_utc?: string; days?: PlaceWarningDay[] };
type HourRow = { at?: string; temperature_2m?: number | null; precipitation_probability?: number | null; precipitation?: number | null };
type HoursView = { status?: string; rows?: HourRow[]; source_id?: string; model?: string; unit?: Record<string, string>; starts?: string; ends?: string };

export function DistrictBlock({ place, onOpen }: { place: { latitude: number; longitude: number }; onOpen: (viewId: string) => void }) {
  const read = useQuery({
    queryKey: ['panel-warnings', place.latitude, place.longitude],
    queryFn: () => getJson<Envelope<PlaceWarnings>>(withQuery('/api/warnings/place', { lat: place.latitude, lon: place.longitude })),
    retry: false,
  });
  const published = read.data?.data;
  const days = (published?.days || []).filter(day => day && (day.colour || day.hazards?.length || day.quiet));
  /* The district block's own source line, from the envelope the read returned: the district name and issue
     instant say which bulletin, and this says which registered source it came through. Without it the block
     stated a hazard and a colour with nothing to check them against. */
  const sources = [...new Set((read.data?.sources || [])
    .filter(entry => entry.source_id)
    .map(entry => [entry.source_id, entry.layer].filter(Boolean).join(' ')))];

  return (
    <section className="g-side-block">
      <p className="g-side-label">Published for this district</p>
      {read.isPending ? <p className="g-side-note">Reading the district’s published warning…</p> : null}
      {read.isError ? <p className="g-side-note">{failureSentence(read.error)}</p> : null}
      {!read.isPending && !read.isError && !published ? (
        <p className="g-side-note">The read answered without a district block, so nothing is printed about a warning here.</p>
      ) : null}
      {/* The glance and the destination: the panel says what is published, and the surface says it in full. */}
      <button type="button" className="g-quiet" onClick={() => onOpen('warnings')}>Warnings in force →</button>
      {published ? (
        <>
          <p className="g-side-note">
            {[published.district, published.state].filter(Boolean).join(', ') || 'The read named no district for this point'}
            {published.issued_at_utc ? ' · issued ' + istStamp(published.issued_at_utc) : ' · the read states no issue time'}
          </p>
          {days.length ? (
            <ul className="g-side-days">
              {days.slice(0, 3).map(day => (
                <li key={(day.date_local || day.label || '') + (day.colour || '')}>
                  <span className="g-side-when">{day.label || day.date_local || 'a published day'}</span>
                  {/* A quiet day is a statement the source made, and it does not also need a hazard line
                      saying the source said nothing: that is the same fact twice, once as a gap. */}
                  {day.quiet ? (
                    <span className="g-side-quiet">nothing flagged</span>
                  ) : (
                    <>
                      <span className="wchip" data-colour={(day.colour || '').toLowerCase()}>{day.colour || 'colour not stated'}</span>
                      {day.hazards?.length ? (
                        <span className="g-side-hazard">{day.hazards.join(', ')}</span>
                      ) : day.source_text ? (
                        <span className="g-side-hazard">{day.source_text}</span>
                      ) : null}
                    </>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="g-side-note">This read published no day for this district, which is not the same as a quiet one.</p>
          )}
        </>
      ) : null}
      {sources.length ? <p className="g-side-source">{sources.join(' · ')}</p> : null}
    </section>
  );
}

export function HoursBlock({ place, onOpen }: { place: { latitude: number; longitude: number }; onOpen: (viewId: string) => void }) {
  const read = useQuery({
    queryKey: ['panel-hours', place.latitude, place.longitude],
    queryFn: () => getJson<Envelope<HoursView>>(withQuery('/api/forecast', { lat: place.latitude, lon: place.longitude, days: 2 })),
    retry: false,
  });
  const hours = read.data?.data;
  const rows = (hours?.rows || []).slice(0, 6);
  const unit = hours?.unit || {};

  return (
    <section className="g-side-block">
      <p className="g-side-label">The next hours</p>
      {read.isPending ? <p className="g-side-note">Reading the model hours…</p> : null}
      {read.isError ? <p className="g-side-note">{failureSentence(read.error)}</p> : null}
      {!read.isPending && !read.isError && !rows.length ? (
        <p className="g-side-note">This read returned no hourly row for the point, so nothing is drawn rather than a value being invented.</p>
      ) : null}
      <button type="button" className="g-quiet" onClick={() => onOpen('forecast')}>The forecast surface →</button>
      {rows.length ? (
        <>
          <ul className="g-side-hours">
            {rows.map(row => (
              <li key={String(row.at)}>
                <span className="g-side-hour">{istClock(row.at)}</span>
                <span className="g-side-value">
                  {typeof row.temperature_2m === 'number' ? row.temperature_2m + (unit.temperature_2m || '') : 'temperature not returned'}
                </span>
                <span className="g-side-value">
                  {typeof row.precipitation_probability === 'number' ? row.precipitation_probability + (unit.precipitation_probability || '') + ' rain chance' : 'rain chance not returned'}
                </span>
              </li>
            ))}
          </ul>
          <p className="g-side-source">
            {[hours?.source_id, hours?.model, hours?.starts && hours?.ends ? istWindow(hours.starts, hours.ends) : null].filter(Boolean).join(' · ')}
          </p>
        </>
      ) : null}
    </section>
  );
}

/* The nearest station's own report for the place this browser holds: the station's wording, its source id,
   when it was read and how far away it is. Extracted so the place's page states the station exactly as the
   panel does — one rendering of one read. */
export function StationBlock() {
  const place = useWorkingPlace();
  const sky = useSky();
  const reading = sky.data;

  return (
    <section className="g-side-block">
      <p className="g-side-label">The nearest station</p>
      {sky.isPending ? <p className="g-side-note">Reading the nearest station report…</p> : null}
      {sky.isError ? <p className="g-side-note">The station read did not answer. Nothing is shown rather than a value being filled in.</p> : null}
      {/* Two different silences, said differently: no place held means no read was made, and a read that
          returned no station is a read that came back empty. One sentence for both would state the first
          when the second happened, which is a fact the surface never measured. */}
      {!sky.isPending && !sky.isError && !reading ? (
        place
          ? <p className="g-side-note">This read returned no station for the point, so nothing is shown rather than a value being filled in.</p>
          : <p className="g-side-note">No place is held, so no station was read.</p>
      ) : null}
      {reading ? (
        /* The reading and its source line are ONE claim region: the product's own atom, so the provenance audit's
           shape check resolves here the way it does on the welcome, the bar and the rail. display: contents keeps
           the block's layout exactly as it was - the wrapper is a region, not a box. */
        <div className="g-claim" style={{ display: 'contents' }}>
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
          <p className="g-side-source g-claim-source">
            {stationSource(reading, { includeStale: false })}
          </p>
          {reading.stale ? <p className="g-side-warn">The source marks this report stale.</p> : null}
        </div>
      ) : null}
    </section>
  );
}

/* One source, as this conversation reached it: the id a claim cites, who published it, and when this
   machine last read it. The panel aggregates these across every answer in the thread. */
export type SourceRead = {
  sourceId: string;
  provider: string | null;
  product: string | null;
  retrievedAt: string | null;
  /** How many claims in this conversation rest on it. */
  claims: number;
};

export type ReadingPanelProps = {
  /** Every source this conversation has read, newest read first. */
  sources: SourceRead[];
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
  sources, language, onLanguage, persona, onPersona, personas, onFindPlace, onOpenView, onClose,
}: ReadingPanelProps) {
  const place = useWorkingPlace();
  const sitePinned = useSyncExternalStore(subscribeSiteLanguage, readSiteLanguage, readSiteLanguage);
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
        {/* The glance and the destination: docs/115 left the place with no page of its own. The anchor is a
            real link — bookmarkable, copyable, openable in a new tab — because "a page a reader can bookmark"
            cannot be a button that rewrites the address. */}
        {place?.label ? (
          <a className="g-quiet" href={placeHref({ label: String(place.label), latitude: place.latitude, longitude: place.longitude })}>
            The place’s own page →
          </a>
        ) : null}
        <p className="g-side-note">
          {place
            ? 'The place is held in this browser and answers about it are read from the sources nearest to it.'
            : 'With no place held, the sun and the hour are read at the centre of the country. Nothing about a place is inferred from anywhere.'}
        </p>
      </section>

      <StationBlock />

      {place && typeof place.latitude === 'number' && typeof place.longitude === 'number' ? (
        <>
          <DistrictBlock place={{ latitude: place.latitude, longitude: place.longitude }} onOpen={onOpenView} />
          <HoursBlock place={{ latitude: place.latitude, longitude: place.longitude }} onOpen={onOpenView} />
        </>
      ) : null}

      <section className="g-side-block">
        {/* THE PRODUCT'S OWN LANGUAGE, which is a different question from the one below it and sits
            above it for that reason. This one changes the rail, the controls and the labels and states
            nothing about the weather, so every option is offered without qualification. The one below
            changes what the ENGINE writes, and its options carry whether writing that language has
            been measured - because there the choice is a claim about an answer. */}
        <label className="g-side-label" htmlFor="site-language">Site language</label>
        <select
          id="site-language"
          className="g-side-select"
          value={sitePinned || ''}
          onChange={event => writeSiteLanguage((event.target.value || null) as ChromeLanguage | null)}
        >
          <option value="">Follow my answer language</option>
          {SITE_LANGUAGES.map(entry => (
            <option key={entry.code} value={entry.code}>
              {entry.own}{entry.own === entry.english ? '' : ' · ' + entry.english}
            </option>
          ))}
        </select>
        <p className="g-side-note">
          Changes the interface only — the rail, the controls and the labels. It does not change what the
          engine writes, and it never changes a value, a unit, a place name or a source.
        </p>

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

      {/* What this conversation has actually read.

          Every claim carries its own source underneath it, which proves that claim. Nothing showed the
          whole set, and the whole set is the thing this product is for: a reader three turns in could not
          say what the answers rested on without opening every fold. It is a list, not a claim, so it
          states only what the citations stated and counts how many claims lean on each. */}
      {sources.length ? (
        <section className="g-side-block" aria-label="Sources read in this conversation">
          <p className="g-side-label">Read in this conversation</p>
          <ul className="g-side-sources">
            {sources.map(source => (
              <li key={source.sourceId}>
                <span className="g-side-source-id">{source.sourceId}</span>
                <span className="g-side-source-name">
                  {[source.product, source.provider].filter(Boolean).join(' · ') || 'no product named in the citation'}
                </span>
                <span className="g-side-source-meta">
                  {source.retrievedAt ? 'read ' + istStamp(source.retrievedAt) : 'read time not recorded'}
                  {' · ' + source.claims + (source.claims === 1 ? ' claim' : ' claims')}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="g-side-block">
        <p className="g-side-label">Ways in</p>
        {/* Only the destinations the blocks above do not already carry: "warnings in force" belongs to the
            district block and "the forecast" to the hours, and a list that repeated them would be three ways
            to the same two places. */}
        <div className="g-side-links">
          <button type="button" className="g-quiet" onClick={() => onOpenView('overview')}>Today across India</button>
          <button type="button" className="g-quiet" onClick={() => onOpenView('sources')}>Sources this machine reads</button>
        </div>
      </section>
    </aside>
  );
}
