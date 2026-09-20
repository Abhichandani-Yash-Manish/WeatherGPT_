/* The service worker PlanWatch.tsx has always registered, and which did not exist until now.
 *
 * Measured 20 September 2026: `navigator.serviceWorker.register('/sw.js')` is called in
 * src/plans/PlanWatch.tsx, the backend push chain is complete and tested (push.py, outbox.py,
 * POST /api/outbox/<id>/ack), and the frontend suites mock the registration - so every layer
 * reported success while a real browser would have taken a 404 and never received a push.
 *
 * What this file is allowed to say is bounded by the same rule the rest of the product follows:
 * warning material is reported as official product state, never as an instruction, and the worker
 * writes no weather text of its own. Every word shown to a reader comes from push_payload() in
 * weathergpt_data/push.py, which builds it from the official facts. A push that arrives without a
 * readable payload is shown as exactly that - an unreadable notice to open the workspace - and
 * never as a warning, because a notification the reader cannot trace is worse than none.
 */

const FALLBACK_TITLE = 'WeatherGPT';
// Shown only when a push carries nothing readable. It states its own emptiness rather than
// implying a hazard: an empty envelope is not an all-clear and is not a warning either.
const UNREADABLE_BODY = 'A watch notification arrived but its contents could not be read. Open the workspace to see the official state.';

self.addEventListener('install', (event) => {
  // The newest worker takes over immediately: a stale worker would keep rendering an old payload
  // shape after the product's notification contract changes.
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

function readPayload(event) {
  if (!event.data) return null;
  try {
    return event.data.json();
  } catch (error) {
    return null;
  }
}

self.addEventListener('push', (event) => {
  const payload = readPayload(event);
  const title = (payload && typeof payload.title === 'string' && payload.title) || FALLBACK_TITLE;
  const body = (payload && typeof payload.body === 'string' && payload.body) || UNREADABLE_BODY;
  const watchId = payload && payload.watch_id ? String(payload.watch_id) : '';
  const outboxId = payload && payload.outbox_id ? String(payload.outbox_id) : '';

  event.waitUntil(self.registration.showNotification(title, {
    body,
    // One notification per watch: a newer edition for the same watch replaces the older one rather
    // than stacking, so the reader is never choosing between two versions of the same official state.
    tag: watchId ? 'weathergpt-watch-' + watchId : 'weathergpt-watch',
    renotify: Boolean(watchId),
    // An official warning should not disappear on its own before it has been read.
    requireInteraction: true,
    timestamp: Date.now(),
    data: {
      watch_id: watchId,
      outbox_id: outboxId,
      checked_at_utc: (payload && payload.checked_at_utc) || null,
      url: (payload && typeof payload.url === 'string' && payload.url) || '/',
    },
    actions: outboxId
      ? [{ action: 'acknowledge', title: 'Acknowledge' }, { action: 'open', title: 'Open' }]
      : [{ action: 'open', title: 'Open' }],
  }));
});

/* Both actions open the workspace, and the PAGE performs the acknowledgement.
 *
 * The ack endpoint requires the workspace token, which the server injects into the page. Keeping
 * the token in the page rather than copying it into the worker's own storage means there is one
 * place it lives and one place it can leak from. The cost is that an acknowledgement requires the
 * workspace to come to the foreground, which is honest: acknowledging a warning you have not
 * looked at is not an acknowledgement.
 */
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const data = event.notification.data || {};
  const base = typeof data.url === 'string' && data.url ? data.url : '/';
  const separator = base.indexOf('?') === -1 ? '?' : '&';
  const target = event.action === 'acknowledge' && data.outbox_id
    ? base + separator + 'ack=' + encodeURIComponent(data.outbox_id)
    : base;

  event.waitUntil((async () => {
    const clientList = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of clientList) {
      if ('focus' in client) {
        // Tell the open workspace what happened rather than reloading it out from under the reader.
        if ('postMessage' in client) {
          client.postMessage({ source: 'weathergpt-sw', kind: 'notificationclick', action: event.action || 'open', data });
        }
        if ('navigate' in client && event.action === 'acknowledge' && data.outbox_id) {
          try {
            await client.navigate(target);
          } catch (error) {
            /* A cross-origin or otherwise refused navigation must not lose the focus above. */
          }
        }
        return client.focus();
      }
    }
    return self.clients.openWindow(target);
  })());
});

/* A subscription can be rotated by the push service without the reader doing anything. Recording
 * that it happened means a watch that has silently stopped being deliverable is visible as an
 * event rather than as an absence of notifications, which is indistinguishable from quiet weather.
 */
self.addEventListener('pushsubscriptionchange', (event) => {
  event.waitUntil((async () => {
    const clientList = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of clientList) {
      if ('postMessage' in client) {
        client.postMessage({ source: 'weathergpt-sw', kind: 'pushsubscriptionchange' });
      }
    }
  })());
});
