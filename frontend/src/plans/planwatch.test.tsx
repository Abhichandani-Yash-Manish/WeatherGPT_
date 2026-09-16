/* The plans, watches and notification inbox panel, checked against payloads shaped like the ones the
   routes actually returned (captured from the loopback workspace while writing it:
   research/reviews/feature4-backbone-20260916/ and the watch inbox payloads in tests/test_notify_ui.js).

   The checks assert what the panel may not lose: the plans the payload returned with the state it
   states for each, a check that names what it did in the payload's own words, delivery rows printed
   exactly as returned, an empty outbox read as empty, the watch-health payload's fresh/reason/note as
   the strongest statement, a failed read rendered as the server's sentence with a retry, and a push
   control that explains itself and never claims a delivery. */
import axe from 'axe-core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, vi } from 'vitest';
import { server } from '../test/msw';
import { istStamp } from '../lib/time';
import { PlanWatch } from './PlanWatch';

function mount(node: JSX.Element) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

const PLAN_ID = '37360c1a-3d57-4605-abe3-84b89b01aff0';
const WATCH_ID = '662a6417-184e-4cc2-b6c7-d64fdf6a79d3';
const OUTBOX_ID = 'aa571362-5e53-4a1b-89c3-6ecdba476be2';
const EDITION_SHA = 'a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90';
const CHECKED_AT = '2026-09-16T22:51:26.969416+00:00';
const NOTE_TEXT = 'Monday 21 Sep for your cotton spraying in Rajkot, Gujarat changed: no warning for your watched hazards \u2192 Thunderstorm/lightning/squall (yellow). This is not an all-clear.';
const OUTBOX_NOTE = 'A notification is enqueued only when a watch check observes a changed official state; delivery is recorded per channel.';
const HEALTH_NOTE = 'No hosted daemon or OS scheduler is installed: checks run while a supervisor loop or a manual trigger fires. A stale tick means nobody is checking watches, and queued warnings wait until the next run.';
const WATCH_NOTE = 'Watches are evaluated only when asked. Opt-in Web Push requires a subscribed browser and a running check/dispatch process. A no-match result is not an all-clear, and a hazard the connected official products do not carry stays recorded as not connected.';

const plansPayload = {
  schema_version: 'plan-inbox-v1',
  mode: 'live',
  delivery: 'local_inbox_and_browser_notifications_while_the_workspace_runs',
  plans: [{
    id: PLAN_ID, label: 'cotton spraying', activity: 'spraying', hazard_codes: ['heavy_rain', 'thunderstorm'],
    kind: 'once', date_local: '2026-09-21', window_start: '2026-09-21T03:30:00+00:00',
    window_end: '2026-09-21T12:00:00+00:00', part_label: 'morning', check_in: true,
    state: 'waiting_for_coverage', not_connected: null, last_checked_at: CHECKED_AT, last_error: null,
    inferred: { activity: 'from your words: cotton spraying', hazards: 'named in your message' },
    place: 'Rajkot, Gujarat', district: 'RAJKOT', hazards: 'no connected warning category', day: 'Monday 21 Sep',
    title: 'Cotton spraying \u00b7 Rajkot, Gujarat \u00b7 Monday 21 Sep morning',
    state_words: 'waiting for IMD coverage', coverage: 'day_rows', bulletin: '20 Sep 2026 23:30 IST',
  }],
  notifications: [{
    id: 1, plan_id: PLAN_ID, kind: 'change', dedupe_key: PLAN_ID + ':change:1',
    created_at: '2026-09-16T22:51:26.969829+00:00', visible_at: '2026-09-16T22:51:26.969831+00:00',
    title: 'Monday 21 Sep \u00b7 Rajkot, Gujarat \u00b7 official warning issued', text: NOTE_TEXT, visible: true,
    receipt: {
      plan_id: PLAN_ID, place: 'Rajkot, Gujarat', district: 'RAJKOT', date: '2026-09-21', day: 2,
      hazard_codes: ['thunderstorm'], hazards: ['Thunderstorm/lightning/squall'], colour: 'yellow', colour_code: 3,
      before: 'no warning for your watched hazards', source_id: 'S63', layer: 'imd-district-warning',
      edition_sha256: EDITION_SHA, bulletin_issued_at_utc: '2026-09-20T18:00:00+00:00',
      retrieved_at_utc: '2026-09-20T18:05:00+00:00', mode: 'live', derived_window: 'bulletin_day',
      origin_authentication: 'unverified', not_established: ['Not an all-clear.', 'Not a flood or cyclone warning.', 'Not a CAP alert.'],
    },
  }],
  watcher: {
    running: true, interval_seconds: 1800,
    last_result: { checked: 1, notified: 1, read: true, error: null,
                   cycle_at_utc: '2026-09-16T22:51:26.969829+00:00', edition_sha256: EDITION_SHA },
    last_cycle_at: CHECKED_AT, last_ok_at: CHECKED_AT, last_error: null,
  },
  recorded_editions: 3,
  limits: [
    'Plans are checked against the IMD district warning product only, every 30 minutes while WeatherGPT runs.',
    'No warning for your watched hazards is not an all-clear, and origin authentication of the IMD service is unverified.',
    'Flood, cyclone and sea-area plans are recorded as not connected and are never mapped onto another product.',
    'Nothing is sent off this machine: no SMS, e-mail, push service or subscription exists.',
  ],
};

const watchesPayload = {
  schema_version: 'watch-inbox-v1',
  delivery: 'local_inbox_and_opt_in_web_push',
  note: WATCH_NOTE,
  checked_products: ['S15 IMD district warning product', 'S06 CAP relay assessment'],
  watches: [{
    id: WATCH_ID, created_at: '2026-09-16T22:51:26.968227+00:00',
    question: 'Notify me if an official heavy rain warning is issued for Thiruvananthapuram, Kerala',
    place: { name: 'Thiruvananthapuram, Kerala', state: '', district: '', kind: 'unknown',
             coordinates: { latitude: 8.5, longitude: 76.9 } },
    hazard: 'heavy_rain', window_start: null, window_end: null, state: 'registered_check_on_request',
    last_checked_at: null, result: null, fingerprint_sha256: null, channels: ['local_inbox'],
    consent_record: { local_inbox: { granted_at: '2026-09-16T22:51:26.968227+00:00', source: 'explicit_chat_request' } },
    expired: false, outbox_pending: 0, last_notification_at: null,
  }],
};

const emptyOutbox = {
  schema_version: 'outbox-v1', delivery: 'local_inbox_and_opt_in_web_push', note: OUTBOX_NOTE, notifications: [],
};

const deliveryRows = {
  ...emptyOutbox,
  notifications: [
    { id: OUTBOX_ID, watch_id: WATCH_ID, correlation_id: 'corr-1', fingerprint_sha256: 'f'.repeat(64),
      state: 'queued', channel: 'local_inbox', created_at: CHECKED_AT, updated_at: CHECKED_AT,
      retry_count: 0, max_retries: 3, next_retry_at: null, last_error: null, error_class: null },
    { id: 'b7c1f0aa-2f3d-4a6e-9f0a-1c2d3e4f5a6b', watch_id: WATCH_ID, correlation_id: 'corr-1',
      fingerprint_sha256: 'f'.repeat(64), state: 'sent', channel: 'local_inbox', created_at: CHECKED_AT,
      updated_at: CHECKED_AT, retry_count: 0, max_retries: 3, next_retry_at: null, last_error: null, error_class: null },
    { id: 'c9d2e1bb-3a4c-5b7d-8e9f-0a1b2c3d4e5f', watch_id: WATCH_ID, correlation_id: 'corr-2',
      fingerprint_sha256: 'e'.repeat(64), state: 'dead', channel: 'web_push', created_at: CHECKED_AT,
      updated_at: CHECKED_AT, retry_count: 3, max_retries: 3, next_retry_at: null,
      last_error: 'The channel is not connected in this workspace', error_class: 'channel_unavailable' },
  ],
};

const healthPayload = {
  schema_version: 'watch-health-v1',
  mode: 'manual-only',
  note: HEALTH_NOTE,
  heartbeat: null,
  tick: { fresh: false, age_seconds: null, reason: 'no watch-check run has ever reported' },
  outbox: { counts: { created: 0, queued: 1, claimed: 0, sent: 1, failed: 0, dead: 1, acked: 0, gone: 0 },
            undispatched_depth: 2, oldest_undispatched_created_at: CHECKED_AT },
  watches: { total: 1, active: 1, expired: 0 },
  plan_watcher: { running: false, interval_seconds: 1800, last_result: null },
};

const pushPayload = {
  schema_version: 'push-state-v1', delivery: 'local_inbox_and_opt_in_web_push',
  note: 'Opt-in Web Push sends encrypted messages through the browser vendor push service to subscribed browsers; the local check process must be running.',
  purged_expired: 0, subscriptions: { active: 0, expired: 0, revoked: 0 },
};

function serveReads(overrides: { plans?: unknown; watches?: unknown; outbox?: unknown; health?: unknown; push?: unknown } = {}) {
  server.use(
    http.get('/api/plans', () => HttpResponse.json(overrides.plans ?? plansPayload)),
    http.get('/api/watches', () => HttpResponse.json(overrides.watches ?? watchesPayload)),
    http.get('/api/outbox', () => HttpResponse.json(overrides.outbox ?? emptyOutbox)),
    http.get('/api/watch-health', () => HttpResponse.json(overrides.health ?? healthPayload)),
    http.get('/api/push/state', () => HttpResponse.json(overrides.push ?? pushPayload)),
  );
}

/* A browser that can take a push subscription. jsdom has no push APIs at all, so the supported branch
   is exercised by handing the panel the objects a supporting browser has, and the harness removes
   them afterwards rather than leaving a global behind for another suite. */
function stubPushApis() {
  const subscription = {
    endpoint: 'https://push.example.org/e1',
    toJSON: () => ({ endpoint: 'https://push.example.org/e1', keys: { p256dh: 'p256dh-key', auth: 'auth-key' } }),
    unsubscribe: vi.fn(async () => true),
  };
  const registration = {
    pushManager: { subscribe: vi.fn(async () => subscription), getSubscription: vi.fn(async () => subscription) },
  };
  Object.defineProperty(window, 'Notification', {
    configurable: true, value: { permission: 'granted', requestPermission: vi.fn(async () => 'granted') },
  });
  Object.defineProperty(window, 'PushManager', { configurable: true, value: function PushManager() { /* the browser's own */ } });
  Object.defineProperty(navigator, 'serviceWorker', {
    configurable: true, value: { register: vi.fn(async () => registration), getRegistration: vi.fn(async () => registration) },
  });
  return { subscription, registration };
}

afterEach(() => {
  ['Notification', 'PushManager'].forEach(key => Reflect.deleteProperty(window, key));
  Reflect.deleteProperty(navigator, 'serviceWorker');
});

beforeEach(() => { serveReads(); });

describe('the plans, watches and notification inbox panel', () => {
  it('renders the saved plans with the state the payload states, its limits, and the close control', async () => {
    const onClose = vi.fn();
    const { container } = mount(<PlanWatch onClose={onClose} />);

    expect(await screen.findByRole('heading', { level: 2, name: 'Plans, watches and the notification inbox' })).toBeInTheDocument();
    // The panel is not a surface: it carries no level-1 heading of its own.
    expect(screen.queryAllByRole('heading', { level: 1 })).toHaveLength(0);

    const table = within(await screen.findByTestId('planwatch-plans'));
    expect(table.getByText('Cotton spraying \u00b7 Rajkot, Gujarat \u00b7 Monday 21 Sep morning')).toBeInTheDocument();
    expect(table.getByText('waiting for IMD coverage')).toBeInTheDocument();
    expect(table.getByText('waiting_for_coverage')).toBeInTheDocument();
    expect(table.getByText('Rajkot, Gujarat \u00b7 RAJKOT')).toBeInTheDocument();
    expect(table.getByText('no connected warning category')).toBeInTheDocument();
    expect(table.getByText('Monday 21 Sep \u00b7 morning')).toBeInTheDocument();
    expect(table.getByText(istStamp(CHECKED_AT))).toBeInTheDocument();

    // The watcher's own numbers, and the notification with the payload's own sentence.
    expect(within(screen.getByTestId('planwatch-plan-watcher')).getByText('1800')).toBeInTheDocument();
    const notifications = within(screen.getByTestId('planwatch-notifications'));
    expect(notifications.getByText('Change')).toBeInTheDocument();
    expect(notifications.getByText(NOTE_TEXT)).toBeInTheDocument();
    expect(screen.getByTestId('planwatch-receipts')).toHaveTextContent('bulletin_issued_at_utc');
    expect(screen.getByTestId('planwatch-receipts')).toHaveTextContent('S63');
    expect(screen.getByTestId('planwatch-payload-limits')).toHaveTextContent('Plans are checked against the IMD district warning product only');
    expect(screen.getByTestId('planwatch-own-limits')).toHaveTextContent('A no-warning result is not an all-clear');

    await userEvent.click(screen.getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalledTimes(1);

    const scan = await axe.run(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(scan.violations.map(violation => violation.id).join(', ')).toBe('');
  });

  it('shows every delivery row with the state exactly as the payload returned it', async () => {
    serveReads({ outbox: deliveryRows });
    mount(<PlanWatch onClose={() => {}} />);

    const table = within(await screen.findByTestId('planwatch-outbox'));
    expect(table.getByText('queued')).toBeInTheDocument();
    expect(table.getByText('sent')).toBeInTheDocument();
    expect(table.getByText('dead')).toBeInTheDocument();
    expect(table.getByText('web_push')).toBeInTheDocument();
    expect(table.getByText('3 of 3')).toBeInTheDocument();
    expect(table.getByText('The channel is not connected in this workspace \u00b7 channel_unavailable')).toBeInTheDocument();
    expect(screen.queryByTestId('planwatch-outbox-empty')).toBeNull();
  });

  it('reads an empty outbox as empty, in words, rather than implying delivery works', async () => {
    mount(<PlanWatch onClose={() => {}} />);

    const empty = await screen.findByTestId('planwatch-outbox-empty');
    expect(empty).toHaveTextContent('The local outbox is empty');
    expect(empty).toHaveTextContent('no row returned');
    expect(empty).toHaveTextContent('it is not evidence that delivery works');
    expect(screen.queryByTestId('planwatch-outbox')).toBeNull();
    expect(screen.getByTestId('planwatch-outbox-note')).toHaveTextContent(OUTBOX_NOTE);
  });

  it('states supervision as the watch-health payload does: fresh false, its reason, and no healthy reading', async () => {
    mount(<PlanWatch onClose={() => {}} />);

    const notFresh = await screen.findByTestId('planwatch-not-fresh');
    expect(notFresh).toHaveTextContent('fresh: false as this payload returns it');
    expect(notFresh).toHaveTextContent('no watch-check run has ever reported');
    expect(notFresh).toHaveTextContent('this is not a running watch service');

    const facts = within(screen.getByTestId('planwatch-health-tick'));
    expect(facts.getByText('fresh (as returned)')).toBeInTheDocument();
    expect(facts.getByText('false')).toBeInTheDocument();
    expect(facts.getByText('no watch-check run has ever reported')).toBeInTheDocument();
    expect(facts.getByText('no tick has ever been reported')).toBeInTheDocument();
    expect(screen.getByTestId('planwatch-health-mode')).toHaveTextContent('manual-only');
    expect(screen.getByTestId('planwatch-health-note')).toHaveTextContent(HEALTH_NOTE);
    expect(within(screen.getByTestId('planwatch-health-outbox')).getByText('dead')).toBeInTheDocument();
    expect(screen.getByTestId('planwatch-health-totals')).toHaveTextContent('1 / 1 / 0');
    expect(screen.getByTestId('planwatch-health-totals')).toHaveTextContent('1800');

    // Nothing on the panel may be read as a running service.
    expect(screen.queryByText(/fresh: true/)).toBeNull();
    expect(document.body.textContent).not.toMatch(/checks are running on schedule|watch service is running/i);
  });

  it('renders a failed read as the server’s own sentence, with a retry that re-reads it', async () => {
    let calls = 0;
    server.use(http.get('/api/plans', () => {
      calls += 1;
      if (calls === 1) return HttpResponse.json({ error: 'the plan store could not be opened' }, { status: 503 });
      return HttpResponse.json(plansPayload);
    }));
    mount(<PlanWatch onClose={() => {}} />);

    const failure = await screen.findByRole('alert');
    expect(failure).toHaveTextContent('The local evidence store is unavailable');
    expect(failure).toHaveTextContent('the plan store could not be opened');
    await userEvent.click(within(failure).getByRole('button', { name: 'Retry this read' }));

    expect(await screen.findByTestId('planwatch-plans')).toBeInTheDocument();
    expect(calls).toBe(2);
  });

  it('runs one plan check and names what it did with the payload’s own sentences and values', async () => {
    const posted: unknown[] = [];
    const results = [
      { checked: 1, notified: 0, read: false,
        error: 'The live read failed and only a cached copy of the product was available.',
        cycle_at_utc: '2026-09-16T23:10:00+00:00', edition_sha256: null },
      { checked: 2, notified: 1, read: true, error: null,
        cycle_at_utc: '2026-09-16T23:40:00+00:00', edition_sha256: EDITION_SHA },
    ];
    let calls = 0;
    server.use(http.post('/api/plans/check', async ({ request }) => {
      posted.push(await request.json());
      const result = results[Math.min(calls, results.length - 1)];
      calls += 1;
      return HttpResponse.json({ schema_version: 'plan-check-v1', result });
    }));
    mount(<PlanWatch onClose={() => {}} />);

    await userEvent.click(await screen.findByRole('button', { name: 'Check saved plans now' }));
    const result = await screen.findByTestId('planwatch-check-result');
    expect(result).toHaveTextContent('its own sentence about the read is: The live read failed and only a cached copy of the product was available.');
    const firstFacts = within(screen.getByTestId('planwatch-check-facts'));
    expect(firstFacts.getByText('read (as returned)')).toBeInTheDocument();
    expect(firstFacts.getByText('false')).toBeInTheDocument();
    expect(firstFacts.getByText(istStamp('2026-09-16T23:10:00+00:00'))).toBeInTheDocument();

    // A second press asks again and reports the second cycle's own result.
    await userEvent.click(screen.getByRole('button', { name: 'Check saved plans now' }));
    expect(await screen.findByText('The check ran: the district warning product was read in this cycle and the plans were evaluated against it.')).toBeInTheDocument();
    const secondFacts = within(screen.getByTestId('planwatch-check-facts'));
    expect(secondFacts.getByText('checked (as returned)')).toBeInTheDocument();
    expect(secondFacts.getByText('2')).toBeInTheDocument();

    expect(posted).toEqual([{}, {}]);
    // The changes a check reports are the notification rows, in the payload's own words.
    expect(screen.getByTestId('planwatch-notifications')).toHaveTextContent(NOTE_TEXT);
  });

  it('explains the browser-push control as a consented local action and claims no delivery', async () => {
    mount(<PlanWatch onClose={() => {}} />);

    const state = await screen.findByTestId('planwatch-push-state');
    expect(state).toHaveTextContent('Subscriptions this read counts as active');
    expect(state).toHaveTextContent('local_inbox_and_opt_in_web_push');
    expect(state).toHaveTextContent('the local check process must be running');

    expect(screen.getByTestId('planwatch-push-what-it-is')).toHaveTextContent('an opt-in channel for one browser on this machine');
    const isNot = screen.getByTestId('planwatch-push-what-it-is-not');
    expect(isNot).toHaveTextContent('SMS, IVR, WhatsApp and e-mail are not connected channels');
    expect(isNot).toHaveTextContent('A stored subscription is a consent record, not a delivery');
    expect(isNot).toHaveTextContent('this panel claims no notification has been delivered');

    // jsdom offers no push APIs, so no subscribe control is offered — and the panel says why.
    expect(screen.getByTestId('planwatch-push-unsupported')).toHaveTextContent('cannot take a push subscription');
    expect(screen.queryByRole('button', { name: 'Subscribe this browser for push' })).toBeNull();
    expect(document.body.textContent).not.toMatch(/delivery succeeded|notification was sent|we sent you|delivered to you|delivery is working/i);
  });

  it('subscribes and revokes this browser only through the consented local routes', async () => {
    const posted: unknown[] = [];
    server.use(
      http.get('/api/push/vapid-key', () => HttpResponse.json({ schema_version: 'push-vapid-v1', public_key: 'BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBA' })),
      http.post('/api/push/subscribe', async ({ request }) => {
        posted.push(await request.json());
        return HttpResponse.json({ schema_version: 'push-subscription-v1', subscribed: true, id: 'sub-1', watch_id: null,
                                   duplicate: false, detail: 'Stored without a watch binding; enable push per watch from the inbox.' });
      }),
      http.post('/api/push/unsubscribe', async ({ request }) => {
        posted.push(await request.json());
        return HttpResponse.json({ endpoint: 'https://push.example.org/e1', revoked: 1, channels_removed: ['web_push'] });
      }),
    );
    stubPushApis();
    mount(<PlanWatch onClose={() => {}} />);

    await userEvent.click(await screen.findByRole('button', { name: 'Subscribe this browser for push' }));
    const subscribed = await screen.findByTestId('planwatch-push-subscribed');
    expect(subscribed).toHaveTextContent('Stored without a watch binding');
    expect(subscribed).toHaveTextContent('does not say a notification was delivered');
    expect(screen.getByText(/Permission this browser reports/)).toHaveTextContent('granted');

    await userEvent.click(screen.getByRole('button', { name: "Revoke this browser's subscription" }));
    const revoked = await screen.findByTestId('planwatch-push-revoked');
    expect(revoked).toHaveTextContent('revoked: 1');
    expect(revoked).toHaveTextContent('web_push');
    expect(revoked).toHaveTextContent('A revoked subscription is no longer an active channel in this workspace');

    expect(posted).toEqual([
      { endpoint: 'https://push.example.org/e1', keys: { p256dh: 'p256dh-key', auth: 'auth-key' }, expirationTime: null, watch_id: null },
      { endpoint: 'https://push.example.org/e1' },
    ]);
  });

  it('lists the registered watch requests and changes them only through the watch routes', async () => {
    const posted: { path: string; body: unknown }[] = [];
    server.use(
      http.post('/api/watches/delete', async ({ request }) => {
        posted.push({ path: '/api/watches/delete', body: await request.json() });
        return HttpResponse.json({ id: WATCH_ID, state: 'expired', cancelled_notifications: 0, watches: [] });
      }),
      http.post('/api/watches/channels', async ({ request }) => {
        posted.push({ path: '/api/watches/channels', body: await request.json() });
        return HttpResponse.json({ schema_version: 'watch-channels-v1', id: WATCH_ID, channels: ['local_inbox', 'web_push'],
                                   detail: 'Delivery channels replaced; consent entries follow real grants only.' });
      }),
    );
    mount(<PlanWatch onClose={() => {}} />);

    const table = within(await screen.findByTestId('planwatch-watches'));
    expect(table.getByText('Thiruvananthapuram, Kerala')).toBeInTheDocument();
    expect(table.getByText('heavy_rain')).toBeInTheDocument();
    expect(table.getByText('registered_check_on_request')).toBeInTheDocument();
    expect(table.getByText('local_inbox')).toBeInTheDocument();
    expect(table.getByText('never notified')).toBeInTheDocument();
    expect(screen.getByTestId('planwatch-watches-note')).toHaveTextContent(WATCH_NOTE);

    await userEvent.click(table.getByRole('button', { name: 'Retire the watch for Thiruvananthapuram, Kerala' }));
    expect(await screen.findByTestId('planwatch-watch-retired')).toHaveTextContent('notifications cancelled as returned 0');

    await userEvent.click(within(screen.getByTestId('planwatch-watches')).getByRole('button', { name: 'Enable push for Thiruvananthapuram, Kerala' }));
    expect(await screen.findByTestId('planwatch-channels-changed')).toHaveTextContent('Delivery channels replaced');

    expect(posted).toEqual([
      { path: '/api/watches/delete', body: { id: WATCH_ID } },
      { path: '/api/watches/channels', body: { id: WATCH_ID, channels: ['local_inbox', 'web_push'] } },
    ]);
  });
});
