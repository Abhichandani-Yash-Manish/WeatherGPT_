/* The stage, as the engine reaches it.
   ============================================================================
   docs/116 batch B put the turn's progress on a stream. The frames carry the payloads the progress route
   already answers with, so a reader is told nothing the poll would not have told them - they are told when it
   happens. Measured against a live turn (docs/131): the first frame at 404 ms, the engine's own `retrieving`
   at 2825 ms, the answer at 6000 ms.

   Three things are pinned here rather than intended: the stage on screen comes from the STREAM; the poll is
   opened only when the stream cannot be (a workspace that cannot stream must still say which stage it is in,
   and a healthy stream must not double the reads); and the stream names the turn's own identifier. */

import { screen, waitFor, within } from '@testing-library/react';
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

function stage(stage: string, label: string) {
  return {
    schema_version: 'chat-progress-v1', state: 'running', stage, stage_label: label,
    stages_seen: ['started', stage],
    queue: { waiting: 0, active: 1, capacity: 3, wait_seconds_before_refusal: 45 },
    stage_note: 'A stage names the work the server is in now. It is not a completion estimate.',
    stages_are_facts_not_progress: true,
  };
}

/* One frame, in the wire format the route writes: `data: {json}` and a blank line. */
function frame(kind: string, payload: Record<string, unknown>) {
  return 'data: ' + JSON.stringify({ kind, ...payload }) + '\n\n';
}

/* The frames are spaced in TIME, because that is what a stream is - and because the first version of this
   enqueued both in one tick, React coalesced the two dispatches, and the intermediate stage was never painted.
   The test then read as if the stream had not delivered it. A burst is not a stream. */
/* The gap is the pace of a real turn rather than the fastest a test can go: at 250 ms the first stage was on
   screen for a window shorter than userEvent's own click, so the assertion raced the click and read as if the
   stage never arrived. The live probe (docs/131) is the measurement of the real pace - 404 ms, then 2825 ms. */
function streamOf(frames: string[], gapMs = 900) {
  const body = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();
      for (const entry of frames) {
        controller.enqueue(encoder.encode(entry));
        await new Promise(resolve => setTimeout(resolve, gapMs));
      }
      controller.close();
    },
  });
  return new HttpResponse(body, { headers: { 'Content-Type': 'text/event-stream; charset=utf-8', 'Cache-Control': 'no-store' } });
}

function askBox() {
  return document.getElementById('question') as HTMLTextAreaElement;
}

function ledger() {
  return http.get('/api/conversations', () => HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [] }));
}

function preview() {
  return http.post('/api/chat/preview', () => HttpResponse.json({ schema_version: 'chat-preview-v1', provisional: true, reading: null }));
}

/* A stage the reader can see, named where it is said.
   Each stage now appears TWICE on a working turn, and both are deliberate: once in `.g-working-stage`,
   the polite live region that states what the turn is doing now, and once in the open trail of every
   stage it has reached. A bare findByText matches both, so these assertions say which they mean - the
   live region for "the stream reported this stage", and the trail for "the reader can see the sequence". */
async function stageSaid(label: string | RegExp) {
  await waitFor(() => expect(document.querySelector('.g-working-stage')).toHaveTextContent(label));
}

async function stageTrailed(label: string) {
  const trail = await screen.findByTestId('live-stages');
  await waitFor(() => expect(within(trail).getByText(label)).toBeInTheDocument());
}

describe('the turn, followed as a stream', () => {
  afterEach(() => {
    try { window.sessionStorage.clear(); } catch { /* storage is optional */ }
  });

  it('shows the stage the stream reports, and never opens the poll', async () => {
    const polled: string[] = [];
    const followed: (string | null)[] = [];
    server.use(
      preview(),
      ledger(),
      http.get('/api/chat/stream', ({ request }) => {
        followed.push(new URL(request.url).searchParams.get('request_id'));
        return streamOf([
          frame('progress', { progress: stage('retrieving', 'Retrieving evidence') }),
          frame('progress', { progress: stage('assembling', 'Assembling the answer') }),
        ]);
      }),
      http.get('/api/chat/progress', ({ request }) => {
        polled.push(String(new URL(request.url).searchParams.get('request_id')));
        return HttpResponse.json(stage('retrieving', 'Retrieving evidence'));
      }),
      /* The POST is held open long enough that the turn is still in flight while the stages are asserted. It was
         600 ms in the first version, and the answer landed between two of the assertions' polls: the stage was on
         screen for half a second and the test read as if the stream had never delivered it. The delay is the
         test's, not the feature's. */
      http.post('/api/chat', async () => {
        await new Promise(resolve => setTimeout(resolve, 4000));
        return HttpResponse.json(PACKET);
      }),
    );
    renderAsk();
    const user = userEvent.setup();
    await user.type(askBox(), 'Will it rain in Ahmedabad?');
    await user.click(screen.getByTestId('send-question'));

    await stageSaid('Retrieving evidence');
    await stageTrailed('Retrieving evidence');
    await stageSaid('Assembling the answer');
    expect(followed).toHaveLength(1);
    expect(followed[0], 'the stream names the turn it is following').toBeTruthy();
    /* Longer than the poll's own interval: if the fallback had started, this is when it would show. */
    await new Promise(resolve => setTimeout(resolve, 1100));
    expect(polled, 'a streamed turn must not also be polled').toEqual([]);
    /* The answer still arrives on the POST, and this is the assertion that says a streamed turn did not break
       that path. The timeout is the test's own POST delay plus room, not a longer wait for the product. */
    expect(await screen.findByRole('article', {}, { timeout: 6000 })).toBeInTheDocument();
  }, 8_000);

  it('falls back to the poll when the stream cannot be opened, rather than losing the stage', async () => {
    const polled: string[] = [];
    server.use(
      preview(),
      ledger(),
      http.get('/api/chat/stream', () => new HttpResponse('Not found', { status: 404 })),
      http.get('/api/chat/progress', ({ request }) => {
        polled.push(String(new URL(request.url).searchParams.get('request_id')));
        return HttpResponse.json(stage('assembling', 'Assembling the answer'));
      }),
      http.post('/api/chat', async () => {
        await new Promise(resolve => setTimeout(resolve, 800));
        return HttpResponse.json(PACKET);
      }),
    );
    renderAsk();
    const user = userEvent.setup();
    await user.type(askBox(), 'Will it rain in Ahmedabad?');
    await user.click(screen.getByTestId('send-question'));

    await stageSaid('Assembling the answer');
    await waitFor(() => expect(polled.length).toBeGreaterThan(0));
    expect(await screen.findByRole('article')).toBeInTheDocument();
  });
});
