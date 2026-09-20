/* The saved-document viewer: one indexed printed edition, opened from the copy this machine holds.

   The workspace answers /api/documents/<sha> before its session-token gate, so a browser navigation to that
   address needs no token header: web/views.js embeds the same same-origin address in an iframe and offers the
   download beside it, and this viewer follows that route rather than sending the reader to a new tab. The
   state read still goes through the client, so the token, the error mapping and the server's own sentence
   travel with it.

   Three answers stay three states, never one blank frame: the body is served and the frame renders it in
   place, the body is outside the retention window (410 — the edition stays indexed while its passages, hash
   and manifest stay citable), or the read failed and is stated as a failure with a retry. A stored document
   is the record of one printed edition, never a current warning. */
import { useEffect, useId, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ApiError, getJson } from '../api/client';
import { orNot, shortHash } from '../lib/format';
import { Facts, Failure, Reading } from './Evidence';

const documentPath = (sha: string): string => '/api/documents/' + sha;

export type DocumentViewerProps = {
  sha: string;
  title?: string;
  onClose: () => void;
  /** The state the catalogue row already states for this body ('available', 'pruned', ...). When the row
      says the body is held there is nothing to ask: the frame is served the file directly, and the route is
      not read a second time through the client (which would transfer the whole PDF to answer a question the
      row already answered). Any other state, or none, asks the route. */
  body?: string | null;
  /** The printed page a passage cited, when a passage opened this viewer: the frame and the anchor
      carry it so a reader lands on the page the evidence names rather than the first page. */
  page?: number | string | null;
};

export function DocumentViewer({ sha, title, onClose, body = null, page = null }: DocumentViewerProps): JSX.Element {
  const heldByTheRow = body === 'available';
  const read = useQuery({
    queryKey: ['document-body', sha],
    queryFn: () => getJson<unknown>(documentPath(sha), { timeoutMs: 20_000 }),
    retry: false,
    enabled: !heldByTheRow,
  });
  const headingId = useId();
  const panel = useRef<HTMLElement | null>(null);
  const close = useRef<HTMLButtonElement | null>(null);
  /* The viewer is opened by a control elsewhere on the page, so focus lands on its own way out: the panel
     is left with a keyboard rather than only a pointer. */
  useEffect(() => { close.current?.focus(); }, []);
  /* Escape closes the panel the reader is in, and only that: this panel sits inside a surface that has its
     own fields, and a key pressed in the catalogue's filter must not be taken as the viewer's exit. */
  useEffect(() => {
    const escape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || !panel.current?.contains(event.target as Node)) return;
      onClose();
    };
    document.addEventListener('keydown', escape);
    return () => document.removeEventListener('keydown', escape);
  }, [onClose]);

  const name = orNot(title, 'Saved source document');
  const path = documentPath(sha);
  /* A page anchor the browser own PDF viewer understands; without one the file opens at the start. */
  const anchored = page === null || page === undefined || page === '' ? path : path + '#page=' + String(page);
  const pruned = read.error instanceof ApiError && read.error.status === 410;

  return (
    <section ref={panel} className="module-section" role="dialog" aria-labelledby={headingId} data-testid="document-viewer">
      <h3 id={headingId}>{name}</h3>
      <p className="module-note">
        Saved source document from this machine · sha256 <span className="evidence">{sha}</span>
      </p>

      {read.isPending && !heldByTheRow ? <Reading what="the saved source document" /> : null}

      {read.isError && pruned ? (
        <div role="status" data-testid="document-viewer-410">
          <p className="reading">
            This read answered HTTP 410 for the saved body, with the route's own sentence — {read.error.message}
          </p>
          <Facts
            testId="document-viewer-410-facts"
            rows={[
              ['Edition in this viewer', name],
              ['What was pruned', 'The saved PDF body, which is outside the local retention window.'],
              ['What survives', 'The extracted passages, the document hash and the publication manifest stay indexed and citable on this machine.'],
              ['Printed issue date and measured currency', 'They belong to the catalogue row that opened this viewer; a pruned body does not make the edition disappear.'],
            ]}
          />
          <p className="module-note">
            A pruned body is not a crash and not a blank page, and there is no file to offer here, so no PDF is embedded or
            downloaded from this panel.
          </p>
          <p className="module-note" data-testid="document-viewer-not-a-warning">
            A stored document is the record of one printed edition: not a current warning, not an all-clear and not a statement that it applies to a place or a decision.
          </p>
        </div>
      ) : null}

      {read.isError && !pruned ? (
        <Failure error={read.error} what="saved source document" onRetry={() => { void read.refetch(); }} />
      ) : null}

      {read.isSuccess || heldByTheRow ? (
        <>
          <div role="region" aria-label="The saved source document, rendered in this page from this machine">
            <iframe
              src={anchored}
              title={'Saved source document ' + shortHash(sha)}
              loading="lazy"
              style={{ width: '100%', height: 'min(76vh, 44rem)', border: '1px solid var(--g-line-soft)', borderRadius: 'var(--g-r)', background: 'var(--g-raise)' }}
            />
          </div>
          <p className="module-note">
            The browser's own PDF viewer renders this frame from this machine's copy of the file, never from the publisher's
            address. If the frame stays blank, use Save this PDF.
          </p>
          {heldByTheRow ? (
            <p className="module-note" data-testid="document-viewer-row-state">
              The catalogue row this viewer was opened from reports the saved body as held, so the frame is served
              the file directly and the route was not read again: a body pruned since that row was read would answer
              410 in the frame instead.
            </p>
          ) : null}
          <div className="module-controls">
            <a className="btn" href={path} download={'source-' + sha.slice(0, 12) + '.pdf'}>Save this PDF</a>
          </div>
          <p className="module-note" data-testid="document-viewer-kept-file">
            This PDF is the publisher's document, kept on this machine: saving it keeps a copy of your own, and opening or
            saving the file is not an official-warning action. Nothing here is delivered, published or pushed.
          </p>
          <p className="module-note" data-testid="document-viewer-not-a-warning">
            A stored document is the record of one printed edition: not a current warning, not an all-clear and not a statement that it applies to a place or a decision.
            The printed issue date and the measured currency belong to the catalogue row that opened this viewer, not to this frame.
          </p>
        </>
      ) : null}

      <div className="module-controls">
        <button type="button" className="btn btn-ghost" ref={close} onClick={onClose}>Close</button>
      </div>
    </section>
  );
}
