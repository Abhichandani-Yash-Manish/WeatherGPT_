import { describe, expect, it } from 'vitest';
import type { AnswerPacket, Fact } from '../api/types';
import { comparisonOf } from './comparison';

function packet(): AnswerPacket {
  const facts: Fact[] = ['place-a', 'place-b'].flatMap(entity => [
    { id: entity + '-gfs', source_id: 'S21', parameter: 'precipitation', value: '0.0', unit: 'mm', entity_id: entity, place: entity, start: '2026-09-23T04:00:00Z', end: '2026-09-23T06:00:00Z' },
    { id: entity + '-hour1', source_id: 'S62', parameter: 'precipitation', value: '0.1', unit: 'mm', entity_id: entity, place: entity, start: '2026-09-23T04:00:00Z', end: '2026-09-23T05:00:00Z' },
    { id: entity + '-hour2', source_id: 'S62', parameter: 'precipitation', value: '0.2', unit: 'mm', entity_id: entity, place: entity, start: '2026-09-23T05:00:00Z', end: '2026-09-23T06:00:00Z' },
  ]);
  return { status: 'answered', answer: 'Recorded comparison', facts,
    calculations: ['place-a', 'place-b'].flatMap(entity => [
      { value: '0.3', unit: 'mm', input_ids: [entity + '-hour1', entity + '-hour2'] },
      { kind: 'source_comparison', value: '0.3', unit: 'mm', input_ids: [entity + '-gfs', entity + '-hour1', entity + '-hour2'] },
    ]),
  } as AnswerPacket;
}

describe('an engine comparison can become a matrix only when its dimensions match', () => {
  it('keeps exact engine values including zero, without doing its own arithmetic', () => {
    const p = packet();
    p.calculations![0].value = '0.300';
    const matrix = comparisonOf(p)!;
    expect(matrix.columns).toHaveLength(2);
    expect(matrix.columns[0].readings.map(row => row.value)).toEqual(['0.0', '0.300']);
    expect(matrix.start).toBe('2026-09-23T04:00:00.000Z');
    expect(matrix.end).toBe('2026-09-23T06:00:00.000Z');
  });
  it.each(['unit', 'parameter', 'entity_id', 'end'] as const)('rejects a mismatched %s instead of aligning unlike values', field => {
    const p = packet();
    p.facts![4][field] = field === 'end' ? '2026-09-23T05:30:00Z' : 'different';
    expect(comparisonOf(p)).toBeNull();
  });
  it('does not sum hourly samples when the engine did not return their total', () => {
    const p = packet();
    p.calculations!.shift();
    expect(comparisonOf(p)).toBeNull();
  });
  it('rejects missing inputs, duplicate totals and observation substitutions', () => {
    const missing = packet(); missing.facts!.pop();
    const ambiguous = packet(); ambiguous.calculations!.push(ambiguous.calculations![0]);
    const observation = packet(); observation.facts![0].observed_at = '2026-09-23T04:00:00Z';
    expect(comparisonOf(missing)).toBeNull();
    expect(comparisonOf(ambiguous)).toBeNull();
    expect(comparisonOf(observation)).toBeNull();
  });
});
