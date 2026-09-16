import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

/* The vanilla component checks hand-wrote a fetch stub per suite. MSW replaces that: one server, real
   fetch semantics, and per-test handlers that a suite adds with server.use(). The defaults below are the
   reads every shell mount performs, so a suite only has to declare what it is actually testing. */
export const server = setupServer(
  http.get('/api/health', () =>
    HttpResponse.json({ schema_version: 'source-health-v1', available: true, products: [], note: 'test store' })),
  // The shell reads the language catalogue on mount; a suite that cares about it overrides this handler.
  http.get('/api/languages', () =>
    HttpResponse.json({ schema_version: 'language-support-view-v1', service_configured: false, languages: [] })),
  http.get('/api/personas', () =>
    HttpResponse.json({ schema_version: 'product-view-v1', view: 'personas', data: { personas: [] }, sources: [], limitations: [] })),
  // The front page reads these two on mount; a suite that tests the strip overrides them.
  http.get('/api/settings/capabilities', () =>
    HttpResponse.json({ schema_version: 'product-view-v1', view: 'settings.capabilities', status: 'ok',
      data: { capabilities: [], sources: [], registered_sources: 0, connected_sources: 0 }, sources: [], limitations: [] })),
  http.get('/api/corpus', () =>
    HttpResponse.json({ schema_version: 'product-view-v1', view: 'corpus', status: 'ok',
      data: { documents: [], families: [], counts: { documents: 0, passages: 0, regions: 0 }, index: 'test' }, sources: [], limitations: [] })),
  http.get('/api/conversations', () =>
    HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [], note: 'stored locally' })),
);

export const unhandled: string[] = [];
