/* The passages an answer carries, drawn as evidence a reader can open.

   These are the rules the vanilla passage card was checked against, ported rather than rewritten:

   1. a passage is a quotation with a locator — the printed page, the family, the issued date — and the
      quotation is rendered as the source printed it, never summarised;
   2. a passage that is bulletin context (a general or warning section rather than a crop row) says so,
      and keeps the sentence that current warning and field applicability remain unverified;
   3. a link to a saved document is followed only when it is a local /api/documents/<sha256> address; a
      remote address is shown as text, and a javascript: or data: address is never made clickable;
   4. a passage with no locator is still rendered, and says the locator was not supplied. */

import type { AnswerPacket } from '../api/types';
import { Disclosure } from './parts';

type Passage = {
  id?: string;
  text?: string;
  crop?: string;
  stage?: string;
  section?: string;
  district?: string;
  state?: string;
  page?: number | string | null;
  issue_date?: string | null;
  family?: string | null;
  evidence_kind?: string | null;
  forecast_start?: string | null;
  forecast_end?: string | null;
  citation_ids?: string[];
  document_sha256?: string | null;
  source_id?: string | null;
  qualification_flags?: string[] | null;
};

const SAFE_LOCAL = /^\/api\/documents\/[a-f0-9]{64}$/;

/* Only a local saved-document address becomes a link, and only a page anchor is appended to it. */
function savedDocument(passage: Passage, citations: AnswerPacket['citations']): string | null {
  if (typeof passage.document_sha256 === 'string' && /^[a-f0-9]{64}$/.test(passage.document_sha256)) {
    return '/api/documents/' + passage.document_sha256;
  }
  for (const id of passage.citation_ids || []) {
    const citation = (citations || []).find(entry => entry.id === id);
    const local = (citation as { local_document_path?: unknown } | undefined)?.local_document_path;
    if (typeof local === 'string' && SAFE_LOCAL.test(local)) return local;
  }
  return null;
}

function passageText(passage: Passage): string {
  return typeof passage.text === 'string' && passage.text.trim() ? passage.text : '';
}

export function Passages({ packet }: { packet: AnswerPacket }) {
  const passages = ((packet.passages || packet.document_evidence || []) as unknown as Passage[]).filter(
    passage => Boolean(passage && (passageText(passage) || passage.page)),
  );
  const whole = (packet as { whole_document?: { passages_served?: number; passages_indexed?: number; sections_indexed?: number } }).whole_document;
  if (!passages.length) return null;

  return (
    <section className="card px-3 py-3" data-testid="passages">
      <p className="eyebrow">Quoted from the published document</p>
      {whole ? (
        <p className="mt-1 text-xs text-ink-soft">
          Whole edition: {String(whole.passages_served ?? 'not recorded')} of {String(whole.passages_indexed ?? 'not recorded')} indexed
          passages, one per printed section in printed order ({String(whole.sections_indexed ?? 'not recorded')} sections indexed).
          A bounded reading of the edition, not its full text; the saved document opens from each passage.
        </p>
      ) : null}
      <div className="mt-2 flex flex-col gap-2">
        {passages.map((passage, index) => {
          const context = passage.evidence_kind === 'published_bulletin_context';
          const label = context
            ? 'Bulletin context: ' + (passage.section || 'section not stated')
            : (passage.crop || 'Passage') + ' · ' + (passage.stage || 'stage not stated');
          const head = [label, passage.district, passage.page ? 'page ' + passage.page : 'page not stated']
            .filter(Boolean)
            .join(' · ');
          const local = savedDocument(passage, packet.citations);
          const remote = passage.source_id ? 'source ' + passage.source_id : 'source not stated';
          return (
            <Disclosure key={passage.id || 'passage-' + index} summary={head}>
              <p className="text-xs quiet">
                {[
                  passage.issue_date ? 'Published ' + passage.issue_date : 'Printed issue date not stated',
                  passage.family ? 'Family ' + passage.family : null,
                  remote,
                  passage.forecast_start || passage.forecast_end
                    ? 'Context window ' + (passage.forecast_start || 'not stated') + ' to ' + (passage.forecast_end || 'not stated')
                    : null,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              </p>
              <blockquote className="reading mt-1 border-l-2 border-line pl-3">{passageText(passage) || 'This passage carried no text.'}</blockquote>
              {context ? (
                <p className="mt-1 text-[11px] quiet">
                  Source context only; current warning and individual field applicability remain unverified.
                </p>
              ) : null}
              {(passage.qualification_flags || []).length ? (
                <p className="mt-1 text-[11px] quiet">
                  Source qualification flags as returned: {(passage.qualification_flags || []).join(', ')}
                </p>
              ) : null}
              {local ? (
                <p className="mt-1 text-xs">
                  <a href={local + (passage.page ? '#page=' + passage.page : '')} target="_blank" rel="noopener noreferrer">
                    Open the saved source PDF
                  </a>
                  {' · '}
                  <a href={local} download={'bulletin-' + local.split('/').pop() + '.pdf'}>
                    Download the saved PDF
                  </a>
                </p>
              ) : (
                <p className="mt-1 text-[11px] quiet">
                  No saved copy of this edition is reachable from this answer, so no locator link is offered.
                </p>
              )}
            </Disclosure>
          );
        })}
      </div>
    </section>
  );
}
