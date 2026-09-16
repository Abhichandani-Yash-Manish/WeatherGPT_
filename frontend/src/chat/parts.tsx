/* The pieces a card is made of. Every one of them renders what the packet holds and states when the
   packet holds nothing; none of them computes a value, a colour meaning or a coverage claim. */

import { useState, type ReactNode } from 'react';
import type { AnswerPacket, Citation, Fact, SourceEntry } from '../api/types';
import { istClock, istDay, istStamp, istWindow } from '../lib/time';
import { copyText, receiptRows, receiptText } from './actions';
import { isHeld, kindOf, parameterName, placeOf, statusLabel, windowFacts } from './model';

export function Tag({ children, tone = 'default', title }: { children: ReactNode; tone?: 'default' | 'quiet' | 'held' | 'good'; title?: string }) {
  const cls = tone === 'quiet' ? 'tag tag-quiet' : tone === 'held' ? 'tag tag-held' : tone === 'good' ? 'tag tag-good' : 'tag';
  return (
    <span className={cls} title={title}>
      {children}
    </span>
  );
}

/* A disclosure is a detail a reader opens; the closed state still names what is inside, so nothing
   material is hidden behind a word like "more". */
export function Disclosure({ summary, children, count, open = false }: { summary: string; children: ReactNode; count?: number; open?: boolean }) {
  return (
    <details className="card px-3 py-2" open={open}>
      <summary className="cursor-pointer select-none text-xs font-semibold text-ink-soft">
        {summary}
        {typeof count === 'number' ? <span className="quiet"> ({count})</span> : null}
      </summary>
      <div className="mt-2">{children}</div>
    </details>
  );
}

export function StatusTags({ packet }: { packet: AnswerPacket }) {
  const requested = packet.trace?.generation?.requested_language;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Tag tone={isHeld(packet.status) ? 'held' : 'default'}>{statusLabel(packet.status)}</Tag>
      {requested && requested !== 'en' ? <Tag tone="quiet">Requested output: {requested}</Tag> : null}
      {/* A conversational turn read no source. The tag says so beside the answer, not only in a disclosure. */}
      {packet.answer_basis === 'conversation' ? <Tag tone="quiet" title="This reply read no source; it states no measurement">No source read</Tag> : null}
      <Tag tone="quiet">{packet.answered_at_utc ? istStamp(packet.answered_at_utc) : 'Time not recorded'}</Tag>
    </div>
  );
}

/* ---- the lead reading ---------------------------------------------------------------------- */
export function LeadReading({ packet, fact }: { packet: AnswerPacket; fact: Fact }) {
  const kind = kindOf(fact);
  const place = placeOf(packet, fact);
  const window = fact.start && fact.end ? istWindow(String(fact.start), String(fact.end)) : fact.observed_at ? istStamp(fact.observed_at) : '';
  return (
    <div className="card-raised card px-4 py-3">
      <p className="eyebrow">{parameterName(fact)}</p>
      <p className="mt-2 flex flex-wrap items-baseline gap-2">
        {kind ? <Tag tone="quiet">{kind}</Tag> : null}
        <span className="lead-value">{String(fact.value)}</span>
        {fact.unit ? <span className="lead-unit">{fact.unit}</span> : null}
      </p>
      {place || window ? (
        <p className="mt-2 text-xs text-ink-soft">
          {place}
          {place && window ? ' \u00b7 ' : ''}
          {window}
        </p>
      ) : null}
      {fact.source_id ? <p className="fact-source mt-1">source {fact.source_id}</p> : null}
    </div>
  );
}

/* ---- the rest of the facts ------------------------------------------------------------------ */
export function FactsTable({ packet, facts }: { packet: AnswerPacket; facts: Fact[] }) {
  if (!facts.length) return null;
  return (
    <div className="card px-3 py-1">
      {facts.map(fact => {
        const kind = kindOf(fact);
        const window = fact.start && fact.end ? istWindow(String(fact.start), String(fact.end)) : fact.observed_at ? istStamp(fact.observed_at) : '';
        return (
          <div key={fact.id} className="fact-row">
            <div>
              <p className="text-xs font-semibold">{parameterName(fact)}</p>
              {kind ? <p className="text-[11px] quiet">{kind}</p> : null}
            </div>
            <div>
              <p className="fact-value">
                {String(fact.value)}
                {fact.unit ? <span className="ml-1 text-xs text-ink-soft">{fact.unit}</span> : null}
              </p>
              <p className="text-[11px] quiet">{placeOf(packet, fact) || 'place not recorded'}{window ? ' \u00b7 ' + window : ''}</p>
            </div>
            <div className="fact-source text-right">{fact.source_id || 'source not stated'}</div>
          </div>
        );
      })}
    </div>
  );
}

/* ---- the validity ruler --------------------------------------------------------------------- */
type Span = { start: number; end: number; covered: boolean; samples: number };

/* The ruler is the answer's window made legible. Every part of it is reachable by keyboard, and a part
   with no retrieved evidence is drawn as a hatched gap rather than left blank, because blank space
   reads as coverage. */
export function ValidityRuler({ packet }: { packet: AnswerPacket }) {
  const [readout, setReadout] = useState('Focus a part of the window to read what the evidence covers there.');
  const facts = windowFacts(packet);
  const spans = facts
    .map(fact => ({ fact, start: Date.parse(String(fact.start)), end: Date.parse(String(fact.end)) }))
    .filter(entry => Number.isFinite(entry.start) && Number.isFinite(entry.end) && entry.end > entry.start);
  if (!spans.length) return null;

  const from = Math.min(...spans.map(entry => entry.start));
  const to = Math.max(...spans.map(entry => entry.end));
  if (!(to > from)) return null;
  const width = 640, track = 8, y = 34, height = 15;
  const scale = (at: number) => track + ((at - from) / (to - from)) * (width - track - 12);
  const hours = Math.round(((to - from) / 3_600_000) * 10) / 10;

  const merged: [number, number][] = spans
    .map(entry => [entry.start, entry.end] as [number, number])
    .sort((left, right) => left[0] - right[0])
    .reduce((accumulator, span) => {
      const last = accumulator[accumulator.length - 1];
      if (last && span[0] <= last[1]) last[1] = Math.max(last[1], span[1]);
      else accumulator.push([span[0], span[1]]);
      return accumulator;
    }, [] as [number, number][]);

  const segments: Span[] = [];
  const sampleCount = (start: number, end: number) => spans.filter(entry => entry.start < end && entry.end > start).length;
  let cursor = from;
  merged.forEach(span => {
    if (span[0] - cursor > 15 * 60 * 1000) segments.push({ start: cursor, end: span[0], covered: false, samples: 0 });
    cursor = Math.max(cursor, span[1]);
  });
  if (to - cursor > 15 * 60 * 1000) segments.push({ start: cursor, end: to, covered: false, samples: 0 });
  merged.forEach(span => segments.push({ start: span[0], end: span[1], covered: true, samples: sampleCount(span[0], span[1]) }));
  segments.sort((left, right) => left.start - right.start);

  const label = (segment: Span) => {
    const range = istWindow(new Date(segment.start).toISOString(), new Date(segment.end).toISOString());
    if (!segment.covered) return 'No retrieved evidence ' + range + ' \u00b7 drawn as a gap and never interpolated';
    return 'Covered by retrieved evidence ' + range + ' \u00b7 ' + segment.samples + ' sample' + (segment.samples === 1 ? '' : 's');
  };

  return (
    <div className="card px-3 py-3">
      <p className="eyebrow">Window covered by the evidence</p>
      <svg viewBox={'0 0 ' + width + ' ' + (y + height + 34)} role="img" className="mt-2 w-full"
           aria-label={
             'Requested window ' + istWindow(String(facts[0].start), String(facts[0].end)) + ', covering ' + hours + ' hours across ' +
             spans.length + ' retrieved sample' + (spans.length === 1 ? '' : 's')
           }>
        <defs>
          <pattern id="ruler-hatch" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
            <line x1="0" y1="0" x2="0" y2="6" stroke="var(--line-strong)" strokeWidth="1" />
          </pattern>
        </defs>
        <rect x={track} y={y} width={width - track - 12} height={height} rx={3} className="ruler-rail" />
        {segments.map(segment => (
          <rect
            key={'seg-' + segment.start}
            x={scale(segment.start).toFixed(1)}
            y={y}
            width={Math.max(2, scale(segment.end) - scale(segment.start)).toFixed(1)}
            height={height}
            rx={3}
            className={segment.covered ? 'ruler-covered' : 'ruler-gap'}
          />
        ))}
        {[0, 0.5, 1].map(fraction => {
          const at = from + (to - from) * fraction;
          const anchor = fraction === 0 ? 'middle' : fraction === 1 ? 'end' : 'middle';
          return (
            <g key={'tick-' + fraction}>
              <line x1={scale(at).toFixed(1)} x2={scale(at).toFixed(1)} y1={y + height + 3} y2={y + height + 8} className="ruler-edge" />
              <text x={scale(at).toFixed(1)} y={y + height + 22} textAnchor={anchor} className="ruler-tick-label">{istClock(new Date(at).toISOString())}</text>
            </g>
          );
        })}
        {segments.map(segment => (
          <rect
            key={'hit-' + segment.start}
            x={scale(segment.start).toFixed(1)}
            y={y - 4}
            width={Math.max(3, scale(segment.end) - scale(segment.start)).toFixed(1)}
            height={height + 8}
            className="ruler-hit"
            tabIndex={0}
            role="button"
            aria-label={label(segment)}
            onFocus={() => setReadout(label(segment))}
            onMouseEnter={() => setReadout(label(segment))}
            onClick={() => setReadout(label(segment))}
            onKeyDown={event => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                setReadout(label(segment));
              }
            }}
          />
        ))}
        <text x={track} y={22} className="ruler-caption">{istDay(String(facts[0].start)) + ' \u00b7 ' + hours + ' h'}</text>
      </svg>
      <p className="mt-1 text-xs text-ink-soft" aria-live="polite">{readout}</p>
      <p className="mt-1 text-[11px] quiet">
        {spans.length + ' retrieved sample' + (spans.length === 1 ? '' : 's') + ' over ' + hours + ' hours. '}
        Source hours start on UTC boundaries, which are :30 in IST. Values are samples, not a continuous trace.
      </p>
    </div>
  );
}

/* ---- the receipt ----------------------------------------------------------------------------- */
export function EvidenceReceipt({ packet, fact }: { packet: AnswerPacket; fact: Fact }) {
  const [state, setState] = useState<'idle' | 'copied' | 'unsupported'>('idle');
  const rows = receiptRows(packet, fact);
  const citation: Citation | undefined = (packet.citations || []).find(entry => (fact.citation_ids || []).includes(entry.id));
  return (
    <div className="receipt px-3 py-3">
      <div className="flex items-center justify-between gap-2">
        <p className="eyebrow">Evidence receipt</p>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={async () => setState(await copyText(receiptText(packet, fact)))}
        >
          {state === 'copied' ? 'Copied' : state === 'unsupported' ? 'Copy refused' : 'Copy this receipt'}
        </button>
      </div>
      <div className="mt-2">
        {rows.map(([key, value]) => (
          <div key={key} className="receipt-row">
            <span className="receipt-key">{key}</span>
            <span className="receipt-val">{value}</span>
          </div>
        ))}
      </div>
      <p className="receipt-chain mt-2 text-ink-soft">
        <span className="evidence">{fact.source_id || 'source not stated'}</span>
        <span aria-hidden="true">→</span>
        <span>retrieved {citation?.retrieved_at_utc ? istStamp(citation.retrieved_at_utc) : 'time not recorded'}</span>
        <span aria-hidden="true">→</span>
        <span>{fact.method || kindOf(fact) || 'typed contract'}</span>
      </p>
      <p className="mt-2 text-[11px] quiet">
        A receipt for the moment it was retrieved, not a standing fact. Model output is not an observation and not a district average.
      </p>
    </div>
  );
}

/* ---- sources --------------------------------------------------------------------------------- */
export function SourceRows({ sources, citations }: { sources?: SourceEntry[]; citations?: Citation[] }) {
  const rows = sources && sources.length ? sources : [];
  if (!rows.length && !(citations || []).length) return null;
  return (
    <div className="card px-3 py-2">
      <p className="eyebrow">Sources reached</p>
      <ul className="mt-1 space-y-1">
        {rows.map(source => (
          <li key={source.source_id + (source.url || '')} className="text-xs">
            <span className="evidence font-semibold">{source.source_id}</span>
            {source.product ? <span className="soft"> · {source.product}</span> : null}
            {source.retrieved_at_utc ? <span className="quiet"> · retrieved {istStamp(source.retrieved_at_utc)}</span> : null}
            {source.sha256_prefix ? <span className="quiet"> · sha256 {source.sha256_prefix}…</span> : null}
            {source.integration_status ? <span className="quiet"> · {source.integration_status}</span> : null}
            {source.url ? <a className="ml-1 underline" href={source.url} rel="noreferrer noopener" target="_blank">source address</a> : null}
          </li>
        ))}
        {(citations || []).map(citation => (
          <li key={citation.id} className="text-xs">
            <span className="evidence font-semibold">{citation.source_id}</span>
            {citation.product ? <span className="soft"> · {citation.product}</span> : null}
            {citation.provider ? <span className="quiet"> · {citation.provider}</span> : null}
            {citation.retrieved_at_utc ? <span className="quiet"> · retrieved {istStamp(citation.retrieved_at_utc)}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
