/* Turn parity: the client checks tests/test_conversation_ui.js makes, held against the React surface. The
   LEDGER and FORECAST payloads are copied verbatim from that suite; the cancel reply is its recorded stub
   response. The workspace-token rule comes from tests/test_suite_ui.js ("every surface request carries the
   workspace token"), which the parent asked to keep with these turn checks. The real surface runs against
   MSW, and the shared harness supplies the reads every mount performs. */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { renderAsk } from '../test/ask';


const FORECAST = {
  schema_version: 'weather-conversation-v1', conversation_id: '44444444-4444-4444-8444-444444444444',
  question: 'Will it rain in Ahmedabad?', status: 'answered',
  answer: 'Ahmedabad: forecast precipitation 0.3 mm.',
  facts: [{ id: 't1-f1', label: 'Forecast rainfall', value: '0.3', unit: 'mm', place: 'Ahmedabad, Ahmad\u0101b\u0101d, State of Gujar\u0101t',
    start: '2026-09-15T06:30:00+05:30', end: '2026-09-15T12:30:00+05:30', source_id: 'S21', parameter: 'precipitation',
    entity_id: 'geonames:1279233', evidence_version: 'a'.repeat(64),
    citation_ids: ['t1-c1'], task_id: 't1' }],
  citations: [{ id: 't1-c1', source_id: 'S21', provider: 'Open-Meteo', product: 'GFS forecast delivery',
    url: 'https://api.open-meteo.com/v1/forecast', retrieved_at_utc: '2026-09-14T10:39:00+00:00' }],
  notes: [], choices: [],
  charts: [], calculations: [], task_results: [], follow_up: null, answered_at_utc: '2026-09-14T10:47:00+00:00',
  expires_at_utc: '2026-09-14T11:47:00+00:00', operational_eligible: false, trace: {}, retrieval_plan: [],
  resolved_points: { Ahmedabad: { selection_id: 'geonames:1279233', label: 'Ahmedabad, Gujar\u0101t', coordinates: { latitude: 23.02579, longitude: 72.58727 } } },
};

/* The vanilla stub's own reply to a stop request (tests/test_conversation_ui.js, check 7). */
const CANCEL_REPLY = {
  state: 'cancel_requested', stage: 'planned',
  detail: 'The server was asked to stop this turn at the next stage boundary; anything already retrieved for it is discarded.',
};

const PREVIEW = {
  schema_version: 'chat-preview-v1',
  provisional: true,
  note: 'A first reading by the deterministic rules planner, before any retrieval.',
  reading: { line: 'place: Ahmedabad \u00b7 window: 15 Sep 2026 12:00-18:00 IST \u00b7 asking about: rain \u00b7 will read: a point forecast' },
};

const WORKING = {
  schema_version: 'chat-progress-v1',
  state: 'working',
  stage: 'retrieving',
  stage_label: 'Retrieving evidence',
  stages_seen: ['started', 'planned', 'resolving', 'retrieving'],
  queue: { waiting: 0, active: 1, capacity: 3, wait_seconds_before_refusal: 45 },
};

/* The reads every mount performs, so a suite declares only what it is testing. Each records the workspace
   token it received, because every surface request must carry it. */
function reads(seen?: (string | null)[]) {
  return [
    http.post('/api/chat/preview', ({ request }) => {
      seen?.push(request.headers.get('X-WeatherGPT-Token'));
      return HttpResponse.json(PREVIEW);
    }),
    http.get('/api/chat/progress', ({ request }) => {
      seen?.push(request.headers.get('X-WeatherGPT-Token'));
      return HttpResponse.json(WORKING);
    }),
    http.get('/api/conversations', ({ request }) => {
      seen?.push(request.headers.get('X-WeatherGPT-Token'));
      return HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [], note: 'stored locally' });
    }),
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

describe('the turn, held against the vanilla client checks', () => {
  afterEach(() => {
    document.querySelector('meta[name="workspace-token"]')?.remove();
  });

  it('sends one question with only the request keys the engine accepts', async () => {
    const bodies: Record<string, unknown>[] = [];
    server.use(
      http.post('/api/chat', async ({ request }) => {
        bodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(FORECAST);
      }),
      ...reads(),
    );
    renderAsk({ language: "en" });
    expect(screen.getByTestId('welcome')).toBeInTheDocument();
    await ask('Will it rain in Ahmedabad?');
    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(Object.keys(bodies[0]).sort()).toEqual(['output_language', 'question', 'request_id']);
    expect(String(bodies[0].request_id)).toMatch(/^[0-9a-f-]{36}$/);
    expect(bodies[0].question).toBe('Will it rain in Ahmedabad?');
    expect(bodies[0].output_language).toBe('en');
    expect(screen.queryByTestId('welcome')).toBeNull();
    expect(await screen.findByText('Ahmedabad: forecast precipitation 0.3 mm.')).toBeInTheDocument();
  });

  it('keeps the conversation id on a follow-up and never sends the rejected entity_id key', async () => {
    const bodies: Record<string, unknown>[] = [];
    server.use(
      http.post('/api/chat', async ({ request }) => {
        bodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(FORECAST);
      }),
      ...reads(),
    );
    renderAsk();
    const user = await ask('Will it rain in Ahmedabad?');
    await screen.findByText('Ahmedabad: forecast precipitation 0.3 mm.');
    const box = screen.getByLabelText('Your question');
    await user.clear(box);
    await user.type(box, 'And in the afternoon?');
    await user.click(screen.getByTestId('send-question'));
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[0].conversation_id).toBeUndefined();
    expect(bodies[1].conversation_id).toBe(FORECAST.conversation_id);
    expect(bodies.every(body => !('entity_id' in body))).toBe(true);
  });

  it('carries the workspace token on every request the surface makes', async () => {
    const seen: (string | null)[] = [];
    document.head.insertAdjacentHTML('beforeend', '<meta name="workspace-token" content="test-token">');
    server.use(
      http.post('/api/chat', ({ request }) => {
        seen.push(request.headers.get('X-WeatherGPT-Token'));
        return HttpResponse.json(FORECAST);
      }),
      ...reads(seen),
    );
    renderAsk();
    await ask('Will it rain in Ahmedabad?');
    await screen.findByText('Ahmedabad: forecast precipitation 0.3 mm.');
    expect(seen.length).toBeGreaterThan(0);
    expect(seen.every(token => token === 'test-token')).toBe(true);
  });

  it('asks the server to cancel the turn in flight and reports its own reply', async () => {
    const chatBodies: Record<string, unknown>[] = [];
    const cancelBodies: Record<string, unknown>[] = [];
    server.use(
      http.post('/api/chat/cancel', async ({ request }) => {
        cancelBodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json({ request_id: String(cancelBodies[0]?.request_id || ''), ...CANCEL_REPLY });
      }),
      http.post('/api/chat', async ({ request }) => {
        chatBodies.push((await request.json()) as Record<string, unknown>);
        await new Promise(resolve => setTimeout(resolve, 1200));
        return HttpResponse.json(FORECAST);
      }),
      ...reads(),
    );
    renderAsk();
    await ask('Will it rain in Porbandar?');
    await userEvent.click(await screen.findByTestId('stop-turn'));
    await waitFor(() => expect(cancelBodies).toHaveLength(1));
    expect(cancelBodies[0].request_id).toBe(chatBodies[0].request_id);
    expect(await screen.findByText(/discarded/)).toBeInTheDocument();
  });

  it('reports a full queue as a bounded queue rather than a generic failure', async () => {
    server.use(
      http.post('/api/chat', () =>
        HttpResponse.json({ error: 'The assistant is already answering its maximum number of waiting questions. Try again shortly.' }, { status: 429 })),
      ...reads(),
    );
    renderAsk();
    await ask('Will it rain in Surat?');
    expect(await screen.findByText(/maximum number of waiting questions/)).toBeInTheDocument();
    expect(screen.queryByRole('article')).toBeNull();
  });

  it('asks for a reload when the workspace token is no longer held', async () => {
    server.use(
      http.post('/api/chat', () =>
        HttpResponse.json({ error: 'Reload this local workspace before sending a request' }, { status: 403 })),
      ...reads(),
    );
    renderAsk();
    await ask('Will it rain?');
    expect(await screen.findByText('Reload this local workspace before sending a request')).toBeInTheDocument();
  });

  it('names the local evidence store when that store is unavailable', async () => {
    server.use(
      http.post('/api/chat', () =>
        HttpResponse.json({ error: 'The local evidence store is unavailable.' }, { status: 503 })),
      ...reads(),
    );
    renderAsk();
    await ask('Will it rain?');
    expect(await screen.findByText('The local evidence store is unavailable.')).toBeInTheDocument();
    expect(screen.queryByText(/Reload this local workspace/)).toBeNull();
  });

  it('returns a refused question to the box and sends it again when the reader asks', async () => {
    const bodies: Record<string, unknown>[] = [];
    let calls = 0;
    server.use(
      http.post('/api/chat', async ({ request }) => {
        bodies.push((await request.json()) as Record<string, unknown>);
        calls += 1;
        if (calls === 1) return HttpResponse.json({ error: 'The local evidence store is unavailable.' }, { status: 503 });
        return HttpResponse.json(FORECAST);
      }),
      ...reads(),
    );
    renderAsk();
    await ask('Will it rain?');
    expect(await screen.findByText('The local evidence store is unavailable.')).toBeInTheDocument();
    expect(screen.getByLabelText('Your question')).toHaveValue('Will it rain?');
    await userEvent.click(screen.getByTestId('send-question'));
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[1].question).toBe('Will it rain?');
    expect(await screen.findByText('Ahmedabad: forecast precipitation 0.3 mm.')).toBeInTheDocument();
  });

  it('starts a new conversation without sending a question and forgets the identifier', async () => {
    const bodies: Record<string, unknown>[] = [];
    server.use(
      http.post('/api/chat', async ({ request }) => {
        bodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(FORECAST);
      }),
      ...reads(),
    );
    renderAsk();
    const user = await ask('Will it rain in Ahmedabad?');
    await screen.findByText('Ahmedabad: forecast precipitation 0.3 mm.');
    await user.click(screen.getByRole('button', { name: /New conversation/ }));
    expect(await screen.findByTestId('welcome')).toBeInTheDocument();
    expect(bodies).toHaveLength(1);
    await user.type(screen.getByLabelText('Your question'), 'Is it raining now?');
    await user.click(screen.getByTestId('send-question'));
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[1].conversation_id).toBeUndefined();
  });

});
