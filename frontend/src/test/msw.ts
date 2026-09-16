import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

/* The vanilla component checks hand-wrote a fetch stub per suite. MSW replaces that: one server, real
   fetch semantics, and per-test handlers that a suite adds with server.use(). R2 ports the recorded
   payloads into handlers; R1 proves the harness works. */
export const server = setupServer(
  http.get('/api/health', () =>
    HttpResponse.json({ schema_version: 'source-health-v1', available: true, products: [], note: 'test store' })),
  // The shell reads the language catalogue on mount; a suite that cares about it overrides this handler.
  http.get('/api/languages', () =>
    HttpResponse.json({ schema_version: 'language-support-view-v1', service_configured: false, languages: [] })),
);

export const unhandled: string[] = [];
