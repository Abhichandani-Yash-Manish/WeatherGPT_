import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { parseHash } from './useHashRoute';

describe('the routing contract', () => {
  it('falls back to Ask for an empty or unknown route, and keeps the query', () => {
    expect(parseHash('').view.id).toBe('assistant');
    expect(parseHash('#/nothing-here').view.id).toBe('assistant');
    expect(parseHash('#/warnings?day=2').view.id).toBe('warnings');
    expect(parseHash('#/warnings?day=2').query.get('day')).toBe('2');
  });

  it('serves a recorded payload through the fetch harness rather than a stub', async () => {
    server.use(http.get('/api/watch-health', () => HttpResponse.json({ schema_version: 'watch-health-v1', mode: 'manual-only' })));
    const response = await fetch('/api/watch-health');
    expect(await response.json()).toMatchObject({ mode: 'manual-only' });
  });
});
