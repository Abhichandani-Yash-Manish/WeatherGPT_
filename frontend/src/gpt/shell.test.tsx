import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Workspace } from './Workspace';
import { SHELL_KEY } from './shellState';

/* The shell's own contract, since the rail stopped being two columns:
   ----------------------------------------------------------------------------
   1. The rail collapses, and the arrangement survives the page — a reader who gave the column its width back
      does not have to give it back again on every visit.
   2. The reading panel is where the language and the persona live now, and it opens from the bar.
   3. A pinned conversation sits above the recency groups rather than in them.
   4. ⌥B and ⌥N are the rail's own keys, and they are ⌥ because a browser owns ⌘B and ⌘1–⌘9. */

function envelope(data: Record<string, unknown>) {
  return { schema_version: 'product-view-v1', view: 'x', status: 'ok', data, sources: [] };
}

const LEDGER = {
  schema_version: 'conversation-ledger-v1',
  total: 2,
  limit: 40,
  conversations: [
    { id: 'c1', updated: new Date().toISOString(), turns: 2, asked: 1, opening_question: 'Will it rain in Surat tomorrow?' },
    { id: 'c2', updated: new Date(Date.now() - 3 * 86_400_000).toISOString(), turns: 2, asked: 1, opening_question: 'Any warning in force for Patna?' },
  ],
};

function serveTheShell() {
  server.use(
    http.get('/api/conversations', () => HttpResponse.json(LEDGER)),
    http.get('/api/personas', () => HttpResponse.json(envelope({ personas: [{ id: 'farmer', label: 'A farmer' }] }))),
    http.get('/api/languages', () => HttpResponse.json({ schema_version: 'language-support-view-v1', service_configured: false, languages: [
      { code: 'hi', english_name: 'Hindi', native_name: 'हिन्दी', understanding: 'verified', output: 'verified' },
    ] })),
  );
}

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  return render(
    <QueryClientProvider client={client}>
      <Workspace onOpen={() => {}} language="" onLanguage={() => {}} persona="" onPersona={() => {}} />
    </QueryClientProvider>,
  );
}

describe('the shell', () => {
  beforeEach(() => {
    serveTheShell();
    try {
      window.localStorage.clear();
    } catch {
      /* storage is optional */
    }
  });

  it('collapses the rail and remembers the arrangement', async () => {
    const first = mount();
    expect(document.querySelector('.g-rail')?.getAttribute('data-collapsed')).toBe('false');
    await userEvent.click(screen.getByLabelText('Collapse the rail'));
    expect(document.querySelector('.g-rail')?.getAttribute('data-collapsed')).toBe('true');
    first.unmount();

    /* A second visit: the rail is still out of the way. */
    mount();
    expect(document.querySelector('.g-rail')?.getAttribute('data-collapsed')).toBe('true');
    expect(JSON.parse(String(window.localStorage.getItem(SHELL_KEY))).rail).toBe('collapsed');
  });

  it('opens the reading panel from the bar, where the language and the persona are', async () => {
    mount();
    expect(screen.queryByRole('complementary', { name: /how this conversation is read/i })).toBeNull();
    await userEvent.click(screen.getByLabelText('Open the reading panel'));
    const panel = await screen.findByRole('complementary', { name: /how this conversation is read/i });
    /* The control the product promises is here, with the measured list under it. */
    const language = within(panel).getByLabelText('Answer language');
    expect(within(language).getByRole('option', { name: /Hindi/ })).toBeInTheDocument();
    expect(within(panel).getByLabelText('Reading as')).toBeInTheDocument();
  });

  it('pins a conversation above the recency groups', async () => {
    mount();
    await screen.findByText('Will it rain in Surat tomorrow?');
    const row = screen.getByText('Will it rain in Surat tomorrow?').closest('.g-row') as HTMLElement;
    await userEvent.click(within(row).getByLabelText(/^Pin /));
    await waitFor(() => expect(screen.getByText('Pinned')).toBeInTheDocument());
    const pinned = screen.getByText('Pinned').parentElement as HTMLElement;
    expect(within(pinned).getByText('Will it rain in Surat tomorrow?')).toBeInTheDocument();
  });

  it('keeps the rail keys on ⌥, which a browser does not own', async () => {
    mount();
    /* With the code, as a browser sends it: on macOS ⌥B arrives as key "∫" and only code "KeyB" is the
       physical key. A check written against the letter would pass here and fail on the machine that matters. */
    fireEvent.keyDown(window, { altKey: true, code: 'KeyB', key: '∫' });
    await waitFor(() => expect(document.querySelector('.g-rail')?.getAttribute('data-collapsed')).toBe('true'));
    /* ⌘B must do nothing: it is the browser's, and taking it would be taking a key that is not ours. */
    fireEvent.keyDown(window, { metaKey: true, code: 'KeyB', key: 'b' });
    expect(document.querySelector('.g-rail')?.getAttribute('data-collapsed')).toBe('true');
    await userEvent.click(screen.getByLabelText('Expand the rail'));
    fireEvent.keyDown(window, { metaKey: true, code: 'KeyB', key: 'b' });
    expect(document.querySelector('.g-rail')?.getAttribute('data-collapsed')).toBe('false');
  });

  it('opens the n-th conversation with ⌥-digit', async () => {
    const asked: string[] = [];
    server.use(http.get('/api/conversations/:id', ({ params }) => {
      asked.push(String(params.id));
      return HttpResponse.json(envelope({ conversation: { id: params.id, history: [], updated: new Date().toISOString() } }));
    }));
    mount();
    await screen.findByText('Will it rain in Surat tomorrow?');
    /* The second row the rail is showing is the second conversation, and the transcript read names it. */
    fireEvent.keyDown(window, { altKey: true, code: 'Digit2', key: '™' });
    await waitFor(() => expect(asked).toContain('c2'));
  });
});
