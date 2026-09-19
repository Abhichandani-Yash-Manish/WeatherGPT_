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

  it('lists the stored conversations, with the place each resolved, and searches every turn', async () => {
    /* The store's own behaviour, reproduced in miniature: a q reaches the turns rather than only the opening
       question, and a conversation that resolved a point carries the place its own answers resolved. */
    const LEDGER = {
      k1: { id: 'k1', updated: new Date().toISOString(), turns: 2, asked: 1,
            opening_question: 'Will it rain in Kochi?', place: { label: 'Kochi, Kerala', latitude: 9.93, longitude: 76.26 } },
      k2: { id: 'k2', updated: new Date().toISOString(), turns: 4, asked: 2,
            opening_question: 'Any warning for Patna?',
            match: { role: 'user', text: 'and what about Kochi tomorrow?' } },
      k3: { id: 'k3', updated: new Date().toISOString(), turns: 2, asked: 1, opening_question: 'Is it humid in Surat?' },
    };
    const asked: string[] = [];
    server.use(http.get('/api/conversations', ({ request }) => {
      const q = new URL(request.url).searchParams.get('q');
      asked.push(String(q));
      const conversations = !q ? Object.values(LEDGER)
        : Object.values(LEDGER).filter(row => JSON.stringify(row).toLowerCase().includes(q.toLowerCase()));
      return HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: conversations.length, limit: 40, conversations, query: q });
    }));
    mount();
    /* The row itself, not the pin and delete controls beside it: those carry the question in their own
       accessible names, which is exactly right for a screen reader and useless for counting rows. */
    const rows = () => Array.from(
      screen.getByRole('region', { name: 'Conversations' }).querySelectorAll('.g-row-text'),
    );
    await waitFor(() => expect(rows()).toHaveLength(3));
    /* The place the answers resolved is on the row, as the engine recorded it. */
    expect(rows()[0]).toHaveTextContent('Kochi, Kerala');

    /* The field is behind the magnifier rather than standing in the rail: a search box on every visit costs
       the column a row for something most visits do not do. */
    await userEvent.click(screen.getByLabelText('Search conversations'));
    await userEvent.type(screen.getByLabelText('Filter conversations'), 'kochi');
    /* The search is the store's, and it waits for the typing to stop before asking. */
    await waitFor(() => expect(asked).toContain('kochi'));
    await waitFor(() => expect(rows()).toHaveLength(2));
    /* The row that matched in a follow-up question says where it matched. */
    const followUp = rows().find(row => row.textContent?.includes('Any warning for Patna?'));
    expect(followUp).toHaveTextContent('in a question: and what about Kochi tomorrow?');
    expect(screen.getByText(/2 conversations mention “kochi”/)).toBeInTheDocument();
  });

  /* The delete control is a real deletion of local evidence, and the audit of 17 September 2026 measured the
     old one at 2.91:1 because a resting opacity blended --red into the paper. Its absence is what this pins;
     the rendered contrast is measured by the axe run, not by this check. */
  it('keeps the delete control readable rather than fading it below the contrast floor', async () => {
    mount();
    const deletes = await screen.findAllByRole('button', { name: /^Delete / });
    expect(deletes.length).toBeGreaterThan(0);
    deletes.forEach(button => expect(button.className).not.toMatch(/opacity-\d/));
  });

  it('filters the list to a place the conversations themselves resolved', async () => {
    server.use(http.get('/api/conversations', () => HttpResponse.json({
      schema_version: 'conversation-ledger-v1', total: 2, limit: 40,
      conversations: [
        { id: 'p1', updated: new Date().toISOString(), turns: 2, asked: 1,
          opening_question: 'Will it rain in Kochi?', place: { label: 'Kochi, Kerala', latitude: 9.93, longitude: 76.26 } },
        { id: 'p2', updated: new Date().toISOString(), turns: 2, asked: 1, opening_question: 'Any warning for Patna?' },
      ],
    })));
    mount();
    const places = await screen.findByRole('region', { name: 'Places this machine knows' });
    /* Two controls carry the label: the row, which holds the place and filters by it, and the row's own
       "Ask about it". The row is the one with no other name. */
    await within(places).findByRole('button', { name: 'Kochi, Kerala' });
    const rows = () => Array.from(screen.getByRole('region', { name: 'Conversations' }).querySelectorAll('.g-row-text'));
    expect(rows()).toHaveLength(2);
    /* Choosing a place makes it the place this browser holds — and narrows the list to it. */
    await userEvent.click(within(places).getByRole('button', { name: 'Kochi, Kerala' }));
    expect(Array.isArray(JSON.parse(String(window.localStorage.getItem('weathergpt.place'))))).toBe(false);
    expect(JSON.parse(String(window.localStorage.getItem('weathergpt.place'))).label).toBe('Kochi, Kerala');
    await waitFor(() => expect(rows()).toHaveLength(1));
    expect(rows()[0]).toHaveTextContent('Will it rain in Kochi?');
  });

  it('opens the key list with ⌥/', async () => {
    mount();
    fireEvent.keyDown(window, { altKey: true, code: 'Slash', key: '÷' });
    expect(await screen.findByRole('dialog', { name: 'Keyboard shortcuts' })).toBeInTheDocument();
    expect(screen.getByText(/a page cannot take ⌘1–⌘9/i)).toBeInTheDocument();
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
  it('keeps the delete failure visible rather than emptying the list on a promise', async () => {
    server.use(
      http.get('/api/conversations', () => HttpResponse.json({
        schema_version: 'conversation-ledger-v1', total: 1, limit: 40, note: 'stored locally',
        conversations: [{ id: '11111111-1111-4111-8111-111111111111', opening_question: 'hello', turns: 2, asked: 1 }],
      })),
      http.delete('/api/conversations/:id', () => HttpResponse.json({ error: 'The local evidence store is unavailable.' }, { status: 503 })),
    );
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    mount();
    await userEvent.click(await screen.findByLabelText('Delete hello'));
    expect(await screen.findByText(/was not deleted: The local evidence store is unavailable/)).toBeInTheDocument();
    /* The row stays: a row that disappears while the store still holds it is a worse lie than a row that
       stays with a sentence under it. */
    expect(screen.getByText('hello')).toBeInTheDocument();
    confirm.mockRestore();
  });

  it('deletes a stored conversation through the local route only, and says when the delete failed', async () => {
    const asked: string[] = [];
    /* A real deletion of local evidence, asked for by name and confirmed first: the store is written to by
       exactly one route, and a failed delete is said rather than swallowed. */
    server.use(
      http.get('/api/conversations', () => HttpResponse.json({
        schema_version: 'conversation-ledger-v1', total: 1, limit: 40, note: 'stored locally',
        conversations: [{ id: '11111111-1111-4111-8111-111111111111', opening_question: 'hello', turns: 2, asked: 1 }],
      })),
      http.delete('/api/conversations/:id', ({ request, params }) => {
        asked.push(request.method + ' ' + String(params.id));
        return HttpResponse.json({ removed: String(params.id) });
      }),
    );
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    mount();
    await userEvent.click(await screen.findByLabelText('Delete hello'));
    await waitFor(() => expect(asked).toEqual(['DELETE 11111111-1111-4111-8111-111111111111']));
    confirm.mockRestore();
  });
});
