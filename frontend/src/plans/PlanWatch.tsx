/* The plans, watches and notification inbox panel.

   This is not a surface: the registry keeps its nineteen public views, and the vanilla frontend opened
   this content as a modal. So the panel carries its own level-2 heading and a Close control, and the
   host decides how it is mounted (a native dialog keeps focus and Escape with the browser).

   Every value below is a value a route returned: /api/plans for saved plans, their notifications and
   the plan watcher; /api/watches for the registered watch requests and the products they are checked
   against; /api/outbox for the delivery rows and /api/outbox/<id>/ack for a reader's answer to one of
   them; /api/watches/dma for the per-place delivery aggregate; /api/watch-health for the supervision
   truth; /api/watches/create for registering one watch from explicit coordinates; and /api/push/state
   with /api/push/subscribe for the consented browser-push record. The panel's own words are about what
   it does and does not do. It publishes nothing, sends nothing to anyone else, and no result here is an
   all-clear. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent, type ReactNode } from 'react';
import { ApiError, getJson, postJson } from '../api/client';
import { count, orNot, shortHash } from '../lib/format';
import { istStamp } from '../lib/time';
import {
  ColourTag, DataTable, Facts, Failure, NO_ROW, NOT_RECORDED, Reading, failureSentence,
} from '../modules/Evidence';
import './plans.css';

type PlanNotification = {
  id?: number | string;
  plan_id?: string;
  kind?: string;
  dedupe_key?: string;
  created_at?: string;
  visible_at?: string;
  visible?: boolean;
  title?: string;
  text?: string;
  receipt?: Record<string, unknown>;
};

type SavedPlan = {
  id?: string;
  title?: string;
  label?: string;
  activity?: string;
  kind?: string;
  state?: string;
  state_words?: string;
  hazards?: string;
  hazard_codes?: string[];
  place?: string;
  district?: string;
  day?: string;
  date_local?: string;
  part_label?: string;
  not_connected?: string | null;
  last_checked_at?: string | null;
  last_error?: string | null;
  coverage?: unknown;
  bulletin?: string | null;
};

type PlanWatcher = {
  running?: boolean;
  interval_seconds?: number;
  last_result?: unknown;
  last_cycle_at?: string | null;
  last_ok_at?: string | null;
  last_error?: string | null;
};

type PlansView = {
  schema_version?: string;
  mode?: string;
  delivery?: string;
  plans?: SavedPlan[];
  notifications?: PlanNotification[];
  watcher?: PlanWatcher;
  recorded_editions?: number;
  limits?: string[];
};

type PlanCheckView = {
  schema_version?: string;
  result?: { checked?: number; notified?: number; read?: boolean | null; error?: string | null;
             cycle_at_utc?: string; edition_sha256?: string | null };
};

type OutboxRow = {
  id?: string;
  watch_id?: string;
  correlation_id?: string;
  fingerprint_sha256?: string;
  state?: string;
  channel?: string;
  created_at?: string;
  updated_at?: string;
  retry_count?: number;
  max_retries?: number;
  next_retry_at?: string | null;
  last_error?: string | null;
  error_class?: string | null;
};

type OutboxView = { schema_version?: string; delivery?: string; note?: string; notifications?: OutboxRow[] };

type WatchRow = {
  id?: string;
  created_at?: string;
  question?: string;
  place?: { name?: string; label?: string; district?: string; state?: string };
  hazard?: string;
  window_start?: string | null;
  window_end?: string | null;
  state?: string;
  last_checked_at?: string | null;
  channels?: string[];
  consent_record?: Record<string, unknown>;
  expired?: boolean;
  outbox_pending?: number;
  last_notification_at?: string | null;
  not_connected?: string[];
};

type WatchesView = {
  schema_version?: string;
  delivery?: string;
  note?: string;
  checked_products?: string[];
  watches?: WatchRow[];
};

type WatchCheckView = {
  schema_version?: string;
  delivery?: string;
  note?: string;
  results?: { id?: string; state?: string; matched?: boolean; detail?: string }[];
  dispatched?: unknown[];
  escalated?: unknown[];
};

type WatchDeleteView = { id?: string; state?: string; cancelled_notifications?: number; watches?: WatchRow[] };

type WatchChannelsView = { schema_version?: string; id?: string; channels?: string[]; detail?: string };

type WatchHealthView = {
  schema_version?: string;
  mode?: string;
  note?: string;
  heartbeat?: { tick_at_utc?: string; trigger?: string; stale_after_seconds?: number; checked?: number;
                enqueued?: number; dispatched?: number; escalated?: number } | null;
  tick?: { fresh?: boolean; age_seconds?: number | null; reason?: string };
  outbox?: { counts?: Record<string, number>; undispatched_depth?: number; oldest_undispatched_created_at?: string | null };
  watches?: { total?: number; active?: number; expired?: number };
  plan_watcher?: { running?: boolean; interval_seconds?: number; last_result?: unknown };
};

type PushStateView = {
  schema_version?: string;
  delivery?: string;
  note?: string;
  purged_expired?: number;
  subscriptions?: { active?: number; expired?: number; revoked?: number };
};

type VapidView = { schema_version?: string; public_key?: string };
type PushSubscribeView = { schema_version?: string; subscribed?: boolean; id?: string; watch_id?: string | null;
                           duplicate?: boolean; detail?: string };
type PushUnsubscribeView = { endpoint?: string; revoked?: number; channels_removed?: string[] };

/* The acknowledgement route returns the store's own record of the answer. */
type OutboxAckView = { schema_version?: string; id?: string; state?: string; response?: string; feedback_id?: string };

/* The create route stores exactly the coordinates it was sent and resolves no district itself. */
type WatchCreateView = {
  schema_version?: string;
  id?: string;
  state?: string;
  hazard?: string;
  connected?: boolean;
  place?: { name?: string; label?: string; district?: string; state?: string };
  delivery?: string;
  detail?: string;
};

type WatchDmaSource = { notifications?: number; acked?: number };

type WatchDmaPlace = {
  place?: string;
  watches?: number;
  notifications?: number;
  acked?: number;
  safe?: number;
  need_help?: number;
  evacuating?: number;
  seen?: number;
  unacked?: number;
  sources?: Record<string, WatchDmaSource>;
};

type WatchDmaView = { schema_version?: string; note?: string; places?: WatchDmaPlace[] };

/* The outbox's own states, in the order the store declares them; a row's state is always printed as
   the string the payload returned, never mapped onto a friendlier word. */
const OUTBOX_STATES = ['created', 'queued', 'claimed', 'sent', 'failed', 'dead', 'acked', 'gone'];

/* The answers the outbox store accepts, in the order weathergpt_data/outbox.py declares them. Each one is
   the reader's report of what they did, never an instruction to anyone else. */
const ACK_ANSWERS: [string, string][] = [
  ['safe', 'Safe'],
  ['need_help', 'Need help'],
  ['evacuating', 'Evacuating'],
  ['seen', 'Seen'],
];
const KIND_WORDS: Record<string, string> = { change: 'Change', check_in: 'Evening check-in', degraded: 'Watch degraded' };

function kindWords(kind?: string): string {
  return KIND_WORDS[kind || ''] || orNot(kind, 'kind not returned');
}

/* A receipt field is printed as the payload returned it. Only three things are formatted: an instant
   becomes the IST stamp every other surface prints, a hash is shortened, and a colour is drawn as a
   hazard chip only when it is one of the four the design system reserves for a stated warning state. */
function receiptValue(key: string, value: unknown): ReactNode {
  if (value === null || value === undefined || value === '') return NOT_RECORDED;
  if (Array.isArray(value)) return value.length ? value.join(', ') : NO_ROW;
  if (typeof value === 'object') return JSON.stringify(value);
  if (key === 'colour') return <ColourTag colour={String(value)} text={String(value)} />;
  if (key.endsWith('_at_utc')) return istStamp(String(value));
  if (key.endsWith('_sha256')) return <span className="evidence">{shortHash(String(value), 16)}</span>;
  return String(value);
}

function watcherResult(result: unknown): string {
  if (!result || typeof result !== 'object') return NOT_RECORDED;
  const row = result as Record<string, unknown>;
  const parts = ['checked', 'notified', 'read', 'error', 'cycle_at_utc', 'edition_sha256']
    .filter(key => row[key] !== undefined && row[key] !== null && String(row[key]) !== '')
    .map(key => key + ': ' + (key === 'edition_sha256' ? shortHash(String(row[key]), 16)
      : key === 'cycle_at_utc' ? istStamp(String(row[key])) : String(row[key])));
  return parts.length ? parts.join(' · ') : NOT_RECORDED;
}

function placeWords(watch: WatchRow): string {
  return orNot(watch.place?.label || watch.place?.name, 'place not returned');
}

/* The first column of the watch table identifies the request even when the read attached no place for
   it: an identifier is a fallback for a name, never the other way round. */
function watchLabel(watch: WatchRow): string {
  return orNot(watch.place?.label || watch.place?.name, shortHash(String(watch.id ?? ''), 8));
}

/* Browser APIs are read from the browser, never assumed. A control that cannot work is stated as
   unsupported with the reason, rather than offered and then failed. */
function browserPushSupport(): string | null {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return 'this browser has no service worker API';
  if (!('PushManager' in window)) return 'this browser has no push manager';
  if (!('Notification' in window)) return 'this browser has no notification API';
  return null;
}

/* The VAPID key crosses as URL-safe base64; the push manager needs the bytes. The return type names
   the ArrayBuffer exactly, because the subscription options accept a BufferSource and not the shared
   variant. */
function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4);
  const raw = window.atob(base64.replace(/-/g, '+').replace(/_/g, '/') + padding);
  const bytes = new Uint8Array(raw.length);
  for (let index = 0; index < raw.length; index += 1) bytes[index] = raw.charCodeAt(index);
  return bytes;
}

async function browserSubscriptionEndpoint(): Promise<string> {
  const registration = await navigator.serviceWorker.getRegistration('/sw.js');
  const subscription = registration ? await registration.pushManager.getSubscription() : null;
  const raw = subscription ? subscription.toJSON() : null;
  const endpoint = raw?.endpoint || subscription?.endpoint;
  if (!endpoint) throw new Error('This browser reports no push subscription for this workspace, so there is nothing to revoke.');
  return String(endpoint);
}

/* A refused browser action has no server sentence to print, so the browser's own message is printed
   as the browser's, with the retry that any failed action is offered. */
function browserSentence(error: unknown): string {
  const message = (error as Error)?.message;
  if (error instanceof ApiError || !message || !message.trim()) return failureSentence(error);
  return 'The browser did not complete this action: ' + message;
}

function withWebPush(channels: string[] | undefined, wanted: boolean): string[] {
  const current = channels && channels.length ? channels : ['local_inbox'];
  if (wanted) return current.indexOf('web_push') >= 0 ? current : current.concat(['web_push']);
  return current.filter(channel => channel !== 'web_push');
}

export function PlanWatch({ onClose }: { onClose: () => void }): JSX.Element {
  const client = useQueryClient();
  const plans = useQuery({ queryKey: ['plans'], queryFn: () => getJson<PlansView>('/api/plans'), retry: false });
  const watches = useQuery({ queryKey: ['watches'], queryFn: () => getJson<WatchesView>('/api/watches'), retry: false });
  const outbox = useQuery({ queryKey: ['outbox'], queryFn: () => getJson<OutboxView>('/api/outbox'), retry: false });
  const health = useQuery({ queryKey: ['watch-health'], queryFn: () => getJson<WatchHealthView>('/api/watch-health'), retry: false });
  const push = useQuery({ queryKey: ['push-state'], queryFn: () => getJson<PushStateView>('/api/push/state'), retry: false });
  const dma = useQuery({ queryKey: ['watches-dma'], queryFn: () => getJson<WatchDmaView>('/api/watches/dma'), retry: false });

  /* The coordinate form keeps what was typed: the route stores the name and coordinates as given and
     refuses what it cannot read, so nothing here parses a coordinate or resolves a district first. */
  const [placeName, setPlaceName] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [hazard, setHazard] = useState('');

  const checkPlans = useMutation({
    mutationFn: () => postJson<PlanCheckView>('/api/plans/check', {}),
    retry: false,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['plans'] });
      void client.invalidateQueries({ queryKey: ['outbox'] });
      void client.invalidateQueries({ queryKey: ['watch-health'] });
    },
  });
  const checkWatches = useMutation({
    mutationFn: () => postJson<WatchCheckView>('/api/watches/check', {}),
    retry: false,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['watches'] });
      void client.invalidateQueries({ queryKey: ['outbox'] });
      void client.invalidateQueries({ queryKey: ['watch-health'] });
    },
  });
  const retireWatch = useMutation({
    mutationFn: (watch: WatchRow) => postJson<WatchDeleteView>('/api/watches/delete', { id: watch.id }),
    retry: false,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['watches'] });
      void client.invalidateQueries({ queryKey: ['outbox'] });
      void client.invalidateQueries({ queryKey: ['watch-health'] });
    },
  });
  const setChannels = useMutation({
    mutationFn: (input: { id?: string; channels: string[] }) => postJson<WatchChannelsView>('/api/watches/channels', input),
    retry: false,
    onSuccess: () => { void client.invalidateQueries({ queryKey: ['watches'] }); },
  });
  const acknowledge = useMutation({
    mutationFn: (input: { row: OutboxRow; response: string }) =>
      postJson<OutboxAckView>('/api/outbox/' + String(input.row.id) + '/ack', { response: input.response }),
    retry: false,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['outbox'] });
      void client.invalidateQueries({ queryKey: ['watch-health'] });
      void client.invalidateQueries({ queryKey: ['watches-dma'] });
    },
  });
  const createWatch = useMutation({
    mutationFn: (input: { place: { name: string; latitude: string; longitude: string }; hazard: string | null }) =>
      postJson<WatchCreateView>('/api/watches/create', input),
    retry: false,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['watches'] });
      void client.invalidateQueries({ queryKey: ['watches-dma'] });
    },
  });
  const subscribePush = useMutation({
    mutationFn: async (watch: WatchRow | null) => {
      const unsupported = browserPushSupport();
      if (unsupported) throw new Error('This browser cannot take a push subscription: ' + unsupported + '.');
      if (Notification.permission === 'denied') {
        throw new Error('This browser has denied notification permission for this page, so no subscription was created.');
      }
      if (Notification.permission !== 'granted') {
        const asked = await Notification.requestPermission();
        if (asked !== 'granted') throw new Error('Notification permission was not granted, so no subscription was created.');
      }
      const vapid = await getJson<VapidView>('/api/push/vapid-key');
      if (!vapid.public_key) throw new Error('The workspace returned no VAPID public key, so this browser cannot subscribe.');
      const registration = await navigator.serviceWorker.register('/sw.js');
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapid.public_key),
      });
      const raw = subscription.toJSON();
      return postJson<PushSubscribeView>('/api/push/subscribe', {
        endpoint: raw.endpoint, keys: raw.keys || {}, expirationTime: raw.expirationTime ?? null,
        watch_id: watch?.id ?? null,
      });
    },
    retry: false,
    onSuccess: () => { void client.invalidateQueries({ queryKey: ['push-state'] }); },
  });
  const unsubscribePush = useMutation({
    mutationFn: async () => {
      const endpoint = await browserSubscriptionEndpoint();
      return postJson<PushUnsubscribeView>('/api/push/unsubscribe', { endpoint });
    },
    retry: false,
    onSuccess: async () => {
      /* The workspace's record is revoked first; the browser's own subscription is dropped only after
         the route answered, so a failed revoke leaves the browser able to try again. */
      const registration = await navigator.serviceWorker.getRegistration('/sw.js');
      const subscription = registration ? await registration.pushManager.getSubscription() : null;
      if (subscription) await subscription.unsubscribe();
      void client.invalidateQueries({ queryKey: ['push-state'] });
    },
  });

  const planView = plans.data;
  const planRows = planView?.plans || [];
  const notifications = planView?.notifications || [];
  const watcher = planView?.watcher || {};
  const checkResult = checkPlans.data?.result;
  const watchRows = watches.data?.watches || [];
  const checkedProducts = watches.data?.checked_products || [];
  const outboxRows = outbox.data?.notifications || [];
  const healthData = health.data;
  const tick = healthData?.tick;
  const counts = healthData?.outbox?.counts || {};
  const planWatcher = healthData?.plan_watcher;
  const pushCounts = push.data?.subscriptions;
  const support = browserPushSupport();
  const dmaView = dma.data;
  const dmaPlaces = dmaView?.places || [];
  const dmaSourceRows: ReactNode[][] = [];
  dmaPlaces.forEach(place => {
    const sources = place.sources || {};
    Object.keys(sources).sort().forEach(source => {
      const cell = sources[source] || {};
      dmaSourceRows.push([
        orNot(place.place, 'place not returned'),
        source,
        orNot(cell.notifications),
        orNot(cell.acked),
      ]);
    });
  });

  /* The acknowledgement control is offered only where the store can take one: a row the payload states
     is sent, with the identifier the route needs. Everything else is stated as it is. */
  const acknowledgeCell = (row: OutboxRow): ReactNode => {
    if (row.state !== 'sent') {
      return (
        <span className="module-note">
          only a sent row can be acknowledged; this row is {orNot(row.state, 'state not returned')}
        </span>
      );
    }
    if (!row.id) {
      return <span className="module-note">this row returned no identifier, so no acknowledgement can be recorded for it</span>;
    }
    return (
      <span className="planwatch-row">
        {ACK_ANSWERS.map(([answer, label]) => (
          <button key={answer} type="button" className="btn btn-ghost"
                  disabled={acknowledge.isPending && acknowledge.variables?.row.id === row.id && acknowledge.variables?.response === answer}
                  aria-label={label + ' for notification ' + shortHash(String(row.id), 8)}
                  onClick={() => acknowledge.mutate({ row, response: answer })}>
            {label}
          </button>
        ))}
      </span>
    );
  };

  const submitCreateWatch = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    createWatch.mutate({ place: { name: placeName, latitude, longitude }, hazard: hazard || null });
  };

  const receiptRows: ReactNode[][] = [];
  notifications.forEach(item => {
    Object.entries(item.receipt || {}).forEach(([key, value]) => {
      receiptRows.push([shortHash(String(item.id ?? ''), 8), key, receiptValue(key, value)]);
    });
  });

  /* Each watch's own notification rows, filtered from the outbox read by the watch_id the row carries.
     The state and the receipt facts are printed from that row, and nothing is merged across watches. */
  const watchHistoryRows: ReactNode[][] = watchRows.flatMap(watch =>
    outboxRows
      .filter(row => row.watch_id === watch.id)
      .map(row => [
        watchLabel(watch),
        row.id ? shortHash(String(row.id), 8) : NOT_RECORDED,
        orNot(row.channel, 'channel not returned'),
        orNot(row.state, 'state not returned'),
        row.created_at ? istStamp(row.created_at) : NOT_RECORDED,
        row.updated_at ? istStamp(row.updated_at) : NOT_RECORDED,
        'correlation_id ' + orNot(row.correlation_id) + ' \u00b7 fingerprint ' +
          (row.fingerprint_sha256 ? shortHash(String(row.fingerprint_sha256), 16) : NOT_RECORDED) +
          ' \u00b7 retries ' + orNot(row.retry_count) + ' of ' + orNot(row.max_retries) +
          ' \u00b7 last error ' + orNot(row.last_error, 'no error recorded'),
      ]));

  return (
    <section className="planwatch" aria-labelledby="planwatch-heading" data-testid="planwatch">
      <header className="planwatch-head">
        <div className="planwatch-title">
          <h2 id="planwatch-heading">Plans, watches and the notification inbox</h2>
          <p className="module-lead">
            The plans and watch requests this machine holds, the notification rows they produced, and whether
            anything is checking them. Everything here is local: nothing is published, nothing is sent to anyone
            else, and no result on this panel is an all-clear.
          </p>
        </div>
        <button type="button" className="btn" onClick={onClose}>Close</button>
      </header>

      <section className="module-section" data-testid="planwatch-plans-section">
        <h3>Saved plans</h3>
        <p className="module-note">
          A plan is written in a conversation and saved here by the workspace. Plan checks run against the official
          district warning product only, while this workspace process runs.
        </p>
        {plans.isPending ? <Reading what="the saved plans" /> : null}
        {plans.isError ? <Failure error={plans.error} what="saved plans" onRetry={() => { void plans.refetch(); }} /> : null}
        {planView ? (
          <>
            <Facts
              testId="planwatch-plan-read"
              rows={[
                ['Plans in this read', count(planRows.length, 'saved plan')],
                ['Mode as returned', orNot(planView.mode)],
                ['Delivery as returned', orNot(planView.delivery)],
                ['Recorded editions available to replay', orNot(planView.recorded_editions)],
              ]}
            />
            <DataTable
              testId="planwatch-plan-watcher"
              caption="The plan watcher as this read returns it; running means the loop is alive in this process only."
              columns={['Watcher field as returned', 'Value as returned']}
              rows={[
                ['running', watcher.running === undefined ? NOT_RECORDED : String(watcher.running)],
                ['interval_seconds', orNot(watcher.interval_seconds)],
                ['last_cycle_at', watcher.last_cycle_at ? istStamp(watcher.last_cycle_at) : NOT_RECORDED],
                ['last_ok_at', watcher.last_ok_at ? istStamp(watcher.last_ok_at) : NOT_RECORDED],
                ['last_error', orNot(watcher.last_error, 'no error recorded')],
                ['last_result', watcherResult(watcher.last_result)],
              ]}
            />
            {planRows.length ? (
              <DataTable
                testId="planwatch-plans"
                caption="Every saved plan this read returned, with the state the payload states for it."
                columns={['Plan', 'State', 'Place', 'Hazards', 'Day', 'Last checked', 'Last error']}
                rows={planRows.map(plan => [
                  orNot(plan.title, plan.id || NOT_RECORDED),
                  <span key="state">
                    <span>{orNot(plan.state_words, 'state words not returned')}</span>{' '}
                    <span className="evidence">{orNot(plan.state, 'state not returned')}</span>
                  </span>,
                  orNot(plan.place, 'place not returned') + (plan.district ? ' · ' + plan.district : ''),
                  orNot(plan.hazards, 'hazards not returned') +
                    (plan.not_connected ? ' · not connected: ' + plan.not_connected : ''),
                  orNot(plan.day, 'day not returned') + (plan.part_label ? ' · ' + plan.part_label : ''),
                  plan.last_checked_at ? istStamp(plan.last_checked_at) : 'not checked yet',
                  orNot(plan.last_error, 'no error recorded'),
                ])}
              />
            ) : (
              <p className="module-note" data-testid="planwatch-plans-empty">
                This read returned no saved plan: {NO_ROW}. A plan is saved by describing it in a conversation; this
                panel does not create one, and an empty list means nothing is being checked.
              </p>
            )}
            <div className="planwatch-actions">
              <button type="button" className="btn btn-primary" disabled={checkPlans.isPending}
                      onClick={() => checkPlans.mutate()}>
                Check saved plans now
              </button>
              <span className="module-note">
                One foreground cycle: the workspace reads the district warning product once and evaluates every active
                plan against it. No day, place or product is chosen here, and nothing is sent anywhere by this press.
              </span>
            </div>
            {checkPlans.isError ? (
              <div role="alert" className="module-failure">
                <p className="reading">{failureSentence(checkPlans.error)}</p>
                <button type="button" className="btn" onClick={() => checkPlans.mutate()}>Retry this check</button>
              </div>
            ) : null}
            {checkResult ? (
              <div className="planwatch-result" data-testid="planwatch-check-result" role="status">
                <p className="reading">
                  {checkResult.error
                    ? 'The check ran, and its own sentence about the read is: ' + checkResult.error
                    : checkResult.read === true
                      ? 'The check ran: the district warning product was read in this cycle and the plans were evaluated against it.'
                      : checkResult.read === false
                        ? 'The check ran and reports that the product was not read in this cycle.'
                        : 'The check ran and reports that no active plan was evaluated, so no product was read in this cycle.'}
                </p>
                <Facts
                  testId="planwatch-check-facts"
                  rows={[
                    ['checked (as returned)', orNot(checkResult.checked)],
                    ['notified (as returned)', orNot(checkResult.notified)],
                    ['read (as returned)', checkResult.read === undefined || checkResult.read === null ? NOT_RECORDED : String(checkResult.read)],
                    ['cycle_at_utc (as returned)', checkResult.cycle_at_utc ? istStamp(checkResult.cycle_at_utc) : NOT_RECORDED],
                    ['edition_sha256 (as returned)', checkResult.edition_sha256 ? shortHash(checkResult.edition_sha256, 16) : NOT_RECORDED],
                  ]}
                />
                <p className="module-note">
                  The notification rows below are the changes this check and earlier cycles wrote. A check that changed
                  nothing writes nothing, and no warning for a watched hazard is not an all-clear.
                </p>
              </div>
            ) : null}
            <h4 className="planwatch-subhead">Notifications this inbox holds</h4>
            <DataTable
              testId="planwatch-notifications"
              caption="Every notification row this read returned, with the payload's own sentence for each one."
              columns={['Kind', 'Written', 'Shown or held', 'Title', 'The notification as written']}
              rows={notifications.map(item => [
                kindWords(item.kind),
                item.created_at ? istStamp(item.created_at) : NOT_RECORDED,
                item.visible === undefined ? 'visibility not returned'
                  : item.visible ? 'shown as returned' : 'held for quiet hours until ' + (item.visible_at ? istStamp(item.visible_at) : NOT_RECORDED),
                orNot(item.title, 'title not returned'),
                orNot(item.text, 'text not returned'),
              ])}
            />
            {notifications.length ? (
              <DataTable
                testId="planwatch-receipts"
                caption="The evidence receipt each notification carries, field by field as the payload returned it."
                columns={['Notification', 'Receipt field as returned', 'Value as returned']}
                rows={receiptRows}
              />
            ) : (
              <p className="module-note">
                No notification row came back with this read, so no receipt is shown. A notification is written only
                when a check observes a changed official state, when a dated plan reaches its evening check-in, or when
                checking has failed for hours.
              </p>
            )}
          </>
        ) : null}
      </section>

      <section className="module-section" data-testid="planwatch-watches-section">
        <h3>Watch requests registered here</h3>
        {watches.isPending ? <Reading what="the registered watch requests" /> : null}
        {watches.isError ? <Failure error={watches.error} what="registered watch requests" onRetry={() => { void watches.refetch(); }} /> : null}
        {watches.data ? (
          <>
            <p className="module-note" data-testid="planwatch-watches-note">
              The watch read's own note: {orNot(watches.data.note, 'this read returned no note')}
            </p>
            <p className="module-note">
              A watch is registered in a conversation or with the explicit-coordinates form below, and it is checked
              only when the workspace is asked. Channels are replaced here, and adding web_push needs an active push
              subscription on this machine first.
            </p>
            <p className="module-note">
              Products this read states the watches are checked against:{' '}
              {checkedProducts.length ? checkedProducts.join(', ') : 'this read named none'}
            </p>
            <p className="module-note" data-testid="planwatch-watch-push-binding-note">
              Push to a watch binds this browser's push subscription to that one watch through POST
              /api/push/subscribe: the route stores the watch_id with the subscription. The binding delivers nothing
              by itself; the route's own returned state is what this panel shows, and a stored subscription is a
              consent record, not a delivery. No binding control is offered in a browser that cannot take a push
              subscription: the push section below states that browser's own reason.
            </p>
            {watchRows.length ? (
              <DataTable
                testId="planwatch-watches"
                caption="Every registered watch request this read returned, with its state and channels as returned."
                columns={['Watch', 'Hazard', 'State', 'Channels', 'Waiting', 'Last checked', 'Last notified', 'Controls']}
                rows={watchRows.map(watch => {
                  const hasPush = (watch.channels || []).indexOf('web_push') >= 0;
                  return [
                    watchLabel(watch),
                    orNot(watch.hazard, 'hazard not returned'),
                    orNot(watch.state, 'state not returned') + (watch.expired ? ' · expired' : ''),
                    (watch.channels && watch.channels.length ? watch.channels.join(', ') : NOT_RECORDED),
                    orNot(watch.outbox_pending),
                    watch.last_checked_at ? istStamp(watch.last_checked_at) : 'not checked yet',
                    watch.last_notification_at ? istStamp(watch.last_notification_at) : 'never notified',
                    <span key="controls" className="planwatch-row">
                      <button type="button" className="btn btn-ghost btn-danger"
                              disabled={retireWatch.isPending && retireWatch.variables?.id === watch.id}
                              aria-label={'Retire the watch for ' + placeWords(watch)}
                              onClick={() => retireWatch.mutate(watch)}>
                        Retire
                      </button>
                      <button type="button" className="btn btn-ghost"
                              disabled={setChannels.isPending && setChannels.variables?.id === watch.id}
                              aria-label={(hasPush ? 'Disable push for ' : 'Enable push for ') + placeWords(watch)}
                              onClick={() => setChannels.mutate({ id: watch.id, channels: withWebPush(watch.channels, !hasPush) })}>
                        {hasPush ? 'Disable push' : 'Enable push'}
                      </button>
                      {!hasPush && !support ? (
                        <button type="button" className="btn btn-ghost"
                                disabled={subscribePush.isPending && subscribePush.variables?.id === watch.id}
                                aria-label={'Push to ' + placeWords(watch)}
                                onClick={() => subscribePush.mutate(watch)}>
                          Push to {placeWords(watch)}
                        </button>
                      ) : null}
                      <span className="module-note">
                        consent as stored: {watch.consent_record ? Object.keys(watch.consent_record).join(', ') || 'none recorded' : NOT_RECORDED}
                      </span>
                    </span>,
                  ];
                })}
              />
            ) : (
              <p className="module-note" data-testid="planwatch-watches-empty">
                This read returned no watch request: {NO_ROW}. Watching starts in a conversation ("notify me if ...") or
                with the coordinates form below, and an empty list means nothing is being checked.
              </p>
            )}
            {retireWatch.data ? (
              <p className="module-note" role="status" data-testid="planwatch-watch-retired">
                The workspace retired watch {shortHash(String(retireWatch.data.id ?? ''), 8)}: state as returned{' '}
                {orNot(retireWatch.data.state)}, notifications cancelled as returned{' '}
                {orNot(retireWatch.data.cancelled_notifications)}. This panel sent nothing and published nothing.
              </p>
            ) : null}
            {retireWatch.isError ? (
              <div role="alert" className="module-failure">
                <p className="reading">{failureSentence(retireWatch.error)}</p>
                <button type="button" className="btn" onClick={() => retireWatch.mutate(retireWatch.variables ?? {})}>Retry this retirement</button>
              </div>
            ) : null}
            {setChannels.data ? (
              <p className="module-note" role="status" data-testid="planwatch-channels-changed">
                The workspace answered: {orNot(setChannels.data.detail, 'this read returned no detail line')} Channels as
                returned: {setChannels.data.channels?.length ? setChannels.data.channels.join(', ') : NOT_RECORDED}.
              </p>
            ) : null}
            {setChannels.isError ? (
              <div role="alert" className="module-failure">
                <p className="reading">{failureSentence(setChannels.error)}</p>
                <button type="button" className="btn" onClick={() => setChannels.mutate(setChannels.variables ?? { channels: [] })}>Retry this channel change</button>
              </div>
            ) : null}
            {subscribePush.data && subscribePush.variables ? (
              <p className="module-note" role="status" data-testid="planwatch-watch-push-bound">
                The workspace answered for the binding: {orNot(subscribePush.data.detail, 'this route returned no detail line')}{' '}
                It returns subscribed: {orNot(subscribePush.data.subscribed)}, subscription{' '}
                {shortHash(String(subscribePush.data.id ?? ''), 8)}, watch_id as returned{' '}
                {orNot(subscribePush.data.watch_id, 'no watch binding')}, duplicate as returned{' '}
                {orNot(subscribePush.data.duplicate)}. This binds this browser's subscription to one watch; it delivers
                nothing by itself, and the route's own state is what this panel shows.
              </p>
            ) : null}
            {subscribePush.isError && subscribePush.variables ? (
              <div role="alert" className="module-failure">
                <p className="reading">{browserSentence(subscribePush.error)}</p>
                <p className="module-note">The binding did not complete; the sentence above is the browser's or the route's own.</p>
                <button type="button" className="btn"
                        onClick={() => { if (subscribePush.variables) subscribePush.mutate(subscribePush.variables); }}>
                  Retry this binding
                </button>
              </div>
            ) : null}
            <h4 className="planwatch-subhead">Register a watch for explicit coordinates</h4>
            <p className="module-note" data-testid="planwatch-create-note">
              This form registers one watch for this machine. The name and coordinates are stored exactly as typed: no
              gazetteer lookup runs here and this form turns no coordinate into a district. The engine resolves names
              when a question is asked, and the watch is checked against the published district warning product only,
              when a check is asked for.
            </p>
            <form className="planwatch-actions" data-testid="planwatch-create" onSubmit={submitCreateWatch}>
              <label className="module-field">
                <span>Watch place name</span>
                <input type="text" value={placeName} onChange={event => setPlaceName(event.target.value)} />
              </label>
              <label className="module-field">
                <span>Latitude</span>
                <input type="text" inputMode="decimal" value={latitude} onChange={event => setLatitude(event.target.value)} />
              </label>
              <label className="module-field">
                <span>Longitude</span>
                <input type="text" inputMode="decimal" value={longitude} onChange={event => setLongitude(event.target.value)} />
              </label>
              <label className="module-field">
                <span>Hazard to watch (optional)</span>
                <input type="text" value={hazard} onChange={event => setHazard(event.target.value)} />
              </label>
              <button type="submit" className="btn" disabled={createWatch.isPending}>Register watch</button>
            </form>
            {createWatch.data ? (
              <p className="module-note" role="status" data-testid="planwatch-watch-created">
                The workspace answered: watch {shortHash(String(createWatch.data.id ?? ''), 8)} is returned state{' '}
                {orNot(createWatch.data.state, 'state not returned')}, hazard as returned{' '}
                {orNot(createWatch.data.hazard, 'hazard not returned')}, connected as returned{' '}
                {createWatch.data.connected === undefined ? NOT_RECORDED : String(createWatch.data.connected)}, place as
                returned {orNot(createWatch.data.place?.label || createWatch.data.place?.name, 'place not returned')}.
                Its own detail line: {orNot(createWatch.data.detail, 'this read returned no detail line')}
              </p>
            ) : null}
            {createWatch.isError ? (
              <div role="alert" className="module-failure">
                <p className="reading">{failureSentence(createWatch.error)}</p>
                <p className="module-note">The route refused this registration; its own sentence is printed above, and nothing was registered.</p>
                <button type="button" className="btn"
                        onClick={() => { if (createWatch.variables) createWatch.mutate(createWatch.variables); }}>
                  Retry this registration
                </button>
              </div>
            ) : null}
          </>
        ) : null}
      </section>

      <section className="module-section" data-testid="planwatch-outbox-section">
        <h3>The local delivery outbox</h3>
        {outbox.isPending ? <Reading what="the local delivery outbox" /> : null}
        {outbox.isError ? <Failure error={outbox.error} what="local delivery outbox" onRetry={() => { void outbox.refetch(); }} /> : null}
        {outbox.data ? (
          <>
            <p className="module-note" data-testid="planwatch-outbox-note">
              The outbox read's own note: {orNot(outbox.data.note, 'this read returned no note')}
            </p>
            {outboxRows.length ? (
              <DataTable
                testId="planwatch-outbox"
                caption="Every delivery row this read returned, with its state exactly as the payload returned it, and the acknowledgement control only where the store accepts one."
                columns={['Notification', 'Watch', 'Channel', 'State', 'Retries', 'Updated', 'Last error', "Reader's acknowledgement"]}
                rows={outboxRows.map(row => [
                  shortHash(String(row.id ?? ''), 8),
                  shortHash(String(row.watch_id ?? ''), 8),
                  orNot(row.channel, 'channel not returned'),
                  <span className="evidence" key="state">{orNot(row.state, 'state not returned')}</span>,
                  orNot(row.retry_count) + ' of ' + orNot(row.max_retries),
                  row.updated_at ? istStamp(row.updated_at) : NOT_RECORDED,
                  orNot(row.last_error, 'no error recorded') +
                    (row.error_class ? ' · ' + row.error_class : ''),
                  acknowledgeCell(row),
                ])}
              />
            ) : (
              <p className="module-note" data-testid="planwatch-outbox-empty">
                The local outbox is empty: this read returned no delivery row at all ({NO_ROW}). An empty outbox means
                nothing has been queued on this machine; it is not evidence that delivery works, and a row's state is the
                only record of what happened to a notification.
              </p>
            )}
            {outboxRows.length ? (
              <p className="module-note" data-testid="planwatch-ack-what-it-means">
                An acknowledgement belongs to a sent row and is the reader telling this workspace what they did: the
                answer is recorded against that notification in this machine's own feedback store. It is not an
                instruction to anyone else, no emergency service is contacted, and it says nothing about whether anyone
                else saw the notice.
              </p>
            ) : null}
            {acknowledge.data ? (
              <p className="module-note" role="status" data-testid="planwatch-ack-recorded">
                The workspace answered: notification {shortHash(String(acknowledge.data.id ?? ''), 8)} is returned state{' '}
                {orNot(acknowledge.data.state, 'state not returned')}, response as returned{' '}
                {orNot(acknowledge.data.response, 'response not returned')}, feedback_id as returned{' '}
                {orNot(acknowledge.data.feedback_id, 'no feedback row returned')}. That is this workspace recording the
                reader's own answer; nothing was sent to anyone else.
              </p>
            ) : null}
            {acknowledge.isError ? (
              <div role="alert" className="module-failure">
                <p className="reading">{failureSentence(acknowledge.error)}</p>
                <p className="module-note">The acknowledgement was not recorded; the route's own sentence is printed above.</p>
                <button type="button" className="btn"
                        onClick={() => { if (acknowledge.variables) acknowledge.mutate(acknowledge.variables); }}>
                  Retry this acknowledgement
                </button>
              </div>
            ) : null}
            <p className="module-note">
              States are the store's own: {OUTBOX_STATES.join(', ')}. The channel and state on each row are this
              machine's record of what happened to that notification and the only record there is: a channel that is not
              connected fails rather than being reported as sent, and this panel adds no claim of its own about any row.
            </p>
          </>
        ) : null}
      </section>

      <section className="module-section" data-testid="planwatch-watch-history-section">
        <h3>Notifications for each watch</h3>
        <p className="module-note" data-testid="planwatch-watch-history-note">
          The outbox rows this read carries for each registered watch, with the state and the receipt facts recorded on
          each row: the channel it was written for, when it was written and last updated, its correlation id and
          fingerprint, its retries and any last error. A row here is this machine's record of writing a notification; it
          is not a claim that anyone received it, and a channel that is not connected fails rather than being reported
          as sent.
        </p>
        {outbox.isPending ? <Reading what="the per-watch notification history" /> : null}
        {outbox.isError ? (
          <Failure error={outbox.error} what="per-watch notification history" onRetry={() => { void outbox.refetch(); }} />
        ) : null}
        {watches.data && outbox.data ? (
          watchHistoryRows.length ? (
            <DataTable
              testId="planwatch-watch-history"
              caption="Every notification row the outbox read carries for a registered watch, with that row's own state and receipt facts."
              columns={['Watch', 'Notification', 'Channel', 'State as returned', 'Written', 'Updated', 'Receipt facts as returned']}
              rows={watchHistoryRows}
            />
          ) : (
            <p className="module-note" data-testid="planwatch-watch-history-empty">
              The outbox read carried no notification row for a watch this read returned ({NO_ROW}), so no per-watch
              history is shown. An empty history here is not evidence that nothing was written, and not evidence that
              nothing was delivered.
            </p>
          )
        ) : null}
      </section>

      <section className="module-section" data-testid="planwatch-dma-section">
        <h3>Delivery by place and source</h3>
        {dma.isPending ? <Reading what="the delivery aggregate" /> : null}
        {dma.isError ? <Failure error={dma.error} what="delivery aggregate" onRetry={() => { void dma.refetch(); }} /> : null}
        {dmaView ? (
          <>
            <p className="module-note" data-testid="planwatch-dma-note">
              The aggregate read's own note: {orNot(dmaView.note, 'this read returned no note')}
            </p>
            {dmaPlaces.length ? (
              <>
                <DataTable
                  testId="planwatch-dma-places"
                  caption="The per-place aggregate this read returned, with the payload's own counts and nothing averaged or inferred."
                  columns={['place', 'watches', 'notifications', 'acked', 'safe', 'need_help', 'evacuating', 'seen', 'unacked']}
                  rows={dmaPlaces.map(place => [
                    orNot(place.place, 'place not returned'),
                    orNot(place.watches),
                    orNot(place.notifications),
                    orNot(place.acked),
                    orNot(place.safe),
                    orNot(place.need_help),
                    orNot(place.evacuating),
                    orNot(place.seen),
                    orNot(place.unacked),
                  ])}
                />
                {dmaSourceRows.length ? (
                  <DataTable
                    testId="planwatch-dma-sources"
                    caption="The per-source counts the payload carries inside each place, with the source identifiers as returned."
                    columns={['place', 'source', 'notifications', 'acked']}
                    rows={dmaSourceRows}
                  />
                ) : (
                  <p className="module-note">
                    No place in this read carried a per-source count, so no source row is shown.
                  </p>
                )}
              </>
            ) : (
              <p className="module-note" data-testid="planwatch-dma-empty">
                No aggregate row came back with this read: {NO_ROW}. Nothing is counted because no notification row
                exists on this machine yet; an empty aggregate is not evidence that delivery works.
              </p>
            )}
            <p className="module-note" data-testid="planwatch-dma-limit">
              A count is not a receipt: it does not prove a device showed the notice, and an unacknowledged row may
              still have been delivered. This table counts rows this machine produced; it is never a delivery claim, and
              nothing in it leaves this machine.
            </p>
          </>
        ) : null}
      </section>

      <section className="module-section" data-testid="planwatch-health-section">
        <h3>Supervision truth</h3>
        {health.isPending ? <Reading what="the watch-health read" /> : null}
        {health.isError ? <Failure error={health.error} what="watch health" onRetry={() => { void health.refetch(); }} /> : null}
        {healthData ? (
          <>
            <p className="reading" data-testid="planwatch-health-mode">
              Mode as this payload returns it: <span className="evidence">{orNot(healthData.mode)}</span>
            </p>
            <Facts
              testId="planwatch-health-tick"
              rows={[
                ['fresh (as returned)', tick?.fresh === undefined ? NOT_RECORDED : String(tick.fresh)],
                ['age_seconds (as returned)', tick?.age_seconds === null || tick?.age_seconds === undefined ? NOT_RECORDED : String(tick.age_seconds)],
                ['reason (as returned)', orNot(tick?.reason, 'no reason was returned')],
                ['Last tick reported', healthData.heartbeat?.tick_at_utc ? istStamp(healthData.heartbeat.tick_at_utc) : 'no tick has ever been reported'],
                ['Trigger that reported it', orNot(healthData.heartbeat?.trigger, 'no trigger recorded')],
                ['Freshness window it named', healthData.heartbeat?.stale_after_seconds === undefined ? NOT_RECORDED : String(healthData.heartbeat.stale_after_seconds) + ' seconds'],
              ]}
            />
            {tick?.fresh === false ? (
              <p className="reading" data-testid="planwatch-not-fresh">
                fresh: false as this payload returns it: this is not a running watch service. The reason it gives is{' '}
                {orNot(tick.reason, 'no reason was returned')}.
              </p>
            ) : null}
            <p className="module-note" data-testid="planwatch-health-note">
              The payload's own wording: {orNot(healthData.note, 'this read returned no note')}
            </p>
            <DataTable
              testId="planwatch-health-outbox"
              caption="The outbox's own counts as this read returns them, one row per state, and the depth waiting for a run."
              columns={['Outbox state', 'Rows as returned']}
              rows={OUTBOX_STATES.concat(Object.keys(counts).filter(state => OUTBOX_STATES.indexOf(state) < 0))
                .map(state => [state, orNot(counts[state])])
                .concat([['awaiting dispatch (created, queued, claimed, failed)', orNot(healthData.outbox?.undispatched_depth)]])
                .concat([['oldest awaiting dispatch', healthData.outbox?.oldest_undispatched_created_at
                  ? istStamp(healthData.outbox.oldest_undispatched_created_at) : NOT_RECORDED]])}
            />
            <Facts
              testId="planwatch-health-totals"
              rows={[
                ['Watches as returned (total / active / expired)', orNot(healthData.watches?.total) + ' / ' + orNot(healthData.watches?.active) + ' / ' + orNot(healthData.watches?.expired)],
                ['Plan watcher (running / interval_seconds)', (planWatcher?.running === undefined ? NOT_RECORDED : String(planWatcher.running)) + ' / ' + orNot(planWatcher?.interval_seconds)],
                ['Plan watcher last result', watcherResult(planWatcher?.last_result)],
              ]}
            />
            <div className="planwatch-actions">
              <button type="button" className="btn btn-primary" disabled={checkWatches.isPending}
                      onClick={() => checkWatches.mutate()}>
                Check open watches now (foreground)
              </button>
              <span className="module-note">
                A foreground check only: it runs one cycle now and records the result in the outbox. The mode and note
                above state whether anything else is checking watches.
              </span>
            </div>
            {checkWatches.isError ? (
              <div role="alert" className="module-failure">
                <p className="reading">{failureSentence(checkWatches.error)}</p>
                <button type="button" className="btn" onClick={() => checkWatches.mutate()}>Retry this check</button>
              </div>
            ) : null}
            {checkWatches.data ? (
              <div className="planwatch-result" data-testid="planwatch-watch-check" role="status">
                <p className="reading">
                  The watch check's own note: {orNot(checkWatches.data.note, 'this read returned no note')}
                </p>
                <p className="module-note">
                  {Array.isArray(checkWatches.data.dispatched) ? count(checkWatches.data.dispatched.length, 'dispatch row') : 'dispatch rows not returned'}
                  {' · '}
                  {Array.isArray(checkWatches.data.escalated) ? count(checkWatches.data.escalated.length, 'escalation row') : 'escalation rows not returned'}
                </p>
                <DataTable
                  testId="planwatch-watch-check-results"
                  caption="Every watch the check reported on, with the payload's own detail for each one."
                  columns={['Watch', 'State', 'Matched', 'Detail as returned']}
                  rows={(checkWatches.data.results || []).map(result => [
                    shortHash(String(result.id ?? ''), 8),
                    orNot(result.state, 'state not returned'),
                    result.matched === undefined ? NOT_RECORDED : String(result.matched),
                    orNot(result.detail, 'no detail returned'),
                  ])}
                />
              </div>
            ) : null}
          </>
        ) : null}
      </section>

      <section className="module-section" data-testid="planwatch-push-section">
        <h3>Browser push on this machine</h3>
        <p className="module-note" data-testid="planwatch-push-what-it-is">
          What this is: an opt-in channel for one browser on this machine. The workspace stores one subscription for a
          browser you consent from, and messages reach it through the browser vendor's push service while the local
          check process runs. It is the only channel besides the local inbox.
        </p>
        <p className="module-note" data-testid="planwatch-push-what-it-is-not">
          What it is not: SMS, IVR, WhatsApp and e-mail are not connected channels, no hosted account is connected, and
          nothing here is published or sent to anyone else. A stored subscription is a consent record, not a delivery:
          this panel claims no notification has been delivered, and the delivery rows in the outbox above are the only
          record of a send.
        </p>
        <p className="module-note" data-testid="planwatch-push-service-worker">
          Subscribing registers the workspace service worker at /sw.js with this browser. If this machine does not serve
          it, the browser refuses the subscription and its own refusal is shown here rather than being reported as a
          success.
        </p>
        {push.isPending ? <Reading what="the push state" /> : null}
        {push.isError ? <Failure error={push.error} what="push state" onRetry={() => { void push.refetch(); }} /> : null}
        {push.data ? (
          <Facts
            testId="planwatch-push-state"
            rows={[
              ['Subscriptions this read counts as active', orNot(pushCounts?.active)],
              ['Subscriptions counted expired', orNot(pushCounts?.expired)],
              ['Subscriptions counted revoked', orNot(pushCounts?.revoked)],
              ['Expired subscriptions this read retired', orNot(push.data.purged_expired)],
              ['Delivery as returned', orNot(push.data.delivery)],
              ['Note as returned', orNot(push.data.note, 'this read returned no note')],
            ]}
          />
        ) : null}
        {support ? (
          <p className="module-note" data-testid="planwatch-push-unsupported">
            This browser cannot take a push subscription: {support}. No subscribe control is offered, and nothing is
            claimed about any browser's delivery.
          </p>
        ) : (
          <>
            <p className="module-note">
              Permission this browser reports: <span className="evidence">{Notification.permission}</span>. The counts
              above are the workspace's record; whether this browser itself holds a subscription is read from the browser
              when you press a control below.
            </p>
            <div className="planwatch-actions">
              <button type="button" className="btn" disabled={subscribePush.isPending} onClick={() => subscribePush.mutate(null)}>
                Subscribe this browser for push
              </button>
              <button type="button" className="btn btn-ghost" disabled={unsubscribePush.isPending} onClick={() => unsubscribePush.mutate()}>
                Revoke this browser's subscription
              </button>
            </div>
          </>
        )}
        {subscribePush.data && !subscribePush.variables ? (
          <p className="module-note" role="status" data-testid="planwatch-push-subscribed">
            The workspace answered: {orNot(subscribePush.data.detail, 'this read returned no detail line')} It returns
            subscribed: {orNot(subscribePush.data.subscribed)}, subscription {shortHash(String(subscribePush.data.id ?? ''), 8)},
            bound to watch {orNot(subscribePush.data.watch_id, 'no watch')}. This records consent for this browser; it does
            not say a notification was delivered, and nothing above is a delivery claim.
          </p>
        ) : null}
        {subscribePush.isError && !subscribePush.variables ? (
          <div role="alert" className="module-failure">
            <p className="reading">{browserSentence(subscribePush.error)}</p>
            <button type="button" className="btn" onClick={() => subscribePush.mutate(null)}>Retry this subscription</button>
          </div>
        ) : null}
        {unsubscribePush.data ? (
          <p className="module-note" role="status" data-testid="planwatch-push-revoked">
            The workspace answered: the endpoint {shortHash(String(unsubscribePush.data.endpoint ?? ''), 24)} is returned
            revoked: {orNot(unsubscribePush.data.revoked)}, channels removed as returned:{' '}
            {unsubscribePush.data.channels_removed?.length ? unsubscribePush.data.channels_removed.join(', ') : 'none'}.
            A revoked subscription is no longer an active channel in this workspace.
          </p>
        ) : null}
        {unsubscribePush.isError ? (
          <div role="alert" className="module-failure">
            <p className="reading">{browserSentence(unsubscribePush.error)}</p>
            <button type="button" className="btn" onClick={() => unsubscribePush.mutate()}>Retry this revocation</button>
          </div>
        ) : null}
      </section>

      <section className="module-section" data-testid="planwatch-limits-section">
        <h3>Limits of this panel</h3>
        <p className="module-note">The plans read's own limits, as returned:</p>
        {planView?.limits?.length ? (
          <ul className="planwatch-list" data-testid="planwatch-payload-limits">
            {planView.limits.map((line, index) => <li key={index}>{line}</li>)}
          </ul>
        ) : (
          <p className="module-note">This read returned no limit line.</p>
        )}
        <ul className="planwatch-list" data-testid="planwatch-own-limits">
          <li>
            Plans are checked only while this workspace process runs on this machine: no hosted service checks them, and a
            plan is evaluated when a loop ticks or when you press the check above. When the process stops, nothing is
            checked.
          </li>
          <li>
            The interval is the payload's: this read states {orNot(watcher.interval_seconds)} seconds for the plan watcher
            and {orNot(planWatcher?.interval_seconds)} seconds for the watch loop. This panel neither sets nor enforces
            either interval.
          </li>
          <li>
            A warning is checked against the published district warning product only
            {checkedProducts.length ? ' (' + checkedProducts.join(', ') + '), as the watch read names it' : ''}: a flood,
            cyclone or sea-area hazard stays recorded as not connected and is never mapped onto another product.
          </li>
          <li>
            Nothing is published and nothing is sent to anyone else: the delivery rows are this machine's, and the only
            other channel is a browser push subscription consented to on this machine. SMS, IVR, WhatsApp and e-mail are
            not connected channels.
          </li>
          <li>
            A no-warning result is not an all-clear, and a check that found nothing has not established that nothing will
            happen.
          </li>
          <li>
            These reads attach no source-registry row: the payloads name identifiers inside them (a notification receipt
            names a source_id and an edition hash, and the watch read names the products checked), and every row that
            names nothing is shown as not recorded rather than resolved elsewhere.
          </li>
        </ul>
      </section>
    </section>
  );
}
