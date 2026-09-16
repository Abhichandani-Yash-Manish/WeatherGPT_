// Component checks for the watch inbox: outbox rows, retire, ack buttons,
// channel toggles, the coordinates create form, push binding and the watch
// deep link. Same rules as test_suite_ui.js: DOM shim with recorded payloads,
// no layout, no styling, no real endpoints.
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path'), assert = require('assert');
const shim = require('./dom_shim.js');

const ROOT = path.join(__dirname, '..');
const TOKEN = 'test-token';
const WATCH = {
  id: 'w1', created_at: '2026-09-15T08:00:00+00:00',
  question: 'Notify me if a heavy rain warning is issued for Thiruvananthapuram, Kerala tomorrow',
  place: { name: 'Thiruvananthapuram, Kerala' }, hazard: 'heavy_rain',
  window_start: null, window_end: null, state: 'matched',
  last_checked_at: '2026-09-16T09:00:00+00:00', result: null,
  channels: ['local_inbox'], consent_record: { local_inbox: { granted_at: '2026-09-15T08:00:00+00:00', source: 'explicit_chat_request' } },
  fingerprint_sha256: 'abc', outbox_pending: 1, last_notification_at: '2026-09-16T10:00:00+00:00'
};
const ROWS = [
  { id: 'o1', watch_id: 'w1', correlation_id: 'c1', fingerprint_sha256: 'abc', state: 'sent',
    channel: 'local_inbox', created_at: '2026-09-16T10:00:00+00:00', updated_at: '2026-09-16T10:00:00+00:00',
    retry_count: 0, max_retries: 3, next_retry_at: null, last_error: null },
  { id: 'o2', watch_id: 'w1', correlation_id: 'c2', fingerprint_sha256: 'def', state: 'queued',
    channel: 'local_inbox', created_at: '2026-09-16T11:00:00+00:00', updated_at: '2026-09-16T11:00:00+00:00',
    retry_count: 0, max_retries: 3, next_retry_at: null, last_error: null }
];
const PAYLOADS = {
  '/api/plans': { schema_version: 'plan-inbox-v1', mode: 'live', plans: [], notifications: [],
                  watcher: { running: false }, recorded_editions: 0, limits: [] },
  '/api/watches': { schema_version: 'watch-inbox-v1', delivery: 'local_inbox_and_opt_in_web_push', note: '',
                    checked_products: [], watches: [WATCH] },
  '/api/watches/check': { schema_version: 'watch-check-v1', delivery: 'local_inbox_and_opt_in_web_push', results: [], dispatched: [], escalated: [] },
  '/api/watches/delete': { schema_version: 'watch-check-v1', id: 'w1', state: 'expired', cancelled_notifications: 1, watches: [] },
  '/api/watches/channels': { schema_version: 'watch-channels-v1', id: 'w1', channels: ['local_inbox', 'web_push'], consent_record: {}, detail: '' },
  '/api/watches/create': { schema_version: 'watch-create-v1', id: 'w2', state: 'registered_check_on_request', hazard: 'heavy_rain', connected: true, place: {}, delivery: '', detail: '' },
  '/api/watch-health': { schema_version: 'watch-health-v1', mode: 'manual-only',
                         note: 'No hosted daemon or OS scheduler is installed.',
                         heartbeat: null, tick: { fresh: false, age_seconds: null, reason: 'no watch-check run has ever reported' },
                         outbox: { counts: { created: 0, queued: 2, claimed: 1, sent: 4, failed: 1, dead: 1, acked: 1, gone: 0 } },
                         watches: { total: 1, active: 1, expired: 0 }, plan_watcher: { running: false } },
  '/api/outbox': { schema_version: 'outbox-v1', delivery: 'local_inbox_and_opt_in_web_push', note: '', notifications: ROWS },
  '/api/outbox/o1/ack': { schema_version: 'outbox-ack-v1', id: 'o1', state: 'acked', response: 'safe', feedback_id: 'f1' },
  '/api/watches/dma': { schema_version: 'watch-dma-v2', note: 'Counts of local notifications and the responses owners sent back, broken down by official source.',
    places: [{ place: 'Thiruvananthapuram, Kerala', watches: 1, notifications: 2, acked: 1, safe: 1, need_help: 0,
               evacuating: 0, seen: 0, unacked: 1, sources: { S15: { notifications: 2, acked: 1 } } }] },
  '/api/push/unsubscribe': { endpoint: 'https://push.example.org/e1', revoked: 1, channels_removed: [] },
  '/api/push/state': { schema_version: 'push-state-v1', delivery: 'local_inbox_and_opt_in_web_push', note: '', purged_expired: 0, subscriptions: { active: 0 } },
  '/api/push/vapid-key': { schema_version: 'push-vapid-v1', public_key: 'B'.repeat(86) + 'A' },
  '/api/push/subscribe': { schema_version: 'push-subscription-v1', subscribed: true, id: 's1', watch_id: 'w1', duplicate: false, detail: '' }
};

function walk(node, out) {
  out = out || [];
  (node.children || []).forEach(child => { out.push(child); walk(child, out); });
  return out;
}
function byTag(node, tag) { return walk(node).filter(child => child.tag === tag); }
function textOf(node) { return (node && node.textContent) || ''; }
function settle(ms) { return new Promise(resolve => setTimeout(resolve, ms === undefined ? 40 : ms)); }

function harness(search) {
  const document = shim.createDocument();
  const calls = [];
  const pushManager = {
    subscription: null,
    getSubscription: async function () { return pushManager.subscription; },
    subscribe: async function () {
      pushManager.subscription = { toJSON: () => ({ endpoint: 'https://push.example.org/e1', keys: { p256dh: 'x', auth: 'y' }, expirationTime: null }) };
      return pushManager.subscription;
    }
  };
  const registration = { pushManager: pushManager };
  const context = Object.create(global);
  const define = (key, value) => Object.defineProperty(context, key, { value: value, writable: true, configurable: true, enumerable: true });
  const NotificationMock = { permission: 'granted', requestPermission: async () => 'granted' };
  const window = { addEventListener: () => {}, matchMedia: () => ({ matches: false, addEventListener: () => {} }),
                   localStorage: { getItem: () => null, setItem: () => {} },
                   location: { hash: '#/overview', search: search || '' },
                   atob: input => Buffer.from(String(input), 'base64').toString('binary'),
                   PushManager: function () {},
                   Notification: NotificationMock,
                   WG: { state: {}, panels: {} } };
  const navigator = { onLine: true,
                      serviceWorker: { register: async () => registration, getRegistration: async () => registration },
                      PushManager: function () {},
                      Notification: NotificationMock };
  define('document', document);
  define('Node', shim.Node);
  define('window', window);
  define('navigator', navigator);
  define('Notification', navigator.Notification);
  define('fetch', async (target, options) => {
    let body = null;
    try { body = options && options.body ? JSON.parse(options.body) : null; } catch (error) { body = null; }
    calls.push({ path: target, method: (options && options.method) || 'GET',
                 headers: (options && options.headers) || {}, body: body });
    const key = String(target).split('?')[0];
    if (!PAYLOADS[key]) return { ok: false, status: 404, json: async () => ({ error: 'Not found' }) };
    return { ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(PAYLOADS[key])) };
  });
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/views.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/shell.js'), 'utf8'), context);
  document.readyState = 'complete';
  return { context, document, window, calls, api: () => window.WG };
}

async function openPanel(h) {
  h.api().wireNotify();
  h.document.getElementById('notify-toggle').dispatch('click');
  await settle(60);
  return h.document.getElementById('notify-body');
}

async function run() {
  const posted = (h, path) => h.calls.filter(call => call.method === 'POST' && call.path === path);

  let h = harness('');
  let body = await openPanel(h);
  assert(/1 local watch\(es\) registered/.test(textOf(body)), 'the inbox lists the registered watch');
  assert(/local_inbox/.test(textOf(body)), 'the watch shows its delivery channels');
  assert(/2026-09-16T10:00:00/.test(textOf(body)), 'the watch shows when it last notified');
  assert(byTag(body, 'button').some(node => textOf(node) === 'Retire'), 'each watch offers Retire');
  assert(byTag(body, 'button').some(node => textOf(node) === 'Enable push'), 'each watch offers a push toggle');
  assert(byTag(body, 'button').some(node => textOf(node) === 'Safe'), 'a sent notification offers Safe');
  assert(byTag(body, 'button').some(node => textOf(node) === 'Register watch'), 'the coordinates create form is offered');
  assert(byTag(body, 'button').some(node => /^Push to /.test(textOf(node))), 'a watch without push offers binding');
  console.log('PASS: the inbox renders outbox state, channels, ack answers, toggles and the create form');

  const retire = byTag(body, 'button').find(node => textOf(node) === 'Retire');
  retire.dispatch('click');
  await settle(60);
  assert.equal(posted(h, '/api/watches/delete').length, 1, 'Retire calls the delete route');
  assert.equal(posted(h, '/api/watches/delete')[0].body.id, 'w1', 'Retire names the watch');
  console.log('PASS: Retire retires the watch through the delete route');

  h = harness('');
  body = await openPanel(h);
  byTag(body, 'button').find(node => textOf(node) === 'Safe').dispatch('click');
  await settle(60);
  assert.equal(posted(h, '/api/outbox/o1/ack').length, 1, 'Safe answers the sent notification');
  assert.equal(posted(h, '/api/outbox/o1/ack')[0].body.response, 'safe', 'the recorded response is safe');
  console.log('PASS: an ack answer reaches the ack route with its response');

  h = harness('');
  body = await openPanel(h);
  byTag(body, 'button').find(node => textOf(node) === 'Enable push').dispatch('click');
  await settle(60);
  assert.equal(posted(h, '/api/watches/channels').length, 1, 'the toggle calls the channels route');
  assert.deepEqual(posted(h, '/api/watches/channels')[0].body.channels, ['local_inbox', 'web_push'],
    'enabling push keeps the inbox and adds web_push');
  console.log('PASS: the channel toggle replaces channels through the channels route');

  h = harness('');
  body = await openPanel(h);
  const inputs = byTag(body, 'input');
  assert(inputs.length >= 4, 'the create form asks for name, coordinates and hazard');
  inputs[0].value = 'Kochi'; inputs[1].value = '9.93'; inputs[2].value = '76.27'; inputs[3].value = 'heavy rain';
  byTag(body, 'button').find(node => textOf(node) === 'Register watch').dispatch('click');
  await settle(60);
  assert.equal(posted(h, '/api/watches/create').length, 1, 'the form calls the create route');
  assert.equal(posted(h, '/api/watches/create')[0].body.place.name, 'Kochi', 'the place travels as given');
  assert.equal(posted(h, '/api/watches/create')[0].body.place.latitude, '9.93', 'coordinates travel as given');
  console.log('PASS: the coordinates form registers a watch without guessing');

  h = harness('');
  body = await openPanel(h);
  const subscribe = byTag(body, 'button').find(node => /Subscribe this browser|Enable notifications/.test(textOf(node)));
  assert(subscribe, 'the push panel offers subscription');
  subscribe.dispatch('click');
  await settle(80);
  body = h.document.getElementById('notify-body');
  const revoke = byTag(body, 'button').find(node => textOf(node) === 'Unsubscribe this browser');
  assert(revoke, 'a bound browser offers revocation, so consent is two-way');
  revoke.dispatch('click');
  await settle(80);
  assert.equal(posted(h, '/api/push/unsubscribe').length, 1, 'revocation calls the unsubscribe route');
  assert.equal(posted(h, '/api/push/unsubscribe')[0].body.endpoint, 'https://push.example.org/e1',
    'revocation names the endpoint it was granted for');
  console.log('PASS: a browser subscription can be revoked through the unsubscribe route');

  h = harness('');
  body = await openPanel(h);
  assert(/Delivery by place and source/.test(textOf(body)), 'the inbox shows the delivery aggregate');
  assert(/Thiruvananthapuram, Kerala/.test(textOf(body)), 'the aggregate names the place');
  assert(/S15/.test(textOf(body)), 'the aggregate keeps the official source dimension');
  assert(/not a receipt/i.test(textOf(body)), 'the aggregate states that a count is not a receipt');
  console.log('PASS: delivery counts are shown per place and per source with their limit');

  h = harness('');
  body = await openPanel(h);
  byTag(body, 'button').find(node => /^Push to /.test(textOf(node))).dispatch('click');
  await settle(60);
  assert.equal(posted(h, '/api/push/subscribe').length, 1, 'binding subscribes the browser');
  assert.equal(posted(h, '/api/push/subscribe')[0].body.watch_id, 'w1', 'the subscription is bound to the watch');
  console.log('PASS: per-watch binding subscribes with the watch id');

  h = harness('?watch=w1');
  h.api().wireNotify();
  await settle(60);
  assert.equal(h.document.getElementById('notify-panel').hidden, false, 'a watch deep link opens the panel');
  console.log('PASS: ?watch= opens the watch panel');

  // The panel states the supervision truth beside the outbox, so a reader cannot read a queue as a service.
  h = harness();
  const healthBody = await openPanel(h);
  const panelText = textOf(healthBody);
  assert(/No supervisor loop is installed/i.test(panelText), 'the panel says no supervisor loop is installed');
  assert(/Supervision manual-only/.test(panelText), 'the panel names the supervision mode it read');
  assert(/last check never/.test(panelText), 'a pipeline that never ran says so instead of showing a fresh tick');
  assert(/waiting 2, in flight 1, dead-lettered 1/.test(panelText), 'the outbox counts are the outbox own numbers');
  console.log('PASS: the inbox panel states the watch supervision mode and the outbox counts');

  const untokened = h.calls.filter(call => call.headers['X-WeatherGPT-Token'] !== TOKEN);
  assert.equal(untokened.length, 0, 'every request carries the workspace token');
  console.log('PASS: every notify request carries the workspace token');

  process.exit(0);
}
run().catch(error => { console.error(error); process.exit(1); });
