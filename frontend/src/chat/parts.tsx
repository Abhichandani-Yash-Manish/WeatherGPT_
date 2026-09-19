/* The pieces a card is made of. Every one of them renders what the packet holds and states when the
   packet holds nothing; none of them computes a value, a colour meaning or a coverage claim. */

import { useState, type ReactNode } from 'react';
import type { AnswerPacket, AirportReport, Calculation, Citation, Fact, SourceEntry } from '../api/types';
import { istClock, istDay, istStamp, istWindow } from '../lib/time';
import { copyText, receiptRows, receiptText } from './actions';
import { calculationKind, chartEvidenceIds, coverageFacts, isHeld, kindOf, parameterName, placeOf, statusLabel, windowFacts } from './model';

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
  /* Not a card. A disclosure sits behind the answer, and giving it the same box as the evidence made four
     of them read as four peers of the reading — the identical-card stack that flattens a column. It is a
     fold now: a chevron, a name, and a hairline down the opened body. */
  return (
    <details className="g-fold" open={open}>
      <summary>
        {summary}
        {typeof count === 'number' ? <span className="quiet"> ({count})</span> : null}
      </summary>
      <div className="g-fold-body">{children}</div>
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

/* ---- calculations --------------------------------------------------------------------------- */
/* A value the engine computed is evidence with its own provenance, not a measurement of ours: it is shown
   in its own block, with the engine's own classification, method and input/source counts. It is never
   promoted to the card's lead reading, and a difference between two sources is stated as a difference
   rather than as skill, accuracy or confidence. */
export function Calculations({ packet }: { packet: AnswerPacket }) {
  const calculations: Calculation[] = packet.calculations || [];
  if (!calculations.length) return null;
  return (
    <div className="flex flex-col gap-2">
      {calculations.map((calculation, index) => {
        const comparison = calculation.kind === 'source_comparison';
        const inputs = calculation.input_ids || [];
        const sources = calculation.source_ids || [];
        const words = [
          inputs.length + ' input value' + (inputs.length === 1 ? '' : 's'),
          sources.length ? 'from ' + sources.join(', ') : null,
          calculation.method || null,
          calculation.interpretation || null,
        ].filter(Boolean).join(' \u00b7 ');
        return (
          <div key={(calculation.label || 'calculation') + '-' + index} className={'calc card px-3 py-2' + (comparison ? ' is-comparison' : '')}>
            <p className="flex flex-wrap items-baseline gap-2">
              <span className="calc-value font-mono">{String(calculation.value ?? 'value not stated')}</span>
              {calculation.unit ? <span className="text-xs text-ink-soft">{calculation.unit}</span> : null}
              <span className="quiet text-xs">{calculationKind(calculation)}</span>
            </p>
            {calculation.label ? <p className="calc-label mt-1 text-xs font-semibold">{calculation.label}</p> : null}
            <p className="mt-1 text-xs text-ink-soft">{words}.</p>
            {comparison ? (
              <p className="mt-1 text-xs text-ink-soft">
                A difference between two sources is not a skill score, an accuracy measure or a confidence value,
                and agreement between them does not establish correctness.
              </p>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

/* ---- airport reports ------------------------------------------------------------------------- */
/* An airport report is the source's own text, kept exactly as it was transmitted, and typed as what it is:
   a METAR is an observation with an observed time, a TAF is a forecast over its stated validity. Neither is
   a flight status, a runway state or an operational clearance, and the card says so beside the report. */
export function AirportReports({ packet }: { packet: AnswerPacket }) {
  const reports: AirportReport[] = packet.airport_reports || [];
  if (!reports.length) return null;
  return (
    <div className="flex flex-col gap-2">
      {reports.map((report, index) => {
        const kindWords = report.kind === 'taf' ? 'Forecast (TAF)' : report.kind === 'metar' ? 'Observed report (METAR)' : (report.kind || 'Report kind not stated');
        const at = report.observed_at || report.valid_start;
        const validity = report.valid_start || report.valid_end
          ? 'Valid ' + (report.valid_start ? istStamp(report.valid_start) : 'not stated') + ' to ' + (report.valid_end ? istStamp(report.valid_end) : 'not stated') + '.'
          : 'No validity interval was stated in this report.';
        return (
          <section key={(report.station || 'station') + '-' + index} className="capability card px-3 py-2">
            <div className="capability-head flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="font-semibold">{(report.station || 'station not stated') + ' \u00b7 ' + kindWords}</h3>
              <Tag tone="quiet">{at ? istStamp(at) : 'Time not supplied'}</Tag>
            </div>
            {report.raw_report ? (
              <pre className="raw-report mt-2 whitespace-pre-wrap font-mono text-xs">{report.raw_report}</pre>
            ) : (
              <p className="mt-1 text-xs text-ink-soft">This report states no raw text.</p>
            )}
            <p className="mt-1 text-[11px] text-ink-soft">
              {validity} A report describes its station and its stated validity, not conditions across a whole city,
              and not a flight status or a clearance; it is also not a runway state and not an operational clearance.
            </p>
          </section>
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
          /* The first label is anchored to the start and the last to the end, or each clips on its own edge. */
          const anchor = fraction === 0 ? 'start' : fraction === 1 ? 'end' : 'middle';
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

/* ---- the series receipt --------------------------------------------------------------------- */
/* A series whose every value is already drawn still carries a receipt: how many values were retrieved, from
   which source and when, and the sentence that a reading of the record is descriptive rather than a
   projection or an attribution. It is drawn only where the payload plotted the values; a fact that is not
   drawn keeps its own row. */
export function SeriesReceipt({ packet }: { packet: AnswerPacket }) {
  const charts = packet.charts || [];
  if (!charts.length) return null;
  const plotted = chartEvidenceIds(packet);
  const series = coverageFacts(packet).filter(fact => plotted.has(fact.id));
  if (!series.length) return null;
  const measures: string[] = [];
  series.forEach(fact => {
    const name = parameterName(fact);
    if (measures.indexOf(name) < 0) measures.push(name);
  });
  const sources: string[] = [];
  series.forEach(fact => {
    if (fact.source_id && sources.indexOf(fact.source_id) < 0) sources.push(fact.source_id);
  });
  const citation = (packet.citations || []).find(entry => (series[0].citation_ids || []).includes(entry.id));
  const sourceLine = [sources.join(', '), citation?.provider, citation?.product].filter(Boolean).join(' \u00b7 ');
  const locator = citation
    ? [citation.page ? 'page ' + citation.page : null, citation.row ? 'row ' + citation.row : null, citation.column || null].filter(Boolean).join(' \u00b7 ')
    : '';
  return (
    <div className="receipt px-3 py-3">
      <p className="eyebrow">Evidence receipt</p>
      <div className="mt-2">
        <div className="receipt-row">
          <span className="receipt-key">Measure</span>
          <span className="receipt-val">{measures.join(', ') || 'measure not recorded'}</span>
        </div>
        <div className="receipt-row">
          <span className="receipt-key">Values</span>
          <span className="receipt-val">{series.length + ' retrieved values, each plotted and inspectable with its own evidence id'}</span>
        </div>
        <div className="receipt-row">
          <span className="receipt-key">Place</span>
          <span className="receipt-val">{placeOf(packet, series[0]) || 'place not recorded'}</span>
        </div>
        <div className="receipt-row">
          <span className="receipt-key">Source</span>
          <span className="receipt-val">{sourceLine || 'source not stated'}</span>
        </div>
        <div className="receipt-row">
          <span className="receipt-key">Retrieved</span>
          <span className="receipt-val">{citation?.retrieved_at_utc ? istStamp(citation.retrieved_at_utc) : 'time not recorded'}</span>
        </div>
        {locator ? (
          <div className="receipt-row">
            <span className="receipt-key">First locator</span>
            <span className="receipt-val">{locator}</span>
          </div>
        ) : null}
        {series[0].evidence_version ? (
          <div className="receipt-row">
            <span className="receipt-key">Evidence id</span>
            <span className="receipt-val">{String(series[0].evidence_version).slice(0, 16) + '\u2026'}</span>
          </div>
        ) : null}
      </div>
      <p className="mt-2 text-[11px] quiet">
        A receipt for the moment the series was retrieved, not a standing fact. The chart is drawn from these
        values; a descriptive slope is not a projection, an attribution or a validated trend.
      </p>
    </div>
  );
}

/* ---- task accounting ------------------------------------------------------------------------ */
/* Asked, answered and incomplete are three different numbers and are reported as three, with the task ids
   the engine returned, so a turn cannot read as wholly answered when part of it was not. */
export function TaskAccounting({ packet }: { packet: AnswerPacket }) {
  const results = packet.task_results || [];
  if (!results.length) return null;
  const coverage = packet.task_coverage;
  const asked = coverage ? coverage.requested : results.length;
  const answered = coverage ? coverage.completed : results.filter(task => task.status === 'answered').length;
  const incomplete = coverage ? (coverage.incomplete_ids || []) : results.filter(task => task.status !== 'answered').map(task => task.id);
  const ids = results.map(task => task.id).filter(Boolean);
  const answeredIds = results.filter(task => task.status === 'answered').map(task => task.id).filter(Boolean);
  return (
    <div className="g-tally">
      <p className="g-eyebrow">Task accounting</p>
      <p className="coverage mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs">
        <span>{'Asked: ' + asked + (ids.length ? ' \u00b7 ' + ids.join(', ') : ' \u00b7 no task id returned')}</span>
        <span className="quiet">{'Answered: ' + answered + (answeredIds.length ? ' \u00b7 ' + answeredIds.join(', ') : '')}</span>
        <span className="quiet">{'Incomplete: ' + incomplete.length + (incomplete.length ? ' \u00b7 ' + incomplete.join(', ') : ' \u00b7 none named')}</span>
      </p>
      <p className="mt-1 text-[11px] quiet">
        The engine counts a task answered only when it returned evidence; a clarification or abstention is not
        counted as answered.
      </p>
    </div>
  );
}

/* ---- the official district warning day ------------------------------------------------------ */
/* A warning day is an official statement for a named district-day: its own period, the colour the payload
   stated and the hazard wording the payload carried, drawn as a table rather than as a measured sample. A
   day the payload leaves unlabelled or uncoloured says so rather than being given a label or a colour here,
   and a quiet district-day is stated to be no all-clear. */
export function WarningPanel({ packet }: { packet: AnswerPacket }) {
  const districts = (packet.warning_evidence || []).flatMap(entry => entry.district_warnings || []);
  if (!districts.length) return null;
  return (
    <div className="flex flex-col gap-2">
      {districts.map((district, index) => {
        const days = district.days || [];
        return (
          <section key={(district.district || district.place || 'district') + '-' + index} className="warning-panel card px-3 py-2">
            <div className="warning-head flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="font-semibold">{'IMD district warning \u00b7 ' + (district.district || district.place || 'district not named')}</h3>
              <Tag tone="quiet">{'Bulletin ' + (district.issued_at_utc ? istStamp(district.issued_at_utc) : 'time not recorded')}</Tag>
            </div>
            {days.length ? (
              <table className="warning-days mt-2 w-full text-left text-xs">
                <thead>
                  <tr>
                    <th scope="col">Day</th>
                    <th scope="col">IMD colour</th>
                    <th scope="col">Official hazard</th>
                    <th scope="col">Window (IST)</th>
                  </tr>
                </thead>
                <tbody>
                  {days.map((day, dayIndex) => {
                    /* A day states the label the payload carries, in whichever field the payload spells it.
                       Where the payload states none, the day says so rather than being given a label here. */
                    const statedLabel = day.label || day.day_label || null;
                    const statedIndex = day.day === undefined || day.day === null ? null : 'Day ' + day.day;
                    const dayWords = statedLabel
                      ? (statedIndex ? statedIndex + ' \u00b7 ' + statedLabel : statedLabel)
                      : (statedIndex ? statedIndex + ' \u00b7 day label not stated' : 'day label not stated');
                    return (
                      <tr key={(statedLabel || 'day') + '-' + dayIndex}>
                        <td>{dayWords}</td>
                        <td><span className="wchip">{day.colour || 'colour not supplied'}</span></td>
                        <td>{day.quiet ? 'No warning in this product' : (day.source_text || (day.hazards || []).join(', ') || 'No hazard code supplied')}</td>
                        <td>{istWindow(day.starts_utc, day.ends_utc)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <p className="mt-1 text-xs text-ink-soft">This district row states no day rows in this product.</p>
            )}
            <p className="field-note mt-1 text-[11px] text-ink-soft">
              Read from IMD district-level warning guidance. Day 1 is the bulletin date, and each following day is
              the next IST calendar day. IMD publishes no per-day validity field in this product, so these windows
              are derived from the bulletin date and IMD's own day selector. The colour is IMD's product colour for
              that district-day, and the hazard text is IMD's own wording.
            </p>
            {days.some(day => day.quiet) ? (
              <p className="field-note mt-1 text-[11px] text-ink-soft">
                A day marked "No warning in this product" means IMD published no warning hazard for that district-day
                in this product. It is not an all-clear, and not a statement that nothing will happen.
              </p>
            ) : null}
          </section>
        );
      })}
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
