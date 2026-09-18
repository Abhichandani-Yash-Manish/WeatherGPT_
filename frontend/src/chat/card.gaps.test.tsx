/* The five card gaps the ported checks named, pinned one check each against the payload shape the engine
   returns: a computed value (and what a source comparison is not), an airport report and its type, the
   receipt for a series whose values are all plotted, task accounting as asked/answered/incomplete, and an
   official district warning day as its own named period. */

import { render, screen } from '@testing-library/react';
import type { AnswerPacket } from '../api/types';
import { AnswerTurn } from './AnswerTurn';

function packet(overrides: Partial<AnswerPacket> = {}): AnswerPacket {
  return {
    conversation_id: '44444444-4444-4444-8444-444444444444',
    question: 'Question under test',
    status: 'answered',
    answer: 'The answer sentence.',
    facts: [],
    citations: [],
    notes: [],
    choices: [],
    charts: [],
    task_results: [],
    answered_at_utc: '2026-09-17T10:47:00+00:00',
    resolved_points: {},
    trace: {},
    retrieval_plan: [],
    ...overrides,
  };
}

function mount(p: AnswerPacket, _register: 'conversational' | 'full' = 'conversational') {
  return render(<AnswerTurn packet={p} onFollowUp={() => {}} />);
}

describe('the airport report', () => {
  it('keeps the source text, names the report kind, and says neither kind is a clearance', () => {
    mount(packet({
      /* The engine names these fields station, kind, raw_report, observed_at, valid_start and valid_end;
         the card keeps those names rather than renaming what it was sent. */
      airport_reports: [
        { kind: 'metar', station: 'VOBL', observed_at: '2026-09-17T05:30:00+00:00',
          raw_report: 'METAR VOBL 170530Z 25008KT 9999 SCT020 27/21 Q1012' },
        { kind: 'taf', station: 'VOBL', valid_start: '2026-09-17T06:00:00+00:00', valid_end: '2026-09-17T12:00:00+00:00',
          raw_report: 'TAF VOBL 170500Z 1706/1712 26010KT 9999 SCT020' },
      ],
    }));
    expect(screen.getByText(/METAR VOBL 170530Z/)).toBeInTheDocument();
    expect(screen.getByText(/TAF VOBL 170500Z/)).toBeInTheDocument();
    expect(screen.getByText(/Observed report \(METAR\)/)).toBeInTheDocument();
    expect(screen.getByText(/Forecast \(TAF\)/)).toBeInTheDocument();
    expect(document.body).toHaveTextContent(/not a flight status or a clearance/);
    expect(document.body).toHaveTextContent(/not a runway state and not an operational clearance/);
  });
});

describe('the computed value', () => {
  it('shows a computation with the engine method, and a source comparison as a difference rather than a score', () => {
    mount(packet({
      calculations: [{
        kind: 'source_comparison',
        value: '-0.8',
        unit: 'mm',
        method: 'difference of complete matching point/window totals',
        interpretation: 'not skill or confidence',
        input_ids: ['t1-f1', 't1-f2'],
        source_ids: ['S21', 'S62'],
      }],
    }));
    const block = document.querySelector('.calc') as HTMLElement;
    expect(block).not.toBeNull();
    expect(block).toHaveTextContent('-0.8');
    expect(block).toHaveTextContent('Difference between sources');
    expect(block).toHaveTextContent('not skill or confidence');
    expect(block).toHaveTextContent(/is not a skill score, an accuracy measure or a confidence value/);
  });
});
describe('the series receipt', () => {
  it('receipts the values it plotted when every returned value is already drawn', () => {
    mount(packet({
      facts: [{ id: 'c1', parameter: 'precipitation', label: 'Forecast rainfall', value: '0.3', unit: 'mm',
                source_id: 'S21', citation_ids: ['cit-1'], evidence_kind: 'forecast' }],
      charts: [{ title: 'Forecast rainfall', unit: 'mm', points: [{ t: '2026-09-18T06:30:00+05:30', v: 0.3, evidence_id: 'c1' }] }],
      citations: [{ id: 'cit-1', source_id: 'S21', provider: 'Open-Meteo', product: 'hourly forecast',
                    retrieved_at_utc: '2026-09-17T10:39:00+00:00', page: 612, row: 1294 }],
    }));
    const receipt = document.querySelector('.receipt') as HTMLElement;
    expect(receipt).not.toBeNull();
    expect(receipt).toHaveTextContent(/1 retrieved value/);
    expect(receipt).toHaveTextContent('S21');
    expect(receipt).toHaveTextContent(/page 612/);
  });
});

describe('task accounting', () => {
  it('reports asked, answered and incomplete separately, and names the incomplete task', () => {
    mount(packet({
      task_coverage: { requested: 2, completed: 1, incomplete_ids: ['t2'] },
      task_results: [
        { id: 't1', request: { kind: 'forecast' }, status: 'answered' },
        { id: 't2', request: { kind: 'warning' }, status: 'unavailable' },
      ],
    }));
    const accounting = screen.getByText('Task accounting').closest('div') as HTMLElement;
    expect(accounting).toHaveTextContent('Asked: 2');
    expect(accounting).toHaveTextContent('Answered: 1');
    expect(accounting).toHaveTextContent('Incomplete: 1');
    expect(accounting).toHaveTextContent('t2');
  });
});

describe('the official warning day', () => {
  it('draws the district day as its named period with the stated colour and the no-all-clear sentence', () => {
    mount(packet({
      warning_evidence: [{
        district_warnings: [{
          district: 'PATNA', state: 'BIHAR', issued_at_utc: '2026-09-17T06:00:00+00:00', source_id: 'S15',
          days: [{ date: '2026-09-17', day_label: 'Day 1', colour: 'yellow', colour_code: 3,
                   hazards: ['Thunderstorm'], wording: 'Thunderstorm/lightning/squall',
                   starts_utc: '2026-09-17T00:00:00+00:00', ends_utc: '2026-09-18T00:00:00+00:00' }],
        }],
      }],
    }));
    const panel = document.querySelector('.warning-panel') as HTMLElement;
    expect(panel).not.toBeNull();
    expect(panel).toHaveTextContent('PATNA');
    expect(panel).toHaveTextContent('Day 1');
    expect(panel).toHaveTextContent('yellow');
    expect(panel).toHaveTextContent(/Thunderstorm/);
    /* The not-an-all-clear sentence belongs to the quiet case, which the payload states with its own field: a
       yellow day is a warning, and the card does not call a warning an all-clear in either direction. */
    expect(panel.textContent).not.toMatch(/all-clear/i);
  });

  it('states that a quiet district-day is not an all-clear', () => {
    mount(packet({
      warning_evidence: [{
        district_warnings: [{
          district: 'AHMADABAD', state: 'GUJARAT', source_id: 'S15',
          days: [{ date: '2026-09-17', day_label: 'Day 1', colour: 'green', quiet: true, source_text: 'No warning in this product' }],
        }],
      }],
    }));
    const quiet = document.querySelector('.warning-panel') as HTMLElement;
    expect(quiet).toHaveTextContent(/No warning in this product/);
    expect(quiet).toHaveTextContent(/not an all-clear, and not a statement that nothing will happen/);
  });
});
