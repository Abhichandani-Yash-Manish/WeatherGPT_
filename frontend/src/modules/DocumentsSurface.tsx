/* Published documents: what this machine has indexed, one row per printed edition, with the measured
   state of its saved body. An index entry is not nationwide coverage and not a current warning; a
   pruned body is a state the document route states, not a crash. */
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';
import { count, orNot } from '../lib/format';
import { viewById } from '../shell/views';
import { VizFigure } from '../charts/VizFigure';
import { libraryCardsSpec } from '../charts/vizSpecs';
import { DataTable, NOT_RECORDED, SurfaceShell } from './Evidence';
import { DocumentViewer } from './DocumentViewer';

type DocumentRow = {
  sha256?: string; sha_prefix?: string; family?: string; family_label?: string; scope?: string | null;
  region?: string | null; district?: string | null; state?: string | null; issue_date?: string | null;
  pages?: number | null; passages?: number; source_id?: string | null; age_days?: number | null;
  currency_recorded_at_intake?: string | null; body?: string | null; extraction_status?: string | null;
  quarantined_passages?: number;
};

type CorpusData = {
  documents?: DocumentRow[];
  families?: { family?: string; label?: string; documents?: number; passages?: number; newest_issue_date?: string | null; registered?: boolean }[];
  counts?: Record<string, number>; index?: string; reason?: string;
  /* Families this build does not register but the index holds, reported per row rather than
     aborting the whole listing (repaired 17 September 2026: one such family answered the whole
     read 400 and this surface showed a retry card instead of what the machine holds). */
  unregistered_families?: string[];
};

export const intents: string[] = (viewById('documents')?.intents ?? []).concat([
  'Which editions does this machine hold, and is the saved body still held?',
]);

const BODY_WORDS: Record<string, string> = { available: 'body held', pruned: 'body pruned', unknown: 'body location unrecorded' };

/* The library draws this many edition cards; the table below carries every row. */
const LIBRARY_CARDS_SHOWN = 24;
function currency(document: DocumentRow): string {
  if (document.age_days === null || document.age_days === undefined) return orNot(document.currency_recorded_at_intake, 'unknown');
  return document.age_days + ' day(s) after the printed issue date';
}

export function Surface(): JSX.Element {
  const [family, setFamily] = useState('');
  const [term, setTerm] = useState('');
  const [selected, setSelected] = useState<{ sha: string; label: string; state: string | null } | null>(null);

  const corpus = useQuery({
    queryKey: ['corpus', family, term],
    queryFn: () => getJson<Envelope<CorpusData>>(withQuery('/api/corpus', { family, q: term })),
    retry: false,
  });

  const data = corpus.data?.data;
  const documents = data?.documents || [];
  const counts = data?.counts || {};

  /* The library the vanilla Documents drew: one card per edition, opening the same viewer as the table below. */
  const library = useMemo(
    () => libraryCardsSpec(documents, LIBRARY_CARDS_SHOWN, (document: unknown) => {
      const row = document as DocumentRow;
      if (row.sha256) setSelected({ sha: String(row.sha256), label: row.family_label || row.family || 'this edition', state: row.body ? String(row.body) : null });
    }),
    [documents],
  );
  const families = data?.families || [];
  const quarantined = documents.filter(document => (document.quarantined_passages || 0) > 0);
  const unregisteredCount = counts.documents_in_an_unregistered_family || 0;
  const unregisteredNames = (data?.unregistered_families || []).join(', ');

  return (
    <SurfaceShell
      title="Published documents"
      lead="One row per printed edition this machine has ingested: the printed issue date, the measured currency and the state of the saved body. Not nationwide coverage, and not a current-warning service."
      what="the local corpus index"
      envelope={corpus.data}
      busy={corpus.isPending}
      error={corpus.error}
      onRetry={() => corpus.refetch()}
      intents={intents}
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
        {/* An index can hold a document family this build does not register. It is listed and
            labelled rather than dropped, and the reader is told which family it is. */}
        {unregisteredCount ? (
          <p className="module-note" data-testid="corpus-unregistered">
            {count(unregisteredCount, 'document')} in this index belong to a family this build does not register
            ({orNot(unregisteredNames) || 'family name not stated'}). They are listed with the family name the index
            holds; opening one is refused rather than answered from an unregistered product.
          </p>
        ) : null}
        <p className="module-note">Index this read used: <span className="evidence">{orNot(data?.index)}</span></p>
        {data?.reason ? <p className="module-note">{data.reason}</p> : null}
      </section>

      {library ? (
        <section className="module-section" data-testid="documents-library-section">
          <h2>The library</h2>
          <p className="module-note">
            The editions this read returned as cards: what each one is, when it was printed, how much text it
            carries and whether the saved body is still held. Choosing a card opens the same viewer as the table below.
          </p>
          <VizFigure kind="libraryCards" spec={library} />
        </section>
      ) : null}

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
                onClick={() => setSelected({ sha: String(document.sha256 || ''), label: document.family_label || document.family || 'this edition', state: document.body ? String(document.body) : null })}
              >
                Read what the document route answers
              </button>
            ),
          ])}
        />
        {selected ? (
          /* The reader asked for this body, so it opens in place: the viewer answers 200, 410 (the edition's
             stated state) and a failed read as three different states, and it is the same component on every
             route that offers a saved body. */
          <DocumentViewer sha={selected.sha} title={selected.label} body={selected.state} onClose={() => setSelected(null)} />
        ) : (
          <p className="module-note">No document has been opened yet. A saved body opens in place here; a body the index reports as pruned states what survives.</p>
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
