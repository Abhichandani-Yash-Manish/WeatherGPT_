import type { AnswerPacket } from '../api/types';
import { istWindow } from '../lib/time';
import { parameterName } from './model';
import type { Comparison } from './comparison';

export function ComparisonTable({ comparison, packet }: { comparison: Comparison; packet: AnswerPacket }) {
  return (
    <section className="g-comparison g-claim" aria-label="Matching source comparison">
      <div className="g-comparison-scroll" tabIndex={0} role="region" aria-label="Comparison table; scroll horizontally for every place">
        <table>
          <caption>{parameterName({ id: '', parameter: comparison.parameter, value: '' })} · {istWindow(comparison.start, comparison.end)}</caption>
          <thead><tr><th scope="col">Source product</th>{comparison.columns.map(column => <th scope="col" key={column.entity}>{column.place}</th>)}</tr></thead>
          <tbody>{comparison.sources.map(source => {
            const citation = packet.citations?.find(c => c.source_id === source);
            return <tr key={source}>
              <th scope="row"><span>{citation?.product || 'Product not recorded'}</span><span className="g-comparison-source">{source}</span></th>
              {comparison.columns.map(column => <td key={column.entity}>{column.readings.find(reading => reading.source === source)!.value}<span> {comparison.unit}</span></td>)}
            </tr>;
          })}</tbody>
        </table>
      </div>
      <p className="g-claim-source">Sources {comparison.sources.join(' · ')}. Engine-returned values for the same parameter and window; source agreement is not an accuracy or confidence score. Individual inputs and receipts follow below.</p>
    </section>
  );
}
