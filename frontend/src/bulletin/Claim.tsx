/* The claim.
   ============================================================================
   One value, one window, one unit, one source, one state. It is the only shape a reader has to learn and
   it is the shape the engine returns: a tool owns the value, so the value is set in the machine face, and
   the source line says where it came from and when it was read. A published hazard colour appears only
   here, only with the source's own words. An absent value prints its absence; a gap in the window stays
   hatched. Depth — the series, the grid, the page — unfolds under the claim that owns it. */

import type { CSSProperties, ReactNode } from 'react';

export type ClaimSpan = { from: number; to: number };

export function Ruler({ spans }: { spans: ClaimSpan[] }) {
  return (
    <div className="b-ruler" aria-hidden="true">
      {spans.map((span, index) => (
        <i key={index} style={{ left: `${span.from}%`, width: `${Math.max(0.5, span.to - span.from)}%` }} />
      ))}
    </div>
  );
}

export type ClaimProps = {
  /** What the claim is about and the window it covers. A noun phrase, never a sentence. */
  eyebrow: ReactNode;
  value?: ReactNode | null | undefined;
  unit?: string | null | undefined;
  /** A published colour's own words, e.g. "yellow · thunderstorm". Its colour comes only from a source. */
  hazard?: string | null | undefined;
  hazardColour?: string | null | undefined;
  note?: ReactNode;
  /** The source line: which source, which cell or page, when it was read. */
  source?: ReactNode;
  spans?: ClaimSpan[];
  compact?: boolean;
  /** The answer's leading claim. */
  lead?: boolean;
  /** One of the remaining facts, kept as a row the port ledger can count. */
  row?: boolean;
  /** What unfolds under this claim. */
  depth?: { label: string; body: ReactNode; open?: boolean }[];
  testId?: string;
  children?: ReactNode;
};

export function Claim({ eyebrow, value, unit, hazard, hazardColour, note, source, spans, compact, lead, row, depth, testId, children }: ClaimProps) {
  const absent = !hazard && (value === undefined || value === null || value === '');
  return (
    <section role="group" aria-label={typeof eyebrow === 'string' ? eyebrow : undefined} className={'b-claim' + (compact ? ' b-claim-compact' : '') + (row ? ' fact-row' : '')} data-testid={testId} data-state={absent ? 'not-stated' : 'stated'}>
      <p className="b-claim-eyebrow">{eyebrow}</p>
      {hazard ? (
        <span className="b-hazard" style={hazardColour ? ({ '--b-hz': hazardColour } as CSSProperties) : undefined}>
          {hazard}
        </span>
      ) : absent ? (
        <p className="b-claim-absent">not stated in this read</p>
      ) : (
        <p className="b-claim-value">
          <span className={'b-claim-number b-machine ' + (lead ? 'lead-value' : 'fact-value')}>{value}</span>
          {unit ? <span className="b-claim-unit">{unit}</span> : null}
        </p>
      )}
      {note ? <p className="b-claim-note">{note}</p> : null}
      {spans && spans.length ? <Ruler spans={spans} /> : null}
      {source ? <p className="b-claim-source">{source}</p> : null}
      {children}
      {(depth || []).map(entry => (
        <details key={entry.label} className="b-depth" open={entry.open}>
          <summary>{entry.label}</summary>
          <div className="b-depth-body">{entry.body}</div>
        </details>
      ))}
    </section>
  );
}
