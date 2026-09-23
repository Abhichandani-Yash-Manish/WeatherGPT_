import type { AnswerPacket, Fact } from '../api/types';

type Reading = { source: string; value: string; inputs: string[] };
type Column = { entity: string; place: string; readings: Reading[] };
export type Comparison = { parameter: string; unit: string; start: string; end: string; columns: Column[]; sources: string[] };

/** Present an engine comparison, never calculate one. A matrix needs two places and
 * exactly matching dimensions. Missing inputs, gaps, overlaps, mixed units and ambiguous
 * totals fall back to the existing complete claim renderer. */
export function comparisonOf(packet: AnswerPacket): Comparison | null {
  const facts = new Map((packet.facts || []).map(fact => [fact.id, fact]));
  const comparisons = (packet.calculations || []).filter(calc => calc.kind === 'source_comparison');
  if (comparisons.length < 2 || comparisons.length > 3) return null;
  let matrix: Comparison | null = null;
  for (const comparison of comparisons) {
    const ids = comparison.input_ids || [];
    if (!ids.length || new Set(ids).size !== ids.length || ids.some(id => !facts.has(id))) return null;
    const inputs = ids.map(id => facts.get(id)!);
    const first = inputs[0];
    if (!first.entity_id || !first.place || !first.unit || !first.parameter) return null;
    if (inputs.some(f => f.entity_id !== first.entity_id || f.place !== first.place || f.unit !== first.unit || f.parameter !== first.parameter || !f.source_id || !f.start || !f.end || f.observed_at)) return null;
    const sources = [...new Set(inputs.map(f => f.source_id!))].sort();
    if (sources.length !== 2) return null;
    const readings: Reading[] = [];
    let start = '', end = '';
    for (const source of sources) {
      const rows: Fact[] = inputs.filter(f => f.source_id === source).sort((a, b) => Date.parse(a.start!) - Date.parse(b.start!));
      if (rows.some((row, index) => !Number.isFinite(Date.parse(row.start!)) || !Number.isFinite(Date.parse(row.end!)) || Date.parse(row.end!) <= Date.parse(row.start!) || (index > 0 && Date.parse(rows[index - 1].end!) !== Date.parse(row.start!)))) return null;
      const from = new Date(rows[0].start!).toISOString();
      const to = new Date(rows[rows.length - 1].end!).toISOString();
      if (start && (from !== start || to !== end)) return null;
      start = from; end = to;
      const inputIds = rows.map(row => row.id);
      let value: string;
      if (rows.length === 1) value = rows[0].value;
      else {
        const totals = (packet.calculations || []).filter(calc => calc.kind !== 'source_comparison' && calc.unit === first.unit && calc.input_ids?.length === inputIds.length && new Set(calc.input_ids).size === inputIds.length && calc.input_ids.every(id => inputIds.includes(id)));
        if (totals.length !== 1 || totals[0].value == null) return null;
        value = String(totals[0].value);
      }
      if (value == null || value === '') return null;
      readings.push({ source, value: String(value), inputs: inputIds });
    }
    if (!matrix) matrix = { parameter: first.parameter, unit: first.unit, start, end, sources, columns: [] };
    if (matrix.parameter !== first.parameter || matrix.unit !== first.unit || matrix.start !== start || matrix.end !== end || matrix.sources.join('|') !== sources.join('|') || matrix.columns.some(column => column.entity === first.entity_id)) return null;
    matrix.columns.push({ entity: first.entity_id, place: first.place, readings });
  }
  return matrix;
}
