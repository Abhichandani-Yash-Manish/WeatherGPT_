import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Workspace } from './Workspace';
import { renderAsk } from '../test/ask';
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
  const carried: string[] = [];
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

  it('saves the whole conversation, not one answer', async () => {
    const saved: { name: string; text: string }[] = [];
    /* The download is a real browser action; jsdom has no Blob URL, so the anchor is what this watches. */
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      saved.push({ name: this.download, text: String((this as HTMLAnchorElement & { __text?: string }).__text || '') });
    });
    const createUrl = vi.fn(() => 'blob:fixture');
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createUrl });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() });
    server.use(http.post('/api/chat', () => HttpResponse.json({
      conversation_id: '44444444-4444-4444-8444-444444444444', question: 'Will it rain in Ahmedabad?',
      status: 'answered', answer: 'Ahmedabad: forecast precipitation 0.3 mm.',
      facts: [{ id: 'f1', label: 'Forecast rainfall', value: '0.3', unit: 'mm', place: 'Ahmedabad, Gujarat',
                start: '2026-09-18T06:30:00+05:30', end: '2026-09-18T12:30:00+05:30', source_id: 'S21',
                parameter: 'precipitation', evidence_kind: 'forecast', citation_ids: [], task_id: 't1' }],
      citations: [], notes: [], choices: [], charts: [], task_results: [], answered_at_utc: '2026-09-18T07:00:00+00:00',
      resolved_points: {}, trace: {}, retrieval_plan: [],
    })));
    mount();
    await userEvent.type(screen.getByLabelText('Your question'), 'Will it rain in Ahmedabad?');
    await userEvent.click(screen.getByTestId('send-question'));
    await screen.findByText('Ahmedabad: forecast precipitation 0.3 mm.');
    const save = await screen.findByLabelText('Save this conversation as Markdown');
    await userEvent.click(save);
    expect(click).toHaveBeenCalled();
    expect(saved.length ? saved[0].name : '').toMatch(/^weathergpt-conversation-.*\.md$/);
    click.mockRestore();
  });

  it('merges two labels the reader named the same thing', async () => {
    server.use(http.get('/api/conversations', () => HttpResponse.json({
      schema_version: 'conversation-ledger-v1', total: 2, limit: 40,
      conversations: [
        { id: 'm1', updated: new Date().toISOString(), turns: 2, asked: 1, opening_question: 'Rain in Nadiad?',
          place: { label: 'Nadiād, Kheda, State of Gujarāt', latitude: 22.69, longitude: 72.86 } },
        { id: 'm2', updated: new Date().toISOString(), turns: 2, asked: 1, opening_question: 'Rain in Nadiad again?',
          place: { label: 'Nadiad, Gujarat', latitude: 22.69, longitude: 72.86 } },
      ],
    })));
    /* The reader's own name for both labels: one row, both labels kept under it. */
    window.localStorage.setItem('weathergpt.shell', JSON.stringify({
      rail: 'open', panel: false, pins: [],
      aliases: { 'Nadiād, Kheda, State of Gujarāt': 'Nadiad', 'Nadiad, Gujarat': 'Nadiad' },
    }));
    mount();
    const places = await screen.findByRole('region', { name: 'Places this machine knows' });
    const rows = within(places).getAllByRole('button', { name: /Nadiad/ });
    expect(rows).toHaveLength(1);
    /* The row carries both catalogue labels, so a merged row can still say which places it holds. */
    expect(rows[0]).toHaveAttribute('title', expect.stringContaining('Nadiād, Kheda'));
    expect(rows[0]).toHaveAttribute('title', expect.stringContaining('Nadiad, Gujarat'));
    /* And the count is the two conversations, not one. */
    expect(within(places).getByText('2')).toBeInTheDocument();
  });

  it('lands on the turn a search sent the reader to, and marks it', async () => {
    server.use(
      http.get('/api/conversations', () => HttpResponse.json({
        schema_version: 'conversation-ledger-v1', total: 1, limit: 40,
        conversations: [{
          id: 's1', updated: new Date().toISOString(), turns: 4, asked: 2,
          opening_question: 'Any warning for Patna?',
          match: { role: 'user', text: 'what about the coastal districts' },
        }],
      })),
      /* The transcript route's own flat shape, not an envelope: the hook reads \`stored.turns\` off it. */
      http.get('/api/conversations/s1', () => HttpResponse.json({
        schema_version: 'conversation-transcript-v1', id: 's1', updated: new Date().toISOString(),
        turns: [
          { role: 'user', content: 'Any warning for Patna?' },
          { role: 'assistant', content: 'Patna has nothing flagged today.' },
          { role: 'user', content: 'what about the coastal districts' },
          { role: 'assistant', content: 'Kochi and Surat are the two to watch.' },
        ],
        note: null,
      })),
    );
    mount();
    await userEvent.click(screen.getByLabelText('Search conversations'));
    await userEvent.type(screen.getByLabelText('Filter conversations'), 'coastal');
    const row = await screen.findByText('Any warning for Patna?');
    await userEvent.click(row);
    /* The turn that matched is marked, so a reader who arrived from a search can see why they are here. */
    await waitFor(() => expect(document.querySelector('.g-turn.g-found')).not.toBeNull());
    expect(document.querySelector('.g-turn.g-found')?.textContent).toContain('coastal districts');
  });

  it('offers the save on a restored conversation too, which holds no packet of its own', async () => {
    server.use(http.get('/api/conversations', () => HttpResponse.json({
      schema_version: 'conversation-ledger-v1', total: 1, limit: 40,
      conversations: [{ id: 'r1', updated: new Date().toISOString(), turns: 2, asked: 1, opening_question: 'Any warning for Patna?' }],
    })));
    server.use(http.get('/api/conversations/r1', () => HttpResponse.json({
      schema_version: 'conversation-transcript-v1', id: 'r1', updated: new Date().toISOString(),
      turns: [
        { role: 'user', content: 'Any warning for Patna?' },
        { role: 'assistant', content: 'Patna has nothing flagged today.' },
      ],
      note: null,
    })));
    mount();
    await userEvent.click(await screen.findByText('Any warning for Patna?'));
    await waitFor(() => expect(document.querySelector('.g-turn')).not.toBeNull());
    expect(screen.getByLabelText('Save this conversation as Markdown')).toBeInTheDocument();
  });

  it('states what is published for the place, and the hours the model returned', async () => {
    window.localStorage.setItem('weathergpt.place', JSON.stringify({ label: 'Patna, Bihar', latitude: 25.59, longitude: 85.14 }));
    window.localStorage.setItem('weathergpt.shell', JSON.stringify({ rail: 'open', panel: true, pins: [], aliases: {} }));
    server.use(
      http.get('/api/warnings/place', () => HttpResponse.json(envelope({
        district: 'Patna', state: 'Bihar', issued_at_utc: '2026-09-18T12:00:00+00:00',
        days: [
          { date_local: '2026-09-19', label: 'Day 1', colour: 'yellow', hazards: ['Thunderstorm', 'Lightning'] },
          { date_local: '2026-09-20', label: 'Day 2', quiet: true },
        ],
      }))),
      http.get('/api/forecast', () => HttpResponse.json(envelope({
        status: 'ok', source_id: 'S62', model: 'gfs', starts: '2026-09-19T12:30:00+05:30', ends: '2026-09-21T12:30:00+05:30',
        unit: { temperature_2m: '°C', precipitation_probability: '%' },
        rows: [{ at: '2026-09-19T12:30:00+05:30', temperature_2m: 30.6, precipitation_probability: 63 }],
      }))),
    );
    mount();
    const panel = await screen.findByRole('complementary', { name: /how this conversation is read/i });
    /* The district line keeps the district, the issue time and the colours the product itself printed. */
    expect(await within(panel).findByText(/Patna, Bihar · issued 18 Sep 2026, 17:30 IST/)).toBeInTheDocument();
    expect(within(panel).getByText('yellow')).toBeInTheDocument();
    expect(within(panel).getByText('Thunderstorm, Lightning')).toBeInTheDocument();
    /* A quiet day is said as quiet, and not also as a missing hazard line. */
    expect(within(panel).getByText('nothing flagged')).toBeInTheDocument();
    /* The hours keep their unit and their source. */
    expect(within(panel).getByText('30.6°C')).toBeInTheDocument();
    expect(within(panel).getByText(/63% rain chance/)).toBeInTheDocument();
    expect(within(panel).getByText(/S62 · gfs/)).toBeInTheDocument();
  });

  it('says what the panel did not get rather than drawing a zero', async () => {
    window.localStorage.setItem('weathergpt.place', JSON.stringify({ label: 'Patna, Bihar', latitude: 25.59, longitude: 85.14 }));
    window.localStorage.setItem('weathergpt.shell', JSON.stringify({ rail: 'open', panel: true, pins: [], aliases: {} }));
    server.use(
      http.get('/api/warnings/place', () => HttpResponse.json(envelope({ district: 'Patna', state: 'Bihar', days: [] }))),
      http.get('/api/forecast', () => HttpResponse.json({ error: 'the store is unavailable' }, { status: 503 })),
    );
    mount();
    const panel = await screen.findByRole('complementary', { name: /how this conversation is read/i });
    expect(await within(panel).findByText(/published no day for this district, which is not the same as a quiet one/)).toBeInTheDocument();
    expect(within(panel).getByText(/local evidence store is unavailable/i)).toBeInTheDocument();
  });

  it('copies one claim with its place, window and source, and not the whole answer', async () => {
    const written: string[] = [];
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async (text: string) => { written.push(text); } },
    });
    server.use(http.post('/api/chat', () => HttpResponse.json({
      conversation_id: '44444444-4444-4444-8444-444444444444', question: 'Will it rain in Ahmedabad?',
      status: 'answered', answer: 'Ahmedabad: forecast precipitation 0.3 mm.',
      facts: [{ id: 'f1', label: 'Forecast rainfall', value: '0.3', unit: 'mm', place: 'Ahmedabad, Gujarat',
                start: '2026-09-18T06:30:00+05:30', end: '2026-09-18T12:30:00+05:30', source_id: 'S21',
                parameter: 'precipitation', evidence_kind: 'forecast', citation_ids: [], task_id: 't1' }],
      citations: [], notes: [], choices: [], charts: [], task_results: [], answered_at_utc: '2026-09-18T07:00:00+00:00',
      resolved_points: {}, trace: {}, retrieval_plan: [],
    })));
    mount();
    await userEvent.type(screen.getByLabelText('Your question'), 'Will it rain in Ahmedabad?');
    await userEvent.click(screen.getByTestId('send-question'));
    await screen.findByText('Ahmedabad: forecast precipitation 0.3 mm.');
    const copies = screen.getAllByLabelText('Copy this value with its place, window and source');
    await userEvent.click(copies[0]);
    await waitFor(() => expect(written).toHaveLength(1));
    /* The claim's own line, in the atom's order: measure, value with its unit, place, window, source, kind —
       and the measure is named the way the card names it, not the way the payload spells it. */
    expect(written[0]).toMatch(/^Forecast rainfall · 0\.3 mm · Ahmedabad, Gujarat/);
    expect(written[0]).toContain('S21');
    expect(written[0]).not.toContain('Ahmedabad: forecast precipitation 0.3 mm.');
  });

  it('holds a place the address names, and opens the panel on it', async () => {
    server.use(http.get('/api/now', ({ request }) => {
      const url = new URL(request.url);
      carried.push(url.searchParams.get('lat') + ',' + url.searchParams.get('lon'));
      return HttpResponse.json(envelope({ schema_version: 'now-v1',
        point: { latitude: 9.93, longitude: 76.26, label: 'Kochi, Kerala' },
        observed: { status: 'ok', stations: [{ name: 'KOCHI', source_id: 'S63', observed_at_utc: '2026-09-19T06:30:00+00:00',
          parameters: [{ field: 'temp', value: 29, unit: '°C' }] }] } }));
    }));
    /* A link somebody can send: the place is in the address, not only in this browser's storage. */
    window.location.hash = '#/assistant?place=Kochi, Kerala&plat=9.93&plon=76.26';
    /* The harness mounts the shell the way App does: the address is read and handed over. */
    renderAsk();
    const panel = await screen.findByRole('complementary', { name: /how this conversation is read/i });
    expect(await within(panel).findByText('Kochi, Kerala')).toBeInTheDocument();
    expect(carried).toContain('9.93,76.26');
    expect(JSON.parse(String(window.localStorage.getItem('weathergpt.place'))).label).toBe('Kochi, Kerala');
  });

  it('links the panel blocks to the surfaces that own them', async () => {
    window.localStorage.setItem('weathergpt.place', JSON.stringify({ label: 'Patna, Bihar', latitude: 25.59, longitude: 85.14 }));
    window.localStorage.setItem('weathergpt.shell', JSON.stringify({ rail: 'open', panel: true, pins: [], aliases: {} }));
    const opened: string[] = [];
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
    render(
      <QueryClientProvider client={client}>
        <Workspace onOpen={id => opened.push(String(id))} language="" onLanguage={() => {}} persona="" onPersona={() => {}} />
      </QueryClientProvider>,
    );
    const panel = await screen.findByRole('complementary', { name: /how this conversation is read/i });
    /* The glance is a glance: each block says where the full thing lives. */
    await userEvent.click(within(panel).getByRole('button', { name: /Warnings in force/ }));
    await userEvent.click(within(panel).getByRole('button', { name: /forecast surface/ }));
    expect(opened).toEqual(['warnings', 'forecast']);
  });

  it('copies a warning as the product published it, colour and source together', async () => {
    const written: string[] = [];
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async (text: string) => { written.push(text); } } });
    const packet = {
      conversation_id: '44444444-4444-4444-8444-444444444444', question: 'Any warning in force for Patna?',
      status: 'answered', answer: 'Patna is under the orange warning published for Day 2.',
      facts: [{ id: 'w1', label: 'Heavy rain', value: 'Heavy rain', place: 'Patna, Patna, Bihar',
                source_id: 'S15', parameter: 'official_district_warning', evidence_kind: 'warning', citation_ids: [], task_id: 't1' }],
      citations: [{ id: 'c1', source_id: 'S15', product: 'IMD district warning', retrieved_at_utc: '2026-09-19T06:30:00+00:00' }],
      warning_evidence: [{ district_warnings: [{ days: [{ colour: 'orange', hazards: ['Heavy rain'], wording: 'Heavy rain' }] }] }],
      notes: [], choices: [], charts: [], task_results: [], answered_at_utc: '2026-09-19T07:00:00+00:00',
      resolved_points: {}, trace: {}, retrieval_plan: [],
    };
    server.use(http.post('/api/chat', () => HttpResponse.json(packet)));
    mount();
    await userEvent.type(screen.getByLabelText('Your question'), 'Any warning in force for Patna?');
    await userEvent.click(screen.getByTestId('send-question'));
    await screen.findByText('Patna is under the orange warning published for Day 2.');
    const copies = screen.getAllByLabelText('Copy this value with its place, window and source');
    await userEvent.click(copies[copies.length - 1]);
    await waitFor(() => expect(written.length).toBeGreaterThan(0));
    const line = written[written.length - 1];
    /* The colour is the one the bulletin printed, taken from the packet's own day rows — never parsed out of
       the wording — and the line keeps the place and the source beside it. */
    expect(line).toContain('orange');
    expect(line).toContain('Heavy rain');
    expect(line).toContain('Patna');
    expect(line).toContain('source S15');
  });

  it('offers a watch only when the answer named a place and something watchable, and sends the sentence', async () => {
    const asked: string[] = [];
    const packet = {
      conversation_id: '44444444-4444-4444-8444-444444444444', question: 'Any warning in force for Patna?',
      status: 'answered', answer: 'Patna is under the orange warning published for Day 2.',
      facts: [{ id: 'w1', label: 'Heavy rain', value: 'Heavy rain', place: 'Patna, Patna, Bihar',
                source_id: 'S15', parameter: 'official_district_warning', evidence_kind: 'warning', citation_ids: [], task_id: 't1' }],
      citations: [], warning_evidence: [{ district_warnings: [{ days: [{ colour: 'orange', hazards: ['Heavy rain'], wording: 'Heavy rain' }] }] }],
      notes: [], choices: [], quick_replies: [], charts: [], task_results: [], answered_at_utc: '2026-09-19T07:00:00+00:00',
      resolved_points: { patna: { label: 'Patna, Bihar', latitude: 25.59, longitude: 85.14 } }, trace: {}, retrieval_plan: [],
    };
    server.use(http.post('/api/chat', async ({ request }) => {
      asked.push(String((await request.json() as { question?: string }).question));
      return HttpResponse.json(packet);
    }));
    mount();
    await userEvent.type(screen.getByLabelText('Your question'), 'Any warning in force for Patna?');
    await userEvent.click(screen.getByTestId('send-question'));
    await screen.findByText('Patna is under the orange warning published for Day 2.');
    const chip = screen.getByRole('button', { name: /Keep me posted/ });
    /* The chip says what it will ask, and asking it sends exactly that sentence — no watch is created here. */
    expect(chip).toHaveAttribute('title', 'Notify me if a heavy rain warning is issued for Patna, Bihar tomorrow');
    await userEvent.click(chip);
    await waitFor(() => expect(asked).toContain('Notify me if a heavy rain warning is issued for Patna, Bihar tomorrow'));
  });

  it('offers no watch on an answer that named a place but nothing watchable', async () => {
    const packet = {
      conversation_id: '44444444-4444-4444-8444-444444444444', question: 'How much rain fell in 1997?',
      status: 'answered', answer: 'The 1997 record for Ahmedabad is 12 mm in July.',
      facts: [{ id: 'f1', label: 'Rainfall', value: '12', unit: 'mm', place: 'Ahmedabad, Gujarat', source_id: 'S27',
                parameter: 'rainfall', evidence_kind: 'history', citation_ids: [], task_id: 't1' }],
      citations: [], notes: [], choices: [], quick_replies: [], charts: [], task_results: [],
      answered_at_utc: '2026-09-19T07:00:00+00:00',
      resolved_points: { ahmedabad: { label: 'Ahmedabad, Gujarat', latitude: 23.02, longitude: 72.57 } }, trace: {}, retrieval_plan: [],
    };
    server.use(http.post('/api/chat', () => HttpResponse.json(packet)));
    mount();
    await userEvent.type(screen.getByLabelText('Your question'), 'How much rain fell in 1997?');
    await userEvent.click(screen.getByTestId('send-question'));
    await screen.findByText('The 1997 record for Ahmedabad is 12 mm in July.');
    /* A record is not watchable: there is nothing to be notified about. */
    expect(screen.queryByRole('button', { name: /Keep me posted/ })).toBeNull();
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
