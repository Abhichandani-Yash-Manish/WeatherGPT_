/* The collection-health gap the port ledger names from tests/test_suite_ui.js (check 24): the topbar
   chip states the store's totals, and behind it the same /api/health read's own per-product rows carry
   each product's jobs, states and newest commit. A read with no product rows says so rather than
   showing a zero, and the chip's failure state is untouched. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { Topbar } from './Topbar';
import { server } from '../test/msw';

function renderTopbar() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(
    <QueryClientProvider client={client}>
      <Topbar
        language=""
        onLanguage={vi.fn()}
        persona=""
        onPersona={vi.fn()}
        theme="system"
        onTheme={vi.fn()}
        onNew={vi.fn()}
        onPalette={vi.fn()}
        onOwner={vi.fn()}
        onMenu={vi.fn()}
        railOpen={false}
        onPlans={vi.fn()}
      />
    </QueryClientProvider>,
  );
}

const HEALTH = {
  schema_version: 'source-health-v1',
  available: true,
  products: [
    { product: 'forecast', jobs: 12, states: { ok: 10, failed: 2 }, newest_commit_utc: '2026-09-14T18:00:00+00:00' },
    { product: 'observations', jobs: 4, states: { ok: 4 }, newest_commit_utc: null },
  ],
  job_states: { ok: 14, failed: 2 },
  streams: 7,
  active_leases: 0,
  cooldowns: [],
  note: 'Read-only projection of the local ingestion store.',
};

async function openProducts() {
  const details = await screen.findByTestId('health-products');
  await userEvent.click(within(details).getByText('By product'));
  return details;
}

describe('the per-product collection-health rows', () => {
  it("lists each product's own job count, job states and newest commit behind the chip", async () => {
    server.use(http.get('/api/health', () => HttpResponse.json(HEALTH)));
    renderTopbar();
    await screen.findByText('Store healthy');

    const details = await openProducts();
    expect(details).toHaveAttribute('open');
    const table = within(details).getByRole('table');
    const forecast = within(table).getByRole('rowheader', { name: 'forecast' }).closest('tr') as HTMLElement;
    expect(forecast).toHaveTextContent('12');
    expect(forecast).toHaveTextContent('ok 10 · failed 2');
    expect(forecast).toHaveTextContent('14 Sep 2026, 23:30 IST');

    const observations = within(table).getByRole('rowheader', { name: 'observations' }).closest('tr') as HTMLElement;
    expect(observations).toHaveTextContent('not recorded');
    expect(details).toHaveTextContent('Job states across this read: ok 14 · failed 2');
    expect(details).toHaveTextContent('streams 7');
  });

  it('states a read with no product rows as no rows returned rather than a zero', async () => {
    server.use(
      http.get('/api/health', () =>
        HttpResponse.json({
          schema_version: 'source-health-v1',
          available: true,
          products: [],
          job_states: {},
          streams: 0,
          active_leases: 0,
          cooldowns: [],
          note: 'the store holds no product rows yet',
        }),
      ),
    );
    renderTopbar();
    await screen.findByText('Store healthy');

    const details = await openProducts();
    expect(within(details).queryByRole('table')).toBeNull();
    expect(details).toHaveTextContent('This read returned no per-product rows.');
    expect(details).toHaveTextContent('the store holds no product rows yet');
    expect(within(details).queryByText('0')).toBeNull();
  });

  it('keeps the unreachable-store chip and shows no product rows when the health read fails', async () => {
    server.use(
      http.get('/api/health', () =>
        HttpResponse.json({ error: 'the local evidence store is unavailable' }, { status: 503 }),
      ),
    );
    renderTopbar();
    expect(await screen.findByText('Store unreachable')).toBeInTheDocument();
    expect(screen.queryByTestId('health-products')).toBeNull();
  });
});
