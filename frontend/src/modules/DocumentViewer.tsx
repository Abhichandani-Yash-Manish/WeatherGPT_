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

export function DocumentViewer({ sha, title, onClose }: { sha: string; title?: string; onClose: () => void }): JSX.Element {
  const read = useQuery({
    queryKey: ['document-body', sha],
    queryFn: () => getJson<unknown>(documentPath(sha), { timeoutMs: 20_000 }),
    retry: false,
  });
  const headingId = useId();
  const close = useRef<HTMLButtonElement | null>(null);
  /* The viewer is opened by a control elsewhere on the page, so focus lands on its own way out: the panel
     is left with a keyboard rather than only a pointer. */
  useEffect(() => { close.current?.focus(); }, []);
  useEffect(() => {
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    document.addEventListener('keydown', escape);
    return () => document.removeEventListener('keydown', escape);
  }, [onClose]);

  const name = orNot(title, 'Saved source document');
  const path = documentPath(sha);
  const pruned = read.error instanceof ApiError && read.error.status === 410;

  return (
    <section className="module-section" role="dialog" aria-labelledby={headingId} data-testid="document-viewer">
      <h3 id={headingId}>{name}</h3>
      <p className="module-note">
        Saved source document from this machine · sha256 <span className="evidence">{sha}</span>
      </p>

      {read.isPending ? <Reading what="the saved source document" /> : null}

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
            A pruned body is not a crash and not a blank page, and there is no file to offer here: the edition stays listed
            in the catalogue with its own printed issue date and currency, and no PDF is embedded or downloaded.
          </p>
          <p className="module-note" data-testid="document-viewer-not-a-warning">
            A stored document is the record of one printed edition: not a current warning, not an all-clear and not a statement that it applies to a place or a decision.
          </p>
        </div>
      ) : null}

      {read.isError && !pruned ? (
        <Failure error={read.error} what="saved source document" onRetry={() => { void read.refetch(); }} />
      ) : null}

      {read.isSuccess ? (
        <>
          <div role="region" aria-label="The saved source document, rendered in this page from this machine">
            <iframe
              src={path}
              title={'Saved source document ' + shortHash(sha)}
              loading="lazy"
              style={{ width: '100%', height: 'min(76vh, 44rem)', border: '1px solid var(--line)', borderRadius: 'var(--r-card)', background: 'var(--paper)' }}
            />
          </div>
          <p className="module-note">
            The browser's own PDF viewer renders this frame from this machine's copy of the file, never from the publisher's
            address. If the frame stays blank, use Save this PDF.
          </p>
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
