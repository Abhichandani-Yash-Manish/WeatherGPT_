/* The transcript's own checks. The payloads are the ones the vanilla component suite recorded, reused
   verbatim, so each check keeps testing the same rule it tested before the port. */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { renderAsk } from '../test/ask';
import { readRegister, REGISTER_KEY, type Register } from './model';
import { isSpeakable, writableLanguages } from './voice';
import { server } from '../test/msw';

const FORECAST = {
  schema_version: 'weather-conversation-v1',
  conversation_id: '44444444-4444-4444-8444-444444444444',
  question: 'Will it rain in Ahmedabad?',
  status: 'answered',
  answer: 'Ahmedabad: forecast precipitation 0.3 mm.',
  facts: [{
    id: 't1-f1', label: 'Forecast rainfall', value: '0.3', unit: 'mm',
    place: 'Ahmedabad, Ahmadabad, State of Gujarat',
    start: '2026-09-15T06:30:00+05:30', end: '2026-09-15T12:30:00+05:30',
    source_id: 'S21', parameter: 'precipitation', entity_id: 'geonames:1279233',
    evidence_kind: 'forecast', evidence_version: 'a'.repeat(64), citation_ids: ['t1-c1'], task_id: 't1',
  }],
  citations: [{ id: 't1-c1', source_id: 'S21', provider: 'Open-Meteo', product: 'GFS forecast delivery',
                url: 'https://api.open-meteo.com/v1/forecast', retrieved_at_utc: '2026-09-14T10:39:00+00:00' }],
  notes: [], choices: [], charts: [], calculations: [], task_results: [], follow_up: null,
  answered_at_utc: '2026-09-14T10:47:00+00:00', expires_at_utc: '2026-09-14T11:47:00+00:00',
  operational_eligible: false,
  trace: { planning: { planner_policy: 'model', provider: 'DeepSeek' }, generation: { provider: 'DeepSeek' }, tools: [{ name: 'point_forecast' }], duration_seconds: 5.9 },
  retrieval_plan: [], task_coverage: { requested: 1, completed: 1, incomplete_ids: [] },
  resolved_points: { Ahmedabad: { selection_id: 'geonames:1279233', label: 'Ahmedabad, Gujarat', coordinates: { latitude: 23.02579, longitude: 72.58727 } } },
};

type ChatOptions = {
  preview?: unknown;
  progress?: unknown;
  onCancel?: (body: unknown) => void;
  /** How long the answer takes, so a test can look at the working state while it is still working. */
  answerAfterMs?: number;
  /** A refusal the engine can actually produce, to check the sentence a reader is shown. */
  refusal?: { status: number; error: string };
};

const PREVIEW = {
  schema_version: 'chat-preview-v1',
  provisional: true,
  note: 'A first reading by the deterministic rules planner, before any retrieval.',
  reading: { line: 'place: Ahmedabad · window: 15 Sep 2026 12:00-18:00 IST · asking about: rain · will read: a point forecast' },
};

const PROGRESS = {
  schema_version: 'chat-progress-v1',
  state: 'working',
  stage: 'retrieving',
  stage_label: 'Retrieving evidence',
  stages_seen: ['started', 'planned', 'resolving', 'retrieving'],
  queue: { waiting: 0, active: 1, capacity: 3, wait_seconds_before_refusal: 45 },
  stage_note: 'A stage names the work the server is in now. It is not a completion estimate.',
};

function handlers(packet: Record<string, unknown>, options: ChatOptions = {}) {
  return [
    http.post('/api/chat/preview', () => HttpResponse.json(options.preview ?? PREVIEW)),
    http.get('/api/chat/progress', () => HttpResponse.json(options.progress ?? PROGRESS)),
    http.post('/api/chat/cancel', async ({ request }) => {
      options.onCancel?.(await request.json());
      return HttpResponse.json({ request_id: 'x', state: 'cancel_requested', stage: 'retrieving', stage_label: 'Retrieving evidence', detail: 'The server was asked to stop this turn at the next stage boundary.' });
    }),
    http.post('/api/chat', async () => {
      if (options.answerAfterMs) await new Promise(resolve => setTimeout(resolve, options.answerAfterMs));
      if (options.refusal) return HttpResponse.json({ error: options.refusal.error }, { status: options.refusal.status });
      return HttpResponse.json(packet);
    }),
    http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 1, limit: 40, conversations: [], note: 'stored locally' })),
  ];
}

async function ask(text: string) {
  const user = userEvent.setup();
  const box = screen.getByLabelText('Your question');
  await user.clear(box);
  await user.type(box, text);
  await user.click(screen.getByTestId('send-question'));
  return user;
}

describe('the transcript', () => {
  afterEach(() => {
    try { window.localStorage.removeItem(REGISTER_KEY); } catch { /* storage is optional */ }
  });

  it('renders a retrieved answer with its value, its source and its window', async () => {
    server.use(...handlers(FORECAST));
    renderAsk();
    await ask('Will it rain in Ahmedabad?');
    /* Twice, by design: the bar names the thread and the transcript holds the question. */
    expect((await screen.findAllByText('Will it rain in Ahmedabad?')).length).toBeGreaterThan(0);
    const card = await screen.findByRole('article');
    expect(within(card).getByText('Forecast rainfall')).toBeInTheDocument();
    expect(within(card).getByText('0.3')).toBeInTheDocument();
    expect(within(card).getByText('Evidence receipt')).toBeInTheDocument();
    expect(within(card).getAllByText(/S21/).length).toBeGreaterThan(0);
    expect(within(card).getByText(/Retrieved/)).toBeInTheDocument();
  });

  it('marks a conversational reply as having read no source and shows no fact table', async () => {
    server.use(...handlers({ ...FORECAST, status: 'conversation', answer_basis: 'conversation', facts: [], citations: [], answer: 'Hello. Ask me about a place and a time.' }));
    renderAsk();
    await ask('hello');
    const card = await screen.findByRole('article');
    expect(within(card).getByText('No source read')).toBeInTheDocument();
    expect(within(card).queryByText('Evidence receipt')).toBeNull();
  });

  it('lets the browser read the direction of the answer sentence', async () => {
    server.use(...handlers({ ...FORECAST, answer: 'احمد آباد میں بارش متوقع ہے۔' }));
    renderAsk({ language: "ur" });
    await ask('کیا بارش ہوگی؟');
    const paragraph = await screen.findByText('احمد آباد میں بارش متوقع ہے۔');
    expect(paragraph).toHaveAttribute('dir', 'auto');
  });

  it('names what a continuation carried and what it changed', async () => {
    server.use(
      ...handlers({
        ...FORECAST,
        trace: { ...FORECAST.trace, context_resolution: { action: 'revise', inherited_fields: ['place', 'window'], changed_fields: ['measure'] } },
      }),
    );
    renderAsk();
    await ask('and what about the evening?');
    const carried = await screen.findByTestId('carried-context');
    expect(carried).toHaveTextContent('Carried from the previous turn: place, window');
    expect(carried).toHaveTextContent('changed here: measure');
  });

  it('sets a held answer apart from a retrieved one', async () => {
    server.use(...handlers({ ...FORECAST, status: 'unavailable', facts: [], citations: [], answer: 'I could not retrieve a usable forecast for that window.' }));
    renderAsk();
    await ask('Will it rain in Surat tomorrow?');
    const tag = await screen.findByText('Evidence gap');
    expect(tag.className).toMatch(/tag-held/);
  });

  it('states the language downgrade in words rather than passing as answered', async () => {
    server.use(...handlers({ ...FORECAST, notes: ['The output language could not be rendered, so the answer is in English.'] }));
    renderAsk({ language: "hi" });
    await ask('बारिश होगी?');
    expect(await screen.findByText(/not in the language you asked for/)).toBeInTheDocument();
  });

  it('states a rendering that did not survive the values intact, not only the unreachable service', async () => {
    /* Measured 18 September 2026: a Kannada question was answered in English with the engine's own sentence
       "This answer was not rewritten in the requested language because some of its values did not survive the
       rendering intact", and the card looked only for "output language could not be rendered", so the reader
       was handed a source-language answer with no warning. The structured state is what the card now reads. */
    const downgraded = {
      ...FORECAST,
      status: 'partial',
      notes: ['This answer was not rewritten in the requested language because some of its values did not survive the rendering intact. Showing a partly rewritten answer could change what a number or a warning means, so the source-language answer is kept instead.'],
      trace: { ...FORECAST.trace, generation: { provider: 'typed_task_renderers', requested_language: 'kn', language_selection: 'user_selected', language_adherence: 'values_did_not_survive' } },
    };
    server.use(...handlers(downgraded));
    renderAsk({ language: "kn" });
    await ask('ಬೆಂಗಳೂರಿನಲ್ಲಿ ಈಗ ಮಳೆ ಬರುತ್ತಿದೆಯೇ?');
    expect(await screen.findByText(/not in the language you asked for/)).toBeInTheDocument();
    /* The sentence appears on the downgrade card and again in the notes list; one copy is enough to
       prove the reader is warned, and the card is the one that matters. */
    expect((await screen.findAllByText(/did not survive the rendering intact/)).length).toBeGreaterThan(0);
  });

  it('draws an uncovered part of the window as a gap and says so', async () => {
    const gapped = {
      ...FORECAST,
      facts: [
        { ...FORECAST.facts[0], id: 't1-f1', start: '2026-09-15T06:30:00+05:30', end: '2026-09-15T08:30:00+05:30' },
        { ...FORECAST.facts[0], id: 't1-f2', start: '2026-09-15T14:30:00+05:30', end: '2026-09-15T16:30:00+05:30' },
      ],
    };
    server.use(...handlers(gapped));
    renderAsk();
    await ask('Will it rain in Ahmedabad?');
    const hits = await screen.findAllByRole('button', { name: /No retrieved evidence/ });
    expect(hits.length).toBeGreaterThan(0);
    expect(hits[0].getAttribute('aria-label')).toMatch(/never interpolated/);
  });

  it('shows the first reading and the stages while a turn works, and stops on request', async () => {
    const cancelled: unknown[] = [];
    server.use(...handlers(FORECAST, { onCancel: body => cancelled.push(body), answerAfterMs: 900 }));
    renderAsk();
    await ask('Will it rain in Ahmedabad?');
    expect(await screen.findByTestId('working-turn')).toBeInTheDocument();
    expect(await screen.findByTestId('reading-line')).toHaveTextContent(/place: Ahmedabad/);
    expect(await screen.findByText('Resolving the place')).toBeInTheDocument();
    /* The wait states the stage it is on, once, in the line a reader is looking at. It used to print five
       paragraphs of pipeline, planner and queue detail here; those are still reached, but from a fold, so
       waiting for an answer about rain is not also a briefing on the retrieval architecture. */
    expect(document.querySelector('.g-working-stage')).toHaveTextContent(/Retrieving evidence/);
    expect(screen.getByText('Resolving the place').closest('details'), 'the machinery belongs behind a fold').not.toBeNull();
    expect(screen.getByTestId('reading-line').closest('details'), 'the first reading is available, not imposed').not.toBeNull();
    await userEvent.click(screen.getByTestId('stop-turn'));
    await waitFor(() => expect(cancelled.length).toBe(1));
    expect(await screen.findByText(/stop this turn at the next stage boundary/)).toBeInTheDocument();
  });

  it('returns the question to the box and states the server message when a turn fails', async () => {
    server.use(...handlers(FORECAST, { refusal: { status: 503, error: 'The assistant is busy longer than the queue allows. Try again shortly.' } }));
    renderAsk();
    await ask('Will it rain in Ahmedabad?');
    expect(await screen.findByText(/busy longer than the queue allows/)).toBeInTheDocument();
    expect(screen.getByLabelText('Your question')).toHaveValue('Will it rain in Ahmedabad?');
  });

  it('keeps the receipt and the machine record reachable as depth under the answer', async () => {
    server.use(...handlers(FORECAST));
    renderAsk();
    await ask('Will it rain in Ahmedabad?');
    await screen.findByText('Evidence receipt');
    expect(screen.getByText('where this came from')).toBeInTheDocument();
    expect(await screen.findByText(/Machine record/)).toBeInTheDocument();
  });

  it('falls back to the conversational register when the stored value is unreadable', () => {
    const stored: Record<string, string> = { [REGISTER_KEY]: 'detailed' };
    const original = window.localStorage;
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: { getItem: (key: string) => (key in stored ? stored[key] : null), setItem: (key: string, value: string) => { stored[key] = String(value); } },
    });
    expect(readRegister()).toBe('conversational');
    stored[REGISTER_KEY] = 'full';
    expect(readRegister()).toBe('full');
    expect(readRegister() as Register).toBe('full');
    Object.defineProperty(window, 'localStorage', { configurable: true, value: original });
  });
});

describe('voice language rules', () => {
  const LANGUAGES = {
    schema_version: 'language-support-view-v1',
    service_configured: true,
    languages: [
      { code: 'en', english_name: 'English', native_name: 'English', measured: { write: 'verified', speak: 'verified' } },
      { code: 'hi', english_name: 'Hindi', native_name: 'हिन्दी', measured: { write: 'verified', speak: 'verified' } },
      { code: 'gu', english_name: 'Gujarati', native_name: 'ગુજરાતી', measured: { write: 'verified', speak: 'unmeasured' } },
      { code: 'ta', english_name: 'Tamil', native_name: 'தமிழ்', measured: { write: 'failed', speak: 'unmeasured' } },
    ],
  };

  it('offers only the languages whose writing this project measured, sorted by name', () => {
    const offered = writableLanguages(LANGUAGES);
    expect(offered.map(entry => entry.code)).toEqual(['en', 'gu', 'hi']);
  });

  it('does not treat a written language as speakable unless speech was verified', () => {
    const gujarati = LANGUAGES.languages.find(entry => entry.code === 'gu');
    const hindi = LANGUAGES.languages.find(entry => entry.code === 'hi');
    expect(isSpeakable(gujarati)).toBe(false);
    expect(isSpeakable(hindi)).toBe(true);
  });
});
