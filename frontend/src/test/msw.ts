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
  // The Workspace dashboard reads these for a chosen place; a suite that tests one of them overrides it.
  http.get('/api/forecast', () =>
    HttpResponse.json({ schema_version: 'product-view-v1', view: 'forecast.point', status: 'ok', data: { parameters: {} }, sources: [], limitations: [] })),
  http.get('/api/warnings/place', () =>
    HttpResponse.json({ schema_version: 'product-view-v1', view: 'warnings.place', status: 'ok', data: { days: [] }, sources: [], limitations: [] })),
  http.get('/api/air-quality', () =>
    HttpResponse.json({ schema_version: 'product-view-v1', view: 'air_quality.point', status: 'ok', data: { parameters: {}, current: {} }, sources: [], limitations: [] })),
  http.get('/api/warnings/national', () =>
    HttpResponse.json({ schema_version: 'product-view-v1', view: 'warnings.national', status: 'ok', data: { districts: [], tally: {} }, sources: [], limitations: [] })),
  // The climate record and the briefs/plans panels read only when they come near the screen; a suite that
  // tests one of them overrides these.
  http.get('/api/climate/index', () =>
    HttpResponse.json({ schema_version: 'product-view-v1', view: 'climate.index', status: 'ok', data: { districts: [] }, sources: [], limitations: [] })),
  http.get('/api/briefs', () =>
    HttpResponse.json({ schema_version: 'briefcase-view-v1', status: 'ok', briefs: [], note: 'nothing kept yet' })),
  http.get('/api/plans', () =>
    HttpResponse.json({ schema_version: 'plan-view-v1', status: 'ok', plans: [], note: 'no plans' })),
  http.get('/api/conversations', () =>
    HttpResponse.json({ schema_version: 'conversation-ledger-v1', total: 0, limit: 40, conversations: [], note: 'stored locally' })),
);

export const unhandled: string[] = [];
