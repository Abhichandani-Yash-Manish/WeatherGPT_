/* The saved-document viewer, mounted with an identity and exercised against the document route's own answers
   through MSW. The 410 case is the one that must never read as a crash: the route names the pruned body
   while the passages, the hash and the manifest stay citable. Any other failure is the client's failure
   sentence with a retry, and the close control is the way out. */
import axe from 'axe-core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { vi } from 'vitest';
import { server } from '../test/msw';
import { DocumentViewer } from './DocumentViewer';

const SHA = 'b'.repeat(64);
const TITLE = 'Ahmedabad district agromet advisory';

/* The 410 body the workspace answers with, read from the live route: the route's own sentence, the retention
   window, its sentence about what stays citable, and the retained-document counts beside them. */
const PRUNED = {
  error: 'The source document body is outside the local retention window.',
  retention_days: 7,
  retained: 'the document hash and its extracted pages remain indexed and citable',
  sha256: SHA,
  document: {
    sha256: SHA,
    family: 'district_agromet',
    region: 'Ahmedabad',
    issue_date: '2026-09-11',
    pages: 4,
    retained_passages: 19,
    retained_physical_pages: [1, 2, 3],
    extraction_version: 'v3',
  },
};

/* One stored PDF, exactly as the route streams it: application/pdf bytes, no envelope around them. */
const pdf = () => new HttpResponse(
  new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x37]),
  { headers: { 'Content-Type': 'application/pdf' } },
);

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

describe('the saved-document viewer', () => {
  it('renders the 410 answer as the edition’s stated state, with what survives', async () => {
    server.use(http.get('/api/documents/:sha', () => HttpResponse.json(PRUNED, { status: 410 })));
    const view = mount(<DocumentViewer sha={SHA} title={TITLE} onClose={() => {}} />);

    const state = await screen.findByTestId('document-viewer-410');
    expect(state).toHaveAttribute('role', 'status');
    expect(state).toHaveTextContent('HTTP 410');
    expect(state).toHaveTextContent('The source document body is outside the local retention window.');
    expect(state).toHaveTextContent('The extracted passages, the document hash and the publication manifest stay indexed and citable on this machine.');
    expect(state).toHaveTextContent('a pruned body does not make the edition disappear');
    expect(within(state).getByText('Edition in this viewer')).toBeInTheDocument();
    expect(within(state).getByText(TITLE)).toBeInTheDocument();
    expect(screen.getByText(SHA)).toBeInTheDocument();

    // A pruned body is a state, not a crash and not a frame that would show the route's JSON body.
    expect(screen.queryByRole('alert')).toBeNull();
    expect(view.container.querySelector('iframe')).toBeNull();
    expect(screen.queryByRole('link', { name: 'Save this PDF' })).toBeNull();

    // The issue date the route carries belongs to the catalogue row: the viewer restates neither it nor a
    // currency this machine did not measure against it.
    expect(screen.queryByText('2026-09-11')).toBeNull();

    // One heading level 3, named by the row that opened the viewer, and the required way out.
    const headings = screen.getAllByRole('heading', { level: 3 });
    expect(headings).toHaveLength(1);
    expect(headings[0]).toHaveTextContent(TITLE);
    expect(screen.getByRole('button', { name: 'Close' })).toBeInTheDocument();
    expect(screen.getByTestId('document-viewer-not-a-warning')).toHaveTextContent('not a current warning');

    // The pruned state carries no axe violation (colour contrast needs a layout engine, and axe-core cannot
    // walk the held-body state's iframe in jsdom, so that state is pinned by the DOM contract above instead).
    const scan = await axe.run(view.container, { rules: { 'color-contrast': { enabled: false } } });
    expect(scan.violations.map(violation => violation.id).join(', ')).toBe('');
  });

  it('renders a held body in place from this origin, with the edition’s own name and the file to keep', async () => {
    let requested = '';
    server.use(http.get('/api/documents/:sha', ({ request }) => {
      requested = new URL(request.url).pathname;
      return pdf();
    }));
    const view = mount(<DocumentViewer sha={SHA} title={TITLE} onClose={() => {}} />);

    const save = await screen.findByRole('link', { name: 'Save this PDF' });
    expect(requested).toBe('/api/documents/' + SHA);
    expect(save).toHaveAttribute('href', '/api/documents/' + SHA);
    expect(save).toHaveAttribute('download', 'source-' + SHA.slice(0, 12) + '.pdf');

    const frame = view.container.querySelector('iframe');
    expect(frame).not.toBeNull();
    expect(frame?.getAttribute('src')).toBe('/api/documents/' + SHA);
    expect(String(frame?.getAttribute('src'))).not.toMatch(/^[a-z][a-z0-9+.-]*:/);
    expect(frame?.getAttribute('title')).toBe('Saved source document ' + SHA.slice(0, 12) + '…');
    expect(screen.getByRole('region', { name: /rendered in this page from this machine/ })).toBeInTheDocument();

    const headings = screen.getAllByRole('heading', { level: 3 });
    expect(headings).toHaveLength(1);
    expect(headings[0]).toHaveTextContent(TITLE);

    const kept = screen.getByTestId('document-viewer-kept-file');
    expect(kept).toHaveTextContent(/publisher.s document, kept on this machine/);
    expect(kept).toHaveTextContent('not an official-warning action');
    expect(screen.getByTestId('document-viewer-not-a-warning')).toHaveTextContent('belong to the catalogue row that opened this viewer');
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.queryByTestId('document-viewer-410')).toBeNull();
  });

  it('renders a 500 as the server’s own sentence with a retry that reads again', async () => {
    let calls = 0;
    server.use(http.get('/api/documents/:sha', () => {
      calls += 1;
      return HttpResponse.json({ error: 'The local evidence store is unavailable. Check its files and retry.' }, { status: 500 });
    }));
    const view = mount(<DocumentViewer sha={SHA} onClose={() => {}} />);

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable. Check its files and retry.');
    expect(failure).toHaveTextContent('The saved source document read failed.');
    expect(view.container.querySelector('iframe')).toBeNull();
    expect(calls).toBe(1);

    await userEvent.click(screen.getByRole('button', { name: 'Retry this read' }));
    await waitFor(() => expect(calls).toBe(2));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('renders a 404 as the failure sentence with a retry, never as a document state', async () => {
    server.use(http.get('/api/documents/:sha', () =>
      HttpResponse.json({ error: 'Verified source document is unavailable' }, { status: 404 })));
    const view = mount(<DocumentViewer sha={SHA} onClose={() => {}} />);

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('This read did not answer: Verified source document is unavailable');
    expect(screen.queryByTestId('document-viewer-410')).toBeNull();
    expect(view.container.querySelector('iframe')).toBeNull();
    expect(screen.getByRole('button', { name: 'Retry this read' })).toBeInTheDocument();
  });

  it('closes from its own control and carries the session token on the state read', async () => {
    const onClose = vi.fn();
    let token: string | null = null;
    server.use(http.get('/api/documents/:sha', ({ request }) => {
      token = request.headers.get('X-WeatherGPT-Token');
      return pdf();
    }));
    const meta = document.createElement('meta');
    meta.setAttribute('name', 'workspace-token');
    meta.setAttribute('content', 'test-session-token');
    document.head.append(meta);
    try {
      mount(<DocumentViewer sha={SHA} title={TITLE} onClose={onClose} />);
      await screen.findByRole('link', { name: 'Save this PDF' });
      expect(token).toBe('test-session-token');

      const close = screen.getByRole('button', { name: 'Close' });
      expect(close).toHaveFocus();
      await userEvent.click(close);
      expect(onClose).toHaveBeenCalledTimes(1);

      await userEvent.keyboard('{Escape}');
      expect(onClose).toHaveBeenCalledTimes(2);
    } finally {
      meta.remove();
    }
  });
});
