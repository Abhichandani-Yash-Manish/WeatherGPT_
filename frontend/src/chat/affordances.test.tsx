/* The three things a reader could not do to a turn: edit it, retry it, ask it again.
   ============================================================================
   A question had to be typed again to correct it, a refusal had no retry beside it, and an answer could
   not be re-read at all. Each of these moves turns rather than only sending a request: an edit drops the
   question and the answer that belonged to it, a retry and a re-ask replace the answer where it stood, and
   none of them may let an abandoned turn's answer land in the conversation that replaced it. */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { renderAsk } from '../test/ask';
import { INFLIGHT_KEY } from './model';
import { server } from '../test/msw';

const RESOLVED = {
  Ahmedabad: { selection_id: 'geonames:1279233', label: 'Ahmedabad, Gujarat', coordinates: { latitude: 23.02579, longitude: 72.58727 } },
};

function packet(answer: string, retrievedAt: string) {
  return {
    schema_version: 'weather-conversation-v1',
    conversation_id: '44444444-4444-4444-8444-444444444444',
    question: 'Will it rain in Ahmedabad?',
    status: 'answered',
    answer,
    facts: [{
      id: 't1-f1', label: 'Forecast rainfall', value: '0.3', unit: 'mm', place: 'Ahmedabad, Gujarat',
      start: '2026-09-15T06:30:00+05:30', end: '2026-09-15T12:30:00+05:30', parameter: 'precipitation',
      source_id: 'S21', evidence_kind: 'forecast', citation_ids: ['t1-c1'], task_id: 't1',
    }],
    citations: [{ id: 't1-c1', source_id: 'S21', provider: 'Open-Meteo', product: 'GFS forecast delivery', retrieved_at_utc: retrievedAt }],
    notes: [], choices: [], charts: [], calculations: [], task_results: [],
    answered_at_utc: '2026-09-14T10:47:00+00:00', trace: {}, retrieval_plan: [], resolved_points: RESOLVED,
  };
}

const LATEST = packet('THE ANSWER THAT WAS RE-READ.', '2026-09-14T11:30:00+00:00');
const EARLIER = packet('THE FIRST ANSWER.', '2026-09-14T10:39:00+00:00');

const box = () => document.getElementById('question') as HTMLTextAreaElement;

function base(answers: Record<string, unknown>[], afterMs = 0) {
  let call = 0;
  const bodies: Record<string, unknown>[] = [];
  return {
    bodies,
    handlers: [
      http.post('/api/chat/preview', () => HttpResponse.json({ schema_version: 'chat-preview-v1', provisional: true, reading: null })),
      http.get('/api/chat/progress', () => HttpResponse.json({ schema_version: 'chat-progress-v1', state: 'running', stage: 'started', stage_label: 'Reading the question', stages_seen: ['started'], queue: { waiting: 0, active: 1, capacity: 3, wait_seconds_before_refusal: 45 } })),
      http.post('/api/chat', async ({ request }) => {
        bodies.push((await request.json()) as Record<string, unknown>);
        const value = answers[Math.min(call, answers.length - 1)];
        call += 1;
        if (afterMs) await new Promise(resolve => setTimeout(resolve, afterMs));
        if (value && (value as { error?: string }).error) {
          return HttpResponse.json(value, { status: (value as { code?: number }).code || 503 });
        }
        return HttpResponse.json(value);
      }),
      http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] })),
    ],
  };
}

async function ask(text: string) {
  const user = userEvent.setup();
  await user.clear(box());
  await user.type(box(), text);
  await user.click(screen.getByTestId('send-question'));
  return user;
}

describe('editing the question just asked', () => {
  afterEach(() => { try { window.sessionStorage.clear(); } catch { /* storage is optional */ } });

  it('replaces the turn and its answer rather than leaving the answer beside the correction', async () => {
    const sent = base([EARLIER, packet('THE ANSWER TO THE CORRECTED QUESTION.', '2026-09-14T10:39:00+00:00')]);
    server.use(...sent.handlers);
    renderAsk();
    const user = await ask('Will it rain in Ahmedabad?');
    await screen.findByText('THE FIRST ANSWER.');
    await user.click(screen.getByRole('button', { name: 'Edit this question' }));
    /* The answer that belonged to the question is gone with the question, and the question is back in the
       box to be corrected where it was asked. */
    expect(screen.queryByText('THE FIRST ANSWER.')).toBeNull();
    expect(document.querySelector('.g-you')).toBeNull();
    expect(box()).toHaveValue('Will it rain in Ahmedabad?');
    await user.clear(box());
    await user.type(box(), 'Will it rain in Surat?');
    await user.click(screen.getByTestId('send-question'));
    await screen.findByText('THE ANSWER TO THE CORRECTED QUESTION.');
    expect(sent.bodies[1].question).toBe('Will it rain in Surat?');
    expect(document.querySelectorAll('.g-you').length).toBe(1);
  });

  it('abandons the request in flight and keeps its answer out of the conversation that replaced it', async () => {
    let release: (value: unknown) => void = () => {};
    const slow = new Promise(resolve => { release = resolve; });
    const bodies: Record<string, unknown>[] = [];
    server.use(
      http.post('/api/chat/preview', () => HttpResponse.json({ schema_version: 'chat-preview-v1', provisional: true, reading: null })),
      http.get('/api/chat/progress', () => HttpResponse.json({ schema_version: 'chat-progress-v1', state: 'running', stage: 'started', stage_label: 'Reading the question', stages_seen: ['started'], queue: { waiting: 0, active: 1, capacity: 3, wait_seconds_before_refusal: 45 } })),
      http.post('/api/chat', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        bodies.push(body);
        if (bodies.length === 1) {
          await slow;
          return HttpResponse.json(packet('THE ABANDONED ANSWER.', '2026-09-14T10:39:00+00:00'));
        }
        return HttpResponse.json(packet('THE ANSWER AFTER THE CORRECTION.', '2026-09-14T10:39:00+00:00'));
      }),
      http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] })),
    );
    renderAsk();
    const user = await ask('Will it rain in Ahmedabad?');
    await screen.findByTestId('working-turn');
    /* The reader corrects the question while it is still being answered. */
    await user.click(screen.getByRole('button', { name: 'Edit this question' }));
    await waitFor(() => expect(screen.queryByTestId('working-turn')).toBeNull());
    await user.clear(box());
    await user.type(box(), 'Will it rain in Surat?');
    await user.click(screen.getByTestId('send-question'));
    await screen.findByText('THE ANSWER AFTER THE CORRECTION.');
    /* The abandoned request resolves now, long after the reader moved on. */
    release(null);
    await new Promise(resolve => setTimeout(resolve, 50));
    expect(screen.queryByText('THE ABANDONED ANSWER.')).toBeNull();
    expect(document.querySelectorAll('.g-you').length).toBe(1);
    /* Twice, by design: the bar names the thread with the question the thread opened with. */
    expect(screen.getAllByText('Will it rain in Surat?').length).toBeGreaterThan(0);
  });
});

describe('retrying a refusal and asking the sources again', () => {
  afterEach(() => { try { window.sessionStorage.clear(); } catch { /* storage is optional */ } });

  it('offers the re-ask beside a refusal, sends the same question, and does not leave the refusal on screen', async () => {
    const sent = base([{ error: 'The assistant is busy longer than the queue allows. Try again shortly.', code: 503 }, EARLIER]);
    server.use(...sent.handlers);
    renderAsk();
    const user = await ask('Will it rain in Ahmedabad?');
    await screen.findByText(/busy longer than the queue allows/);
    const retry = screen.getByRole('button', { name: 'Ask again' });
    /* A control that sends a sentence carries that sentence. */
    expect(retry.getAttribute('title')).toContain('Will it rain in Ahmedabad?');
    await user.click(retry);
    await screen.findByText('THE FIRST ANSWER.');
    expect(sent.bodies[1].question).toBe(sent.bodies[0].question);
    expect(screen.queryByText(/busy longer than the queue allows/)).toBeNull();
    /* One question, one answer: the retry replaced the refusal instead of adding a second turn. */
    expect(document.querySelectorAll('.g-you').length).toBe(1);
  });

  it('asks the sources for fresh evidence before re-reading, and says what happened', async () => {
    const sent = base([EARLIER, LATEST]);
    const collected: Record<string, unknown>[] = [];
    server.use(
      ...sent.handlers,
      http.post('/api/refresh', async ({ request }) => {
        collected.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json({ refresh: { state: 'collected', message: 'A fresh collection was requested for this point.' } });
      }),
    );
    renderAsk();
    const user = await ask('Will it rain in Ahmedabad?');
    await screen.findByText('THE FIRST ANSWER.');
    await user.click(screen.getByRole('button', { name: 'Ask the sources again' }));
    await screen.findByText('THE ANSWER THAT WAS RE-READ.');
    expect(collected).toHaveLength(1);
    expect(collected[0].coordinates).toEqual({ latitude: 23.02579, longitude: 72.58727 });
    expect(sent.bodies[1].question).toBe('Will it rain in Ahmedabad?');
    /* The answer states which of the two things happened: this one was retrieved later than the one it
       replaced, and the collection's own sentence travels with it. */
    expect(screen.getByText(/later than the previous answer/)).toBeInTheDocument();
    expect(screen.getByText(/A fresh collection was requested for this point/)).toBeInTheDocument();
    expect(screen.queryByText('THE FIRST ANSWER.')).toBeNull();
  });

  it('says when the workspace served the read it already held instead of fetching again', async () => {
    const sent = base([EARLIER, packet('THE SAME READ SERVED AGAIN.', '2026-09-14T10:39:00+00:00')]);
    server.use(
      ...sent.handlers,
      http.post('/api/refresh', () => HttpResponse.json({ refresh: { state: 'already_fresh', message: 'The stored evidence is still within its serving lifetime.' } })),
    );
    renderAsk();
    const user = await ask('Will it rain in Ahmedabad?');
    await screen.findByText('THE FIRST ANSWER.');
    await user.click(screen.getByRole('button', { name: 'Ask the sources again' }));
    await screen.findByText('THE SAME READ SERVED AGAIN.');
    expect(screen.getByText(/the same read the previous answer used/)).toBeInTheDocument();
  });

  it('states no freshness when neither answer records when its evidence was retrieved', async () => {
    const bare = { ...EARLIER, citations: [{ id: 't1-c1', source_id: 'S21' }] };
    const sent = base([bare, { ...bare, answer: 'AN ANSWER THAT RECORDS NO RETRIEVAL TIME.' }]);
    server.use(
      ...sent.handlers,
      http.post('/api/refresh', () => HttpResponse.json({ refresh: { state: 'already_fresh', message: 'Nothing to collect.' } })),
    );
    renderAsk();
    const user = await ask('Will it rain in Ahmedabad?');
    await screen.findByText('THE FIRST ANSWER.');
    await user.click(screen.getByRole('button', { name: 'Ask the sources again' }));
    await screen.findByText('AN ANSWER THAT RECORDS NO RETRIEVAL TIME.');
    expect(screen.getByText(/records when its evidence was retrieved, so nothing here says/)).toBeInTheDocument();
  });

  it('keeps the pointer for the turn in flight and spends it when the answer lands', async () => {
    const sent = base([EARLIER], 60);
    server.use(...sent.handlers);
    renderAsk();
    await ask('Will it rain in Ahmedabad?');
    await waitFor(() => expect(window.sessionStorage.getItem(INFLIGHT_KEY)).not.toBeNull());
    await screen.findByText('THE FIRST ANSWER.');
    await waitFor(() => expect(window.sessionStorage.getItem(INFLIGHT_KEY)).toBeNull());
    /* And the copy the card draws is not a second reader of the answer. */
    const card = screen.getByRole('article');
    expect(within(card).getByText('THE FIRST ANSWER.')).toBeInTheDocument();
  });
});
