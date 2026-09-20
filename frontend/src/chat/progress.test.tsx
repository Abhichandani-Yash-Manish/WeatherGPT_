/* A turn reads only its own progress.
   ============================================================================
   The progress route answered with whatever turn the workspace had started last and the client sent no
   identifier, so two pages waiting on two turns were each told the other one's stage. The client now
   mints the request id, sends it with the question, and sends the same one with every progress read of
   that turn. These pin the identifier on the wire and the turn's own stage on screen. */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { renderAsk } from '../test/ask';
import { server } from '../test/msw';

const PACKET = {
  schema_version: 'weather-conversation-v1',
  conversation_id: '44444444-4444-4444-8444-444444444444',
  question: 'Will it rain in Ahmedabad?',
  status: 'answered',
  answer: 'Ahmedabad: forecast precipitation 0.3 mm.',
  facts: [], citations: [], notes: [], choices: [], charts: [], calculations: [], task_results: [],
  answered_at_utc: '2026-09-14T10:47:00+00:00', trace: {}, retrieval_plan: [], resolved_points: {},
};

const PROGRESS = {
  schema_version: 'chat-progress-v1',
  state: 'running',
  stage: 'retrieving',
  stage_label: 'Retrieving evidence',
  stages_seen: ['started', 'planned', 'resolving', 'retrieving'],
  queue: { waiting: 0, active: 1, capacity: 3, wait_seconds_before_refusal: 45 },
  stage_note: 'A stage names the work the server is in now. It is not a completion estimate.',
  stages_are_facts_not_progress: true,
};

function askBox() {
  return document.getElementById('question') as HTMLTextAreaElement;
}

describe('the progress of one turn', () => {
  afterEach(() => {
    try { window.sessionStorage.clear(); } catch { /* storage is optional */ }
  });

  it('sends the identifier of the turn it is reading', async () => {
    const asked: (string | null)[] = [];
    const polled: (string | null)[] = [];
    server.use(
      http.post('/api/chat/preview', () => HttpResponse.json({ schema_version: 'chat-preview-v1', provisional: true, reading: null })),
      http.get('/api/chat/progress', ({ request }) => {
        polled.push(new URL(request.url).searchParams.get('request_id'));
        return HttpResponse.json(PROGRESS);
      }),
      http.post('/api/chat', async ({ request }) => {
        const body = (await request.json()) as { request_id?: string };
        asked.push(body.request_id || null);
        await new Promise(resolve => setTimeout(resolve, 120));
        return HttpResponse.json(PACKET);
      }),
      http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] })),
    );
    renderAsk();
    const user = userEvent.setup();
    await user.type(askBox(), 'Will it rain in Ahmedabad?');
    await user.click(screen.getByTestId('send-question'));
    await waitFor(() => expect(polled.length).toBeGreaterThan(0));
    expect(asked).toHaveLength(1);
    expect(asked[0], 'the client mints the turn identifier').toBeTruthy();
    /* Every read of this turn names that same turn. Without the identifier the read answered with the
       workspace's newest turn, which is what two pages waiting at once used to see. */
    polled.forEach(id => expect(id).toBe(asked[0]));
    expect(await screen.findByRole('article')).toBeInTheDocument();
  });

  it('shows the stage of the turn it is reading, not an estimate of it', async () => {
    server.use(
      http.post('/api/chat/preview', () => HttpResponse.json({ schema_version: 'chat-preview-v1', provisional: true, reading: null })),
      http.get('/api/chat/progress', () => HttpResponse.json({
        ...PROGRESS,
        state: 'queued',
        stage: null,
        stage_label: null,
        stages_seen: [],
        stage_note: 'This turn has been accepted and is waiting for the workspace to start it.',
      })),
      http.post('/api/chat', async () => {
        await new Promise(resolve => setTimeout(resolve, 300));
        return HttpResponse.json(PACKET);
      }),
      http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] })),
    );
    renderAsk();
    const user = userEvent.setup();
    await user.type(askBox(), 'Will it rain in Ahmedabad?');
    await user.click(screen.getByTestId('send-question'));
    await screen.findByTestId('working-turn');
    /* The server's own sentence for a queued turn, and no percentage or ETA beside it. */
    expect(await screen.findByText(/waiting for the workspace to start it/)).toBeInTheDocument();
    const working = screen.getByTestId('working-turn');
    expect(working.textContent || '').not.toMatch(/%|ETA/i);
  });

  it('reads each of two turns separately, so the second never borrows the first', async () => {
    const polled: (string | null)[] = [];
    const asked: string[] = [];
    server.use(
      http.post('/api/chat/preview', () => HttpResponse.json({ schema_version: 'chat-preview-v1', provisional: true, reading: null })),
      http.get('/api/chat/progress', ({ request }) => {
        polled.push(new URL(request.url).searchParams.get('request_id'));
        return HttpResponse.json(PROGRESS);
      }),
      http.post('/api/chat', async ({ request }) => {
        const body = (await request.json()) as { request_id?: string; question: string };
        asked.push(String(body.request_id));
        await new Promise(resolve => setTimeout(resolve, 150));
        return HttpResponse.json(PACKET);
      }),
      http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] })),
    );
    renderAsk();
    const user = userEvent.setup();
    await user.type(askBox(), 'Will it rain in Ahmedabad?');
    await user.click(screen.getByTestId('send-question'));
    await screen.findByRole('article');
    const before = polled.length;
    await user.clear(askBox());
    await user.type(askBox(), 'Will it rain in Surat?');
    await user.click(screen.getByTestId('send-question'));
    await waitFor(() => expect(polled.length).toBeGreaterThan(before));
    expect(asked).toHaveLength(2);
    expect(asked[0]).not.toBe(asked[1]);
    /* Every read after the second question names the second turn. */
    polled.slice(before).forEach(id => expect(id).toBe(asked[1]));
  });
});
