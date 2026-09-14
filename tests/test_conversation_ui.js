// Component-level client checks: request shape, refusals, cancellation, retry and
// retention controls. Not a browser, load or concurrency acceptance test.
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path'), assert = require('assert');
const shim = require('./dom_shim.js');

const ROOT = path.join(__dirname, '..');
const LEDGER = {
  schema_version: 'conversation-ledger-v1', total: 3, limit: 40,
  conversations: [
    { id: '11111111-1111-4111-8111-111111111111', updated: '2026-09-14T10:00:00+00:00', turns: 2, asked: 1, opening_question: 'Will it rain in Kochi, Kerala tomorrow?' },
    { id: '22222222-2222-4222-8222-222222222222', updated: '2026-09-14T09:00:00+00:00', turns: 2, asked: 1, opening_question: 'What is the current weather at VOBL?' },
    { id: '33333333-3333-4333-8333-333333333333', updated: '2026-09-14T08:00:00+00:00', turns: 4, asked: 2, opening_question: 'Show the annual rainfall trend for Ahmedabad district' }
  ],
  note: 'stored locally'
};
const HEALTH = { schema_version: 'source-health-v1', available: true, products: [{ product: 'forecast', jobs: 30, states: { succeeded: 30 }, newest_commit_utc: '2026-09-14T11:09:29+00:00' }], job_states: { succeeded: 30 }, total_jobs: 30, streams: 1, active_leases: 0, cooldowns: [], note: 'read-only projection' };
const FORECAST = {
  schema_version: 'weather-conversation-v1', conversation_id: '44444444-4444-4444-8444-444444444444',
  question: 'Will it rain in Ahmedabad?', status: 'answered',
  answer: 'Ahmedabad: forecast precipitation 0.3 mm.',
  facts: [{ id: 't1-f1', label: 'Forecast rainfall', value: '0.3', unit: 'mm', place: 'Ahmedabad, Ahmadābād, State of Gujarāt',
    start: '2026-09-15T06:30:00+05:30', end: '2026-09-15T12:30:00+05:30', source_id: 'S21', parameter: 'precipitation',
    entity_id: 'geonames:1279233', evidence_version: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    citation_ids: ['t1-c1'], task_id: 't1' }],
  citations: [{ id: 't1-c1', source_id: 'S21', provider: 'Open-Meteo', product: 'GFS forecast delivery',
    url: 'https://api.open-meteo.com/v1/forecast', retrieved_at_utc: '2026-09-14T10:39:00+00:00' }],
  notes: [], choices: [],
  charts: [], calculations: [], task_results: [], follow_up: null, answered_at_utc: '2026-09-14T10:47:00+00:00',
  expires_at_utc: '2026-09-14T11:47:00+00:00', operational_eligible: false, trace: {}, retrieval_plan: [],
  resolved_points: { Ahmedabad: { selection_id: 'geonames:1279233', label: 'Ahmedabad, Gujarāt', coordinates: { latitude: 23.02579, longitude: 72.58727 } } }
};
const REFRESH = { refresh: { state: 'succeeded', job_id: 'job-1', worker_state: 'succeeded', claims_this_action: 1, job_provider_attempts: 1, retry_due_utc_epoch: 1789383600, message: 'Collection completed; answer checked against the stored evidence.' } };

function harness(options) {
  options = options || {};
  const document = shim.createDocument();
  ['composer-fields', 'cancel', 'error', 'jump-latest', 'banner'].forEach(id => { document.getElementById(id).hidden = true; });
  document.getElementById('question').value = '';
  const calls = [];
  let printed = 0;
  const context = Object.create(global);
  const window = {
    localStorage: { getItem: () => null, setItem: () => {} },
    location: { hash: '', pathname: '/' },
    history: { replaceState: () => {} },
    addEventListener: () => {},
    confirm: () => true,
    print: () => { printed += 1; },
    WeatherGPT: null
  };
  // Some host globals are getter-only on the prototype chain, so every shim global
  // is defined rather than assigned.
  const define = (key, value) => Object.defineProperty(context, key, { value: value, writable: true, configurable: true, enumerable: true });
  define('document', document);
  define('Node', shim.Node);
  define('window', window);
  define('navigator', { onLine: true, clipboard: null });
  define('AbortController', AbortController);
  define('Blob', Blob);
  define('URL', URL);
  define('requestAnimationFrame', fn => setTimeout(fn, 0));
  define('fetch', (target, options2) => {
    const call = { path: target, method: (options2 && options2.method) || 'GET', body: options2 && options2.body ? JSON.parse(options2.body) : null, signal: options2 && options2.signal };
    calls.push(call);
    if (options.respond) return options.respond(call, calls.length);
    if (call.path === '/api/conversations') return Promise.resolve({ ok: true, status: 200, json: async () => LEDGER });
    if (call.path === '/api/health') return Promise.resolve({ ok: true, status: 200, json: async () => HEALTH });
    if (call.path === '/api/chat') return Promise.resolve({ ok: true, status: 200, json: async () => FORECAST });
    if (call.path === '/api/refresh') return Promise.resolve({ ok: true, status: 200, json: async () => REFRESH });
    return Promise.resolve({ ok: false, status: 404, json: async () => ({ error: 'Not found' }) });
  });
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/views.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/charts.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/app.js'), 'utf8'), context);
  return { context, document, window, calls, printed: () => printed, api: () => window.WeatherGPT };
}
function walk(node, out) {
  out = out || [];
  (node.children || []).forEach(child => { out.push(child); walk(child, out); });
  return out;
}
function withClass(node, cls) { return walk(node).filter(child => String(child.className || '').split(/\s+/).indexOf(cls) >= 0); }
function buttonByText(node, text) { return walk(node).filter(child => child.tag === 'button' && child.textContent === text)[0] || null; }
function chatCalls(calls) { return calls.filter(call => call.path === '/api/chat'); }
function settle(ms) { return new Promise(resolve => setTimeout(resolve, ms === undefined ? 25 : ms)); }
const plain = respond => function (call) {
  if (call.path === '/api/conversations') return Promise.resolve({ ok: true, status: 200, json: async () => LEDGER });
  if (call.path === '/api/health') return Promise.resolve({ ok: true, status: 200, json: async () => HEALTH });
  return respond(call);
};

async function run() {
  // 1. an empty question is refused at the page, with no request made
  let h = harness();
  await settle(5);
  const before = h.calls.length;
  h.document.getElementById('question').value = '   ';
  h.document.getElementById('ask-form').dispatch('submit');
  await settle(5);
  assert.equal(h.calls.length, before, 'An empty question must not reach the workspace');
  assert.equal(h.document.getElementById('error').hidden, false, 'An empty question is explained in the page');
  assert(/Type a question first/.test(h.document.getElementById('error').textContent));
  console.log('PASS: an empty question is refused in the page without a request (component only)');

  // 2. the request shape uses only keys the engine accepts, and the opening card retires
  h = harness();
  await settle(5);
  const thread = h.document.getElementById('thread');
  assert.equal(withClass(thread, 'welcome').length, 1, 'The opening card is shown first');
  await h.api().ask({ question: 'Will it rain in Ahmedabad?' });
  const posts = chatCalls(h.calls);
  assert.equal(posts.length, 1, 'One question sends one request');
  assert.deepEqual(Object.keys(posts[0].body).sort(), ['question']);
  assert.equal(posts[0].path, '/api/chat');
  assert.equal(withClass(thread, 'turn').length, 1, 'The answer is appended to the thread');
  assert.equal(withClass(thread, 'welcome').length, 0, 'The opening card is retired once the conversation starts');
  assert.equal(h.api().state.conversationId, FORECAST.conversation_id, 'The conversation id is kept for the follow-up');
  console.log('PASS: a question sends only accepted keys and retires the opening card');

  // 3. a follow-up carries the conversation id, never the rejected legacy key
  await h.api().ask({ question: 'And in the afternoon?' });
  const follow = chatCalls(h.calls)[1];
  assert.equal(follow.body.conversation_id, FORECAST.conversation_id);
  assert(h.calls.every(call => Object.keys(call.body || {}).indexOf('entity_id') < 0), 'The engine-rejected entity_id key is never sent');
  console.log('PASS: a follow-up keeps the conversation id and never sends the rejected legacy key');

  // 4. choosing a place sends the selection id the engine offered
  h = harness({ respond: plain(call => {
    if (call.path === '/api/chat') return Promise.resolve({ ok: true, status: 200, json: async () => Object.assign({}, FORECAST, { status: 'needs_selection', answer: 'Which place?', choices: [{ selection_id: 'geonames:1279233', label: 'Ahmedabad, Gujarāt', source_id: 'S61', coordinates: { latitude: 23.02579, longitude: 72.58727 } }] }) });
    return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
  }) });
  await settle(5);
  await h.api().ask({ question: 'Tell me about rainfall in Ahmedabad' });
  const choiceButton = withClass(h.document.getElementById('thread'), 'choice')[0];
  assert(choiceButton, 'A candidate is offered as a button');
  choiceButton.dispatch('click');
  await settle(40);
  const chosenCall = chatCalls(h.calls).filter(call => call.body.selection_id)[0];
  assert(chosenCall, 'Choosing a candidate sends a selection');
  assert.equal(chosenCall.body.selection_id, 'geonames:1279233');
  console.log('PASS: choosing an offered place sends that selection id back to the engine');

  // 5. a lock collision is explained as one-at-a-time, not as a generic failure
  h = harness({ respond: plain(call => {
    if (call.path === '/api/chat') return Promise.resolve({ ok: false, status: 400, json: async () => ({ error: 'Another conversation is using the local model. Please retry shortly.' }) });
    return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
  }) });
  await settle(5);
  await h.api().ask({ question: 'Will it rain in Surat?' });
  const locked = h.document.getElementById('error').textContent;
  assert(/one conversation at a time/.test(locked), 'A lock collision says what happened: ' + locked);
  assert(/does not queue a second one/.test(locked), 'A lock collision does not promise a queue');
  console.log('PASS: a lock collision is explained as one-at-a-time and promises no queue');

  // 6. an expired token and an unavailable store are told apart
  const failing = status => plain(call => {
    if (call.path === '/api/chat') return Promise.resolve({ ok: false, status: status, json: async () => ({ error: status === 503 ? 'The local evidence store is unavailable.' : 'Reload this local workspace before sending a request' }) });
    return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
  });
  h = harness({ respond: failing(403) });
  await settle(5);
  await h.api().ask({ question: 'Will it rain?' });
  assert(/no longer holds the workspace token/.test(h.document.getElementById('error').textContent), 'A 403 asks for a reload');
  assert.equal(h.document.getElementById('service-state').textContent, 'Reload needed');
  h = harness({ respond: failing(503) });
  await settle(5);
  await h.api().ask({ question: 'Will it rain?' });
  assert(/evidence store is unavailable/.test(h.document.getElementById('error').textContent), 'A 503 names the store');
  assert.equal(h.document.getElementById('service-state').textContent, 'Store unavailable');
  console.log('PASS: an expired token and an unavailable store produce different, accurate states');

  // 7. stopping a turn does not claim the server stopped working
  h = harness({ respond: plain(call => {
    if (call.path === '/api/chat') return new Promise((resolve, reject) => {
      if (call.signal && call.signal.addEventListener) call.signal.addEventListener('abort', () => { const error = new Error('aborted'); error.name = 'AbortError'; reject(error); });
    });
    return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
  }) });
  await settle(5);
  const pending = h.api().ask({ question: 'Will it rain in Porbandar?' });
  await settle(10);
  assert(h.api().state.controller, 'A turn in flight exposes a cancellation handle');
  h.api().state.controller.abort();
  await pending;
  const stopped = withClass(h.document.getElementById('thread'), 'notice')[0];
  assert(stopped, 'Stopping a turn is reported in the thread');
  assert(/may still be finishing/.test(stopped.textContent), 'Stopping says the server may still be working');
  assert(/nothing is queued behind it/.test(stopped.textContent), 'Stopping does not imply a queue');
  assert.equal(h.document.getElementById('busy').textContent, 'Ready', 'The page returns to a ready state');
  console.log('PASS: stopping a turn states that server work may continue and nothing is queued');

  // 8. collecting fresh evidence posts the resolved point and reports claims honestly
  h = harness();
  await settle(5);
  await h.api().ask({ question: 'Will it rain in Ahmedabad?' });
  const collect = buttonByText(h.document.getElementById('thread'), 'Collect fresh evidence');
  assert(collect, 'A resolved point offers a bounded collection');
  collect.dispatch('click');
  await settle(80);
  const refreshCall = h.calls.filter(call => call.path === '/api/refresh')[0];
  assert(refreshCall, 'Collecting posts to the refresh route');
  assert.deepEqual(refreshCall.body.coordinates, { latitude: 23.02579, longitude: 72.58727 });
  assert.equal(refreshCall.body.question, FORECAST.question);
  const refreshNotice = withClass(h.document.getElementById('thread'), 'notice').filter(node => /Collection completed/.test(node.textContent))[0];
  assert(refreshNotice, 'The collection result is shown');
  assert(/1 provider claim\(s\) this action/.test(refreshNotice.textContent), 'Provider claims are counted, not hidden');
  assert(/no background worker keeps collecting/.test(refreshNotice.textContent), 'The notice denies a background worker');
  assert.equal(chatCalls(h.calls).length, 2, 'The answer is re-read after collecting');
  console.log('PASS: collecting fresh evidence posts the resolved point and reports claims honestly');

  // 9. a new conversation clears the thread and the identifier without sending anything
  const beforeNew = h.calls.length;
  h.document.getElementById('new-conversation').dispatch('click');
  await settle(30);
  assert.equal(withClass(h.document.getElementById('thread'), 'welcome').length, 1, 'A new conversation shows the opening card again');
  assert.equal(h.api().state.conversationId, null, 'A new conversation forgets the previous identifier');
  assert.equal(h.calls.length, beforeNew + 1, 'Starting a new conversation only refreshes the ledger');
  assert.equal(h.calls[h.calls.length - 1].path, '/api/conversations');
  console.log('PASS: a new conversation clears the thread and identifier without sending a question');

  // 10. the ledger lists stored conversations and searches them
  h = harness();
  await settle(10);
  const list = h.document.getElementById('ledger');
  assert.equal(withClass(list, 'ledger-item').length, 3, 'Every stored conversation is listed');
  assert(/3 stored on this machine; the 3 most recent are listed/.test(h.document.getElementById('ledger-note').textContent));
  h.document.getElementById('ledger-search').value = 'kochi';
  h.document.getElementById('ledger-search').dispatch('input');
  assert.equal(withClass(list, 'ledger-item').length, 1, 'The search narrows the list');
  assert(/1 of the 3 most recent conversations match/.test(h.document.getElementById('ledger-note').textContent));
  h.document.getElementById('ledger-search').value = '';
  h.document.getElementById('ledger-search').dispatch('input');
  assert.equal(withClass(list, 'ledger-item').length, 3, 'Clearing the search restores the list');
  console.log('PASS: the ledger lists and searches the stored conversations');

  // 11. a stored turn is deleted through the local route only
  const removeButton = walk(h.document.getElementById('ledger')).filter(node => node.tag === 'button' && node.textContent === 'Delete')[0];
  assert(removeButton, 'A stored conversation can be deleted');
  removeButton.dispatch('click');
  await settle(50);
  const deletes = h.calls.filter(call => call.method === 'DELETE');
  assert.equal(deletes.length, 1, 'Deleting sends one DELETE');
  assert(/^\/api\/conversations\//.test(deletes[0].path), 'The delete names the conversation');
  console.log('PASS: a stored conversation is deleted through the local route only');

  // 12. the field builder writes the question box and never submits it
  h = harness();
  await settle(5);
  const beforeBuild = h.calls.length;
  h.document.getElementById('place').value = 'Ahmedabad, Gujarat';
  h.document.getElementById('start').value = '09:30';
  h.document.getElementById('end').value = '12:30';
  h.document.getElementById('use-fields').dispatch('click');
  await settle(5);
  const written = h.document.getElementById('question').value;
  assert(/Ahmedabad, Gujarat/.test(written), 'The builder writes the box: ' + written);
  assert(/09:30 to 12:30/.test(written), 'The builder writes the window');
  assert.equal(h.calls.length, beforeBuild, 'The builder never submits by itself');
  assert(h.document.getElementById('question').focused, 'Focus moves to the box so the question stays editable');
  console.log('PASS: the field builder writes the editable question box and never submits on its own');

  // 13. a resolved point is read from the packet, or reported absent
  h = harness();
  await settle(5);
  assert.deepEqual(h.api().firstPoint(FORECAST), { latitude: 23.02579, longitude: 72.58727, label: 'Ahmedabad, Gujarāt' });
  assert.equal(h.api().firstPoint({ resolved_points: {} }), null, 'No resolved point means no collection claim');
  console.log('PASS: the resolved collection point comes from the packet, or is reported absent');
}
run().then(() => process.exit(0), error => { console.error(error); process.exit(1); });
