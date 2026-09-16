/* Parity checks for the plans, watches and notification inbox panel, ported from the vanilla component
   suite tests/test_notify_ui.js. Every payload constant below is copied verbatim from that suite, so each
   rule is held here against the same recorded reads the vanilla check used.

   Held here (5 of the suite's 11 printed checks, plus the rendering half of check 1):
   - check 2  Retire calls POST /api/watches/delete with the watch id;
   - check 4  the push toggle calls POST /api/watches/channels keeps local_inbox and adds web_push;
   - check 6  revocation calls POST /api/push/unsubscribe with the endpoint the browser was granted for;
   - check 10 watch-health's supervision mode, tick reason and per-state outbox counts are printed as returned;
   - check 11 every request carries the workspace token;
   - check 1  in part: the watch row renders its channels and last-notified instant, and the outbox rows render
              the store's own states. The React panel renders no 'n watch(es) registered' count, no ack answer
              buttons and no create form.

   Not portable, reported rather than asserted: check 3 (a 'Safe' ack over /api/outbox/<id>/ack), check 5 (the
   coordinates create form over /api/watches/create), check 7 (the per-place, per-source delivery aggregate over
   /api/watches/dma), check 8 (per-watch push binding posting watch_id), and check 9 (the ?watch= deep link that
   opens the panel: the React shell opens it from the topbar or the palette only). */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, vi } from 'vitest';
import { istStamp } from '../lib/time';
import { server } from '../test/msw';
import { PlanWatch } from './PlanWatch';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const TOKEN = 'test-token';
const WATCH = {
  id: 'w1', created_at: '2026-09-15T08:00:00+00:00',
  question: 'Notify me if a heavy rain warning is issued for Thiruvananthapuram, Kerala tomorrow',
  place: { name: 'Thiruvananthapuram, Kerala' }, hazard: 'heavy_rain',
  window_start: null, window_end: null, state: 'matched',
  last_checked_at: '2026-09-16T09:00:00+00:00', result: null,
  channels: ['local_inbox'], consent_record: { local_inbox: { granted_at: '2026-09-15T08:00:00+00:00', source: 'explicit_chat_request' } },
  fingerprint_sha256: 'abc', outbox_pending: 1, last_notification_at: '2026-09-16T10:00:00+00:00',
};
const ROWS = [
  { id: 'o1', watch_id: 'w1', correlation_id: 'c1', fingerprint_sha256: 'abc', state: 'sent',
    channel: 'local_inbox', created_at: '2026-09-16T10:00:00+00:00', updated_at: '2026-09-16T10:00:00+00:00',
    retry_count: 0, max_retries: 3, next_retry_at: null, last_error: null },
  { id: 'o2', watch_id: 'w1', correlation_id: 'c2', fingerprint_sha256: 'def', state: 'queued',
    channel: 'local_inbox', created_at: '2026-09-16T11:00:00+00:00', updated_at: '2026-09-16T11:00:00+00:00',
    retry_count: 0, max_retries: 3, next_retry_at: null, last_error: null },
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
  '/api/push/subscribe': { schema_version: 'push-subscription-v1', subscribed: true, id: 's1', watch_id: 'w1', duplicate: false, detail: '' },
};

type Seen = { path: string; method: string; token: string | null; body: unknown };
const seen: Seen[] = [];

async function note(request: Request, body: unknown = null): Promise<void> {
  seen.push({ path: new URL(request.url).pathname, method: request.method,
              token: request.headers.get('X-WeatherGPT-Token'), body });
}

function post(route: keyof typeof PAYLOADS) {
  return http.post(route, async ({ request }) => {
    let body: unknown = null;
    try { body = await request.json(); } catch { body = null; }
    await note(request, body);
    return HttpResponse.json(PAYLOADS[route]);
  });
}

function serveRecordedReads() {
  server.use(
    http.get('/api/plans', async ({ request }) => { await note(request); return HttpResponse.json(PAYLOADS['/api/plans']); }),
    http.get('/api/watches', async ({ request }) => { await note(request); return HttpResponse.json(PAYLOADS['/api/watches']); }),
    http.get('/api/outbox', async ({ request }) => { await note(request); return HttpResponse.json(PAYLOADS['/api/outbox']); }),
    http.get('/api/watch-health', async ({ request }) => { await note(request); return HttpResponse.json(PAYLOADS['/api/watch-health']); }),
    http.get('/api/push/state', async ({ request }) => { await note(request); return HttpResponse.json(PAYLOADS['/api/push/state']); }),
    post('/api/watches/delete'),
    post('/api/watches/channels'),
    post('/api/push/unsubscribe'),
  );
}

const posted = (path: string) => seen.filter(entry => entry.method === 'POST' && entry.path === path).map(entry => entry.body);
const retired = (path: string) => seen.filter(entry => entry.method === 'POST' && entry.path === path);

/* A browser that can take a push subscription: jsdom has no push APIs, so the supported branch is
   exercised with the objects a supporting browser has, removed again after the suite. */
function stubPushApis() {
  const subscription = {
    endpoint: 'https://push.example.org/e1',
    toJSON: () => ({ endpoint: 'https://push.example.org/e1', keys: { p256dh: 'x', auth: 'y' }, expirationTime: null }),
    unsubscribe: vi.fn(async () => true),
  };
  const registration = { pushManager: { subscribe: vi.fn(async () => subscription), getSubscription: vi.fn(async () => subscription) } };
  Object.defineProperty(window, 'Notification', {
    configurable: true, value: { permission: 'granted', requestPermission: vi.fn(async () => 'granted') },
  });
  Object.defineProperty(window, 'PushManager', { configurable: true, value: function PushManager() { /* the browser's own */ } });
  Object.defineProperty(navigator, 'serviceWorker', {
    configurable: true, value: { register: vi.fn(async () => registration), getRegistration: vi.fn(async () => registration) },
  });
}

function workspaceToken(): () => void {
  const meta = document.createElement('meta');
  meta.setAttribute('name', 'workspace-token');
  meta.setAttribute('content', TOKEN);
  document.head.append(meta);
  return () => meta.remove();
}

beforeEach(() => { seen.length = 0; serveRecordedReads(); });

afterEach(() => {
  ['Notification', 'PushManager'].forEach(key => Reflect.deleteProperty(window, key));
  Reflect.deleteProperty(navigator, 'serviceWorker');
});

describe('watch inbox parity', () => {
  it('retires the watch through the delete route, naming the watch it was asked to retire', async () => {
    mount(<PlanWatch onClose={() => {}} />);
    await screen.findByTestId('planwatch-watches');

    await userEvent.click(screen.getByRole('button', { name: 'Retire the watch for Thiruvananthapuram, Kerala' }));
    await screen.findByTestId('planwatch-watch-retired');

    expect(posted('/api/watches/delete')).toEqual([{ id: 'w1' }]);
  });

  it('replaces the delivery channels through the channels route, keeping the inbox and adding web_push', async () => {
    mount(<PlanWatch onClose={() => {}} />);
    await screen.findByTestId('planwatch-watches');

    await userEvent.click(screen.getByRole('button', { name: 'Enable push for Thiruvananthapuram, Kerala' }));
    await screen.findByTestId('planwatch-channels-changed');

    expect(posted('/api/watches/channels')).toEqual([{ id: 'w1', channels: ['local_inbox', 'web_push'] }]);
  });

  it('revokes the browser subscription through the unsubscribe route, naming the endpoint it was granted for', async () => {
    stubPushApis();
    mount(<PlanWatch onClose={() => {}} />);
    await screen.findByTestId('planwatch-watches');

    const revoke = await screen.findByRole('button', { name: "Revoke this browser's subscription" });
    await userEvent.click(revoke);
    await screen.findByTestId('planwatch-push-revoked');

    expect(posted('/api/push/unsubscribe')).toEqual([{ endpoint: 'https://push.example.org/e1' }]);
  });

  it('states the supervision mode and the outbox counts the health read returned, as that read returned them', async () => {
    mount(<PlanWatch onClose={() => {}} />);
    await screen.findByTestId('planwatch-watches');

    expect(await screen.findByTestId('planwatch-health-mode')).toHaveTextContent('manual-only');
    expect(screen.getByTestId('planwatch-health-note')).toHaveTextContent('No hosted daemon or OS scheduler is installed.');
    const notFresh = screen.getByTestId('planwatch-not-fresh');
    expect(notFresh).toHaveTextContent('fresh: false as this payload returns it');
    expect(notFresh).toHaveTextContent('no watch-check run has ever reported');
    expect(notFresh).toHaveTextContent('this is not a running watch service');
    expect(within(screen.getByTestId('planwatch-health-tick')).getByText('no tick has ever been reported')).toBeInTheDocument();

    /* The panel prints one row per state, so the vanilla wording ('waiting 2, in flight 1, dead-lettered 1')
       becomes the payload's own per-state numbers: queued 2, claimed 1, dead 1. */
    const counts = within(screen.getByTestId('planwatch-health-outbox'));
    const rowOf = (state: string) => counts.getByRole('rowheader', { name: state }).closest('tr') as HTMLElement;
    expect(within(rowOf('queued')).getByText('2')).toBeInTheDocument();
    expect(within(rowOf('claimed')).getByText('1')).toBeInTheDocument();
    expect(within(rowOf('dead')).getByText('1')).toBeInTheDocument();
    expect(screen.getByTestId('planwatch-health-totals')).toHaveTextContent('1 / 1 / 0');
  });

  it('renders the registered watch with its channels and last-notified instant, and the outbox states as recorded', async () => {
    mount(<PlanWatch onClose={() => {}} />);

    const watches = within(await screen.findByTestId('planwatch-watches'));
    expect(watches.getByText('Thiruvananthapuram, Kerala')).toBeInTheDocument();
    expect(watches.getByText('heavy_rain')).toBeInTheDocument();
    expect(watches.getByText('matched')).toBeInTheDocument();
    expect(watches.getByText('local_inbox')).toBeInTheDocument();
    expect(watches.getByText(istStamp(WATCH.last_checked_at))).toBeInTheDocument();
    expect(watches.getByText(istStamp(WATCH.last_notification_at))).toBeInTheDocument();

    const outbox = within(screen.getByTestId('planwatch-outbox'));
    expect(outbox.getByText('sent')).toBeInTheDocument();
    expect(outbox.getByText('queued')).toBeInTheDocument();
    expect(outbox.getAllByText('local_inbox')).toHaveLength(2);
  });

  it('carries the workspace token on every request the panel made', async () => {
    const cleanup = workspaceToken();
    try {
      mount(<PlanWatch onClose={() => {}} />);
      await screen.findByTestId('planwatch-watches');
      await userEvent.click(screen.getByRole('button', { name: 'Retire the watch for Thiruvananthapuram, Kerala' }));
      await screen.findByTestId('planwatch-watch-retired');

      const reads = new Set(seen.filter(entry => entry.method === 'GET').map(entry => entry.path));
      expect(reads).toEqual(new Set(['/api/plans', '/api/watches', '/api/outbox', '/api/watch-health', '/api/push/state']));
      expect(retired('/api/watches/delete')).toHaveLength(1);
      expect(seen.filter(entry => entry.token !== TOKEN)).toEqual([]);
      await waitFor(() => expect(seen.length).toBeGreaterThanOrEqual(6));
    } finally {
      cleanup();
    }
  });
});
