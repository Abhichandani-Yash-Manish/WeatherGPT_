/* WeatherGPT watch push: show the official state, never invent one.
   The push body carries the outbox payload's facts verbatim. Tapping the
   notification focuses the workspace tab that owns the watch. */
self.addEventListener('push', event => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (error) { data = {}; }
  const title = typeof data.title === 'string' && data.title ? data.title : 'WeatherGPT watch';
  const body = typeof data.body === 'string' && data.body ? data.body : 'Notification content is unavailable. Open the workspace to inspect its recorded state.';
  event.waitUntil(self.registration.showNotification(title, {
    body: body,
    tag: 'weathergpt-watch-' + String(data.watch_id || 'general'),
    renotify: true,
    data: { watch_id: data.watch_id || null, outbox_id: data.outbox_id || null,
            url: typeof data.url === 'string' && data.url.charAt(0) === '/' ? data.url : '/' }
  }));
});

/* The push service can retire a subscription (e.g. after long disuse). Re-subscribing
   needs the workspace page (the VAPID key lives behind its session token), so the worker
   tells the owner to open it; the page re-subscribes on its next paint when none exists. */
self.addEventListener('pushsubscriptionchange', event => {
  event.waitUntil(self.registration.showNotification('WeatherGPT notifications paused', {
    body: 'The browser retired this workspace\u2019s push subscription. Open the workspace Watch panel and press Subscribe again.',
    tag: 'weathergpt-push-resubscribe',
    renotify: true,
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
