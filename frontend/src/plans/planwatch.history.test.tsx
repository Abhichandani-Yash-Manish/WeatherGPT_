/* The watch-inbox checks the port ledger names from tests/test_notify_ui.js, held against the same
   recorded payloads that vanilla suite uses:

   - check 1  the inbox renders the outbox state, the watch channels, the ack answers, the channel
              toggles and the explicit-coordinates create form;
   - the per-watch notification history: the notifications the outbox payload carries for a registered
              watch, each with its own state and the receipt facts recorded on its row. PlanWatch had no
              such block when this spec was written, so this batch adds the 'Notifications for each watch'
              section (data-testid planwatch-watch-history); this spec is its first check.

   The watch's last-notified instant itself stays in the watch row and is held by planwatch.parity.test.tsx. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { PlanWatch } from './PlanWatch';

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={client}>
      <PlanWatch onClose={() => {}} />
    </QueryClientProvider>,
  );
}

/* Copied verbatim from tests/test_notify_ui.js, so each rule is held against the same recorded read the
   vanilla check used. */
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
  '/api/watches/dma': { schema_version: 'watch-dma-v2', note: 'Counts of local notifications and the responses owners sent back, broken down by official source.',
    places: [{ place: 'Thiruvananthapuram, Kerala', watches: 1, notifications: 2, acked: 1, safe: 1, need_help: 0,
               evacuating: 0, seen: 0, unacked: 1, sources: { S15: { notifications: 2, acked: 1 } } }] },
  '/api/push/state': { schema_version: 'push-state-v1', delivery: 'local_inbox_and_opt_in_web_push', note: '', purged_expired: 0, subscriptions: { active: 0 } },
};

function serveRecordedReads() {
  server.use(
    http.get('/api/plans', () => HttpResponse.json(PAYLOADS['/api/plans'])),
    http.get('/api/watches', () => HttpResponse.json(PAYLOADS['/api/watches'])),
    http.get('/api/outbox', () => HttpResponse.json(PAYLOADS['/api/outbox'])),
    http.get('/api/watch-health', () => HttpResponse.json(PAYLOADS['/api/watch-health'])),
    http.get('/api/push/state', () => HttpResponse.json(PAYLOADS['/api/push/state'])),
    http.get('/api/watches/dma', () => HttpResponse.json(PAYLOADS['/api/watches/dma'])),
  );
}

describe('the watch inbox', () => {
  it('renders the inbox with the outbox state, channels, ack answers, toggles and the create form', async () => {
    serveRecordedReads();
    mount();

    const watches = within(await screen.findByTestId('planwatch-watches'));
    expect(watches.getByText('Thiruvananthapuram, Kerala')).toBeInTheDocument();
    expect(watches.getByText('local_inbox')).toBeInTheDocument();
    expect(watches.getByText('16 Sep 2026, 15:30 IST')).toBeInTheDocument();
    expect(watches.getByRole('button', { name: 'Retire the watch for Thiruvananthapuram, Kerala' })).toBeInTheDocument();
    expect(watches.getByRole('button', { name: 'Enable push for Thiruvananthapuram, Kerala' })).toBeInTheDocument();

    const outbox = within(screen.getByTestId('planwatch-outbox'));
    expect(outbox.getByText('sent')).toBeInTheDocument();
    expect(outbox.getByText('queued')).toBeInTheDocument();
    expect(outbox.getAllByText('local_inbox').length).toBeGreaterThanOrEqual(2);
    expect(outbox.getByRole('button', { name: 'Safe for notification o1' })).toBeInTheDocument();
    expect(outbox.getByRole('button', { name: 'Need help for notification o1' })).toBeInTheDocument();
    expect(outbox.getByRole('button', { name: 'Evacuating for notification o1' })).toBeInTheDocument();
    expect(outbox.getByRole('button', { name: 'Seen for notification o1' })).toBeInTheDocument();
    expect(outbox.getByText('only a sent row can be acknowledged; this row is queued')).toBeInTheDocument();

    const create = within(screen.getByTestId('planwatch-create'));
    expect(create.getByLabelText('Watch place name')).toBeInTheDocument();
    expect(create.getByLabelText('Latitude')).toBeInTheDocument();
    expect(create.getByLabelText('Longitude')).toBeInTheDocument();
    expect(create.getByLabelText('Hazard to watch (optional)')).toBeInTheDocument();
    expect(create.getByRole('button', { name: 'Register watch' })).toBeInTheDocument();
  });
});

describe('the per-watch notification history', () => {
  it('renders the notifications the payload carries for each watch, each with its own state and receipt facts', async () => {
    serveRecordedReads();
    mount();

    const history = within(await screen.findByTestId('planwatch-watch-history'));

    const sent = history.getByRole('row', { name: /o1/ });
    expect(sent).toHaveTextContent('Thiruvananthapuram, Kerala');
    expect(sent).toHaveTextContent('local_inbox');
    expect(sent).toHaveTextContent('sent');
    expect(sent).toHaveTextContent('16 Sep 2026, 15:30 IST');
    expect(sent).toHaveTextContent('correlation_id c1');
    expect(sent).toHaveTextContent('fingerprint abc');
    expect(sent).toHaveTextContent('retries 0 of 3');
    expect(sent).toHaveTextContent('last error no error recorded');

    const queued = history.getByRole('row', { name: /o2/ });
    expect(queued).toHaveTextContent('queued');
    expect(queued).toHaveTextContent('correlation_id c2');
    expect(queued).toHaveTextContent('fingerprint def');
    expect(queued).toHaveTextContent('16 Sep 2026, 16:30 IST');
    // Each row keeps its own facts: the neighbour's receipt is not merged into it.
    expect(queued).not.toHaveTextContent('correlation_id c1');

    expect(screen.getByTestId('planwatch-watch-history-note')).toHaveTextContent('not a claim that anyone received it');
  });
});
