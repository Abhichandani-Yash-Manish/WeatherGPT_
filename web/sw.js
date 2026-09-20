/* WeatherGPT watch push: show the official state, never invent one.
   The push body carries the outbox payload's facts verbatim. Tapping the notification focuses the workspace
   tab that owns the watch, and the PAGE records the acknowledgement over POST /api/outbox/<id>/ack - the
   endpoint needs the workspace token, which only the page has. That is deliberate and it is why this worker
   offers no Acknowledge action of its own: an action that navigated to a query parameter nothing reads would
   put a button on a notification that silently did nothing, and the ledger would still show it unacknowledged.

   This file is the ONE worker this repository ships, and tests/test_shell_assets_served.py holds that: exactly
   one worker file exists and the bytes served at /sw.js are it. A second copy under frontend/public/ was
   written once and never served - the server answers /sw.js from here, and web/dist/ is not a directory it
   reads - so an edit there looked live and was not.

   It is a push worker and not an offline cache: nothing is stored and there is no network handler. Offline
   stays what docs/92 says it is - the shell needs the local server, which owns the evidence. */

const FALLBACK_TITLE = 'WeatherGPT';
/* Shown only when a push carries nothing readable. It states its own emptiness rather than implying a hazard:
   an empty envelope is not an all-clear and is not a warning either. */
const UNREADABLE_BODY = 'A watch notification arrived but its contents could not be read. Open the workspace to see the official state.';

self.addEventListener('install', event => {
  /* The newest worker takes over immediately: a stale worker would keep rendering an old payload shape after
     the product's notification contract changes. */
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', event => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (error) { data = {}; }
  const title = typeof data.title === 'string' && data.title ? data.title : FALLBACK_TITLE;
  const body = typeof data.body === 'string' && data.body ? data.body : UNREADABLE_BODY;
  const watchId = typeof data.watch_id === 'string' || typeof data.watch_id === 'number' ? String(data.watch_id) : '';
  event.waitUntil(self.registration.showNotification(title, {
    body: body,
    /* One notification per watch: a newer edition for the same watch replaces the older one rather than
       stacking, so the reader is never choosing between two versions of the same official state. */
    tag: watchId ? 'weathergpt-watch-' + watchId : 'weathergpt-watch',
    renotify: Boolean(watchId),
    /* An official warning should not disappear on its own before it has been read. */
    requireInteraction: true,
    timestamp: Date.now(),
    data: { watch_id: watchId || null, outbox_id: data.outbox_id || null,
            url: typeof data.url === 'string' && data.url.charAt(0) === '/' ? data.url : '/' }
  }));
});

/* The push service can retire a subscription (e.g. after long disuse). Re-subscribing needs the workspace page
   (the VAPID key lives behind its session token), so the worker tells the owner to open it; the page
   re-subscribes on its next paint when none exists. */
self.addEventListener('pushsubscriptionchange', event => {
  event.waitUntil(self.registration.showNotification('WeatherGPT notifications paused', {
    body: 'The browser retired this workspace\u2019s push subscription. Open the workspace Watch panel and press Subscribe again.',
    tag: 'weathergpt-push-resubscribe',
    renotify: true,
    requireInteraction: true,
    data: { resubscribe: true }
  }));
});

self.addEventListener('notificationclick', event => {
  const data = (event.notification && event.notification.data) || {};
  const url = typeof data.url === 'string' && data.url.charAt(0) === '/' ? data.url : '/';
  event.notification.close();
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of windows) {
      if ('focus' in client) {
        if ('navigate' in client && url !== '/') { try { await client.navigate(url); } catch (error) { /* focus still helps */ } }
        await client.focus();
        return;
      }
    }
    if (self.clients.openWindow) await self.clients.openWindow(url);
  })());
});
