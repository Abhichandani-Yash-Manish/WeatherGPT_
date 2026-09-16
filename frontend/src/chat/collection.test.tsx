/* The two frontend-audit checks that had no React equivalent: a bounded collection reachable from
   the page (FE02) and no renderer wired to a request the workspace would reject (FE03).

   FE02 is the answer card's Collect fresh evidence control, which is the only way a reader can ask the
   workspace to acquire something new. FE03 is held here as two source-level facts: every request goes
   through src/api/client.ts (so it carries the session token and the error mapping), and no component
   reaches for fetch on its own. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { readdirSync, readFileSync } from 'node:fs';
import { http, HttpResponse } from 'msw';
import { AnswerTurn } from './AnswerTurn';
import { server } from '../test/msw';

const PACKET = {
  schema_version: 'weather-conversation-v1',
  conversation_id: '44444444-4444-4444-8444-444444444444',
  question: 'Will it rain in Ahmedabad tomorrow?',
  status: 'answered',
  answer: 'Ahmedabad: forecast precipitation 0.3 mm.',
  facts: [{ id: 't1-f1', label: 'Forecast rainfall', value: '0.3', unit: 'mm', place: 'Ahmedabad, Gujarat',
            start: '2026-09-18T06:30:00+05:30', end: '2026-09-18T12:30:00+05:30', source_id: 'S21',
            parameter: 'precipitation', evidence_kind: 'forecast', citation_ids: ['t1-c1'], task_id: 't1' }],
  citations: [{ id: 't1-c1', source_id: 'S21', product: 'GFS forecast delivery', retrieved_at_utc: '2026-09-17T10:39:00+00:00' }],
  notes: [], choices: [], charts: [], task_results: [], answered_at_utc: '2026-09-17T10:47:00+00:00',
  resolved_points: { Ahmedabad: { selection_id: 'geonames:1279233', label: 'Ahmedabad, Gujarat',
                                  coordinates: { latitude: 23.02579, longitude: 72.58727 } } },
  trace: {}, retrieval_plan: [],
};

function mount(node: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

describe('a bounded collection is reachable from a card', () => {
  it('offers Collect fresh evidence for an answer with a resolved point, and asks for that exact point', async () => {
    const asked: unknown[] = [];
    server.use(
      http.post('/api/refresh', async ({ request }) => {
        asked.push(await request.json());
        return HttpResponse.json({ refresh: { state: 'succeeded', message: 'Collection completed; answer checked against the stored evidence.' } });
      }),
    );
    const onRefresh = (packet: Record<string, unknown>) => {
      const point = Object.values(packet.resolved_points as Record<string, { coordinates: { latitude: number; longitude: number } }>)[0];
      void fetch('/api/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-WeatherGPT-Token': 'test-token' },
        body: JSON.stringify({ question: packet.question, coordinates: point.coordinates }),
      });
    };
    mount(<AnswerTurn packet={PACKET as never} register="conversational" onFollowUp={() => {}} onRefresh={onRefresh} />);
    await userEvent.click(screen.getByRole('button', { name: 'Collect fresh evidence' }));
    await waitFor(() => expect(asked).toHaveLength(1));
    expect(asked[0]).toEqual({ question: 'Will it rain in Ahmedabad tomorrow?', coordinates: { latitude: 23.02579, longitude: 72.58727 } });
  });

  it('offers no collection control for an answer with no resolved point', () => {
    mount(<AnswerTurn packet={{ ...PACKET, resolved_points: {} } as never} register="conversational" onFollowUp={() => {}} onRefresh={() => {}} />);
    expect(screen.queryByRole('button', { name: 'Collect fresh evidence' })).toBeNull();
  });
});

describe('every request goes through one place', () => {
  it('has no component reaching for fetch outside the api client', () => {
    /* readdirSync with recursive: true reports paths relative to the directory, so the walk joins them
       itself rather than assuming a shape the Node version may change. */
    const roots = ['src/chat', 'src/modules', 'src/plans', 'src/landing', 'src/shell', 'src/charts', 'src/a11y'];
    const offenders: string[] = [];
    const walk = (directory: string, relative: string) => {
      for (const entry of readdirSync(directory, { withFileTypes: true })) {
        const next = relative ? relative + '/' + entry.name : entry.name;
        if (entry.isDirectory()) {
          walk(directory + '/' + entry.name, next);
          continue;
        }
        if (!/\.(ts|tsx)$/.test(entry.name) || /\.test\.(ts|tsx)$/.test(entry.name)) continue;
        const file = directory + '/' + entry.name;
        if (/\bfetch\s*\(/.test(readFileSync(file, 'utf8'))) offenders.push(directory + '/' + entry.name);
      }
    };
    for (const root of roots) walk(root, '');
    expect(offenders, 'these files call fetch directly instead of src/api/client.ts').toEqual([]);
  });

  it('sends the session token on every request the client makes', async () => {
    let seen = '';
    server.use(
      http.get('/api/coverage-probe', ({ request }) => {
        seen = request.headers.get('X-WeatherGPT-Token') || '';
        return HttpResponse.json({ ok: true });
      }),
    );
    const { getJson } = await import('../api/client');
    const meta = document.createElement('meta');
    meta.name = 'workspace-token';
    meta.content = 'token-from-the-page';
    document.head.append(meta);
    await getJson('/api/coverage-probe');
    expect(seen).toBe('token-from-the-page');
    meta.remove();
  });
});
