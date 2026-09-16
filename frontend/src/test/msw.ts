import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

/* The vanilla component checks hand-wrote a fetch stub per suite. MSW replaces that: one server, real
   fetch semantics, and per-test handlers that a suite adds with server.use(). R2 ports the recorded
   payloads into handlers; R1 proves the harness works. */
export const server = setupServer(
  http.get('/api/health', () =>
    HttpResponse.json({ schema_version: 'source-health-v1', available: false, products: [], note: 'no store in this test' })),
);

export const unhandled: string[] = [];
