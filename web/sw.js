/* WeatherGPT watch push: show the official state, never invent one.
   The push body carries the outbox payload's facts verbatim. Tapping the
   notification focuses the workspace tab that owns the watch. */
self.addEventListener('push', event => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (error) { data = {}; }
  const title = typeof data.title === 'string' && data.title ? data.title : 'WeatherGPT watch';
  const body = typeof data.body === 'string' && data.body ? data.body : 'A watched official state changed.';
  event.waitUntil(self.registration.showNotification(title, {
    body: body,
    tag: 'weathergpt-watch-' + String(data.watch_id || 'general'),
    renotify: true,
    data: { watch_id: data.watch_id || null, outbox_id: data.outbox_id || null }
  }));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of windows) {
      if ('focus' in client) { await client.focus(); return; }
    }
    if (self.clients.openWindow) await self.clients.openWindow('/');
  })());
});
