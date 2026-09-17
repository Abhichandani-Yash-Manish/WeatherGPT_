/* The framing every module surface shares: one h1, the envelope's own header, named coverage counts,
   the limitations and not-established lines in the surface's own voice, and the source rows.
   Nothing here invents a value or a meaning. Absence is stated as absence ('not recorded',
   'no row returned', 'this read did not answer'), never as a blank, a zero or an empty chart.
   It also owns the two small local memories a reader keeps beside a read: the loading skeleton that
   reserves the shape of an answer in progress, and the pinned-place list the shell shows on every route. */
import { useId, useMemo, useState, useSyncExternalStore, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ApiError, getJson, withQuery } from '../api/client';
import type { Envelope, SourceEntry } from '../api/types';
import { orNot, titleCase } from '../lib/format';
import { istStamp } from '../lib/time';
import './modules.css';

/* React 19's types no longer publish a global JSX namespace. The module contract this repository
   records (Block, Surface, intents) is written in terms of JSX.Element, so the alias is declared
   once, here, instead of every surface spelling the same return type two different ways. */
declare global {
  namespace JSX {
    type Element = import('react').JSX.Element;
  }
}

export const NOT_RECORDED = 'not recorded';
export const NO_ROW = 'no row returned';
export const NO_SOURCE_ROW = 'No source row came back with this read.';
export const COLOUR_NOT_STATED = 'colour not stated';
/* The hazard ramp the design system reserves for an official warning state. A colour name is only
   ever drawn as a colour when the payload stated one of these; anything else is set as a word. */
export const HAZARD_COLOURS = ['red', 'orange', 'yellow', 'green'];

export function failureSentence(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 503 || error.kind === 'unavailable') return 'The local evidence store is unavailable: ' + error.message;
    if (error.kind === 'offline') return 'This read did not answer. ' + error.message;
    return 'This read did not answer: ' + error.message;
  }
  const message = (error as Error)?.message;
  return 'This read did not answer: ' + (message && message.trim() ? message : NOT_RECORDED);
}

/* A caller may name its subject with or without a leading article ('the advisory directory', 'district
   directory'). The article is stripped here so both read as one sentence rather than as 'The the ...'. */
function subject(what: string): string {
  return what.replace(/^the\s+/i, '').trim();
}

/* A read that is still working reserves the shape of what it will occupy: bars stand for the lines a
   result will carry and a frame stands for a chart. It is aria-hidden because the sentence is the part
   worth announcing, carries no number, colour or label that could be read as data, and is drawn without
   animation: this project has no measured progress to animate, so nothing here may read as one. */
export function Skeleton(): JSX.Element {
  return (
    <div className="mt-2 flex flex-col gap-1.5" data-testid="skeleton" aria-hidden="true">
      <span className="h-[9px] w-[82%] rounded bg-sunk" data-skeleton="bar" />
      <span className="h-[9px] w-full rounded bg-sunk" data-skeleton="bar" />
      <span className="h-[9px] w-[46%] rounded bg-sunk" data-skeleton="bar" />
      <span className="h-[92px] rounded-card border border-dashed border-line bg-sunk" data-skeleton="frame" />
    </div>
  );
}

export function Reading({ what }: { what: string }): JSX.Element {
  return (
    <div data-reading={subject(what)}>
      <p className="module-note" role="status">
        Reading {subject(what)} from the local store…
      </p>
      <Skeleton />
    </div>
  );
}

export function Failure({ error, what, onRetry }: { error: unknown; what: string; onRetry?: () => void }): JSX.Element {
  return (
    <div className="module-failure" role="alert">
      <p className="reading">{failureSentence(error)}</p>
      <p className="module-note">
        The {subject(what)} read failed. This surface shows that failure; it is not an empty result and not a quiet day.
      </p>
      {onRetry ? (
        <button type="button" className="btn" onClick={onRetry}>
          Retry this read
        </button>
      ) : null}
    </div>
  );
}

/* A colour chip is drawn only where the read stated a colour from the hazard ramp, and the product's
   own wording stays beside it. An unstated colour is a word, never a green. */
export function ColourTag({ colour, text }: { colour?: string | null; text?: string }): JSX.Element {
  const stated = typeof colour === 'string' ? colour.trim().toLowerCase() : '';
  if (!HAZARD_COLOURS.includes(stated)) {
    return <span className="chip chip-unstated">{text || stated || COLOUR_NOT_STATED}</span>;
  }
  return (
    <span className="chip chip-colour" data-colour={stated}>
      {text || stated}
    </span>
  );
}

export type Fact = [label: string, value: ReactNode];

export function Facts({ rows, testId, id }: { rows: Fact[]; testId?: string; id?: string }): JSX.Element {
  return (
    <dl className="module-facts" data-testid={testId} id={id}>
      {rows.map(([label, value]) => (
        <div className="fact-row" key={label}>
          <dt className="module-fact-label">{label}</dt>
          <dd className="fact-value">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function DataTable({ caption, columns, rows, testId }: {
  caption: string;
  columns: string[];
  rows: ReactNode[][];
  testId?: string;
}): JSX.Element {
  if (!rows.length) return <p className="module-note">{NO_ROW} for this table: {caption}</p>;
  return (
    <table className="module-table" data-testid={testId}>
      <caption>{caption}</caption>
      <thead>
        <tr>
          {columns.map(name => (
            <th key={name} scope="col">
              {name}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={index}>
            {row.map((cell, column) =>
              column === 0 ? (
                <th key={column} scope="row">
                  {cell}
                </th>
              ) : (
                <td key={column}>{cell}</td>
              ),
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function coverageValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return NOT_RECORDED;
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function Coverage({ coverage }: { coverage?: Record<string, unknown> }): JSX.Element {
  const names = Object.keys(coverage || {});
  return (
    <div className="module-coverage">
      <h3>Coverage as this read returned it</h3>
      {names.length ? (
        <dl className="module-counts">
          {names.map(name => (
            <div className="module-count" key={name}>
              <dt>{titleCase(name)}</dt>
              <dd className="evidence">{coverageValue(coverage?.[name])}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="module-note">This read returned no coverage count.</p>
      )}
    </div>
  );
}

export function Limits({ limitations, not_established }: { limitations?: string[]; not_established?: string[] }): JSX.Element {
  const limits = limitations || [];
  const open = not_established || [];
  return (
    <div className="module-limits">
      <h3>Limits of this read</h3>
      {limits.length ? (
        <ul>
          {limits.map((line, index) => (
            <li key={index}>{line}</li>
          ))}
        </ul>
      ) : (
        <p className="module-note">This read returned no limitation line.</p>
      )}
      <h3>Not established here</h3>
      {open.length ? (
        <ul>
          {open.map((line, index) => (
            <li key={index}>{line}</li>
          ))}
        </ul>
      ) : (
        <p className="module-note">This read returned no not-established line.</p>
      )}
    </div>
  );
}

export function Sources({ sources }: { sources?: SourceEntry[] }): JSX.Element {
  const rows = sources || [];
  return (
    <div className="module-sources">
      <h3>Sources</h3>
      {rows.length ? (
        <DataTable
          caption="Every source row this read attached, as the registry returned it."
          columns={['Source', 'Product', 'Retrieved', 'sha256 prefix']}
          rows={rows.map(source => [
            <span className="evidence" key="id">
              {orNot(source.source_id)}
            </span>,
            orNot(source.product),
            source.retrieved_at_utc ? istStamp(source.retrieved_at_utc) : NOT_RECORDED,
            source.sha256_prefix ? <span className="evidence">{source.sha256_prefix}</span> : NOT_RECORDED,
          ])}
        />
      ) : (
        <p className="module-note">{NO_SOURCE_ROW}</p>
      )}
    </div>
  );
}

export function EvidenceFooter({ envelope }: { envelope: Envelope<unknown> }): JSX.Element {
  return (
    <footer className="module-evidence">
      <h2>What this read returned</h2>
      <Coverage coverage={envelope.coverage} />
      <Limits limitations={envelope.limitations} not_established={envelope.not_established} />
      <Sources sources={envelope.sources} />
    </footer>
  );
}

export function SurfaceShell({ title, lead, what, envelope, busy, error, onRetry, children }: {
  title: string;
  lead: string;
  what: string;
  envelope?: Envelope<unknown>;
  busy: boolean;
  error?: unknown;
  onRetry?: () => void;
  children: ReactNode;
}): JSX.Element {
  return (
    <section className="module" data-module={envelope?.view || title.toLowerCase()}>
      <header className="module-head">
        <h1>{title}</h1>
        <p className="module-lead">{lead}</p>
        {envelope ? (
          <p className="module-envelope evidence">
            {orNot(envelope.view)} · status {orNot(envelope.status)} · read{' '}
            {envelope.generated_at_utc ? istStamp(envelope.generated_at_utc) : NOT_RECORDED}
          </p>
        ) : null}
      </header>
      {busy ? <Reading what={what} /> : null}
      {!busy && error ? <Failure error={error} what={what} onRetry={onRetry} /> : null}
      {!busy && !error ? children : null}
      {!busy && !error && envelope ? <EvidenceFooter envelope={envelope} /> : null}
    </section>
  );
}

export type PlaceChoice = { label?: string | null; latitude: number; longitude: number };
export type PlaceMatch = {
  label?: string | null;
  name?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  admin1?: string | null;
  admin2?: string | null;
  selection_id?: string;
  coordinates?: { latitude?: number | null; longitude?: number | null };
};

function placePoint(row: PlaceMatch): PlaceChoice | null {
  const latitude = typeof row.latitude === 'number' ? row.latitude : row.coordinates?.latitude;
  const longitude = typeof row.longitude === 'number' ? row.longitude : row.coordinates?.longitude;
  if (typeof latitude !== 'number' || typeof longitude !== 'number') return null;
  return { label: row.label || row.name || null, latitude, longitude };
}

/* ---- pinned places -----------------------------------------------------------------------------
   A pin is the reader's own shortcut to a place name: a label and two coordinates held in this
   browser's local storage, and nothing else. It saves no answer, carries no reading and makes no
   claim about the place. A place the record did not give coordinates for is refused rather than
   guessed, because a pin without a coordinate would invent a location; and when this browser refuses
   local storage the pin lasts only until the page is reloaded, which the panel states. */
export type PinnedPlace = { label: string; latitude: number; longitude: number };
export type PinCandidate = { label?: string | null; latitude?: number | null; longitude?: number | null };
export const PIN_KEY = 'weathergpt.pinned';
export const PIN_LIMIT = 8;

function routablePlace(place: PinCandidate | null | undefined): boolean {
  if (!place || !place.label) return false;
  return [place.latitude, place.longitude].every(value => typeof value === 'number' && Number.isFinite(value));
}

function parsePins(raw: string | null): PinnedPlace[] {
  if (!raw) return [];
  try {
    const list: unknown = JSON.parse(raw);
    if (!Array.isArray(list)) return [];
    return list
      .filter((item): item is PinnedPlace => routablePlace(item as PinCandidate))
      .map(item => ({ label: String(item.label), latitude: Number(item.latitude), longitude: Number(item.longitude) }))
      .slice(0, PIN_LIMIT);
  } catch {
    return [];
  }
}

/* When local storage refuses a write the list is kept for this page load instead of disappearing. */
let sessionPins: PinnedPlace[] | null = null;
const pinListeners = new Set<() => void>();

export function readPins(): PinnedPlace[] {
  if (sessionPins) return sessionPins;
  try {
    return parsePins(window.localStorage.getItem(PIN_KEY));
  } catch {
    return [];
  }
}

export function subscribePins(listener: () => void): () => void {
  pinListeners.add(listener);
  return () => {
    pinListeners.delete(listener);
  };
}

function pinnedSnapshot(): string {
  return JSON.stringify(readPins());
}

function savePins(list: PinnedPlace[]): PinnedPlace[] {
  const next = list.slice(0, PIN_LIMIT);
  try {
    window.localStorage.setItem(PIN_KEY, JSON.stringify(next));
  } catch {
    /* the browser refused storage; keep the list for this page load and say so in the panel */
    sessionPins = next;
  }
  pinListeners.forEach(listener => listener());
  return next;
}

export function pinPlace(place: PinCandidate | null | undefined): PinnedPlace[] {
  if (!routablePlace(place)) return readPins();
  const target: PinnedPlace = { label: String(place?.label), latitude: Number(place?.latitude), longitude: Number(place?.longitude) };
  return savePins([target].concat(readPins().filter(item => item.label !== target.label)));
}

export function unpinPlace(place: PinCandidate | null | undefined): PinnedPlace[] {
  const label = place?.label ? String(place.label) : '';
  if (!label) return readPins();
  return savePins(readPins().filter(item => item.label !== label));
}

export function isPinned(place: PinCandidate | null | undefined): boolean {
  return Boolean(place?.label) && readPins().some(item => item.label === place?.label);
}

export function pinsAreStoredLocally(): boolean {
  return sessionPins === null;
}

export function usePinnedPlaces(): PinnedPlace[] {
  const snapshot = useSyncExternalStore(subscribePins, pinnedSnapshot);
  return useMemo(() => parsePins(snapshot), [snapshot]);
}

/* The pin control states the place it would keep and flips its own label; a place without coordinates
   is told it cannot be pinned rather than being pinned anyway. When the place is already written next
   to the control, the control names itself and points at that text instead of repeating the name. */
export function PinPlaceButton({ place, describedBy }: { place: PinCandidate; describedBy?: string }): JSX.Element {
  const pinned = useSyncExternalStore(subscribePins, () => isPinned(place));
  if (!routablePlace(place)) {
    return (
      <span className="module-note">
        Coordinates are not recorded for this place, so it cannot be pinned: a pin is never guessed.
      </span>
    );
  }
  const label = orNot(place.label, 'place name not recorded');
  return (
    <button
      type="button"
      className="btn btn-ghost"
      aria-label={(pinned ? 'Unpin' : 'Pin') + (describedBy ? ' this place' : ' ' + label)}
      aria-describedby={describedBy}
      onClick={() => {
        if (pinned) unpinPlace(place);
        else pinPlace(place);
      }}
    >
      {pinned ? 'Unpin' : 'Pin'}
    </button>
  );
}

/* The list the shell shows wherever the reader is: the pins this browser remembers, each with the
   coordinates it holds and its own removal. Nothing here reads a route or states a value. */
export function PinnedPlaces(): JSX.Element {
  const pins = usePinnedPlaces();
  return (
    <section className="border-b border-line bg-paper px-4 py-2" aria-label="Pinned places" data-testid="pinned-places">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="eyebrow">Pinned places</h2>
        <p className="text-xs quiet">
          A pin is a shortcut to a place name you resolved. It saves no answer and makes no claim about the place; it is kept in this
          browser's local storage and sent nowhere.
        </p>
      </div>
      {pins.length ? (
        <ul className="mt-1 flex flex-wrap items-center gap-2" data-testid="pinned-places-list">
          {pins.map(pin => (
            <li key={pin.label} className="flex items-center gap-2 rounded-pill bg-sunk px-2 py-0.5 text-xs">
              <span className="evidence">{pin.label}</span>
              <span className="quiet">
                {pin.latitude}, {pin.longitude}
              </span>
              <button type="button" className="btn btn-ghost" aria-label={'Remove pin ' + pin.label} onClick={() => unpinPlace(pin)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="module-note" data-testid="pinned-places-empty">
          No place is pinned in this browser yet.
        </p>
      )}
      {pins.length && !pinsAreStoredLocally() ? (
        <p className="module-note">This browser refused local storage, so these pins last only until this page is reloaded.</p>
      ) : null}
    </section>
  );
}

/* The reader names a place; the catalogue answers with rows, and only a row that states coordinates
   can be read as a point. A row without coordinates is shown as one rather than resolved elsewhere. */
export function PlacePicker({ onPick, hint }: { onPick: (place: PlaceChoice) => void; hint?: string }): JSX.Element {
  const [term, setTerm] = useState('');
  const query = term.trim();
  const field = useId();
  const rowId = field + '-row-';
  const search = useQuery({
    queryKey: ['places', query],
    queryFn: () => getJson<Envelope<{ matches?: PlaceMatch[] }>>(withQuery('/api/places/search', { q: query })),
    enabled: query.length >= 2,
    retry: false,
  });
  const matches = search.data?.data?.matches || [];
  return (
    <div className="module-place">
      <label className="module-field" htmlFor={field}>
        <span>Name a place</span>
        <input
          id={field}
          type="search"
          value={term}
          placeholder="Type at least two characters"
          onChange={event => setTerm(event.target.value)}
        />
      </label>
      <div className="module-place-results" aria-live="polite">
        {query.length < 2 ? (
          <p className="module-note">{hint || 'The place search reads GET /api/places/search and needs at least two characters.'}</p>
        ) : search.isPending ? (
          <Reading what="the place search" />
        ) : search.isError ? (
          <Failure error={search.error} what="place search" onRetry={() => search.refetch()} />
        ) : matches.length ? (
          <>
            <ul className="module-place-list">
              {matches.map((row, index) => {
                const point = placePoint(row);
                const label = orNot(row.label || row.name, 'place name not recorded');
                const where = orNot([row.admin2, row.admin1].filter(Boolean).join(', '), 'administrative area not recorded');
                return (
                  <li key={row.selection_id || label + ':' + index} className="flex flex-wrap items-center gap-2">
                    {point ? (
                      <>
                        <button
                          type="button"
                          id={rowId + index}
                          className="btn btn-ghost module-place-button"
                          onClick={() => onPick(point)}
                        >
                          {label} · {where} · {point.latitude}, {point.longitude}
                        </button>
                        <PinPlaceButton place={point} describedBy={rowId + index} />
                      </>
                    ) : (
                      <span className="module-note">{label} · {where} · coordinates not recorded, so this row cannot be read as a point</span>
                    )}
                  </li>
                );
              })}
            </ul>
            <p className="module-note">
              Pinning a row keeps its name and these coordinates in this browser as a shortcut to that place. A pin saves no answer, no
              reading and no claim about the place.
            </p>
          </>
        ) : (
          <p className="module-note">No place row came back for this name. {NO_ROW}.</p>
        )}
      </div>
    </div>
  );
}
