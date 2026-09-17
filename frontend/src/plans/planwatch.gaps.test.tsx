/* The four notify checks the port ledger could not claim when the React panel was written, held here
   against the same recorded payloads the vanilla component suite tests/test_notify_ui.js used:

   - check 3  a sent delivery row is acknowledged over POST /api/outbox/<id>/ack with the answer the reader
              chose (safe, need_help, evacuating, seen), and the server's own reply is printed;
   - check 5  the explicit-coordinates form posts to /api/watches/create with the name and coordinates as
              given and no district guessed, and the route's own refusal is printed when it refuses;
   - check 7  GET /api/watches/dma is rendered as its own table with the payload's own labels and counts,
              and a count is stated as a count of local rows, never a delivery claim;
   - check 8  the per-watch binding subscribes with watch_id, and the panel says the binding delivers
              nothing by itself.

   Every payload constant below is copied verbatim from tests/test_notify_ui.js, so each rule is held
   against the same recorded reads the vanilla check used. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, vi } from 'vitest';
import { server } from '../test/msw';
import { PlanWatch } from './PlanWatch';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

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
  '/api/watch-health': { schema_version: 'watch-health-v1', mode: 'manual-only',
                         note: 'No hosted daemon or OS scheduler is installed.',
                         heartbeat: null, tick: { fresh: false, age_seconds: null, reason: 'no watch-check run has ever reported' },
                         outbox: { counts: { created: 0, queued: 2, claimed: 1, sent: 4, failed: 1, dead: 1, acked: 1, gone: 0 } },
                         watches: { total: 1, active: 1, expired: 0 }, plan_watcher: { running: false } },
  '/api/outbox': { schema_version: 'outbox-v1', delivery: 'local_inbox_and_opt_in_web_push', note: '', notifications: ROWS },
  '/api/outbox/o1/ack': { schema_version: 'outbox-ack-v1', id: 'o1', state: 'acked', response: 'safe', feedback_id: 'f1' },
  '/api/watches/create': { schema_version: 'watch-create-v1', id: 'w2', state: 'registered_check_on_request', hazard: 'heavy_rain', connected: true, place: {}, delivery: '', detail: '' },
  '/api/watches/dma': { schema_version: 'watch-dma-v2', note: 'Counts of local notifications and the responses owners sent back, broken down by official source.',
    places: [{ place: 'Thiruvananthapuram, Kerala', watches: 1, notifications: 2, acked: 1, safe: 1, need_help: 0,
               evacuating: 0, seen: 0, unacked: 1, sources: { S15: { notifications: 2, acked: 1 } } }] },
  '/api/push/state': { schema_version: 'push-state-v1', delivery: 'local_inbox_and_opt_in_web_push', note: '', purged_expired: 0, subscriptions: { active: 0 } },
  '/api/push/vapid-key': { schema_version: 'push-vapid-v1', public_key: 'B'.repeat(86) + 'A' },
  '/api/push/subscribe': { schema_version: 'push-subscription-v1', subscribed: true, id: 's1', watch_id: 'w1', duplicate: false, detail: '' },
};

type Seen = { path: string; method: string; body: unknown };
const seen: Seen[] = [];

async function note(request: Request, body: unknown = null): Promise<void> {
  seen.push({ path: new URL(request.url).pathname, method: request.method, body });
}

function recordedPost(route: keyof typeof PAYLOADS) {
  return http.post(route, async ({ request }) => {
    let body: unknown = null;
    try { body = await request.json(); } catch { body = null; }
    await note(request, body);
    return HttpResponse.json(PAYLOADS[route]);
  });
}

function serveRecordedReads() {
  server.use(
    http.get('/api/plans', () => HttpResponse.json(PAYLOADS['/api/plans'])),
    http.get('/api/watches', () => HttpResponse.json(PAYLOADS['/api/watches'])),
    http.get('/api/watch-health', () => HttpResponse.json(PAYLOADS['/api/watch-health'])),
    http.get('/api/outbox', () => HttpResponse.json(PAYLOADS['/api/outbox'])),
    http.get('/api/watches/dma', () => HttpResponse.json(PAYLOADS['/api/watches/dma'])),
    http.get('/api/push/state', () => HttpResponse.json(PAYLOADS['/api/push/state'])),
    http.get('/api/push/vapid-key', () => HttpResponse.json(PAYLOADS['/api/push/vapid-key'])),
    recordedPost('/api/outbox/o1/ack'),
    recordedPost('/api/watches/create'),
    recordedPost('/api/push/subscribe'),
  );
}

const posted = (path: string) => seen.filter(entry => entry.method === 'POST' && entry.path === path).map(entry => entry.body);

/* jsdom carries no push APIs, so the supported branch is exercised with the objects a supporting browser
   has, removed again after each check. */
function stubPushApis(): void {
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

beforeEach(() => { seen.length = 0; serveRecordedReads(); });

afterEach(() => {
  ['Notification', 'PushManager'].forEach(key => Reflect.deleteProperty(window, key));
  Reflect.deleteProperty(navigator, 'serviceWorker');
});

describe('the notify gaps the vanilla checks named', () => {
  it('answers a sent delivery row through its own ack route with the reader’s chosen answer, and prints the server’s reply', async () => {
    mount(<PlanWatch onClose={() => {}} />);

    const meaning = await screen.findByTestId('planwatch-ack-what-it-means');
    expect(meaning).toHaveTextContent('the reader telling this workspace what they did');
    expect(meaning).toHaveTextContent('not an instruction to anyone else');

    await userEvent.click(screen.getByRole('button', { name: 'Safe for notification o1' }));
    const recorded = await screen.findByTestId('planwatch-ack-recorded');

    expect(posted('/api/outbox/o1/ack')).toEqual([{ response: 'safe' }]);
    expect(recorded).toHaveTextContent('is returned state acked');
    expect(recorded).toHaveTextContent('response as returned safe');
    expect(recorded).toHaveTextContent('feedback_id as returned f1');
    expect(recorded).toHaveTextContent('nothing was sent to anyone else');
  });

  it('offers the acknowledgement only on a sent row, with every answer the store accepts', async () => {
    mount(<PlanWatch onClose={() => {}} />);

    const outbox = within(await screen.findByTestId('planwatch-outbox'));
    const sentRow = outbox.getByText('sent').closest('tr') as HTMLElement;
    const queuedRow = outbox.getByText('queued').closest('tr') as HTMLElement;

    ['Safe', 'Need help', 'Evacuating', 'Seen'].forEach(label => {
      expect(within(sentRow).getByRole('button', { name: label + ' for notification o1' })).toBeInTheDocument();
    });
    expect(within(queuedRow).queryByRole('button')).toBeNull();
    expect(queuedRow).toHaveTextContent('only a sent row can be acknowledged');

    await userEvent.click(within(sentRow).getByRole('button', { name: 'Need help for notification o1' }));
    await screen.findByTestId('planwatch-ack-recorded');
    expect(posted('/api/outbox/o1/ack')).toEqual([{ response: 'need_help' }]);
  });

  it('binds this browser’s subscription to one watch through the subscribe route, and says the binding delivers nothing by itself', async () => {
    stubPushApis();
    mount(<PlanWatch onClose={() => {}} />);

    const note = await screen.findByTestId('planwatch-watch-push-binding-note');
    expect(note).toHaveTextContent('binds this browser\'s push subscription to that one watch');
    expect(note).toHaveTextContent('delivers nothing by itself');
    expect(note).toHaveTextContent('consent record, not a delivery');

    await userEvent.click(screen.getByRole('button', { name: 'Push to Thiruvananthapuram, Kerala' }));
    const bound = await screen.findByTestId('planwatch-watch-push-bound');

    expect(posted('/api/push/subscribe')).toEqual([{
      endpoint: 'https://push.example.org/e1',
      keys: { p256dh: 'x', auth: 'y' },
      expirationTime: null,
      watch_id: 'w1',
    }]);
    expect(bound).toHaveTextContent('watch_id as returned w1');
    expect(bound).toHaveTextContent('delivers nothing by itself');
    expect(screen.queryByTestId('planwatch-push-subscribed')).toBeNull();
  });

  it('renders the per-place delivery aggregate with the payload’s own labels and counts, and says it is not a delivery claim', async () => {
    mount(<PlanWatch onClose={() => {}} />);

    expect(await screen.findByRole('heading', { name: 'Delivery by place and source' })).toBeInTheDocument();
    const places = within(await screen.findByTestId('planwatch-dma-places'));
    ['place', 'watches', 'notifications', 'acked', 'safe', 'need_help', 'evacuating', 'seen', 'unacked'].forEach(label => {
      expect(places.getByRole('columnheader', { name: label })).toBeInTheDocument();
    });
    const placeRow = places.getByRole('rowheader', { name: 'Thiruvananthapuram, Kerala' }).closest('tr') as HTMLElement;
    expect(within(placeRow).getByText('2')).toBeInTheDocument();
    expect(within(placeRow).getAllByText('1')).toHaveLength(4);
    expect(within(placeRow).getAllByText('0')).toHaveLength(3);

    const sources = within(screen.getByTestId('planwatch-dma-sources'));
    const sourceRow = sources.getByText('S15').closest('tr') as HTMLElement;
    expect(within(sourceRow).getByText('2')).toBeInTheDocument();
    expect(within(sourceRow).getByText('1')).toBeInTheDocument();

    expect(screen.getByTestId('planwatch-dma-note')).toHaveTextContent(PAYLOADS['/api/watches/dma'].note);
    const limit = screen.getByTestId('planwatch-dma-limit');
    expect(limit).toHaveTextContent('not a receipt');
    expect(limit).toHaveTextContent('counts rows this machine produced');
    expect(limit).toHaveTextContent('never a delivery claim');
  });

  it('registers one watch from explicit coordinates, sending them as given, and says no coordinate is turned into a district here', async () => {
    mount(<PlanWatch onClose={() => {}} />);

    const note = await screen.findByTestId('planwatch-create-note');
    expect(note).toHaveTextContent('registers one watch for this machine');
    expect(note).toHaveTextContent('turns no coordinate into a district');
    expect(note).toHaveTextContent('The engine resolves names');

    await userEvent.type(screen.getByLabelText('Watch place name'), 'Kochi');
    await userEvent.type(screen.getByLabelText('Latitude'), '9.93');
    await userEvent.type(screen.getByLabelText('Longitude'), '76.27');
    await userEvent.type(screen.getByLabelText('Hazard to watch (optional)'), 'heavy rain');
    await userEvent.click(screen.getByRole('button', { name: 'Register watch' }));

    const created = await screen.findByTestId('planwatch-watch-created');
    expect(posted('/api/watches/create')).toEqual([{
      place: { name: 'Kochi', latitude: '9.93', longitude: '76.27' },
      hazard: 'heavy rain',
    }]);
    expect(created).toHaveTextContent('registered_check_on_request');
    expect(created).toHaveTextContent('hazard as returned heavy_rain');
    expect(created).toHaveTextContent('connected as returned true');
    expect(created).toHaveTextContent('Its own detail line: this read returned no detail line');
  });

  it('prints the create route’s own refusal, with a retry that sends the same request again', async () => {
    server.use(http.post('/api/watches/create', async ({ request }) => {
      let body: unknown = null;
      try { body = await request.json(); } catch { body = null; }
      await note(request, body);
      return HttpResponse.json({ error: 'Give numeric latitude and longitude' }, { status: 400 });
    }));
    mount(<PlanWatch onClose={() => {}} />);

    await screen.findByTestId('planwatch-create');
    await userEvent.type(screen.getByLabelText('Watch place name'), 'Kochi');
    await userEvent.click(screen.getByRole('button', { name: 'Register watch' }));

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('Give numeric latitude and longitude');
    expect(failure).toHaveTextContent('nothing was registered');
    expect(screen.getByLabelText('Watch place name')).toHaveValue('Kochi');

    await userEvent.click(screen.getByRole('button', { name: 'Retry this registration' }));
    await waitFor(() => expect(posted('/api/watches/create')).toHaveLength(2));
    expect(posted('/api/watches/create')).toEqual([
      { place: { name: 'Kochi', latitude: '', longitude: '' }, hazard: null },
      { place: { name: 'Kochi', latitude: '', longitude: '' }, hazard: null },
    ]);
  });
});
