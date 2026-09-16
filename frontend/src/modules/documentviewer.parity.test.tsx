/* Parity checks for the saved-document viewer, ported from the vanilla component suite
   tests/test_bulletin_ui.js. The recorded citation and passage constants below are copied verbatim from that
   suite. The vanilla checks were written against renderTurn's passage card; the React viewer is a different
   component that takes the stored body's sha and the catalogue row's own label, never a packet, a citation or
   a publisher URL — so the packet-shaped helper it used has no counterpart here, and the sha is derived from
   the recorded local_document_path.

   Held here (3 of the suite's 6 printed checks, plus one half of a fourth):
   - check 3  the stored copy is preferred to the changing publisher address, and that address never reaches
              the page (the vanilla #page=2 locator has no counterpart: this viewer takes no page);
   - check 5  a same-origin download fallback exists beside the in-place view;
   - check 6  the stored PDF is rendered in place from this origin only, and only once the route has answered
              (there is no toggle and no aria-expanded here: the viewer itself is opened by the catalogue's own
              control, and closing is the host unmounting the panel);
   - check 4  in part: a stored edition is labelled apart from current alerts ('not a current warning', 'not an
              all-clear'). The parent-context/crop-evidence separation half has no React counterpart.

   Not portable, reported rather than asserted: check 1 (the passage card's own bound citation, crop/district
   heading, page locator and literal source text) and check 2 (a javascript: citation URL refused as a link).
   The React answer card (chat/AnswerTurn.tsx) renders no packet.passages and no citation-bound links at all, so
   there is no component here that receives a passage text or a citation URL and could refuse one. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { vi } from 'vitest';
import { server } from '../test/msw';
import { DocumentViewer } from './DocumentViewer';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const basePassage = {
  id: 'p1', crop: 'Rice', stage: 'Tillering', district: 'Kamrup', page: 2,
  issue_date: '2026-09-11', forecast_start: '2026-09-12', forecast_end: '2026-09-16',
  text: '<script>untrusted source text</script>', citation_ids: ['t1-doc'],
};
const boundCitation = { id: 't1-doc', url: 'https://imdagrimet.gov.in/Services/DistrictBulletin.php?district=Kamrup', source_id: 'S27' };
const savedCitation = { id: 't1-doc', url: 'https://imdagrimet.gov.in/current.pdf', source_id: 'S27', local_document_path: '/api/documents/' + 'a'.repeat(64) };
const SHA = savedCitation.local_document_path.replace('/api/documents/', '');
/* The viewer names the edition with the catalogue row's own label; the recorded passage's district is the
   only place name this payload states. */
const TITLE = basePassage.district + ' district bulletin';

/* One stored PDF as the route streams it: application/pdf bytes with no envelope around them. */
const pdf = () => new HttpResponse(
  new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x37]),
  { headers: { 'Content-Type': 'application/pdf' } },
);

describe('saved-document viewer parity', () => {
  it('opens the copy this machine holds in place rather than the changing publisher address', async () => {
    server.use(http.get('/api/documents/:sha', () => pdf()));
    const view = mount(<DocumentViewer sha={SHA} title={TITLE} onClose={() => {}} />);

    const save = await screen.findByRole('link', { name: 'Save this PDF' });
    const frame = view.container.querySelector('iframe');
    expect(frame).not.toBeNull();
    expect(frame?.getAttribute('src')).toBe(savedCitation.local_document_path);
    expect(save).toHaveAttribute('href', savedCitation.local_document_path);

    // The recorded publisher address is not the address this viewer renders, offers or mentions.
    expect(view.container.innerHTML).not.toContain('imdagrimet.gov.in');
    expect(view.container.innerHTML).not.toContain(savedCitation.url);
    expect(view.container.innerHTML).not.toContain(boundCitation.url);
    expect([...view.container.querySelectorAll('a')].map(link => link.getAttribute('href')))
      .toEqual([savedCitation.local_document_path]);
    expect([...view.container.querySelectorAll('a[href^="javascript:"]')]).toHaveLength(0);
  });

  it('keeps a same-origin download fallback beside the in-place view', async () => {
    server.use(http.get('/api/documents/:sha', () => pdf()));
    const view = mount(<DocumentViewer sha={SHA} title={TITLE} onClose={() => {}} />);

    const save = await screen.findByRole('link', { name: 'Save this PDF' });
    expect(save).toHaveAttribute('href', savedCitation.local_document_path);
    expect(save).toHaveAttribute('download', 'source-' + SHA.slice(0, 12) + '.pdf');
    expect(save.getAttribute('href')).not.toMatch(/^[a-z][a-z0-9+.-]*:/);
    expect(save.getAttribute('href')).not.toMatch(/^\/\//);
    expect(view.container.querySelector('iframe')).not.toBeNull();
  });

  it('renders the stored PDF in place from this origin only, once the route has answered', async () => {
    let release!: () => void;
    const gate = new Promise<void>(resolve => { release = resolve; });
    let reads = 0;
    server.use(http.get('/api/documents/:sha', async () => { reads += 1; await gate; return pdf(); }));
    const onClose = vi.fn();
    const view = mount(<DocumentViewer sha={SHA} title={TITLE} onClose={onClose} />);

    // The reader opened the viewer, but the frame is not created until the route has answered.
    expect(view.container.querySelector('iframe')).toBeNull();

    release();
    await waitFor(() => expect(view.container.querySelector('iframe')).not.toBeNull());
    const frame = view.container.querySelector('iframe');
    expect(frame?.getAttribute('src')).toBe(savedCitation.local_document_path);
    expect(String(frame?.getAttribute('src'))).not.toMatch(/^[a-z][a-z0-9+.-]*:/);
    expect(frame?.getAttribute('title')).toMatch(/^Saved source document /);
    expect(reads).toBe(1);

    await userEvent.click(screen.getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalledTimes(1);
    view.unmount();
    expect(view.container.querySelector('iframe')).toBeNull();
    expect(reads).toBe(1);
  });

  it('labels a stored edition apart from current alerts rather than as a warning', async () => {
    server.use(http.get('/api/documents/:sha', () => pdf()));
    mount(<DocumentViewer sha={SHA} title={TITLE} onClose={() => {}} />);
    await screen.findByRole('link', { name: 'Save this PDF' });

    const note = screen.getByTestId('document-viewer-not-a-warning');
    expect(note).toHaveTextContent('not a current warning');
    expect(note).toHaveTextContent('not an all-clear');
    expect(note).toHaveTextContent('belong to the catalogue row that opened this viewer');
  });
});
