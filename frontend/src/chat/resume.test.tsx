/* A turn that outlived the page.
   ============================================================================
   A dropped connection lost the turn: the server held the answer and the page held the request id, and
   no route traded one for the other. GET /api/chat/result?request_id= is that trade, and it answers with
   one of the workspace's own states — pending, ready, cancelled, expired, unknown — never an empty
   success. These pin what a reload does with each of them. */

import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { renderAsk } from '../test/ask';
import { INFLIGHT_KEY } from './model';
import { server } from '../test/msw';

const PACKET = {
  schema_version: 'weather-conversation-v1',
  conversation_id: '44444444-4444-4444-8444-444444444444',
  question: 'Will it rain in Ahmedabad?',
  status: 'answered',
  answer: 'THE TURN THAT OUTLIVED THE PAGE.',
  facts: [], citations: [], notes: [], choices: [], charts: [], calculations: [], task_results: [],
  answered_at_utc: '2026-09-14T10:47:00+00:00', trace: {}, retrieval_plan: [], resolved_points: {},
};

const REQUEST_ID = '11111111-1111-4111-8111-111111111111';

function storeInflight(question = 'Will it rain in Ahmedabad?') {
  window.sessionStorage.setItem(INFLIGHT_KEY, JSON.stringify({
    request_id: REQUEST_ID, question, at: '2026-09-14T10:40:00+00:00', conversation_id: null,
  }));
}

function resultRoute(states: Record<string, unknown>[]) {
  let call = 0;
  return http.get('/api/chat/result', () => {
    const state = states[Math.min(call, states.length - 1)];
    call += 1;
    return HttpResponse.json(state);
  });
}

describe('a reload in the middle of a turn', () => {
  beforeEach(() => {
    try { window.sessionStorage.clear(); } catch { /* storage is optional */ }
  });
  afterEach(() => {
    try { window.sessionStorage.clear(); } catch { /* storage is optional */ }
  });

  it('lands the answer the workspace still holds for that turn', async () => {
    storeInflight();
    const asked: string[] = [];
    server.use(
      http.get('/api/chat/progress', () => HttpResponse.json({ schema_version: 'chat-progress-v1', state: 'idle', stage: null, stages_seen: [], queue: { waiting: 0, active: 0, capacity: 3, wait_seconds_before_refusal: 45 } })),
      http.get('/api/chat/result', ({ request }) => {
        asked.push(String(new URL(request.url).searchParams.get('request_id')));
        return HttpResponse.json({ schema_version: 'chat-result-v1', request_id: REQUEST_ID, state: 'ready', detail: 'finished', packet: PACKET });
      }),
      http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] })),
    );
    renderAsk();
    /* The question the page had been waiting on is shown again, and the answer the server held lands. */
    expect(await screen.findByText('THE TURN THAT OUTLIVED THE PAGE.')).toBeInTheDocument();
    expect(document.querySelectorAll('.g-you').length).toBe(1);
    expect(asked[0]).toBe(REQUEST_ID);
    /* The pointer is spent: a second reload has nothing to collect. */
    expect(window.sessionStorage.getItem(INFLIGHT_KEY)).toBeNull();
  });

  it('waits for a turn that is still running, showing its own stage', async () => {
    storeInflight();
    let reads = 0;
    server.use(
      http.get('/api/chat/result', () => {
        reads += 1;
        if (reads <= 2) return HttpResponse.json({ schema_version: 'chat-result-v1', request_id: REQUEST_ID, state: 'pending', detail: 'This turn has been accepted and has not finished.' });
        return HttpResponse.json({ schema_version: 'chat-result-v1', request_id: REQUEST_ID, state: 'ready', detail: 'finished', packet: PACKET });
      }),
      http.get('/api/chat/progress', () => HttpResponse.json({
        schema_version: 'chat-progress-v1', request_id: REQUEST_ID, state: 'running', stage: 'retrieving', stage_label: 'Retrieving evidence',
        stages_seen: ['started', 'retrieving'], queue: { waiting: 0, active: 1, capacity: 3, wait_seconds_before_refusal: 45 },
        stage_note: 'A stage names the work the server is in now.', stages_are_facts_not_progress: true,
      })),
      http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] })),
    );
    renderAsk();
    await screen.findByTestId('working-turn');
    expect(document.querySelector('.g-working-stage')).toHaveTextContent(/Retrieving evidence/);
    expect(await screen.findByText('THE TURN THAT OUTLIVED THE PAGE.', {}, { timeout: 6000 })).toBeInTheDocument();
  });

  it('shows the stopped turn the workspace kept rather than an empty success', async () => {
    storeInflight();
    server.use(
      resultRoute([{ schema_version: 'chat-result-v1', request_id: REQUEST_ID, state: 'cancelled', detail: 'stopped at the reader\'s request', packet: { ...PACKET, status: 'cancelled', answer: 'You stopped waiting for this turn.' } }]),
      http.get('/api/chat/progress', () => HttpResponse.json({ schema_version: 'chat-progress-v1', state: 'idle', stage: null, stages_seen: [], queue: { waiting: 0, active: 0, capacity: 3, wait_seconds_before_refusal: 45 } })),
      http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] })),
    );
    renderAsk();
    expect(await screen.findByText(/You stopped waiting for this turn/)).toBeInTheDocument();
    expect(screen.getByText('Stopped')).toBeInTheDocument();
  });

  it('claims nothing about a turn the workspace never had, and nothing about a read that failed', async () => {
    storeInflight();
    server.use(
      resultRoute([{ schema_version: 'chat-result-v1', request_id: REQUEST_ID, state: 'unknown', detail: 'This workspace has no turn with this identifier.' }]),
      http.get('/api/chat/progress', () => HttpResponse.json({ schema_version: 'chat-progress-v1', state: 'idle', stage: null, stages_seen: [], queue: { waiting: 0, active: 0, capacity: 3, wait_seconds_before_refusal: 45 } })),
      http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] })),
    );
    renderAsk();
    /* Nothing is put on screen: no question, no notice, no working box — the pointer was not evidence. */
    await waitFor(() => expect(screen.getByTestId('send-question')).toBeInTheDocument());
    expect(document.querySelector('.g-you')).toBeNull();
    expect(screen.queryByTestId('working-turn')).toBeNull();
    await waitFor(() => expect(window.sessionStorage.getItem(INFLIGHT_KEY)).toBeNull());
  });

  it('leaves the workspace a question rather than an error when it does not answer the read', async () => {
    storeInflight();
    server.use(
      http.get('/api/chat/result', () => HttpResponse.json({ error: 'The local evidence store is unavailable.' }, { status: 503 })),
      http.get('/api/chat/progress', () => HttpResponse.json({ schema_version: 'chat-progress-v1', state: 'idle', stage: null, stages_seen: [], queue: { waiting: 0, active: 0, capacity: 3, wait_seconds_before_refusal: 45 } })),
      http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] })),
    );
    renderAsk();
    await waitFor(() => expect(screen.getByTestId('send-question')).toBeInTheDocument());
    expect(screen.queryByText(/unavailable/)).toBeNull();
    expect(document.querySelector('.g-you')).toBeNull();
    await waitFor(() => expect(window.sessionStorage.getItem(INFLIGHT_KEY)).toBeNull());
  });

  it('does nothing at all when this tab has no turn in flight', async () => {
    const reads: string[] = [];
    server.use(
      http.get('/api/chat/result', ({ request }) => {
        reads.push(String(new URL(request.url).searchParams.get('request_id')));
        return HttpResponse.json({ schema_version: 'chat-result-v1', request_id: 'x', state: 'unknown', detail: 'no' });
      }),
      http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] })),
    );
    renderAsk();
    await new Promise(resolve => setTimeout(resolve, 60));
    expect(reads).toEqual([]);
  });
});
