/* The framing every module surface shares: one h1, the envelope's own header, named coverage counts,
   the limitations and not-established lines in the surface's own voice, and the source rows.
   Nothing here invents a value or a meaning. Absence is stated as absence ('not recorded',
   'no row returned', 'this read did not answer'), never as a blank, a zero or an empty chart. */
import { useId, useState, type ReactNode } from 'react';
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

export function Reading({ what }: { what: string }): JSX.Element {
  return (
    <p className="module-note" role="status">
      Reading {what} from the local store…
    </p>
  );
}

export function Failure({ error, what, onRetry }: { error: unknown; what: string; onRetry?: () => void }): JSX.Element {
  return (
    <div className="module-failure" role="alert">
      <p className="reading">{failureSentence(error)}</p>
      <p className="module-note">
        The {what} read failed. This surface shows that failure; it is not an empty result and not a quiet day.
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

export function Facts({ rows, testId }: { rows: Fact[]; testId?: string }): JSX.Element {
  return (
    <dl className="module-facts" data-testid={testId}>
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

/* The reader names a place; the catalogue answers with rows, and only a row that states coordinates
   can be read as a point. A row without coordinates is shown as one rather than resolved elsewhere. */
export function PlacePicker({ onPick, hint }: { onPick: (place: PlaceChoice) => void; hint?: string }): JSX.Element {
  const [term, setTerm] = useState('');
  const query = term.trim();
  const field = useId();
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
          <ul className="module-place-list">
            {matches.map((row, index) => {
              const point = placePoint(row);
              const label = orNot(row.label || row.name, 'place name not recorded');
              const where = orNot([row.admin2, row.admin1].filter(Boolean).join(', '), 'administrative area not recorded');
              return (
                <li key={row.selection_id || label + ':' + index}>
                  {point ? (
                    <button type="button" className="btn btn-ghost module-place-button" onClick={() => onPick(point)}>
                      {label} · {where} · {point.latitude}, {point.longitude}
                    </button>
                  ) : (
                    <span className="module-note">{label} · {where} · coordinates not recorded, so this row cannot be read as a point</span>
                  )}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="module-note">No place row came back for this name. {NO_ROW}.</p>
        )}
      </div>
    </div>
  );
}
