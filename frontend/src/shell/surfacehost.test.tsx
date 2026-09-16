/* The surface host: a ported module is fetched as its own chunk and rendered, and a module that is not ported
   yet says so and offers to ask one of its questions in the conversation. The first half is the route-level
   integration the module suite could not reach on its own. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { SurfaceHost } from './SurfaceHost';
import { viewById, type ViewEntry } from './views';

const WARNINGS = {
  schema_version: 'product-view-v1',
  generated_at_utc: '2026-09-17T02:00:00+00:00',
  view: 'warnings.national',
  status: 'ok',
  data: {
    districts: [
      {
        key: 'patna-bihar',
        district: 'PATNA',
        state: 'BIHAR',
        bulletin_date: '2026-09-15',
        issued_at_utc: '2026-09-15T06:00:00+00:00',
        days: [{ date: '2026-09-15', day_label: 'Day 1', colour: 'yellow', hazards: ['Thunderstorm'], wording: 'Thunderstorm/lightning/squall' }],
      },
    ],
    tally: { yellow: 1, green: 0 },
    skipped: [],
  },
  sources: [],
  coverage: { districts_listed: 1 },
  limitations: ['A quiet district-day is not an all-clear.'],
  not_established: ['Radar and satellite imagery are not connected here.'],
};

function host(id: string, onAsk = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <SurfaceHost view={viewById(id)!} onAsk={onAsk} />
    </QueryClientProvider>,
  );
  return onAsk;
}

describe('the surface host', () => {
  it('loads a ported module as its own chunk and renders it with its own limits', async () => {
    server.use(http.get('/api/warnings/national', () => HttpResponse.json(WARNINGS)));
    host('warnings');
    expect(await screen.findByRole('heading', { level: 1, name: 'Warnings' })).toBeInTheDocument();
    expect((await screen.findAllByText('PATNA')).length).toBeGreaterThan(0);
    expect(screen.getByText(/not an all-clear/i)).toBeInTheDocument();
  });

  it('states that a module is not ported yet, names its stage, and offers its questions to the conversation', async () => {
    /* A synthetic entry rather than a registry id: the placeholder contract must stay checkable after every
       surface has been ported, and this way the check does not depend on which ones are left. */
    const pending: ViewEntry = {
      /* An id no module claims, so the placeholder path is exercised even once every real surface is ported. */
      id: 'not-yet-ported' as ViewEntry['id'],
      label: 'Sea and rivers',
      group: 'more',
      portedIn: 'R4',
      intents: ['What is the sea like near Kochi tomorrow?', 'How much water is in the river at Surat?'],
    };
    const onAsk = vi.fn();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <SurfaceHost view={pending} onAsk={onAsk} />
      </QueryClientProvider>,
    );
    expect(screen.getByRole('heading', { level: 1, name: 'Sea and rivers' })).toBeInTheDocument();
    expect(screen.getByText(/not ported yet/i)).toBeInTheDocument();
    expect(screen.getByText('R4')).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole('button', { name: /Ask this in the conversation/i })[0]);
    expect(onAsk).toHaveBeenCalledWith(pending.intents[0]);
  });
});
