import { ArrowUpRight, BookOpen } from 'lucide-react';
import type { Citation } from '../api/types';
import { istStamp } from '../lib/time';

/** A margin belonging to ONE packet, not the conversation's aggregate source inventory.
 * Grouping by source is navigation only: every edition, read time and locator stays in its receipt.
 */
export function AnswerEvidence({ citations }: { citations: Citation[] }) {
  const groups = new Map<string, Citation[]>();
  for (const citation of citations) {
    const rows = groups.get(citation.source_id) || [];
    rows.push(citation);
    groups.set(citation.source_id, rows);
  }
  if (!groups.size) return null;
  return (
    <aside className="g-evidence-margin" aria-label="Evidence for this answer">
      <div className="g-evidence-heading"><BookOpen size={15} aria-hidden="true" /><h3>Evidence</h3><span className="g-fold-count">{groups.size}</span></div>
      <p className="g-evidence-intro">The sources behind this answer.</p>
      {[...groups].map(([id, rows]) => (
        <details className="g-evidence-entry" key={id}>
          <summary>
            <span className="g-evidence-id g-claim-source">{id}</span>
            <span><strong>{rows[0].provider || 'Source'}</strong><span className="g-evidence-product">{[...new Set(rows.map(row => row.product).filter(Boolean))].join(' · ') || 'Product not recorded'}</span></span>
          </summary>
          <div className="g-evidence-receipts">
            {rows.map((citation, index) => (
              <div className="g-evidence-receipt g-claim-source" key={(citation.id || 'receipt') + '-' + index}>
                <p>{citation.product || 'Product not recorded'}</p>
                <p>Read {citation.retrieved_at_utc ? istStamp(citation.retrieved_at_utc) : 'time not recorded'}</p>
                <p>{citation.id || 'Citation id not recorded'}{citation.page != null ? ' · page ' + citation.page : ''}{citation.row != null ? ' · row ' + citation.row : ''}{citation.column ? ' · column ' + citation.column : ''}</p>
                {citation.locator ? <p>{citation.locator}</p> : null}
                {citation.sha256 ? <p title={citation.sha256}>SHA256 {citation.sha256.slice(0, 12)}…</p> : null}
                {citation.url && /^https?:\/\//i.test(citation.url) ? <a href={citation.url} target="_blank" rel="noreferrer noopener">Open publisher <ArrowUpRight size={13} aria-hidden="true" /></a> : null}
              </div>
            ))}
          </div>
        </details>
      ))}
    </aside>
  );
}
