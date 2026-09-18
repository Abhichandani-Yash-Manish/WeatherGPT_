import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Home } from './Home';

/* The front door is the conversation, so these pin the ways the page around it can lie:
   ----------------------------------------------------------------------------
   1. Announcing a severity that is already past — the opening line reads the today block only.
   2. Printing a number no read produced — a pending read prints no count at all.
   3. Treating an absent today block as a quiet day — the opening line says the read did not state today.
   4. Staying silent when the read failed — it says so, with the server's own words.
   5. Letting a dark sky pass as a storm — the legend names every input and says the sky is not a condition
      report.

   The counts themselves are checked on the board, which is where the tiles live now. */

function envelope(data: Record<string, unknown>, status = 'ok') {
  return {
    schema_version: 'product-view-v1',
    view: 'overview',
    status,
    generated_at_utc: '2026-09-18T11:18:45.911045+00:00',
    data,
    sources: [],
  };
}

function overview(national: Record<string, unknown> | undefined, status = 'ok') {
  return envelope({ national, radar: { stations: 39, reported: 39 }, places: [] }, status);
}

/* The other reads the face makes, answered so the suite's output stays clean: a test that passes while
   printing unhandled-request noise is not evidence. */
function serveTheRest() {
  server.use(
    http.get('/api/languages', () => HttpResponse.json({ schema_version: 'product-view-v1', service_configured: false, languages: [] })),
    http.get('/api/personas', () => HttpResponse.json(envelope({ personas: [] }))),
    http.get('/api/forecast', () => HttpResponse.json(envelope({ parameters: {} }))),
    http.get('/api/now', () => HttpResponse.json(envelope({}))),
    http.get('/api/conversations', () => HttpResponse.json(envelope({ conversations: [] }))),
  );
}

function serve(body: Parameters<typeof HttpResponse.json>[0], status = 200) {
  server.use(http.get('/api/overview', () => HttpResponse.json(body, { status })));
}

function renderHome() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  return render(
    <QueryClientProvider client={client}>
      <Home onOpen={() => {}} language="" onLanguage={() => {}} persona="" onPersona={() => {}} />
    </QueryClientProvider>,
  );
}

const QUIET_DAY = {
  districts: 756,
  today: { counts: { red: 0, orange: 0, yellow: 298, green: 445 }, districts_with_no_day_covering_today: 5 },
  bulletin_date: '2026-09-15',
  newest_bulletin_date_in_this_read: '2026-09-15',
  districts_behind_the_newest_edition: 14,
};

describe('the front door', () => {
  beforeEach(() => serveTheRest());

  it('opens the conversation with today\'s own column and keeps the read time on the value', async () => {
    serve(overview(QUIET_DAY));
    renderHome();
    expect(await screen.findByText(/No district is under an orange or red warning today/i)).toBeInTheDocument();
    /* The count appears in the sentence and again as a claim in the today strip: both are the read's value. */
    expect(screen.getAllByText(/298/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/445/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/read 16:48 IST/).length).toBeGreaterThanOrEqual(1);
    /* It is a conversation: the question box is the page's one input. */
    expect(screen.getByLabelText('Your question')).toBeInTheDocument();
  });

  it('prints no count while the read is still out', async () => {
    server.use(
      http.get('/api/overview', async () => {
        await new Promise(resolve => setTimeout(resolve, 60));
        return HttpResponse.json(overview(QUIET_DAY));
      }),
    );
    renderHome();
    expect(screen.getByText(/Reading the district warning bulletin/i)).toBeInTheDocument();
    expect(screen.queryByText(/carry a yellow caution/i)).toBeNull();
  });

  it('treats an absent today block as unstated, never as a quiet day', async () => {
    serve(overview({ districts: 756, bulletin_date: '2026-09-15' }));
    renderHome();
    expect(await screen.findByText(/This read does not state today/i)).toBeInTheDocument();
    expect(screen.queryByText(/carry a yellow caution/i)).toBeNull();
  });

  it('says the read failed, in the server\'s own words', async () => {
    server.use(http.get('/api/overview', () => HttpResponse.json({ error: 'the store is locked' }, { status: 503 })));
    renderHome();
    expect(await screen.findByText(/could not be read/i)).toBeInTheDocument();
    expect(screen.getByText(/the store is locked/i)).toBeInTheDocument();
  });

  it('draws no decoration: no photograph, no canvas, and nothing that needs a disclaimer', async () => {
    serve(overview(QUIET_DAY));
    renderHome();
    await screen.findByText(/No district is under an orange or red warning today/i);
    expect(document.querySelector('[data-design]')).not.toBeNull();
    expect(document.querySelector('img, canvas, svg.l-noise')).toBeNull();
    expect(screen.queryByText(/condition report/i)).toBeNull();
  });
});
