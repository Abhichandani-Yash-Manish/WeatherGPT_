/* X1 for the conversation surface: no number reaches a reader without visible provenance.
   ============================================================================
   The RULE lives in ./provenance.ts — the walker, the exclusions, the three checked shapes — and is held
   here against the rendered DOM, over the eight recorded packets the card suite already reads, inside the
   gate that already runs. docs/108 states the rule and names scripts/audit_claims.py for it; docs/120 records
   the decisions behind this file and its stated limits. src/flagship/provenance.surfaces.test.tsx holds the
   same definitions against the rest of the product's surfaces, which is why this file no longer carries its
   own copy of them.

   The rule exists because provenance that is true in the engine and absent on the screen is not provenance.
   A reader who cannot see where 38.1 mm came from has to trust the page, and this product's whole claim is
   that they should not have to.

   Run over the eight recorded packets, it reported 8 of 8 failing and 27 offenders. Each one was answered at
   its cause: the notes region did not carry the class this file had always named for it, the historical trend
   stated its inputs and no source, timestamps were spans rather than <time> elements, and three regions are
   genuinely not values — a fold's row count, a series receipt's provenance rows, and a station's own raw
   report text. See docs/120 for the decision on each. The module surfaces are a later lane, so nothing under
   src/modules is audited here. */

import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { AnswerPacket } from '../api/types';
import { AnswerTurn } from '../chat/AnswerTurn';
import airportJson from '../../../research/reviews/frontend-overhaul-20260914/packets/airport.json';
import clarificationJson from '../../../research/reviews/frontend-overhaul-20260914/packets/clarification.json';
import forecastJson from '../../../research/reviews/frontend-overhaul-20260914/packets/forecast-simple.json';
import hindiJson from '../../../research/reviews/frontend-overhaul-20260914/packets/language-hindi.json';
import historicalJson from '../../../research/reviews/frontend-overhaul-20260914/packets/historical-chart.json';
import marineJson from '../../../research/reviews/frontend-overhaul-20260914/packets/marine.json';
import multiJson from '../../../research/reviews/frontend-overhaul-20260914/packets/multi-task.json';
import warningJson from '../../../research/reviews/frontend-overhaul-20260914/packets/warning.json';
import { CARRIES_PROVENANCE, NOT_A_VALUE, excused, numberBearingNodes, provenanceOffenders } from './provenance';

const PACKETS: [string, AnswerPacket][] = [
  ['clarification', clarificationJson.packet as unknown as AnswerPacket],
  ['forecast-simple', forecastJson.packet as unknown as AnswerPacket],
  ['language-hindi', hindiJson.packet as unknown as AnswerPacket],
  ['multi-task', multiJson.packet as unknown as AnswerPacket],
  ['historical-chart', historicalJson.packet as unknown as AnswerPacket],
  ['marine', marineJson.packet as unknown as AnswerPacket],
  ['airport', airportJson.packet as unknown as AnswerPacket],
  ['warning', warningJson.packet as unknown as AnswerPacket],
];

describe('X1 — every number on screen is inside a Claim with its source', () => {
  it.each(PACKETS)('%s', (name, packet) => {
    const { container } = render(<AnswerTurn packet={packet} onFollowUp={() => {}} />);
    const offenders = provenanceOffenders(container);

    expect(offenders, `${name}: ${offenders.length} number(s) reach the reader without provenance:\n  ${offenders.join('\n  ')}`).toEqual([]);
  });

  it('the audit can fail — a bare number carries no provenance', () => {
    /* An audit nobody has seen fail is an audit nobody knows is running. */
    const { container } = render(<p>38.1 mm</p>);
    const loose = numberBearingNodes(container).filter(entry => !excused(entry.element));
    expect(loose).toHaveLength(1);
    expect(CARRIES_PROVENANCE.some(shape => loose[0].element.closest(shape.selector))).toBe(false);
    expect(provenanceOffenders(container)).toHaveLength(1);
  });

  it('a shape that only looks right does not pass — the check is on the content', () => {
    /* A calculation block with no source id is a number in calculation clothing. */
    const { container } = render(<div className="calc"><span>6.0</span><p>a total</p></div>);
    const block = container.querySelector('.calc') as Element;
    const shape = CARRIES_PROVENANCE.find(entry => entry.selector === '.calc')!;
    expect(shape.check(block)).toBe(false);
    expect(provenanceOffenders(container)).toHaveLength(1);
  });

  it('every exclusion says what it is, not that it was inconvenient', () => {
    for (const rule of NOT_A_VALUE) {
      expect(rule.because.length, rule.selector).toBeGreaterThan(20);
    }
  });
});
