/* A turn owns its own outcome, and an abandoned one owns nothing.
   ============================================================================
   The reducer guards `preview`, `progress`, `stopping` and `stopped` by the turn's key — an update that
   arrives for a turn that is no longer the working one is dropped. `answer` and `notice` carry a key too
   and never checked it.

   So a question whose request is still in flight when the reader starts a new conversation lands in that
   new conversation, minutes later, under a question that is no longer on screen. The same holds for a
   refusal. These pin it. */

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
  answer: 'THE ABANDONED ANSWER.',
  facts: [], citations: [], notes: [], choices: [], charts: [], calculations: [], task_results: [],
  answered_at_utc: '2026-09-14T10:47:00+00:00', trace: {}, retrieval_plan: [], resolved_points: {},
};

function handlers(answerAfterMs: number, refusal?: { status: number; error: string }) {
  return [
    http.post('/api/chat/preview', () => HttpResponse.json({ schema_version: 'chat-preview-v1', provisional: true, reading: { line: 'place: Ahmedabad' } })),
    http.get('/api/chat/progress', () => HttpResponse.json({ schema_version: 'chat-progress-v1', state: 'working', stage: 'retrieving', stage_label: 'Retrieving evidence', stages_seen: ['retrieving'] })),
    http.post('/api/chat/cancel', () => HttpResponse.json({ request_id: 'x', state: 'cancel_requested', detail: 'asked to stop' })),
    http.post('/api/chat', async () => {
      await new Promise(resolve => setTimeout(resolve, answerAfterMs));
      if (refusal) return HttpResponse.json({ error: refusal.error }, { status: refusal.status });
      return HttpResponse.json(PACKET);
    }),
    http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] })),
  ];
}

async function askThenAbandon() {
  const user = userEvent.setup();
  const box = document.getElementById('question') as HTMLTextAreaElement;
  await user.type(box, 'Will it rain in Ahmedabad?');
  await user.click(screen.getByTestId('send-question'));
  await screen.findByTestId('working-turn');
  /* The reader gives up on it and starts something else. */
  await user.click(screen.getByRole('button', { name: /New conversation/i }));
  await waitFor(() => expect(screen.queryByTestId('working-turn')).toBeNull());
  return user;
}

describe('an abandoned turn', () => {
  it('does not drop its answer into the conversation that replaced it', async () => {
    server.use(...handlers(400));
    renderAsk();
    await askThenAbandon();
    /* Long enough for the abandoned request to have resolved. */
    await new Promise(resolve => setTimeout(resolve, 700));
    expect(screen.queryByText(/THE ABANDONED ANSWER/)).toBeNull();
  });

  it('does not drop its refusal there either, nor put its question back in the box', async () => {
    server.use(...handlers(400, { status: 503, error: 'THE ABANDONED REFUSAL.' }));
    renderAsk();
    await askThenAbandon();
    await new Promise(resolve => setTimeout(resolve, 700));
    expect(screen.queryByText(/THE ABANDONED REFUSAL/)).toBeNull();
    /* A refusal returns the question to the composer so it can be edited and sent again. An abandoned
       turn must not do that to a box the reader has since moved on from. */
    expect(document.getElementById('question')).toHaveValue('');
  });
});
