/* Resolving a place choice inside its turn, and changing one thing about a turn.
   ============================================================================
   A `needs_selection` answer cost a whole turn: the chips sent a new request and the transcript grew a
   second question. Choosing one now resolves inside the turn that offered it — the engine binds a
   selection to the question it was offered for, so the client sends that same question and the engine
   records one answer. And a reader who wants the same question for another place or another window no
   longer rewrites the sentence: the change travels beside it, in its own field, and the changed turn
   states what changed from the engine's own record of it. */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { renderAsk } from '../test/ask';
import { server } from '../test/msw';

const CHOICE = { label: 'Bhopāl, Ashoknagar, Madhya Pradesh', value: 'Bhopāl, Ashoknagar, Madhya Pradesh', selection_id: 'geonames:1275836', place: 'Bhopal' };

const CLARIFICATION = {
  schema_version: 'weather-conversation-v1',
  conversation_id: '44444444-4444-4444-8444-444444444444',
  question: 'Tell me about rainfall in Bhopal.',
  status: 'needs_selection',
  answer: 'I found 3 possible places for Bhopal. Please confirm the intended location and spelling.',
  facts: [], citations: [], notes: [],
  choices: [CHOICE, { label: 'Bhopal, Madhya Pradesh', selection_id: 'geonames:1' }, { label: 'Bhopāl, Raisen', selection_id: 'geonames:2' }],
  charts: [], calculations: [], task_results: [], follow_up: 'Choose a place, or add its district and state.',
  answered_at_utc: '2026-09-14T10:47:00+00:00', trace: {}, retrieval_plan: [], resolved_points: {},
};

function answered(answer: string, extra: Record<string, unknown> = {}) {
  return {
    schema_version: 'weather-conversation-v1',
    conversation_id: '44444444-4444-4444-8444-444444444444',
    question: 'Tell me about rainfall in Bhopal.',
    status: 'answered',
    answer,
    facts: [{
      id: 't1-f1', label: 'Forecast rainfall', value: '3.2', unit: 'mm', place: 'Ahmedabad, Gujarat',
      start: '2026-09-15T06:30:00+05:30', end: '2026-09-15T12:30:00+05:30', parameter: 'precipitation',
      source_id: 'S21', evidence_kind: 'forecast', citation_ids: ['t1-c1'], task_id: 't1',
    }],
    citations: [{ id: 't1-c1', source_id: 'S21', product: 'GFS forecast delivery', retrieved_at_utc: '2026-09-14T10:39:00+00:00' }],
    notes: [], choices: [], charts: [], calculations: [], task_results: [],
    answered_at_utc: '2026-09-14T10:47:00+00:00', trace: {}, retrieval_plan: [],
    resolved_points: { Ahmedabad: { label: 'Ahmedabad, Gujarat', coordinates: { latitude: 23.02579, longitude: 72.58727 } } },
    ...extra,
  };
}

const box = () => document.getElementById('question') as HTMLTextAreaElement;

function routes(answers: Record<string, unknown>[]) {
  const bodies: Record<string, unknown>[] = [];
  let call = 0;
  return {
    bodies,
    handlers: [
      http.post('/api/chat/preview', () => HttpResponse.json({ schema_version: 'chat-preview-v1', provisional: true, reading: null })),
      http.get('/api/chat/progress', () => HttpResponse.json({ schema_version: 'chat-progress-v1', state: 'running', stage: 'started', stage_label: 'Reading the question', stages_seen: ['started'], queue: { waiting: 0, active: 1, capacity: 3, wait_seconds_before_refusal: 45 } })),
      http.post('/api/chat', async ({ request }) => {
        bodies.push((await request.json()) as Record<string, unknown>);
        const value = answers[Math.min(call, answers.length - 1)];
        call += 1;
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

describe('choosing a place inside its turn', () => {
  afterEach(() => { try { window.sessionStorage.clear(); } catch { /* storage is optional */ } });

  it('sends the question the choice belongs to, with the choice, and keeps one turn', async () => {
    const sent = routes([CLARIFICATION, answered('THE ROW THE READER CHOSE.')]);
    server.use(...sent.handlers);
    renderAsk();
    const user = await ask('Tell me about rainfall in Bhopal.');
    await screen.findByText(/I found 3 possible places/);
    await user.click(screen.getByRole('button', { name: CHOICE.label }));
    await screen.findByText('THE ROW THE READER CHOSE.');
    await waitFor(() => expect(sent.bodies).toHaveLength(2));
    expect(sent.bodies[1].selection_id).toBe(CHOICE.selection_id);
    /* The question the choice was offered for. The engine binds a selection to that question and refuses
       the choice's own label as a question: measured 20 September 2026, the label with a valid selection
       id answered "This place choice belongs to another question." */
    expect(sent.bodies[1].question).toBe(CLARIFICATION.question);
    /* One question and one answer: the choice did not cost a second turn. */
    expect(document.querySelectorAll('.g-you').length).toBe(1);
    expect(document.querySelectorAll('article').length).toBe(1);
    expect(screen.queryByText(/I found 3 possible places/)).toBeNull();
    /* The placeholder is not left in the box for a turn that has been resolved. */
    expect(box()).toHaveValue('');
    expect(box()).not.toHaveValue(CHOICE.label);
  });

  it('sends a quick reply that is not a place choice as an ordinary new question', async () => {
    const withReply = answered('THE ANSWER THAT OFFERS A FOLLOW-UP.', { quick_replies: [{ label: 'And tomorrow?', reply: 'And tomorrow?' }] });
    const sent = routes([withReply, answered('THE FOLLOW-UP ANSWER.')]);
    server.use(...sent.handlers);
    renderAsk();
    const user = await ask('Tell me about rainfall in Bhopal.');
    await screen.findByText('THE ANSWER THAT OFFERS A FOLLOW-UP.');
    await user.click(screen.getByRole('button', { name: 'And tomorrow?' }));
    await waitFor(() => expect(sent.bodies).toHaveLength(2));
    expect(sent.bodies[1].selection_id).toBeUndefined();
    expect(sent.bodies[1].question).toBe('And tomorrow?');
    await waitFor(() => expect(document.querySelectorAll('article').length).toBe(2));
  });
});

describe('changing one thing about a turn', () => {
  afterEach(() => { try { window.sessionStorage.clear(); } catch { /* storage is optional */ } });

  it('changes only the place, sending the same question and the place the reader picked', async () => {
    const changed = answered('THE ANSWER AT THE PLACE THE READER CHOSE.', {
      reader_changes: [{ field: 'place', label: 'Surat, Gujarat', latitude: 21.1702, longitude: 72.8311, named_in_question: 'Ahmedabad', basis: 'supplied by the reader for this turn' }],
    });
    const sent = routes([answered('THE FIRST ANSWER.'), changed]);
    server.use(
      ...sent.handlers,
      http.get('/api/places/search', () => HttpResponse.json({
        schema_version: 'product-view-v1', view: 'places.search', status: 'ok',
        data: { matches: [{ label: 'Surat, Gujarat', name: 'Surat', latitude: 21.1702, longitude: 72.8311, state: 'Gujarat' }] },
        sources: [], limitations: [],
      })),
    );
    renderAsk();
    const user = await ask('Tell me about rainfall in Bhopal.');
    await screen.findByText('THE FIRST ANSWER.');
    await user.click(screen.getByRole('button', { name: 'Change the place' }));
    await user.type(document.getElementById('turn-place') as HTMLInputElement, 'Surat');
    /* The rows are the catalogue's own options, the shape the place picker already draws. */
    await user.click(await screen.findByRole('option', { name: /Surat, Gujarat/ }));
    await screen.findByText('THE ANSWER AT THE PLACE THE READER CHOSE.');
    await waitFor(() => expect(sent.bodies).toHaveLength(2));
    /* The sentence is not rewritten: the question travels unchanged and the place travels beside it. */
    expect(sent.bodies[1].question).toBe('Tell me about rainfall in Bhopal.');
    expect(sent.bodies[1].place).toEqual({ label: 'Surat, Gujarat', latitude: 21.1702, longitude: 72.8311, state: 'Gujarat', district: undefined });
    /* The changed turn says what changed, from the engine's own record of it. */
    expect(screen.getByText(/Asked again at Surat, Gujarat/)).toBeInTheDocument();
    expect(document.querySelectorAll('.g-you').length).toBe(1);
    expect(screen.queryByText('THE FIRST ANSWER.')).toBeNull();
  });

  it('changes only the window, in the engine\'s own words, and says whether it was applied', async () => {
    const applied = answered('THE ANSWER FOR TOMORROW EVENING.', {
      reader_changes: [{ field: 'window', requested: 'tomorrow evening', applied: true, label: '15 Sep 2026 18:30-22:30 IST', basis: "resolved from the engine's own day tables, not by the planner" }],
    });
    const sent = routes([answered('THE FIRST ANSWER.'), applied]);
    server.use(...sent.handlers);
    renderAsk();
    const user = await ask('Tell me about rainfall in Bhopal.');
    await screen.findByText('THE FIRST ANSWER.');
    await user.click(screen.getByRole('button', { name: 'Change the window' }));
    const chip = screen.getByRole('button', { name: 'Tomorrow evening' });
    /* A control that sends a sentence carries that sentence. */
    expect(chip.getAttribute('title')).toContain('Tell me about rainfall in Bhopal.');
    await user.click(chip);
    await screen.findByText('THE ANSWER FOR TOMORROW EVENING.');
    await waitFor(() => expect(sent.bodies).toHaveLength(2));
    expect(sent.bodies[1].window).toBe('tomorrow evening');
    expect(sent.bodies[1].question).toBe('Tell me about rainfall in Bhopal.');
    expect(sent.bodies[1].place).toBeUndefined();
    expect(screen.getByText(/Asked again for 15 Sep 2026 18:30-22:30 IST/)).toBeInTheDocument();
    expect(screen.queryByText('THE FIRST ANSWER.')).toBeNull();
  });

  it('says when the window the reader asked for could not be resolved, instead of looking like a quiet one', async () => {
    const refused = answered('THE ANSWER FOR THE WINDOW IN THE QUESTION.', {
      reader_changes: [{ field: 'window', requested: 'today evening', applied: false, detail: 'the phrase does not name a day the engine can resolve' }],
    });
    const sent = routes([answered('THE FIRST ANSWER.'), refused]);
    server.use(...sent.handlers);
    renderAsk();
    const user = await ask('Tell me about rainfall in Bhopal.');
    await screen.findByText('THE FIRST ANSWER.');
    await user.click(screen.getByRole('button', { name: 'Change the window' }));
    await user.click(screen.getByRole('button', { name: 'Today' }));
    await screen.findByText('THE ANSWER FOR THE WINDOW IN THE QUESTION.');
    expect(screen.getByText(/could not resolve it/)).toBeInTheDocument();
    expect(screen.getByText(/The window written in the question is what was read/)).toBeInTheDocument();
  });
});
