/* The claim.
   ============================================================================
   One value, one window, one unit, one source, one state — the atom every answer is built from. A tool
   owns the value, so it is set in the machine face and counts up from zero to exactly the number the tool
   returned; a published hazard colour appears only here, only with the source's own words; an absent value
   prints its absence; a gap in the window stays hatched. Depth — the receipt, the series, the district
   grid — unfolds under the claim that owns it. Glass over the atmosphere, never a card in a grid. */

import type { CSSProperties, ReactNode } from 'react';
import { AnimatedNumber } from './motion';

export type ClaimSpan = { from: number; to: number };

export function Ruler({ spans }: { spans: ClaimSpan[] }) {
  return (
    <div className="g-ruler" aria-hidden="true">
      {spans.map((span, index) => (
        <i key={index} style={{ left: `${span.from}%`, width: `${Math.max(0.5, span.to - span.from)}%` }} />
      ))}
    </div>
  );
}

export type ClaimProps = {
  eyebrow: ReactNode;
  value?: ReactNode | null | undefined;
  unit?: string | null | undefined;
  hazard?: string | null | undefined;
  hazardColour?: string | null | undefined;
  note?: ReactNode;
  source?: ReactNode;
  spans?: ClaimSpan[];
  compact?: boolean;
  lead?: boolean;
  row?: boolean;
  depth?: { label: string; body: ReactNode; open?: boolean }[];
  testId?: string;
  children?: ReactNode;
};

export function Claim({ eyebrow, value, unit, hazard, hazardColour, note, source, spans, compact, lead, row, depth, testId, children }: ClaimProps) {
  const absent = !hazard && (value === undefined || value === null || value === '');
  const text = typeof value === 'string' || typeof value === 'number' ? String(value) : null;
  return (
    <section
      role="group"
      aria-label={typeof eyebrow === 'string' ? eyebrow : undefined}
      className={'g-claim ' + (compact ? ' g-claim-compact' : '') + (row ? ' fact-row' : '')}
      /* --g-lit, not --g-claim-lit: the rule that paints the edge reads --g-lit, so the old name left
         `background: var(--g-lit)` invalid at computed-value time and the bar painted nothing. data-lit is
         what that rule selects on, and it was never set either — so the published colour had two
         independent reasons never to appear. The child .g-hazard inherits this now. */
      style={hazardColour ? ({ '--g-lit': hazardColour } as CSSProperties) : undefined}
      data-testid={testId}
      data-lit={hazardColour ? 'true' : undefined}
      data-lead={lead ? 'true' : undefined}
      data-state={absent ? 'not-stated' : 'stated'}
    >
      <p className="g-claim-eyebrow">{eyebrow}</p>
      {hazard ? (
        <span className="g-hazard" style={hazardColour ? ({ '--g-lit': hazardColour } as CSSProperties) : undefined}>
          {hazard}
        </span>
      ) : absent ? (
        <p className="g-claim-absent">not stated in this read</p>
      ) : (
        <p className="g-claim-value">
          {text !== null ? (
            <AnimatedNumber value={text} className={'g-claim-number ' + (lead ? 'lead-value' : 'fact-value')} />
          ) : (
            <span className={'g-claim-number ' + (lead ? 'lead-value' : 'fact-value')}>{value}</span>
          )}
          {unit ? <span className="g-claim-unit">{unit}</span> : null}
        </p>
      )}
      {note ? <p className="g-claim-note">{note}</p> : null}
      {spans && spans.length ? <Ruler spans={spans} /> : null}
      {source ? <p className="g-claim-source">{source}</p> : null}
      {children}
      {(depth || []).map(entry => (
        <details key={entry.label} className="g-fold" open={entry.open}>
          <summary>{entry.label}</summary>
          <div className="g-fold-body">{entry.body}</div>
        </details>
      ))}
    </section>
  );
}
