/* Does the stream arrive progressively, or all at once when the turn ends?
   ============================================================================
   The route's own tests read the body to the end, which proves the frames are there and says nothing about WHEN
   they arrive. This asks a real question, opens the stream for its identifier while the turn is still running, and
   records the moment each frame lands. A stream whose frames all arrive with the answer is not a stream - it is
   the poll, one round trip late.

     node research/reviews/frontend-batch-20260920/probe-stream.mjs   (with the workspace already running)

   UI_BASE_URL points at the workspace; the session token is read from the served page, as the tests do. */
import { randomUUID } from 'node:crypto';

const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8765';
const QUESTION = process.env.UI_QUESTION || 'Will it rain in Kochi tomorrow morning?';

const html = await (await fetch(BASE + '/')).text();
const token = (html.match(/name="workspace-token" content="([^"]+)"/) || [])[1];
if (!token) throw new Error('no workspace token in the served page');
const headers = { 'X-WeatherGPT-Token': token, 'Content-Type': 'application/json' };

const requestId = randomUUID();
const started = Date.now();
const at = () => String(Date.now() - started).padStart(6) + ' ms';

/* The question goes out first and is not awaited: the stream has to be opened WHILE the turn runs. */
const asked = fetch(BASE + '/api/chat', { method: 'POST', headers, body: JSON.stringify({ question: QUESTION, request_id: requestId }) })
  .then(async response => ({ status: response.status, at: at(), body: await response.json() }));

await new Promise(resolve => setTimeout(resolve, 400));
const response = await fetch(BASE + '/api/chat/stream?request_id=' + requestId, { headers });
console.log('stream status', response.status, response.headers.get('content-type'), 'opened at', at());

const frames = [];
const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';
for (;;) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const parts = buffer.split('\n\n');
  buffer = parts.pop() || '';
  for (const part of parts) {
    const line = part.split('\n').find(entry => entry.startsWith('data: '));
    if (!line) continue;
    const frame = JSON.parse(line.slice(6));
    const arrived = at();
    frames.push(arrived);
    const stage = frame.kind === 'progress' ? (frame.progress.stage || frame.progress.state) : frame.kind + '/' + (frame.result && frame.result.state);
    console.log('frame', String(frames.length).padStart(2), arrived, frame.kind, stage);
  }
}
const answered = await asked;
console.log('the POST answered at', answered.at, 'with status', answered.status);
const firstFrame = frames.length ? parseInt(frames[0], 10) : null;
const answerAt = parseInt(answered.at, 10);
const progressive = firstFrame !== null && firstFrame < answerAt - 250;
console.log('');
console.log('frames:', frames.length, '| first frame at', frames[0] || 'none', '| answer at', answered.at);
console.log(progressive
  ? 'PROGRESSIVE: a frame reached the reader before the turn finished, so the wait can show the engine\u2019s own stages as they happen'
  : 'NOT PROGRESSIVE: every frame arrived with the answer, so this is the poll with one round trip more');
process.exit(progressive ? 0 : 1);
