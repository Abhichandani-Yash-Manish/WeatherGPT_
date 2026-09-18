/* The five card gaps the ported checks named, held against the recorded payloads rather than invented
   fixtures:

   1. packet.calculations (tests/test_views.js checks 7 and 14): the recorded packets carry the engine's own
      computations, including the between-source difference and the descriptive trend;
   2. packet.airport_reports (check 11): the recorded METAR response and the recorded VAAH TAF response, so
      both kinds (an observed report and a forecast) are read from a real packet;
   3. the series receipt (check 14): the recorded series packet plots all of its retrieved values, so the card
      must still receipt them;
   4. task accounting (check 5): the recorded multi-task packet carries task_coverage and two task_results;
   5. the official warning day (check 15): the packet tests/test_views.js writes inline, copied verbatim, with
      one clause that removes the day label and the colour to check that the card states absence rather than
      choosing a label or a colour.

   The card's own tests/test_views.js counterparts are the contract; nothing here re-implements a product
   rule, and a check fails if its block is removed. */

import { render } from '@testing-library/react';
import type { AnswerPacket } from '../api/types';
import { AnswerTurn } from './AnswerTurn';
import airportJson from '../../../research/reviews/frontend-overhaul-20260914/packets/airport.json';
import historicalJson from '../../../research/reviews/frontend-overhaul-20260914/packets/historical-chart.json';
import multiJson from '../../../research/reviews/frontend-overhaul-20260914/packets/multi-task.json';
import tafJson from '../../../research/implementation/conversation-engine-20260912/final-breadth/taf-0.json';

const MULTI = multiJson.packet as unknown as AnswerPacket;
const HISTORICAL = historicalJson.packet as unknown as AnswerPacket;
const AIRPORT = airportJson.packet as unknown as AnswerPacket;
const TAF = tafJson as unknown as AnswerPacket;

/* Copied verbatim from tests/test_views.js check 15: the warning-day packet that suite wrote inline. Its
   citation states no retrieval time, and its single day is a quiet green day. */
const WARNING_DAY: AnswerPacket = {
  schema_version: 'weather-conversation-v1', conversation_id: 'w', question: 'Is there an official warning?', status: 'answered',
  answer: 'IMD district warning for PATNA.',
  citations: [{ id: 'district-warning', source_id: 'S15', provider: 'India Meteorological Department', product: 'District-wise warning product', url: 'https://reactjs.imd.gov.in/geoserver/wfs' }],
  notes: [], choices: [], charts: [], calculations: [], task_results: [],
  facts: [{
    id: 't1-f1', label: 'Day 1 \u00b7 14 Sep 2026', value: 'No warning in this product', unit: 'IMD district warning colour',
    place: 'PATNA', start: '2026-09-13T18:30:00+00:00', end: '2026-09-14T18:30:00+00:00', source_id: 'S15',
    parameter: 'official_district_warning', entity_id: 'imd-district:364', citation_ids: ['district-warning'],
  }],
  warning_evidence: [{
    records: [], latest_sent: null, assessment: { eligible_by_lifecycle: 0 },
    district_warnings: [{
      place: 'Patna', district: 'PATNA', issued_at_utc: '2026-09-14T06:00:00+00:00',
      days: [{ day: 1, label: '14 Sep 2026', colour: 'green', colour_code: 4, quiet: true, hazards: ['No warning in this product'], source_text: '', starts_utc: '2026-09-13T18:30:00+00:00', ends_utc: '2026-09-14T18:30:00+00:00' }],
    }],
    stale_districts: [], points_outside_districts: [],
  }],
};

function mountCard(packet: AnswerPacket, _register: 'conversational' | 'full' = 'conversational') {
  return render(<AnswerTurn packet={packet} onFollowUp={() => {}} />);
}

describe('the calculations the engine returned', () => {
  it('renders each returned calculation in its own block, and a source difference as a difference rather than a score', () => {
    const { container } = mountCard(MULTI);
    const returned = MULTI.calculations || [];
    expect(returned.length).toBeGreaterThan(0);
    expect(container.querySelectorAll('.calc')).toHaveLength(returned.length);

    /* The between-source difference keeps its returned value and method, is never the card's headline, and
       states in words that it is not skill, accuracy or confidence. */
    const comparison = container.querySelector('.calc.is-comparison');
    expect(comparison).not.toBeNull();
    expect(comparison?.querySelector('.lead-value')).toBeNull();
    expect(comparison?.textContent).toContain('-0.8');
    expect(comparison?.textContent).toContain('Difference between sources');
    expect(comparison?.textContent).toContain('Best-match minus GFS precipitation');
    expect(comparison?.textContent).toContain('difference of complete matching point/window totals; not skill or confidence');
    expect(comparison?.textContent).toMatch(/not a skill score, an accuracy measure or a confidence value/);
    expect(comparison?.textContent).toMatch(/agreement between them does not establish correctness/);

    const values = Array.from(container.querySelectorAll('.calc-value')).map(node => node.textContent || '');
    expect(values.some(text => text.includes('0.0'))).toBe(true);
    expect(values).toContain('-0.8');

    /* The card's headline is the one returned fact that is not already drawn, not a computed entry. */
    expect(container.querySelector('.lead-value')?.textContent).toBe('0.8');
  });

  it('shows a series computed value as its own block and never as the headline', () => {
    const { container } = mountCard(HISTORICAL);
    expect(container.querySelectorAll('.lead-value')).toHaveLength(0);
    const trend = container.querySelector('.calc');
    expect(trend).not.toBeNull();
    expect(trend?.textContent).toContain('54.654');
    expect(trend?.textContent).toContain('mm/decade');
    expect(trend?.textContent).toContain('Descriptive trend');
    expect(trend?.textContent).toContain('OLS against actual calendar year; slope multiplied by 10; rounded to 0.001');
    expect(trend?.textContent).toContain('Descriptive source-series slope, not homogenized climate change attribution or a future projection');
  });
});

describe('the recorded airport reports', () => {
  it('shows the recorded METAR raw and typed, with the station, its observed time and the no-clearance sentence', () => {
    const { container } = mountCard(AIRPORT);
    expect(container.querySelector('h2')?.textContent).toBe('Airport report');
    const report = (AIRPORT.airport_reports || [])[0];
    const raw = container.querySelector('.raw-report');
    expect(raw).not.toBeNull();
    expect(raw?.textContent).toBe(report.raw_report);
    expect(container.textContent).toContain('VOBL');
    expect(container.textContent).toContain('Observed report (METAR)');
    expect(container.textContent).toContain('14 Sep 2026, 16:30 IST');
    expect(container.textContent).toMatch(/not a flight status or a clearance/i);
    expect(container.textContent).toMatch(/runway state/i);
    expect(container.textContent).toMatch(/operational clearance/i);
    expect(container.querySelectorAll('.fact-row')).toHaveLength(1);
  });

  it('shows the recorded TAF as a forecast over its stated validity rather than as an observation', () => {
    const { container } = mountCard(TAF);
    expect(container.querySelector('h2')?.textContent).toBe('Airport report');
    const report = (TAF.airport_reports || [])[0];
    expect(container.querySelector('.raw-report')?.textContent).toBe(report.raw_report);
    expect(container.textContent).toContain('Forecast (TAF)');
    expect(container.textContent).toContain('Valid 12 Sep 2026, 23:30 IST to 13 Sep 2026, 08:30 IST');
    expect(container.textContent).toMatch(/not a flight status or a clearance/i);
  });
});

describe('the series receipt', () => {
  it('gives the recorded series a receipt with its retrieved count, source, retrieval time and descriptive reading', () => {
    const { container } = mountCard(HISTORICAL);
    expect(container.querySelectorAll('.lead-value')).toHaveLength(0);
    expect(container.querySelectorAll('.fact-row')).toHaveLength(0);
    const receipts = container.querySelectorAll('.receipt');
    expect(receipts).toHaveLength(1);
    const receipt = receipts[0];
    expect(receipt.textContent).toMatch(/30 retrieved values, each plotted and inspectable with its own evidence id/);
    expect(receipt.textContent).toContain('S27');
    expect(receipt.textContent).toContain('IMD');
    expect(receipt.textContent).toContain('Historical district rainfall publication');
    expect(receipt.textContent).toContain('page 612');
    /* The recorded citations state no retrieval time; the receipt says so instead of leaving it implied. */
    expect(receipt.textContent).toMatch(/Retrieved/);
    expect(receipt.textContent).toMatch(/time not recorded/);
    expect(receipt.textContent).toMatch(/not a projection, an attribution or a validated trend/);
  });
});

describe('task accounting', () => {
  it('reports the recorded turn as asked, answered and incomplete with the task ids', () => {
    const { container } = mountCard(MULTI);
    const coverage = container.querySelector('.coverage');
    expect(coverage).not.toBeNull();
    expect(coverage?.textContent).toMatch(/Asked: 2/);
    expect(coverage?.textContent).toMatch(/Answered: 2/);
    expect(coverage?.textContent).toMatch(/Incomplete: 0/);
    expect(coverage?.textContent).toContain('t1');
    expect(coverage?.textContent).toContain('t2');
    expect(container.textContent).not.toMatch(/requested tasks completed/);

    /* Each returned task keeps its id, kind and operation, not only a count of them. */
    const full = mountCard(MULTI, 'full');
    const tasks = full.container.querySelector('.tasks');
    expect(tasks).not.toBeNull();
    expect(tasks?.textContent).toContain('t1');
    expect(tasks?.textContent).toContain('t2');
    expect(tasks?.textContent).toContain('forecast');
    expect(tasks?.textContent).toContain('crosscheck');
  });
});

describe('the official warning day', () => {
  it('draws the recorded warning day as its named period with the stated colour, hazard and window', () => {
    const { container } = mountCard(WARNING_DAY);
    expect(container.querySelectorAll('.lead-value')).toHaveLength(0);
    expect(container.querySelector('.ruler-rail')).toBeNull();
    expect(container.querySelectorAll('.fact-row')).toHaveLength(0);
    const panels = container.querySelectorAll('.warning-panel');
    expect(panels).toHaveLength(1);
    const panel = panels[0] as HTMLElement;
    const cells = Array.from(panel.querySelectorAll('td')).map(cell => cell.textContent || '');
    expect(cells.some(text => text.includes('Day 1 \u00b7 14 Sep 2026'))).toBe(true);
    expect(cells.some(text => text.includes('green'))).toBe(true);
    expect(cells.some(text => text.includes('No warning in this product'))).toBe(true);
    expect(cells.some(text => text.includes('14 Sep 2026, 00:00-15 Sep 2026, 00:00 IST'))).toBe(true);
    expect(panel.textContent).toMatch(/not an all-clear, and not a statement that nothing will happen/);
    expect(container.querySelectorAll('.receipt')).toHaveLength(1);
  });

  it('says a warning day states no label or colour rather than choosing one', () => {
    /* The recorded check-15 packet with those two fields removed: an absence the card must state, not fill. */
    const packet = JSON.parse(JSON.stringify(WARNING_DAY)) as AnswerPacket;
    const day = (packet.warning_evidence?.[0]?.district_warnings?.[0]?.days?.[0] || {}) as Record<string, unknown>;
    delete day.label;
    delete day.colour;
    const { container } = mountCard(packet);
    const panel = container.querySelector('.warning-panel') as HTMLElement;
    expect(panel).not.toBeNull();
    expect(panel.textContent).toContain('Day 1 \u00b7 day label not stated');
    expect(panel.textContent).toContain('colour not supplied');
    expect(panel.textContent).not.toContain('green');
  });
});
