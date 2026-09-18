/* The work.
   ============================================================================
   The engine runs a list of steps and reports them. This shows that list as it is — named steps, real
   durations, refused steps kept with their reason — collapsed to one line under every answer, because the
   apparatus is reachable, never compulsory. Nothing here is a percentage or an ETA. */

import type { ReactNode } from 'react';

export type WorkState = 'done' | 'refused' | 'working';
export type WorkStep = { state: WorkState; title: string; detail?: string; ms?: string };

const GLYPH: Record<WorkState, string> = { done: '✓', working: '◐', refused: '✗' };

export function Work({ steps, summary, foot, open, testId }: { steps: WorkStep[]; summary: string; foot?: ReactNode; open?: boolean; testId?: string }) {
  return (
    <details className="b-work" open={open} data-testid={testId}>
      <summary>{summary}</summary>
      <div>
        {steps.map((step, index) => (
          <div className="b-work-row" data-state={step.state} key={index}>
            <span className="b-work-glyph" aria-hidden="true">{GLYPH[step.state]}</span>
            <div>
              <p className="b-work-title">{step.title}</p>
              {step.detail ? <p className="b-work-detail">{step.detail}</p> : null}
            </div>
            {step.ms ? <span className="b-work-ms">{step.ms}</span> : <span />}
          </div>
        ))}
      </div>
      {foot ? <p className="b-work-detail" style={{ marginTop: 8 }}>{foot}</p> : null}
    </details>
  );
}
