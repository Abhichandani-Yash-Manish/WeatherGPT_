/* Published documents: what this machine has indexed, one row per printed edition, with the measured
   state of its saved body. An index entry is not nationwide coverage and not a current warning; a
   pruned body is a state the document route states, not a crash. */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ApiError, getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { viewById } from '../shell/views';
import { DataTable, Failure, NOT_RECORDED, Reading, SurfaceShell } from './Evidence';

type DocumentRow = {
  sha256?: string; sha_prefix?: string; family?: string; family_label?: string; scope?: string | null;
  region?: string | null; district?: string | null; state?: string | null; issue_date?: string | null;
  pages?: number | null; passages?: number; source_id?: string | null; age_days?: number | null;
  currency_recorded_at_intake?: string | null; body?: string | null; extraction_status?: string | null;
  quarantined_passages?: number;
};

type CorpusData = {
  documents?: DocumentRow[];
  families?: { family?: string; label?: string; documents?: number; passages?: number; newest_issue_date?: string | null }[];
  counts?: Record<string, number>; index?: string; reason?: string;
};

export const intents: string[] = (viewById('documents')?.intents ?? []).concat([
  'Which editions does this machine hold, and is the saved body still held?',
]);

const BODY_WORDS: Record<string, string> = { available: 'body held', pruned: 'body pruned', unknown: 'body location unrecorded' };

function currency(document: DocumentRow): string {
  if (document.age_days === null || document.age_days === undefined) return orNot(document.currency_recorded_at_intake, 'unknown');
  return document.age_days + ' day(s) after the printed issue date';
}

/* The one read of the document route: a 410 is the document's stated state, every other failure is a
   failed read with a retry, and nothing here decides that a document does not exist. */
function DocumentBodyState({ sha, label }: { sha: string; label: string }): JSX.Element {
  const read = useQuery({
    queryKey: ['document-body', sha],
    queryFn: () => getJson<unknown>('/api/documents/' + sha, { timeoutMs: 20_000 }),
    retry: false,
  });
  if (read.isPending) return <Reading what="the document route" />;
  if (read.isError) {
    const status = read.error instanceof ApiError ? read.error.status : 0;
    if (status === 410) {
      return (
        <div className="module-note" role="status" data-testid="document-state-410">
          <p className="reading">{label}: this read answered HTTP 410 for the saved body, with its own sentence — {read.error.message}</p>
          <p className="module-note">
            That is the edition's stated state, not a crash: the body was pruned while the identity, pages and passages stay indexed.
          </p>
        </div>
      );
    }
    return <Failure error={read.error} what="document route" onRetry={() => read.refetch()} />;
  }
  return (
    <p className="reading" role="status" data-testid="document-state-held">
      {label}: this read answered with the saved body, so the file is still held and can be read at{' '}
      <a href={'/api/documents/' + sha}>/api/documents/{sha.slice(0, 12)}…</a>.
    </p>
  );
}

export function Surface(): JSX.Element {
  const [family, setFamily] = useState('');
  const [term, setTerm] = useState('');
  const [selected, setSelected] = useState<{ sha: string; label: string } | null>(null);

  const corpus = useQuery({
    queryKey: ['corpus', family, term],
    queryFn: () => getJson<Envelope<CorpusData>>(withQuery('/api/corpus', { family, q: term })),
    retry: false,
  });

  const data = corpus.data?.data;
  const documents = data?.documents || [];
  const counts = data?.counts || {};
  const families = data?.families || [];
  const quarantined = documents.filter(document => (document.quarantined_passages || 0) > 0);

  return (
    <SurfaceShell
      title="Published documents"
      lead="One row per printed edition this machine has ingested: the printed issue date, the measured currency and the state of the saved body. Not nationwide coverage, and not a current-warning service."
      what="the local corpus index"
      envelope={corpus.data}
      busy={corpus.isPending}
      error={corpus.error}
      onRetry={() => corpus.refetch()}
    >
      <section className="module-section">
        <h2>Filters and counts</h2>
        <div className="module-controls">
          <label className="module-field" htmlFor="corpus-family">
            <span>Family</span>
            <select id="corpus-family" value={family} onChange={event => setFamily(event.target.value)}>
              <option value="">Every family</option>
              {families.map(entry => (
                <option key={orNot(entry.family, 'family not stated')} value={entry.family || ''}>
                  {orNot(entry.label || entry.family, 'family not stated')} ({orNot(entry.documents)})
                </option>
              ))}
            </select>
          </label>
          <label className="module-field" htmlFor="corpus-term">
            <span>Region, state or district contains</span>
            <input id="corpus-term" type="search" value={term} onChange={event => setTerm(event.target.value)} />
          </label>
        </div>
        <p className="module-note">Both filters are sent to GET /api/corpus as family and q, so every count below describes the index this read returned.</p>
        <p className="module-note" role="status" data-testid="corpus-count">
          {count(counts.documents, 'document')} in the index · {count(counts.passages, 'passage')} · {count(counts.regions, 'region')} ·{' '}
          {count(counts.families, 'family', 'families')} indexed · {orNot(counts.bodies_available)} with a saved body, {orNot(counts.pruned)} pruned ·{' '}
          {orNot(counts.documents_without_a_printed_issue_date)} without a printed issue date
        </p>
        <p className="module-note">Index this read used: <span className="evidence">{orNot(data?.index)}</span></p>
        {data?.reason ? <p className="module-note">{data.reason}</p> : null}
      </section>

      <section className="module-section">
        <h2>The editions indexed</h2>
        <DataTable
          testId="corpus-table"
          caption="One row per indexed edition. 'not stated' is a value the edition did not print; 'unknown' is a currency this machine cannot measure."
          columns={['Family', 'Region', 'Printed issue', 'Pages', 'Passages', 'Currency', 'Saved body', 'Extraction', 'Source', 'Saved-body state']}
          rows={documents.map(document => [
            orNot(document.family_label || document.family),
            orNot(document.region || [document.district, document.state].filter(Boolean).join(', ')),
            orNot(document.issue_date, 'not stated'),
            document.pages === null || document.pages === undefined ? NOT_RECORDED : String(document.pages),
            orNot(document.passages),
            currency(document),
            BODY_WORDS[String(document.body)] || 'body state unrecorded',
            orNot(document.extraction_status),
            orNot(document.source_id),
            /* A body the index reports as held is offered as the file itself, so no PDF body is pulled
               into this page just to restate what the row already says. */
            document.body === 'available' && document.sha256 ? (
              <a key="state" href={'/api/documents/' + document.sha256}>
                Open the saved body
              </a>
            ) : (
              <button
                key="state"
                type="button"
                className="btn btn-ghost"
                disabled={!document.sha256}
                onClick={() => setSelected({ sha: String(document.sha256 || ''), label: document.family_label || document.family || 'this edition' })}
              >
                Read what the document route answers
              </button>
            ),
          ])}
        />
        {selected ? (
          <DocumentBodyState sha={selected.sha} label={selected.label} />
        ) : (
          <p className="module-note">No document route has been read yet, so no saved-body state is stated here.</p>
        )}
      </section>

      <section className="module-section">
        <h2>Families and quarantines</h2>
        <DataTable
          testId="corpus-families"
          caption="Every family the index holds, with the newest printed issue date it records."
          columns={['Family', 'Documents', 'Passages', 'Newest printed issue date']}
          rows={families.map(entry => [
            orNot(entry.label || entry.family),
            orNot(entry.documents),
            orNot(entry.passages),
            orNot(entry.newest_issue_date, 'no issue date recorded'),
          ])}
        />
        <p className="module-note">
          {quarantined.length
            ? 'A quarantined passage is counted, never served as evidence: ' + quarantined.map(document => orNot(document.family_label || document.family) + ' ' + orNot(document.quarantined_passages)).join('; ')
            : 'No edition on this page reports a quarantined passage.'}
        </p>
      </section>
    </SurfaceShell>
  );
}

export default Surface; // the surface host loads a module with React.lazy, which reads the default export
